"""
Backtest Agent - Executes backtests using generated strategies
"""

import backtrader as bt
import pandas as pd
from io import StringIO
from .base_agent import BaseAgent
from typing import Dict, Any

class BacktestAgent(BaseAgent):
    """Agent that executes backtests using Backtrader"""
    
    def __init__(self):
        super().__init__("Backtest")
        self.default_params = {
            'initial_cash': 100000,
            'commission': 0.001,
            'start_date': None,
            'end_date': None
        }
    
    def run_backtest(self, strategy_code: str, market_data: Dict[str, pd.DataFrame], 
                    params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run backtest with given strategy and data"""
        if params is None:
            params = self.default_params.copy()
        
        try:
            # Execute strategy code to get strategy class
            exec_globals = {'bt': bt, 'btind': bt.indicators}
            exec(strategy_code, exec_globals)
            
            # Find the strategy class
            strategy_class = None
            for name, obj in exec_globals.items():
                if (isinstance(obj, type) and 
                    issubclass(obj, bt.Strategy) and 
                    obj != bt.Strategy):
                    strategy_class = obj
                    break
            
            if not strategy_class:
                return {'error': 'No valid strategy class found'}
            
            # Use first available symbol for demo
            symbol = list(market_data.keys())[0]
            data = market_data[symbol]
            
            print(f"🔍 Debug - symbol: {symbol}, data type: {type(data)}")
            if hasattr(data, 'columns'):
                print(f"🔍 Debug - data columns: {list(data.columns)}")
            else:
                print(f"🔍 Debug - data content: {data}")
            
            # Convert to DataFrame if it's a list
            if isinstance(data, list):
                print("⚠️ Converting list to DataFrame")
                data = pd.DataFrame(data)
            
            # Ensure proper datetime index for Backtrader
            if not isinstance(data.index, pd.DatetimeIndex):
                if 'date' in data.columns:
                    data['date'] = pd.to_datetime(data['date'])
                    data.set_index('date', inplace=True)
                else:
                    print("⚠️ No Date column found, using default index")
                    data.index = pd.date_range(start='2022-01-01', periods=len(data), freq='D')
            
            # Create Cerebro engine
            cerebro = bt.Cerebro()
            cerebro.addstrategy(strategy_class)
            
            # Add data
            bt_data = bt.feeds.PandasData(dataname=data)
            cerebro.adddata(bt_data)
            
            # Set parameters
            cerebro.broker.setcash(params.get('initial_cash', 100000))
            cerebro.broker.setcommission(commission=params.get('commission', 0.001))
            
            # Add analyzers
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            
            # Run backtest
            initial_value = cerebro.broker.getvalue()
            results = cerebro.run()
            final_value = cerebro.broker.getvalue()
            
            # Extract results
            strat = results[0]
            
            return {
                'initial_value': initial_value,
                'final_value': final_value,
                'total_return': (final_value - initial_value) / initial_value * 100,
                'metrics': {
                    'Sharpe Ratio': getattr(strat.analyzers.sharpe.get_analysis(), 'sharperatio', 'N/A'),
                    'Max Drawdown': f"{strat.analyzers.drawdown.get_analysis()['max']['drawdown']:.2f}%",
                    'Total Return': f"{((final_value - initial_value) / initial_value * 100):.2f}%"
                },
                'symbol': symbol,
                'strategy_class': strategy_class.__name__
            }
            
        except Exception as e:
            return {'error': f'Backtest failed: {str(e)}'}
    
    def process(self, input_data: Any) -> Any:
        """Process backtest request"""
        if isinstance(input_data, dict):
            strategy_code = input_data.get('strategy_code')
            market_data = input_data.get('market_data')
            params = input_data.get('params')
            return self.run_backtest(strategy_code, market_data, params)
        else:
            return {'error': 'Invalid input format'}
