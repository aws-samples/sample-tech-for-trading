"""
Backtest Agent - Executes backtests using generated strategies
"""

import backtrader as bt
import pandas as pd
from io import StringIO
from typing import Dict, Any

class BacktestTool():
    """Tool that executes backtests using Backtrader"""
    
    def __init__(self):
        pass
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
            # print(f"\n🔍 BACKTEST DEBUG - Starting detailed analysis...")
            
            # STEP 1: Execute strategy code to get strategy class
            print(f"📝 STEP 1: Executing strategy code...")
            try:
                exec_globals = {'bt': bt, 'btind': bt.indicators}
                exec(strategy_code, exec_globals)
                print(f"✅ Strategy code executed successfully")
            except Exception as e:
                print(f"❌ Strategy code execution failed: {e}")
                return {'error': f'Strategy code execution failed: {str(e)}'}
            
            # STEP 2: Find the strategy class
            print(f"🔍 STEP 2: Finding strategy class...")
            strategy_class = None
            available_classes = []
            for name, obj in exec_globals.items():
                if isinstance(obj, type):
                    available_classes.append(name)
                    if (issubclass(obj, bt.Strategy) and obj != bt.Strategy):
                        strategy_class = obj
                        print(f"✅ Found strategy class: {name}")
                        break
            
            if not strategy_class:
                print(f"❌ No valid strategy class found. Available classes: {available_classes}")
                return {'error': 'No valid strategy class found'}
            
            # STEP 3: Extract and validate market data
            print(f"📊 STEP 3: Processing market data...")
            symbol = list(market_data.keys())[0]
            data = market_data[symbol]
            
            # print(f"🔍 Market data analysis:")
            print(f"   Symbol: {symbol}")
            # print(f"   Data type: {type(data)}")
            # print(f"   Data shape: {data.shape if hasattr(data, 'shape') else 'N/A'}")
            
            if hasattr(data, 'columns'):
                print(f"   Columns: {list(data.columns)}")
                print(f"   Index type: {type(data.index)}")
                print(f"   Index length: {len(data.index)}")
                
                # Check for required columns
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                missing_cols = [col for col in required_cols if col not in data.columns]
                if missing_cols:
                    print(f"❌ Missing required columns: {missing_cols}")
                    return {'error': f'Missing required columns: {missing_cols}'}
            else:
                print(f"   Data content: {data}")
            
            # STEP 4: Convert to DataFrame if needed
            # print(f"🔄 STEP 4: Data conversion...")
            if isinstance(data, list):
                print("⚠️ Converting list to DataFrame")
                try:
                    data = pd.DataFrame(data)
                    print(f"✅ Conversion successful, new shape: {data.shape}")
                except Exception as e:
                    print(f"❌ DataFrame conversion failed: {e}")
                    return {'error': f'DataFrame conversion failed: {str(e)}'}
            
            # STEP 5: Ensure proper datetime index
            # print(f"📅 STEP 5: Setting up datetime index...")
            try:
                if not isinstance(data.index, pd.DatetimeIndex):
                    if 'date' in data.columns:
                        print("🔄 Converting date column to datetime index")
                        data['date'] = pd.to_datetime(data['date'])
                        data.set_index('date', inplace=True)
                        print(f"✅ Date index set successfully")
                    else:
                        print("⚠️ No date column found, using default index")
                        data.index = pd.date_range(start='2022-01-01', periods=len(data), freq='D')
                        print(f"✅ Default date index created")

                
                # print(f"📅 Final index info:")
                # print(f"   Index type: {type(data.index)}")
                # print(f"   Date range: {data.index.min()} to {data.index.max()}")
                # print(f"   Total periods: {len(data.index)}")
                
            except Exception as e:
                print(f"❌ Date index setup failed: {e}")
                return {'error': f'Date index setup failed: {str(e)}'}
            
            # STEP 6: Create Cerebro engine
            print(f"🧠 STEP 4: Creating Cerebro engine...")
            try:
                cerebro = bt.Cerebro()
                # print(f"✅ Cerebro created successfully")
            except Exception as e:
                print(f"❌ Cerebro creation failed: {e}")
                return {'error': f'Cerebro creation failed: {str(e)}'}
            
            # STEP 7: Add strategy
            print(f"📈 STEP 5: Adding strategy to Cerebro...")
            try:
                cerebro.addstrategy(strategy_class)
                # print(f"✅ Strategy added successfully: {strategy_class.__name__}")
            except Exception as e:
                print(f"❌ Strategy addition failed: {e}")
                return {'error': f'Strategy addition failed: {str(e)}'}
            
            # STEP 8: Create and add data feed
            print(f"📊 STEP 6: Creating Backtrader data feed...")
            try:
                # print(f"🔍 Pre-feed data validation:")
                print(f"   DataFrame shape: {data.shape}")
                
                # Additional validation for Backtrader
                if len(data) == 0:
                    print(f"❌ Empty DataFrame")
                    return {'error': 'Empty DataFrame - no data to backtest'}
                
                # # Check for NaN values
                # nan_counts = data.isnull().sum()
                # if nan_counts.any():
                #     print(f"⚠️ NaN values found: {nan_counts[nan_counts > 0].to_dict()}")
                
                bt_data = bt.feeds.PandasData(dataname=data)
                # print(f"✅ PandasData feed created successfully")
                
                cerebro.adddata(bt_data)
                print(f"✅ Data feed added to Cerebro")
                
            except Exception as e:
                print(f"❌ Data feed creation/addition failed: {e}")
                import traceback
                from io import StringIO
                
                # Capture full traceback as string
                tb_str = traceback.format_exc()
                print(f"📋 Full traceback:")
                print(tb_str)
                
                return {
                    'error': f'Data feed creation failed: {str(e)}',
                    'traceback': tb_str,
                    'error_location': 'bt.feeds.PandasData creation or cerebro.adddata()',
                    'debug_info': {
                        'data_shape': data.shape if hasattr(data, 'shape') else 'N/A',
                        'data_columns': list(data.columns) if hasattr(data, 'columns') else 'N/A'
                    }
                }
            
            # STEP 9: Set broker parameters
            print(f"💰 STEP 7: Setting broker parameters...")
            try:
                cerebro.broker.setcash(params.get('initial_cash', 100000))
                cerebro.broker.setcommission(commission=params.get('commission', 0.001))
                print(f"✅ Broker parameters set - Cash: {params.get('initial_cash', 100000)}, Commission: {params.get('commission', 0.001)}")
            except Exception as e:
                print(f"❌ Broker setup failed: {e}")
                return {'error': f'Broker setup failed: {str(e)}'}
            
            # STEP 10: Add analyzers
            print(f"📊 STEP 8: Adding analyzers...")
            try:
                cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
                cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
                cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
                print(f"✅ Analyzers SharpeRatio, Returns, DrawDown added successfully")
            except Exception as e:
                print(f"❌ Analyzer addition failed: {e}")
                return {'error': f'Analyzer addition failed: {str(e)}'}
            
            # STEP 11: Run backtest
            print(f"🚀 STEP 9: Running backtest...")
            try:
                initial_value = cerebro.broker.getvalue()
                # print(f"💰 Initial portfolio value: ${initial_value:,.2f}")
                
                # print(f"⏳ Executing backtest...")
                results = cerebro.run()
                # print(f"✅ Backtest execution completed")
                
                final_value = cerebro.broker.getvalue()
                print(f"💰 Final portfolio value: ${final_value:,.2f}")
                
            except Exception as e:
                print(f"❌ BACKTEST EXECUTION FAILED: {e}")
                import traceback
                import sys
                from io import StringIO
                
                # Capture full traceback as string
                tb_str = traceback.format_exc()
                print(f"📋 Full traceback:")
                print(tb_str)
                
                # Also capture to string buffer for return
                tb_buffer = StringIO()
                traceback.print_exc(file=tb_buffer)
                tb_content = tb_buffer.getvalue()
                
                return {
                    'error': f'Backtest execution failed: {str(e)}',
                    'traceback': tb_content,
                    'error_location': 'cerebro.run() execution',
                    'debug_info': {
                        'data_shape': data.shape if hasattr(data, 'shape') else 'N/A',
                        'data_columns': list(data.columns) if hasattr(data, 'columns') else 'N/A',
                        'strategy_class': strategy_class.__name__ if strategy_class else 'N/A'
                    }
                }
            
            # STEP 12: Extract results
            print(f"📈 STEP 10: Extracting results...")
            try:
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
                print(f"❌ Results extraction failed: {e}")
                return {'error': f'Results extraction failed: {str(e)}'}
            
        except Exception as e:
            print(f"❌ UNEXPECTED ERROR in run_backtest: {e}")
            import traceback
            from io import StringIO
            
            # Capture full traceback as string
            tb_str = traceback.format_exc()
            print(f"📋 Full traceback:")
            print(tb_str)
            
            return {
                'error': f'Backtest failed: {str(e)}',
                'traceback': tb_str,
                'error_location': 'Unknown - unexpected error',
                'debug_info': 'Check traceback for details'
            }
    
    def process(self, input_data: Any) -> Any:
        """Process backtest request"""
        if isinstance(input_data, dict):
            strategy_code = input_data.get('strategy_code')
            market_data = input_data.get('market_data')
            params = input_data.get('params')
            return self.run_backtest(strategy_code, market_data, params)
        else:
            return {'error': 'Invalid input format'}
