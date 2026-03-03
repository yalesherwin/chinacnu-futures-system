import rqdatac as rq
import pandas as pd

class RQClient:
    def __init__(self, username: str, password: str):
        rq.init(username, password)

    def bars(self, symbol: str, count: int = 300, freq: str = '1m') -> pd.DataFrame:
        df = rq.get_price(symbol, frequency=freq, fields=['open','high','low','close','volume'], adjust_type='none', count=count)
        return df.reset_index()

    def latest(self, symbol: str):
        snap = rq.current_snapshot(symbol)
        return {
            'symbol': symbol,
            'last': float(getattr(snap, 'last', 0.0) or 0.0),
            'open': float(getattr(snap, 'open', 0.0) or 0.0),
            'high': float(getattr(snap, 'high', 0.0) or 0.0),
            'low': float(getattr(snap, 'low', 0.0) or 0.0),
            'volume': float(getattr(snap, 'volume', 0.0) or 0.0),
        }
