import pandas as pd
import numpy as np
import datetime
import backtrader as bt
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import io
import os
import json
import uuid
import traceback
from ..utils.data_loader import DataLoader, WeightingMethod
from ..utils.db_manager import DBManager
from .observers import PortfolioObserver


class FactorStrategyData(bt.feeds.PandasData):
    """Custom data feed for factor data"""
    lines = ('factor',)
    params = (('factor', -1),)


class FactorStrategy(bt.Strategy):
    """Backtrader strategy implementation for factor-based strategies"""
    
    params = (
        ('user_strategy', None),  # User strategy instance
        ('rebalance_period', 1),  # days
        ('take_profit_pct', None),
        ('stop_loss_pct', None),
        ('cooldown_period', 0),
    )
    
    def __init__(self):
        self.strategy = self.params.user_strategy
        self.rebalance_period = self.params.rebalance_period
        
        # Configure strategy with risk parameters
        if self.strategy:
            self.strategy.take_profit_pct = self.params.take_profit_pct
            self.strategy.stop_loss_pct = self.params.stop_loss_pct
            self.strategy.cooldown_period = self.params.cooldown_period
        
        # Track positions and entry prices
        self.position_tracker = {}  # Track positions
        self.entry_prices = {}
        self.last_rebalance_date = None
        self.days_since_rebalance = 0
        
        # Lists to store orders and trades
        self.order_list = []
        self.trade_list = []
        
    def next(self):
        current_date = self.datas[0].datetime.date()
        
        # Initialize positions dict if first run
        if not self.position_tracker:
            self.position_tracker = {d._name: 0 for d in self.datas}
            
        # Update current positions
        for data in self.datas:
            symbol = data._name
            position = self.getposition(data).size
            self.position_tracker[symbol] = position
            
            # Track entry prices for new positions
            if position != 0 and symbol not in self.entry_prices:
                self.entry_prices[symbol] = data.close[0]
        
        # Apply risk management (stop-loss/take-profit)
        current_prices = {d._name: d.close[0] for d in self.datas}
        self.position_tracker = self.strategy.apply_risk_management(
            self.position_tracker, current_prices, self.entry_prices, current_date
        )
        
        # Execute orders from risk management
        for data in self.datas:
            symbol = data._name
            current_position = self.getposition(data).size
            target_position = self.position_tracker[symbol]
            
            if current_position != target_position:
                self.order_target_size(data, target_position)
                # Reset entry price if position closed
                if target_position == 0:
                    if symbol in self.entry_prices:
                        del self.entry_prices[symbol]
        
        # Check if rebalance is needed
        self.days_since_rebalance += 1
        if self.days_since_rebalance >= self.rebalance_period:
            self.rebalance(current_date)
            self.days_since_rebalance = 0
            self.last_rebalance_date = current_date
    
    def rebalance(self, date):
        """Rebalance the portfolio based on factor signals"""
        # Prepare factor data for the current date
        factors_data = {}
        for data in self.datas:
            symbol = data._name
            if hasattr(data.lines, 'factor'):
                factors_data[symbol] = data.factor[0]
        
        factors_df = pd.DataFrame({
            'symbol': list(factors_data.keys()),
            'combined_factor': list(factors_data.values())
        })
        factors_df.index = [date] * len(factors_df)
        
        # Generate signals
        signals = self.strategy.generate_signals(None, factors_df, date)
        
        if signals.empty:
            return
            
        # Get current prices
        prices = {d._name: d.close[0] for d in self.datas}
        
        # Get current cash balance from broker
        current_cash = self.broker.get_cash()
        
        # Rebalance portfolio with current cash information
        new_positions = self.strategy.rebalance(self.position_tracker, signals, prices, date, cash=current_cash)
        
        # Execute orders
        for data in self.datas:
            symbol = data._name
            current_position = self.getposition(data).size
            target_position = new_positions.get(symbol, 0)
            
            if current_position != target_position:
                self.order_target_size(data, target_position)
                
                # Update entry price for new positions
                if target_position != 0 and (symbol not in self.entry_prices or current_position == 0):
                    self.entry_prices[symbol] = data.close[0]
    
    def notify_order(self, order):
        """Called when order status changes"""
        # Get data source related to this order
        data = order.data
        
        if order.status == order.Submitted:
            # Order submitted/created
            order_info = {
                'date': bt.num2date(data.datetime[0]),
                'symbol': data._name,
                'order_type': 'BUY' if order.isbuy() else 'SELL',
                'order_price': order.created.price if hasattr(order.created, 'price') else data.close[0],
                'order_size': order.created.size if hasattr(order.created, 'size') else order.size,
                'order_value': (order.created.price if hasattr(order.created, 'price') else data.close[0]) * 
                              (order.created.size if hasattr(order.created, 'size') else order.size),
                'execution_status': 'PENDING',
                'reason': getattr(order, 'reason', '')
            }
            self.order_list.append(order_info)
            print(f"Order created: {order_info['symbol']} {order_info['order_type']} {order_info['order_size']} @ {order_info['order_price']}")
            
        elif order.status == order.Completed:
            # Order executed
            # Find matching pending orders
            matching_orders = [o for o in self.order_list 
                              if o['symbol'] == data._name 
                              and o['order_type'] == ('BUY' if order.isbuy() else 'SELL')
                              and o['execution_status'] == 'PENDING']
            
            if matching_orders:
                # Update the most recent matching order
                order_info = matching_orders[-1]
                order_info['execution_status'] = 'EXECUTED'
                order_info['execution_price'] = order.executed.price
                print(f"Order executed: {order_info['symbol']} {order_info['order_type']} {order_info['order_size']} @ {order_info['execution_price']}")
            else:
                # If no matching pending order found, create a new executed order record
                order_info = {
                    'date': bt.num2date(data.datetime[0]),
                    'symbol': data._name,
                    'order_type': 'BUY' if order.isbuy() else 'SELL',
                    'order_price': order.executed.price,
                    'order_size': order.executed.size,
                    'order_value': order.executed.price * order.executed.size,
                    'execution_status': 'EXECUTED',
                    'execution_price': order.executed.price,
                    'reason': getattr(order, 'reason', '')
                }
                self.order_list.append(order_info)
                print(f"Direct execution: {order_info['symbol']} {order_info['order_type']} {order_info['order_size']} @ {order_info['execution_price']}")
    
    def notify_trade(self, trade):
        """Called when a trade is completed"""
        # Get data source related to this trade
        data = trade.data
        symbol = data._name
        
        # Get trade reference ID
        trade_ref = getattr(trade, 'ref', None)
        
        # Find existing trade for this reference
        existing_trade = None
        if trade_ref is not None:
            for t in self.trade_list:
                if t.get('trade_ref') == trade_ref:
                    existing_trade = t
                    break
        
        current_date = bt.num2date(data.datetime[0])
        
        if trade.justopened:
            # New trade opened
            trade_entry = {
                'entry_date': current_date,
                'symbol': symbol,
                'entry_price': trade.price,
                'entry_size': trade.size,
                'entry_value': trade.price * abs(trade.size),
                'status': 'OPEN',
                'trade_ref': trade_ref,
                'buys': [(trade.size, trade.price)] if trade.size > 0 else [],
                'sells': [(abs(trade.size), trade.price)] if trade.size < 0 else []
            }
            self.trade_list.append(trade_entry)
            print(f"Trade opened: {symbol} size={trade.size} price={trade.price} ref={trade_ref}")
        
        elif not trade.isclosed and existing_trade is not None:
            # Position increase for existing trade
            if trade.size > 0:  # Buy
                existing_trade['buys'].append((trade.size, trade.price))
            else:  # Sell
                existing_trade['sells'].append((abs(trade.size), trade.price))

            # Update entry information with weighted average
            if (trade.size > 0 and existing_trade.get('entry_size', 0) >= 0) or \
               (trade.size < 0 and existing_trade.get('entry_size', 0) <= 0):
                # For long positions, update with buys
                # For short positions, update with sells
                if trade.size > 0:  # Long position
                    total_buy_size = sum(size for size, _ in existing_trade['buys'])
                    total_buy_value = sum(size * price for size, price in existing_trade['buys'])
                    
                    existing_trade['entry_size'] = total_buy_size
                    existing_trade['entry_value'] = total_buy_value
                    existing_trade['entry_price'] = total_buy_value / total_buy_size if total_buy_size > 0 else 0
                else:  # Short position
                    total_sell_size = sum(size for size, _ in existing_trade['sells'])
                    total_sell_value = sum(size * price for size, price in existing_trade['sells'])
                    
                    existing_trade['entry_size'] = -total_sell_size  # Negative for short positions
                    existing_trade['entry_value'] = total_sell_value
                    existing_trade['entry_price'] = total_sell_value / total_sell_size if total_sell_size > 0 else 0

            print(f"Position updated: {symbol} added size={trade.size} price={trade.price} ref={trade_ref}")
        
        elif trade.isclosed:
            # Trade is being closed
            if existing_trade is None and trade_ref is not None:
                # Try to find by reference again
                for t in self.trade_list:
                    if t.get('trade_ref') == trade_ref:
                        existing_trade = t
                        break
            
            # If still not found, use fallback matching
            if existing_trade is None:
                # Try to match by symbol and size
                for t in self.trade_list:
                    if t['symbol'] == symbol and t['status'] == 'OPEN' and abs(t['entry_size']) == abs(trade.size):
                        existing_trade = t
                        break
                
                # If still no match, use FIFO
                if existing_trade is None:
                    open_trades = [t for t in self.trade_list if t['symbol'] == symbol and t['status'] == 'OPEN']
                    if open_trades:
                        existing_trade = open_trades[0]
            
            if existing_trade:
                # Update the trade with exit information
                existing_trade['status'] = 'CLOSED'
                existing_trade['exit_date'] = current_date
                
                # Calculate weighted average exit price from trade history
                if hasattr(trade, 'history') and len(trade.history) > 0:
                    total_exit_value = 0
                    total_exit_size = 0
                    
                    # Determine if this is a long or short position
                    is_long_position = existing_trade.get('entry_size', 0) > 0
                    
                    # Process all history events
                    for h in trade.history:
                        event_price = h.event.price
                        event_size = abs(h.event.size)
                        event_is_buy = h.event.size > 0
                        
                        # For long positions, sells are exits
                        # For short positions, buys are exits
                        is_exit_event = (is_long_position and not event_is_buy) or (not is_long_position and event_is_buy)
                        
                        if is_exit_event:
                            total_exit_value += event_price * event_size
                            total_exit_size += event_size
                    
                    if total_exit_size > 0:
                        existing_trade['exit_price'] = total_exit_value / total_exit_size
                        existing_trade['exit_size'] = total_exit_size
                        existing_trade['exit_value'] = total_exit_value
                    else:
                        existing_trade['exit_price'] = trade.price
                        existing_trade['exit_size'] = abs(trade.size)
                        existing_trade['exit_value'] = trade.price * abs(trade.size)
                else:
                    # No history available, use current trade info
                    existing_trade['exit_price'] = trade.price
                    existing_trade['exit_size'] = abs(trade.size)
                    existing_trade['exit_value'] = trade.price * abs(trade.size)
                
                # Set P&L information
                existing_trade['pnl'] = trade.pnlcomm
                existing_trade['pnl_pct'] = (trade.pnlcomm / existing_trade['entry_value']) * 100 if existing_trade['entry_value'] != 0 else 0
                existing_trade['exit_reason'] = getattr(trade, 'reason', 'REBALANCE')
                
                print(f"Trade closed: {symbol} pnl={existing_trade['pnl']:.2f} ({existing_trade['pnl_pct']:.2f}%) ref={trade_ref}")
            else:
                print(f"Warning: Could not find matching open trade for {symbol} ref={trade_ref}")


class BacktestEngine:
    """Engine for running backtests"""
    
    def __init__(self, 
                 strategy_class,
                 db_host, db_port, db_user, db_password, db_database,
                 start_date, 
                 end_date, 
                 initial_capital=100000,
                 rebalance_period=1,
                 take_profit_pct=None,
                 stop_loss_pct=None,
                 cooldown_period=0,
                 factors=None,
                 weighting_method=WeightingMethod.RSQUARED,
                 commission_pct=0.08):
        """
        Initialize the backtest engine.
        
        Args:
            strategy_class: Strategy class to backtest.
            start_date (datetime.date): Start date for backtest.
            end_date (datetime.date): End date for backtest.
            initial_capital (float): Initial capital for backtest.
            rebalance_period (int): Number of days between rebalances.
            take_profit_pct (float, optional): Take profit percentage threshold.
            stop_loss_pct (float, optional): Stop loss percentage threshold.
            cooldown_period (int, optional): Number of days to wait before re-entering 
                                            a position after take-profit or stop-loss.
            factors (list, optional): List of factor names to use (default: ['DebtToEquity', 'NewsSentiment']).
            weighting_method (WeightingMethod, optional): Method to weight factors (default: RSQUARED).
            commission_pct (float, optional): Commission percentage for trades (default: 0.08%).
        """
        self.strategy_class = strategy_class
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.rebalance_period = rebalance_period
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.cooldown_period = cooldown_period
        self.factors = factors if factors is not None else ['DebtToEquity', 'NewsSentiment']
        self.weighting_method = weighting_method
        self.commission_pct = commission_pct
        self.data_loader = DataLoader(db_host, db_port, db_user, db_password, db_database)
        self.db_manager = DBManager(db_host, db_port, db_user, db_password, db_database)
        
        # For tracking orders and trades
        self.orders = []
        self.trades = []
        self.portfolio_snapshots = []
        
    def run(self, strategy_params=None):
        """
        Run the backtest.
        
        Args:
            strategy_params (dict, optional): Parameters for the strategy.
            
        Returns:
            dict: Backtest results.
        """
        if strategy_params is None:
            strategy_params = {}
            
        # Initialize Backtrader cerebro
        cerebro = bt.Cerebro(tradehistory=True)
        cerebro.broker.setcash(self.initial_capital)
        
        # Set commission scheme (percentage-based)
        cerebro.broker.setcommission(commission=self.commission_pct/100.0)  # Convert percentage to decimal
        
        # Load price and factor data
        data = self.data_loader.load_data(
            self.start_date, 
            self.end_date,
            factors=self.factors,
            weighting_method=self.weighting_method
        )

        print("finished data_loader.load_data")
        
        # Add data feeds to cerebro
        for symbol, df in data['price_data'].items():
            if symbol in data['factor_data']:
                # Combine price and factor data
                combined_df = df.copy()
                combined_df['factor'] = data['factor_data'][symbol]
                
                # Create data feed
                data_feed = FactorStrategyData(
                    dataname=combined_df,
                    name=symbol,
                    fromdate=self.start_date,
                    todate=self.end_date,
                    factor='factor'
                )
                cerebro.adddata(data_feed)
        
        # Create strategy instance
        strategy_instance = self.strategy_class(**strategy_params)
        
        # Add strategy to cerebro
        cerebro.addstrategy(
            FactorStrategy,
            user_strategy=strategy_instance,  # 使用新的参数名
            rebalance_period=self.rebalance_period,
            take_profit_pct=self.take_profit_pct,
            stop_loss_pct=self.stop_loss_pct,
            cooldown_period=self.cooldown_period
        )
        
        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # Add observers for tracking portfolio
        cerebro.addobserver(PortfolioObserver)
        
        # Run backtest
        results = cerebro.run()
        strat = results[0]
        
        # Extract metrics
        metrics = {
            'sharpe_ratio': strat.analyzers.sharpe.get_analysis()['sharperatio'],
            'max_drawdown': strat.analyzers.drawdown.get_analysis()['max']['drawdown'],
            'total_return': strat.analyzers.returns.get_analysis()['rtot'],
            'annual_return': strat.analyzers.returns.get_analysis()['rnorm'],
            'num_trades': strat.analyzers.trades.get_analysis().get('total', {}).get('total', 0),
            'win_rate': self._calculate_win_rate(strat.analyzers.trades.get_analysis()),
            'profit_factor': self._calculate_profit_factor(strat.analyzers.trades.get_analysis()),
            'final_value': cerebro.broker.getvalue(),
        }
        
        # Extract orders and trades from strategy
        orders = strat.order_list if hasattr(strat, 'order_list') else []
        
        # Get trades and filter out incomplete ones
        all_trades = strat.trade_list if hasattr(strat, 'trade_list') else []
        trades = []
        for trade in all_trades:
            if trade.get('status') == 'CLOSED':
                # Make sure all required fields exist
                if 'exit_date' not in trade or 'exit_price' not in trade or 'exit_size' not in trade:
                    print(f"Warning: Incomplete trade data for {trade.get('symbol')}: {trade}")
                    # Add missing fields with default values
                    if 'exit_date' not in trade:
                        trade['exit_date'] = trade.get('entry_date')
                    if 'exit_price' not in trade:
                        trade['exit_price'] = trade.get('entry_price', 0.0)
                    if 'exit_size' not in trade:
                        trade['exit_size'] = 0
                    if 'exit_value' not in trade:
                        trade['exit_value'] = trade.get('exit_price', 0.0) * trade.get('exit_size', 0)
                    if 'pnl' not in trade:
                        trade['pnl'] = 0.0
                    if 'pnl_pct' not in trade:
                        trade['pnl_pct'] = 0.0
                    if 'exit_reason' not in trade:
                        trade['exit_reason'] = 'UNKNOWN'
                trades.append(trade)
        
        print(f"Found {len(orders)} orders in strategy")
        print(f"Found {len(trades)} completed trades in strategy (from {len(all_trades)} total)")
        
        # Extract portfolio snapshots from observer
        portfolio_snapshots = []
        for observer in strat.getobservers():
            if isinstance(observer, PortfolioObserver):
                portfolio_snapshots = observer.portfolio_snapshots
                print(f"Found PortfolioObserver with {len(portfolio_snapshots)} snapshots")
        
        # Save backtest results to database
        self._save_backtest_to_db(strategy_instance, metrics, orders, trades, portfolio_snapshots, strategy_params)

        return {
            'metrics': metrics,
            'parameters': {
                'strategy': strategy_instance.__class__.__name__,
                'strategy_params': strategy_params,
                'start_date': self.start_date.strftime('%Y-%m-%d'),
                'end_date': self.end_date.strftime('%Y-%m-%d'),
                'initial_capital': self.initial_capital,
                'rebalance_period': self.rebalance_period,
                'take_profit_pct': self.take_profit_pct,
                'stop_loss_pct': self.stop_loss_pct,
                'cooldown_period': self.cooldown_period,
                'commission_pct': self.commission_pct,
                'factors': self.factors,
                'weighting_method': self.weighting_method.name
            }
        }
    
    def _calculate_win_rate(self, trade_analysis):
        """Calculate win rate from trade analysis"""
        if not trade_analysis or 'won' not in trade_analysis or 'total' not in trade_analysis:
            return 0.0
            
        total_trades = trade_analysis['total']['total']
        if total_trades == 0:
            return 0.0
            
        won_trades = trade_analysis['won']['total']
        return won_trades / total_trades
    
    def _calculate_profit_factor(self, trade_analysis):
        """Calculate profit factor from trade analysis"""
        if not trade_analysis:
            return 0.0
            
        won_total = trade_analysis.get('won', {}).get('pnl', {}).get('total', 0)
        lost_total = abs(trade_analysis.get('lost', {}).get('pnl', {}).get('total', 0))
        
        if lost_total == 0:
            return float('inf') if won_total > 0 else 0.0
            
        return won_total / lost_total
    
    def _generate_plot(self, cerebro):
        """Generate plot of backtest results"""
        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        
        # Plot equity curve
        cerebro.plot(style='candlestick', barup='green', bardown='red', 
                    volup='green', voldown='red', plotdist=1, 
                    start=self.start_date, end=self.end_date,
                    use=ax)
        
        return fig
        
    def _save_backtest_to_db(self, strategy_instance, metrics, orders, trades, portfolio_snapshots, strategy_params):
        """
        Save backtest results to the database.
        
        Args:
            strategy_instance: Strategy instance.
            metrics (dict): Performance metrics.
            orders (list): List of orders.
            trades (list): List of trades.
            portfolio_snapshots (list): List of portfolio snapshots.
            strategy_params (dict): Strategy parameters.
        """
        try:
            print(f"Orders to save: {len(orders)}")
            print(f"Trades to save: {len(trades)}")
            print(f"Portfolio snapshots to save: {len(portfolio_snapshots)}")
            
            # Save strategy if it doesn't exist
            strategy_name = strategy_instance.__class__.__name__
            strategy_class = strategy_instance.__class__.__module__ + '.' + strategy_name
            strategy_description = strategy_instance.__class__.__doc__ or ""
            
            # Check if strategy exists with same class, parameters, and creator
            strategy_id = None
            strategy_params_json = json.dumps(strategy_params)
            current_user = os.getenv('USER', 'unknown')
            
            strategies = self.db_manager.client.execute(
                """
                SELECT strategy_id FROM strategy_definitions 
                WHERE strategy_class = %(strategy_class)s 
                AND strategy_parameters = %(strategy_parameters)s
                AND created_by = %(created_by)s
                """,
                {
                    'strategy_class': strategy_class,
                    'strategy_parameters': strategy_params_json,
                    'created_by': current_user
                }
            )
            
            if strategies:
                strategy_id = strategies[0][0]
                print(f"Found existing strategy with ID: {strategy_id}")
            else:
                strategy_id = self.db_manager.save_strategy(
                    strategy_name=strategy_name,
                    strategy_class=strategy_class,
                    strategy_description=strategy_description,
                    strategy_parameters=strategy_params,
                    created_by=current_user
                )
                print(f"Created new strategy with ID: {strategy_id}")
            
            # Save backtest
            backtest_id = self.db_manager.save_backtest(
                strategy_id=strategy_id,
                start_date=self.start_date,
                end_date=self.end_date,
                initial_capital=self.initial_capital,
                final_capital=metrics['final_value'],
                rebalance_period=self.rebalance_period,
                take_profit_pct=self.take_profit_pct,
                stop_loss_pct=self.stop_loss_pct,
                cooldown_period=self.cooldown_period,
                max_position_size=strategy_params.get('max_position_size', 0.05),
                factors=self.factors,
                weighting_method=self.weighting_method.name,
                metrics=metrics,
                strategy_parameters=strategy_params,
                run_by=os.getenv('USER', 'unknown')
            )
            
            # Save portfolio snapshots in batch
            print(f"Saving {len(portfolio_snapshots)} portfolio snapshots in batch...")
            self.db_manager.save_portfolio_snapshots_batch(backtest_id, portfolio_snapshots)
            
            # Save orders in batch
            print(f"Saving {len(orders)} orders in batch...")
            self.db_manager.save_orders_batch(backtest_id, orders)
            
            # Prepare trades for batch saving
            print(f"Saving {len(trades)} trades in batch...")
            # Ensure all trades have required fields with default values
            processed_trades = []
            for trade in trades:
                trade_data = {
                    'symbol': trade.get('symbol', 'UNKNOWN'),
                    'entry_date': trade.get('entry_date'),
                    'entry_price': trade.get('entry_price', 0.0),
                    'entry_size': trade.get('entry_size', 0),
                    'entry_value': trade.get('entry_value', 0.0),
                    'exit_date': trade.get('exit_date', trade.get('entry_date')),  # Default to entry date if missing
                    'exit_price': trade.get('exit_price', trade.get('entry_price', 0.0)),  # Default to entry price if missing
                    'exit_size': trade.get('exit_size', 0),
                    'exit_value': trade.get('exit_value', 0.0),
                    'pnl': trade.get('pnl', 0.0),
                    'pnl_pct': trade.get('pnl_pct', 0.0),
                    'exit_reason': trade.get('exit_reason', 'UNKNOWN')
                }
                processed_trades.append(trade_data)
            
            # Save trades in batch
            try:
                self.db_manager.save_trades_batch(backtest_id, processed_trades)
            except Exception as e:
                print(f"Error saving trades batch: {e}")
                print(f"Will try to save trades individually...")
                
                # Fall back to individual trade saving if batch fails
                for trade_data in processed_trades:
                    try:
                        self.db_manager.save_trade(
                            backtest_id=backtest_id,
                            symbol=trade_data['symbol'],
                            entry_date=trade_data['entry_date'],
                            entry_price=trade_data['entry_price'],
                            entry_size=trade_data['entry_size'],
                            entry_value=trade_data['entry_value'],
                            exit_date=trade_data['exit_date'],
                            exit_price=trade_data['exit_price'],
                            exit_size=trade_data['exit_size'],
                            exit_value=trade_data['exit_value'],
                            pnl=trade_data['pnl'],
                            pnl_pct=trade_data['pnl_pct'],
                            exit_reason=trade_data['exit_reason']
                        )
                    except Exception as e2:
                        print(f"Error saving trade {trade_data['symbol']}: {e2}")
                        print(f"Trade data: {trade_data}")
                        # Continue with next trade instead of failing the entire process
            
            print(f"Backtest results saved to database with ID: {backtest_id}")
            return backtest_id
            
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error saving backtest results to database: {e}")
            print(f"Stack trace:\n{error_trace}")
            return None
