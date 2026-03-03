from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import yaml
from pathlib import Path
from urllib import request, parse
import json
import os
from typing import Optional

from data.rq_client import RQClient
from strategies.hc_fu_trend import signal
from engine.paper_executor import PaperExecutor

cfg = yaml.safe_load(Path('config/settings.yaml').read_text()) if Path('config/settings.yaml').exists() else yaml.safe_load(Path('config/settings.example.yaml').read_text())

# 环境变量覆盖（部署到 Render 时使用）
if os.getenv('TRADING_API_BASE_URL'):
    cfg.setdefault('trading_api', {})['base_url'] = os.getenv('TRADING_API_BASE_URL')
if os.getenv('TRADING_API_TOKEN'):
    cfg.setdefault('trading_api', {})['token'] = os.getenv('TRADING_API_TOKEN')
if os.getenv('TRADING_API_REALTIME_PATH'):
    cfg.setdefault('trading_api', {})['realtime_path'] = os.getenv('TRADING_API_REALTIME_PATH')
if os.getenv('TRADING_API_KLINE_PATH'):
    cfg.setdefault('trading_api', {})['kline_path'] = os.getenv('TRADING_API_KLINE_PATH')
if os.getenv('TRADING_API_ORDER_PATH'):
    cfg.setdefault('trading_api', {})['order_path'] = os.getenv('TRADING_API_ORDER_PATH')
if os.getenv('TRADING_API_ENABLED'):
    cfg.setdefault('trading_api', {})['enabled'] = os.getenv('TRADING_API_ENABLED').lower() in ('1', 'true', 'yes', 'on')

rq_client = None
rq_startup_error = None
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
    price: Optional[float] = None


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


def _api_url(path: str, query: Optional[dict] = None):
    base_url = _trading_cfg().get('base_url', '').rstrip('/')
    p = path if path.startswith('/') else '/' + path
    url = f'{base_url}{p}'
    if query:
        url = f"{url}?{parse.urlencode(query)}"
    return url


def _use_external_api() -> bool:
    tcfg = _trading_cfg()
    return bool(tcfg.get('enabled', False) and str(tcfg.get('base_url', '')).strip())


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
    global rq_client, rq_startup_error
    try:
        rq_client = RQClient(cfg['rqdata']['username'], cfg['rqdata']['password'])
        rq_startup_error = None
    except Exception as e:
        rq_client = None
        rq_startup_error = str(e)


@app.get('/health')
def health():
    tcfg = _trading_cfg()
    return {
        'ok': True,
        'rqdata_connected': rq_client is not None,
        'trading_api_enabled': bool(tcfg.get('enabled', False)),
        'trading_api_base': tcfg.get('base_url', ''),
        'mode': 'external_api' if _use_external_api() else 'rqsdk',
        'rq_startup_error': rq_startup_error,
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
    if _use_external_api():
        url = _api_url(tcfg.get('realtime_path', '/market/realtime'), {'symbol': _symbol_alias(symbol)})
        try:
            data = _http_get(url)
            return {'ok': True, 'symbol': symbol, 'data': data, 'source': 'external_api'}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'source': 'external_api'}

    if rq_client is None:
        return {'ok': False, 'error': 'rqdata_not_connected'}
    try:
        data = rq_client.latest(_symbol_alias(symbol))
        return {'ok': True, 'symbol': symbol, 'data': data, 'source': 'rqdatac'}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'source': 'rqdatac'}


@app.get('/api/market/kline')
def api_market_kline(symbol: str = 'HC', period: str = '1m', limit: int = 120):
    tcfg = _trading_cfg()
    if _use_external_api():
        query = {'symbol': _symbol_alias(symbol), 'period': period, 'limit': limit}
        url = _api_url(tcfg.get('kline_path', '/market/kline'), query)
        try:
            data = _http_get(url)
            return {'ok': True, 'symbol': symbol, 'period': period, 'data': data, 'source': 'external_api'}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'source': 'external_api'}

    if rq_client is None:
        return {'ok': False, 'error': 'rqdata_not_connected'}
    try:
        bars = rq_client.bars(_symbol_alias(symbol), count=limit, freq=period)
        if hasattr(bars, 'to_dict'):
            bars = bars.to_dict('records')
        return {'ok': True, 'symbol': symbol, 'period': period, 'data': {'bars': bars}, 'source': 'rqdatac'}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'source': 'rqdatac'}


@app.post('/api/order')
def api_order(req: OrderReq):
    tcfg = _trading_cfg()
    payload = {
        'symbol': _symbol_alias(req.symbol),
        'side': req.side,
        'offset': req.offset,
        'qty': req.qty,
    }
    if req.price is not None:
        payload['price'] = req.price

    if _use_external_api():
        url = _api_url(tcfg.get('order_path', '/trade/order'))
        try:
            data = _http_post(url, payload)
            return {'ok': True, 'request': payload, 'data': data, 'source': 'external_api'}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'request': payload, 'source': 'external_api'}

    # RQData 仅行情，不提供下单；这里回退到本地 paper executor
    if rq_client is None:
        return {'ok': False, 'error': 'rqdata_not_connected', 'request': payload, 'source': 'paper'}
    try:
        latest = rq_client.latest(payload['symbol'])
        px = req.price if req.price is not None else float(latest.get('last') or 0)
        trade = executor.order(req.symbol, req.side, req.qty, px)
        return {'ok': True, 'request': payload, 'data': trade, 'source': 'paper'}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'request': payload, 'source': 'paper'}
