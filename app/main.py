from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import yaml
from pathlib import Path
from urllib import request, parse
import json

from data.rq_client import RQClient
from strategies.hc_fu_trend import signal
from engine.paper_executor import PaperExecutor

cfg = yaml.safe_load(Path('config/settings.yaml').read_text()) if Path('config/settings.yaml').exists() else yaml.safe_load(Path('config/settings.example.yaml').read_text())

rq_client = None
executor = PaperExecutor(initial_cash=float(cfg['engine']['initial_cash']), fee_rate=float(cfg['engine']['fee_rate']))

app = FastAPI(title='chinacnu 期货自主交易系统', version='0.2.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

class RunReq(BaseModel):
    symbol: str
    qty: int = 1

class OrderReq(BaseModel):
    symbol: str
    side: str  # BUY/SELL
    offset: str = 'OPEN'  # OPEN/CLOSE
    qty: int = 1
    price: float | None = None


def _trading_cfg():
    return cfg.get('trading_api', {})


def _api_headers():
    tcfg = _trading_cfg()
    token = tcfg.get('token', '')
    hname = tcfg.get('token_header', 'Authorization')
    prefix = tcfg.get('token_prefix', 'Bearer ')
    headers = {'Content-Type': 'application/json'}
    if token:
        headers[hname] = f'{prefix}{token}'
    return headers


def _api_url(path: str, query: dict | None = None):
    base_url = _trading_cfg().get('base_url', '').rstrip('/')
    p = path if path.startswith('/') else '/' + path
    url = f'{base_url}{p}'
    if query:
        url = f"{url}?{parse.urlencode(query)}"
    return url


def _symbol_alias(symbol: str):
    m = _trading_cfg().get('symbol_map', {})
    return m.get(symbol, symbol)


def _http_get(url: str):
    req = request.Request(url=url, headers=_api_headers(), method='GET')
    with request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _http_post(url: str, payload: dict):
    req = request.Request(url=url, headers=_api_headers(), method='POST', data=json.dumps(payload).encode('utf-8'))
    with request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))


@app.on_event('startup')
def startup_event():
    global rq_client
    try:
        rq_client = RQClient(cfg['rqdata']['username'], cfg['rqdata']['password'])
    except Exception:
        rq_client = None


@app.get('/health')
def health():
    tcfg = _trading_cfg()
    return {
        'ok': True,
        'rqdata_connected': rq_client is not None,
        'trading_api_enabled': bool(tcfg.get('enabled', False)),
        'trading_api_base': tcfg.get('base_url', ''),
    }


@app.get('/portfolio')
def portfolio():
    return {'cash': executor.cash, 'positions': executor.pos, 'logs': executor.logs[-20:]}


@app.post('/signal/run')
def run_signal(req: RunReq):
    if rq_client is None:
        return {'ok': False, 'error': 'rqdata_not_connected'}
    bars = rq_client.bars(req.symbol, count=300, freq='1m')
    sig = signal(bars)
    latest = rq_client.latest(req.symbol)

    trade = None
    if sig['action'] in ('BUY', 'SELL'):
        trade = executor.order(req.symbol, sig['action'], req.qty, latest['last'])

    return {
        'ok': True,
        'symbol': req.symbol,
        'latest': latest,
        'signal': sig,
        'trade': trade,
        'portfolio': {'cash': executor.cash, 'positions': executor.pos},
    }


@app.get('/api/market/realtime')
def api_market_realtime(symbol: str = 'HC'):
    tcfg = _trading_cfg()
    if not tcfg.get('enabled', False):
        return {'ok': False, 'error': 'trading_api_disabled'}

    url = _api_url(tcfg.get('realtime_path', '/market/realtime'), {'symbol': _symbol_alias(symbol)})
    try:
        data = _http_get(url)
        return {'ok': True, 'symbol': symbol, 'data': data}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@app.get('/api/market/kline')
def api_market_kline(symbol: str = 'HC', period: str = '1m', limit: int = 120):
    tcfg = _trading_cfg()
    if not tcfg.get('enabled', False):
        return {'ok': False, 'error': 'trading_api_disabled'}

    query = {'symbol': _symbol_alias(symbol), 'period': period, 'limit': limit}
    url = _api_url(tcfg.get('kline_path', '/market/kline'), query)
    try:
        data = _http_get(url)
        return {'ok': True, 'symbol': symbol, 'period': period, 'data': data}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@app.post('/api/order')
def api_order(req: OrderReq):
    tcfg = _trading_cfg()
    if not tcfg.get('enabled', False):
        return {'ok': False, 'error': 'trading_api_disabled'}

    payload = {
        'symbol': _symbol_alias(req.symbol),
        'side': req.side,
        'offset': req.offset,
        'qty': req.qty,
    }
    if req.price is not None:
        payload['price'] = req.price

    url = _api_url(tcfg.get('order_path', '/trade/order'))
    try:
        data = _http_post(url, payload)
        return {'ok': True, 'request': payload, 'data': data}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'request': payload}
