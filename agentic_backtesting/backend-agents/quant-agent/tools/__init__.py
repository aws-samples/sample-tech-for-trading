"""
Multi-Agent Trading System Tools
"""

from tools.backtest import BacktestTool
from tools.strategy_generator import generate_trading_strategy
from tools.market_data import fetch_market_data_via_gateway
from tools.backtest_tool_sandbox import run_backtest
from tools.results_summary import create_results_summary
from tools.history import get_backtest_history

# Optional: use the A2A version as the strategy generator
# (requires STRATEGY_GENERATOR_A2A_ARN and the strategy-generator-a2a-agent deployed)
#from tools.strategy_generator_a2a import generate_trading_strategy_a2a
#generate_trading_strategy = generate_trading_strategy_a2a

__all__ = [
    'BacktestTool',
    'generate_trading_strategy',
    'fetch_market_data_via_gateway',
    'run_backtest',
    'create_results_summary',
    'get_backtest_history'
]
