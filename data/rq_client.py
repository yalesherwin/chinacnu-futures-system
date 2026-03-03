import pandas as pd

class RQClient:
    def __init__(self, username: str, password: str):
        try:
            import rqdatac as rq  # 可选依赖
        except Exception as e:
            raise RuntimeError(f'rqdatac_not_installed: {e}')
        self.rq = rq
        self.rq.init(username, password)

    def bars(self, symbol: str, count: int = 300, freq: str = '1m') -> pd.DataFrame:
        df = self.rq.get_price(symbol, frequency=freq, fields=['open','high','low','close','volume'], adjust_type='none', count=count)
        return df.reset_index()

    def latest(self, symbol: str):
        snap = self.rq.current_snapshot(symbol)
        return {
            'symbol': symbol,
            'last': float(getattr(snap, 'last', 0.0) or 0.0),
            'open': float(getattr(snap, 'open', 0.0) or 0.0),
            'high': float(getattr(snap, 'high', 0.0) or 0.0),
            'low': float(getattr(snap, 'low', 0.0) or 0.0),
            'volume': float(getattr(snap, 'volume', 0.0) or 0.0),
        }
