import backtrader as bt

class OrderObserver(bt.observer.Observer):
    """Observer for tracking orders - simplified version that only plots order events"""
    
    lines = ('order_created', 'order_executed')
    
    def __init__(self):
        self.orders = []
        
    def next(self):
        self.lines.order_created[0] = float('nan')
        self.lines.order_executed[0] = float('nan')


class TradeObserver(bt.observer.Observer):
    """Observer for tracking trades - simplified version that only plots trade events"""
    
    lines = ('trade_entry', 'trade_exit')
    
    def __init__(self):
        self.trades = []
        
    def next(self):
        self.lines.trade_entry[0] = float('nan')
        self.lines.trade_exit[0] = float('nan')


class PortfolioObserver(bt.observer.Observer):
    """Observer for tracking portfolio snapshots"""
    
    lines = ('portfolio_value',)
    
    def __init__(self):
        self.portfolio_snapshots = []
        self.last_snapshot_date = None
        
    def next(self):
        current_date = self.data.datetime.date()
        
        # Take snapshot on first day, last day, or when date changes
        if (self.last_snapshot_date is None or 
            current_date != self.last_snapshot_date or 
            len(self.data) == self.data.buflen() - 1):
            
            # Get portfolio details
            portfolio = self._owner.broker.getvalue()
            cash = self._owner.broker.getcash()
            equity = portfolio - cash
            
            # Get positions
            positions = {}
            for data in self._owner.datas:
                symbol = data._name
                position = self._owner.getposition(data)
                if position.size != 0:
                    positions[symbol] = {
                        'size': position.size,
                        'price': position.price,
                        'value': position.size * data.close[0]
                    }
            
            # Store snapshot
            snapshot = {
                'date': current_date,
                'portfolio_value': portfolio,
                'cash': cash,
                'equity': equity,
                'positions': positions,
                'is_initial': self.last_snapshot_date is None,
                'is_final': len(self.data) == self.data.buflen() - 1
            }
            self.portfolio_snapshots.append(snapshot)
            
            self.last_snapshot_date = current_date
        
        self.lines.portfolio_value[0] = self._owner.broker.getvalue()
