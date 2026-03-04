import os


class RQClient:
    def __init__(self, username: str = None, password: str = None, license_key: str = None):
        try:
            import rqdatac as rq  # 可选依赖
        except Exception as e:
            raise RuntimeError(f'rqdatac_not_installed: {e}')
        self.rq = rq

        # 兼容 License Key 模式（优先支持 RQSDK 授权）
        lk = (license_key or '').strip()
        if lk and not lk.startswith('your_'):
            # 不同版本 rqdatac 的接口可能不一致，尽量多路径兼容
            if hasattr(self.rq, 'set_license'):
                try:
                    self.rq.set_license(lk)
                except Exception:
                    pass
            os.environ.setdefault('RQ_LICENSE_KEY', lk)
            os.environ.setdefault('RQ_LICENSE', lk)
            os.environ.setdefault('RQDATAC_LICENSE', lk)

        u = None if not username or str(username).startswith('your_') else username
        p = None if not password or str(password).startswith('your_') else password

        # 有账号密码则走账号模式；否则走 rqdatac.init()（由 License 或本地配置驱动）
        if u and p:
            self.rq.init(u, p)
        else:
            self.rq.init()

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
