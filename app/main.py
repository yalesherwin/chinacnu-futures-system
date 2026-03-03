from fastapi import FastAPI
from pydantic import BaseModel
import yaml
from pathlib import Path

from data.rq_client import RQClient
from strategies.hc_fu_trend import signal
from engine.paper_executor import PaperExecutor

cfg = yaml.safe_load(Path('config/settings.yaml').read_text()) if Path('config/settings.yaml').exists() else yaml.safe_load(Path('config/settings.example.yaml').read_text())

rq_client = None
executor = PaperExecutor(initial_cash=float(cfg['engine']['initial_cash']), fee_rate=float(cfg['engine']['fee_rate']))

app = FastAPI(title='chinacnu 期货自主交易系统', version='0.1.0')

class RunReq(BaseModel):
    symbol: str
    qty: int = 1

@app.on_event('startup')
def startup_event():
    global rq_client
    try:
        rq_client = RQClient(cfg['rqdata']['username'], cfg['rqdata']['password'])
    except Exception:
        rq_client = None

@app.get('/health')
def health():
    return {'ok': True, 'rqdata_connected': rq_client is not None}

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
    if sig['action'] in ('BUY','SELL'):
        trade = executor.order(req.symbol, sig['action'], req.qty, latest['last'])

    return {
        'ok': True,
        'symbol': req.symbol,
        'latest': latest,
        'signal': sig,
        'trade': trade,
        'portfolio': {'cash': executor.cash, 'positions': executor.pos}
    }
