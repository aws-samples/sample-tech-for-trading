#!/usr/bin/env python3
"""
Script to run backtests locally for testing before deploying to AWS.
"""

import os
import sys
import json
import datetime
import argparse
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from trading_strategies_model.strategies.long_short_equity import LongShortEquityStrategy
from trading_strategies_model.backtesting.backtest_engine import BacktestEngine
from trading_strategies_model.utils.data_loader import WeightingMethod


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run backtest locally')
    
    parser.add_argument('--strategy', type=str, default='LongShortEquityStrategy',
                        help='Strategy class name')
    parser.add_argument('--start-date', type=str, default='2020-01-01',
                        help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2022-12-31',
                        help='End date (YYYY-MM-DD)')
    parser.add_argument('--initial-capital', type=float, default=1000000,
                        help='Initial capital')
    parser.add_argument('--rebalance-period', type=int, default=7,
                        help='Rebalance period in days') # 7, 14, 28, 60
    parser.add_argument('--take-profit', type=float, default=None,
                        help='Take profit percentage') # 0.1, 0.11, ~ 0.20
    parser.add_argument('--stop-loss', type=float, default=None,
                        help='Stop loss percentage') # 0.05, 0.06, 0.07, 0.08 ~ 0.20
    parser.add_argument('--cooldown-period', type=int, default=0,
                        help='Cooldown period in days') # 14, 28, 60, 120
    parser.add_argument('--long-pct', type=float, default=0.2,
                        help='Percentage of universe to go long on') # 1/30, 2/30, 3/30, 4/30, 5/30, 6/30
    parser.add_argument('--short-pct', type=float, default=0.2,
                        help='Percentage of universe to short') # 1/30, 2/30, 3/30, 4/30, 5/30, 6/30
    parser.add_argument('--max-position-size', type=float, default=0.05,
                        help='Maximum position size as percentage of portfolio') # 0.05, 0.1, 0.15, 0.2, 0.25
    parser.add_argument('--commission', type=float, default=0.0008,
                        help='Commission percentage for trades (default: 0.08%)')
    parser.add_argument('--output-dir', type=str, default='./backtest_results',
                        help='Output directory for results')
    parser.add_argument('--factors', type=str, default='DebtToEquity,NewsSentiment',
                        help='Comma-separated list of factors to use')
    parser.add_argument('--weighting-method', type=int, default=1,
                        choices=[1, 2, 3],
                        help='Factor weighting method: 1=RSQUARED, 2=TSTAT, 3=EQUAL') # 1, 2, 3
    
    return parser.parse_args()


def main():
    """Main entry point for local backtest."""
    # Load environment variables from .env file
    load_dotenv()
    print(f"CLICKHOUSE_HOST: {os.environ.get('CLICKHOUSE_HOST', 'Not loaded')}")
    
    # Parse command line arguments
    args = parse_args()
    
    # Convert dates
    start_date = datetime.datetime.strptime(args.start_date, '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime(args.end_date, '%Y-%m-%d').date()
    
    # Parse factors
    factors = [f.strip() for f in args.factors.split(',')]
    
    # Convert weighting method
    weighting_method = WeightingMethod(args.weighting_method)
    
    # Get strategy class
    strategy_class = globals()[args.strategy]
    
    # Strategy parameters
    strategy_params = {
        'long_pct': args.long_pct,
        'short_pct': args.short_pct,
        'max_position_size': args.max_position_size,
        'take_profit_pct': args.take_profit,
        'stop_loss_pct': args.stop_loss,
        'cooldown_period': args.cooldown_period
    }
    
    # Create backtest engine
    engine = BacktestEngine(
        strategy_class=strategy_class,
        db_host=os.environ.get('CLICKHOUSE_HOST', 'localhost'),
        db_port=int(os.environ.get('CLICKHOUSE_PORT', 9000)),
        db_user=os.environ.get('CLICKHOUSE_USER', 'default'),
        db_password=os.environ.get('CLICKHOUSE_PASSWORD', ''),
        db_database=os.environ.get('CLICKHOUSE_DATABASE', 'default'),
        start_date=start_date,
        end_date=end_date,
        initial_capital=args.initial_capital,
        rebalance_period=args.rebalance_period,
        take_profit_pct=args.take_profit,
        stop_loss_pct=args.stop_loss,
        cooldown_period=args.cooldown_period,
        factors=factors,
        commission_pct=args.commission
    )
    
    print(f"Running backtest with parameters:")
    print(f"  Strategy: {args.strategy}")
    print(f"  Date range: {args.start_date} to {args.end_date}")
    print(f"  Initial capital: ${args.initial_capital:,.2f}")
    print(f"  Rebalance period: {args.rebalance_period} days")
    print(f"  Take profit: {args.take_profit}%")
    print(f"  Stop loss: {args.stop_loss}%")
    print(f"  Cooldown period: {args.cooldown_period} days")
    print(f"  Long percentage: {args.long_pct * 100}%")
    print(f"  Short percentage: {args.short_pct * 100}%")
    print(f"  Max position size: {args.max_position_size * 100}%")
    print(f"  Commission: {args.commission}%")
    print(f"  Factors: {', '.join(factors)}")
    print(f"  Weighting method: {weighting_method.name}")
    
    # Run backtest
    print("Running backtest...")
    
    # Set factors and weighting method in data loader
    engine.data_loader.factors = factors
    engine.data_loader.weighting_method = weighting_method
    
    results = engine.run(strategy_params=strategy_params)
    
    # Print metrics
    metrics = results['metrics']
    print("\nBacktest Results:")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}" if metrics['sharpe_ratio'] is not None else "  Sharpe Ratio: N/A")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2f}%" if metrics['max_drawdown'] is not None else "  Max Drawdown: N/A")
    print(f"  Total Return: {metrics['total_return'] * 100:.2f}%" if metrics['total_return'] is not None else "  Total Return: N/A")
    print(f"  Annual Return: {metrics['annual_return'] * 100:.2f}%" if metrics['annual_return'] is not None else "  Annual Return: N/A")
    print(f"  Number of Trades: {metrics['num_trades']}")
    print(f"  Win Rate: {metrics['win_rate'] * 100:.2f}" if metrics['win_rate'] is not None else "  Win Rate: N/A")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}" if metrics['profit_factor'] is not None else "  Profit Factor: N/A")
    print(f"  Final Value: ${metrics['final_value']:,.2f}" if metrics['final_value'] is not None else "  Final Value: N/A")
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Save metrics to JSON
    metrics_file = os.path.join(args.output_dir, 'metrics.json')
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    # Save parameters
    params_file = os.path.join(args.output_dir, 'parameters.json')
    params_to_save = results['parameters'].copy()
    params_to_save.update({
        'factors': factors,
        'weighting_method': weighting_method.name
    })
    with open(params_file, 'w') as f:
        json.dump(params_to_save, f, indent=2)
    
    print(f"\nResults saved to {args.output_dir}/")


if __name__ == "__main__":
    main()
