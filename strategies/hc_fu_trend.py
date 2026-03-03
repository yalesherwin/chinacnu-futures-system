def _to_close_list(data):
    # 兼容 list[dict] / pandas.DataFrame-like
    if hasattr(data, 'to_dict'):
        try:
            rows = data.to_dict('records')
            return [float(r.get('close', 0) or 0) for r in rows]
        except Exception:
            pass
    if isinstance(data, list):
        out = []
        for r in data:
            if isinstance(r, dict):
                out.append(float(r.get('close', 0) or 0))
            elif isinstance(r, (list, tuple)) and len(r) >= 5:
                out.append(float(r[4] or 0))
        return out
    return []


def ema(values, n: int):
    if not values:
        return []
    alpha = 2 / (n + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out


def signal(df_like):
    # 简单趋势策略：EMA20 上穿 EMA60 做多，下穿做空
    c = _to_close_list(df_like)
    if len(c) < 80:
        return {'action': 'HOLD', 'reason': 'not_enough_bars'}

    e20 = ema(c, 20)
    e60 = ema(c, 60)
    prev = e20[-2] - e60[-2]
    curr = e20[-1] - e60[-1]

    if prev <= 0 and curr > 0:
        return {'action': 'BUY', 'reason': 'ema_cross_up'}
    if prev >= 0 and curr < 0:
        return {'action': 'SELL', 'reason': 'ema_cross_down'}
    return {'action': 'HOLD', 'reason': 'no_cross'}
