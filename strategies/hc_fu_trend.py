import pandas as pd

def ema(s: pd.Series, n: int):
    return s.ewm(span=n, adjust=False).mean()

def signal(df: pd.DataFrame):
    # 简单趋势策略：EMA20 上穿 EMA60 做多，下穿做空
    c = df['close'].astype(float)
    e20 = ema(c, 20)
    e60 = ema(c, 60)
    if len(df) < 80:
        return {'action': 'HOLD', 'reason': 'not_enough_bars'}
    prev = e20.iloc[-2] - e60.iloc[-2]
    curr = e20.iloc[-1] - e60.iloc[-1]
    if prev <= 0 and curr > 0:
        return {'action': 'BUY', 'reason': 'ema_cross_up'}
    if prev >= 0 and curr < 0:
        return {'action': 'SELL', 'reason': 'ema_cross_down'}
    return {'action': 'HOLD', 'reason': 'no_cross'}
