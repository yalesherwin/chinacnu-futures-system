class RQClient:
    def __init__(self, username: str = None, password: str = None):
        try:
            import rqdatac as rq  # 可选依赖
        except Exception as e:
            raise RuntimeError(f'rqdatac_not_installed: {e}')
        self.rq = rq
        u = None if not username or str(username).startswith('your_') else username
        p = None if not password or str(password).startswith('your_') else password
        self.rq.init(u, p)

    def bars(self, symbol: str, count: int = 300, freq: str = '1m'):
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
