class PaperExecutor:
    def __init__(self, initial_cash: float, fee_rate: float = 0.0002):
        self.cash = initial_cash
        self.fee_rate = fee_rate
        self.pos = {}
        self.logs = []

    def order(self, symbol: str, side: str, qty: int, price: float):
        cost = qty * price
        fee = cost * self.fee_rate
        if side == 'BUY':
            self.cash -= (cost + fee)
            self.pos[symbol] = self.pos.get(symbol, 0) + qty
        elif side == 'SELL':
            self.cash += (cost - fee)
            self.pos[symbol] = self.pos.get(symbol, 0) - qty
        self.logs.append({'symbol': symbol, 'side': side, 'qty': qty, 'price': price, 'fee': fee, 'cash': self.cash})
        return self.logs[-1]
