#!/usr/bin/env python3
"""
AWS Batch job for running backtests.
"""

import sys
import json
import os
import datetime
import argparse
import boto3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_strategies_model.strategies.long_short_equity import LongShortEquityStrategy
from trading_strategies_model.backtesting.backtest_engine import BacktestEngine


def get_batch_parameters():
    """
    Get parameters from AWS Batch job parameters.
    AWS Batch passes parameters as environment variables with AWS_BATCH_JOB_PARAMETERS_ prefix.
    """
    params = {}
    
    # Check if running in AWS Batch environment
    if 'AWS_BATCH_JOB_ID' in os.environ:
        # In AWS Batch, parameters are available as environment variables
        # They are prefixed with AWS_BATCH_JOB_PARAMETERS_
        for key, value in os.environ.items():
            if key.startswith('AWS_BATCH_JOB_PARAMETERS_'):
                param_name = key.replace('AWS_BATCH_JOB_PARAMETERS_', '').lower()
                params[param_name] = value
    
    # Also check for direct parameter environment variables (fallback)
    batch_params = [
        'strategy_class', 'start_date', 'end_date', 'take_profit', 'stop_loss',
        'cooldown_period', 'long_pct', 'short_pct', 'initial_capital', 'rebalance_period',
        'db_host', 'db_port', 'db_user', 'db_password', 'db_database'
    ]
    
    for param in batch_params:
        if param.upper() in os.environ:
            params[param] = os.environ[param.upper()]
        elif param in os.environ:
            params[param] = os.environ[param]
    
    return params


def get_database_config(batch_params):
    """
    Get database configuration from environment variables or batch parameters.
    
    Args:
        batch_params (dict): Parameters from AWS Batch
        
    Returns:
        dict: Database configuration
    """
    # Try to get from batch parameters first, then environment variables
    db_config = {
        'db_host': (
            batch_params.get('db_host') or 
            os.environ.get('CLICKHOUSE_HOST') or 
            os.environ.get('DB_HOST', 'localhost')
        ),
        'db_port': int(
            batch_params.get('db_port') or 
            os.environ.get('CLICKHOUSE_PORT') or 
            os.environ.get('DB_PORT', '9000')
        ),
        'db_user': (
            batch_params.get('db_user') or 
            os.environ.get('CLICKHOUSE_USER') or 
            os.environ.get('DB_USER', 'default')
        ),
        'db_password': (
            batch_params.get('db_password') or 
            os.environ.get('CLICKHOUSE_PASSWORD') or 
            os.environ.get('DB_PASSWORD', '')
        ),
        'db_database': (
            batch_params.get('db_database') or 
            os.environ.get('CLICKHOUSE_DATABASE') or 
            os.environ.get('DB_DATABASE', 'default')
        )
    }
    
    return db_config


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run backtest job')
    
    # Strategy parameters
    parser.add_argument('--strategy-class', default='LongShortEquityStrategy', 
                       help='Strategy class name')
    parser.add_argument('--start-date', required=False, 
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=False, 
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--initial-capital', type=float, default=1000000, 
                       help='Initial capital')
    parser.add_argument('--rebalance-period', type=int, default=1, 
                       help='Rebalance period in days')
    parser.add_argument('--take-profit', type=float, 
                       help='Take profit percentage')
    parser.add_argument('--stop-loss', type=float, 
                       help='Stop loss percentage')
    parser.add_argument('--cooldown-period', type=int, default=0, 
                       help='Cooldown period in days')
    
    # Strategy-specific parameters
    parser.add_argument('--long-pct', type=float, default=0.2, 
                       help='Long position percentage')
    parser.add_argument('--short-pct', type=float, default=0.2, 
                       help='Short position percentage')
    
    # Database connection parameters
    parser.add_argument('--db-host', 
                       help='Database host (default: from CLICKHOUSE_HOST env var)')
    parser.add_argument('--db-port', type=int, 
                       help='Database port (default: from CLICKHOUSE_PORT env var)')
    parser.add_argument('--db-user', 
                       help='Database user (default: from CLICKHOUSE_USER env var)')
    parser.add_argument('--db-password', 
                       help='Database password (default: from CLICKHOUSE_PASSWORD env var)')
    parser.add_argument('--db-database', 
                       help='Database name (default: from CLICKHOUSE_DATABASE env var)')
    
    return parser.parse_args()


def run_backtest(config):
    """
    Run a backtest with the given configuration.
    
    Args:
        config (dict): Backtest configuration.
        
    Returns:
        dict: Backtest results.
    """
    # Parse configuration
    strategy_class_name = config.get('strategy_class', 'LongShortEquityStrategy')
    start_date_str = config.get('start_date', '2020-01-01')
    end_date_str = config.get('end_date', '2022-12-31')
    initial_capital = config.get('initial_capital', 1000000)
    rebalance_period = config.get('rebalance_period', 1)
    take_profit_pct = config.get('take_profit_pct')
    stop_loss_pct = config.get('stop_loss_pct')
    cooldown_period = config.get('cooldown_period', 0)
    factors = [f.strip() for f in config.get('factors').split(',')]
    strategy_params = config.get('strategy_params', {})
    
    # Get database configuration
    db_config = config.get('db_config', {})
    
    # Convert dates
    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Get strategy class
    strategy_class = globals()[strategy_class_name]
    
    # Create backtest engine with database configuration
    engine = BacktestEngine(
        strategy_class=strategy_class,
        db_host=db_config['db_host'],
        db_port=db_config['db_port'],
        db_user=db_config['db_user'],
        db_password=db_config['db_password'],
        db_database=db_config['db_database'],
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        rebalance_period=rebalance_period,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        factors=factors,
        cooldown_period=cooldown_period
    )
    
    # Run backtest
    results = engine.run(strategy_params=strategy_params)
    
    return results


def save_results(results, config):
    """
    Save backtest results to S3.
    
    Args:
        results (dict): Backtest results.
        config (dict): Backtest configuration.
    """
    # Create unique identifier for this backtest
    strategy_name = config.get('strategy_class', 'LongShortEquityStrategy')
    rebalance_period = config.get('rebalance_period', 1)
    take_profit_pct = config.get('take_profit_pct', 'None')
    stop_loss_pct = config.get('stop_loss_pct', 'None')
    cooldown_period = config.get('cooldown_period', 0)
    
    identifier = f"{strategy_name}_rb{rebalance_period}_tp{take_profit_pct}_sl{stop_loss_pct}_cd{cooldown_period}"
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Get S3 bucket from environment
    s3_bucket = os.environ.get('RESULTS_BUCKET', 'trading-strategies-results')
    
    # Save metrics to JSON
    metrics = results['metrics']
    metrics_json = json.dumps(metrics, default=str)  # Handle datetime serialization

    # Save parameters to JSON
    params_json = json.dumps(results['parameters'], default=str)
    
    # Upload to S3
    s3 = boto3.client('s3')
    
    # Upload metrics
    s3.put_object(
        Bucket=s3_bucket,
        Key=f"backtest_results/{identifier}/{timestamp}/metrics.json",
        Body=metrics_json
    )

    # # Save plot to PNG
    # plot_data = results['plot'].getvalue()
    # # Upload plot
    # s3.put_object(
    #     Bucket=s3_bucket,
    #     Key=f"backtest_results/{identifier}/{timestamp}/plot.png",
    #     Body=plot_data
    # )
    
    # Upload parameters
    s3.put_object(
        Bucket=s3_bucket,
        Key=f"backtest_results/{identifier}/{timestamp}/parameters.json",
        Body=params_json
    )
    
    print(f"Results saved to s3://{s3_bucket}/backtest_results/{identifier}/{timestamp}/")


def main():
    """Main entry point for the batch job."""
    print("Starting backtest job...")
    print(f"Job ID: {os.environ.get('AWS_BATCH_JOB_ID', 'N/A')}")
    print(f"Job Queue: {os.environ.get('AWS_BATCH_JQ_NAME', 'N/A')}")
    
    # Get parameters from AWS Batch
    batch_params = get_batch_parameters()
    print(f"Batch parameters: {batch_params}")
    
    # Get database configuration
    db_config = get_database_config(batch_params)
    print(f"Database config: {db_config}")
    
    # Check if we have legacy JSON config or new parameter format
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--') and batch_params == {}:
        # Legacy mode: JSON config as first argument
        print("Using legacy JSON config mode")
        config_json = sys.argv[1]
        config = json.loads(config_json)
        # Add database config if not present
        if 'db_config' not in config:
            config['db_config'] = db_config
    elif batch_params:
        # AWS Batch parameters mode
        print("Using AWS Batch parameters mode")
        config = {
            'strategy_class': batch_params.get('strategy_class', 'LongShortEquityStrategy'),
            'start_date': batch_params.get('start_date', '2022-01-01'),
            'end_date': batch_params.get('end_date', '2022-12-31'),
            'initial_capital': float(batch_params.get('initial_capital', 1000000)),
            'rebalance_period': int(batch_params.get('rebalance_period', 1)),
            'take_profit_pct': float(batch_params.get('take_profit')) if batch_params.get('take_profit') else None,
            'stop_loss_pct': float(batch_params.get('stop_loss')) if batch_params.get('stop_loss') else None,
            'cooldown_period': int(batch_params.get('cooldown_period', 0)),
            'factors': batch_params.get('factors', 'DebtToEquity,NewsSentiment'),
            'strategy_params': {
                'long_pct': float(batch_params.get('long_pct', 0.2)),
                'short_pct': float(batch_params.get('short_pct', 0.2))
            },
            'db_config': db_config
        }
    else:
        # Command line arguments mode
        print("Using command line arguments mode")
        args = parse_args()
        
        # Convert args to config dictionary
        config = {
            'strategy_class': args.strategy_class,
            'start_date': args.start_date or '2022-01-01',
            'end_date': args.end_date or '2022-12-31',
            'initial_capital': args.initial_capital,
            'rebalance_period': args.rebalance_period,
            'take_profit_pct': args.take_profit,
            'stop_loss_pct': args.stop_loss,
            'cooldown_period': args.cooldown_period,
            'factors': args.factors,
            'strategy_params': {
                'long_pct': args.long_pct,
                'short_pct': args.short_pct
            },
            'db_config': db_config
        }
    
    print(f"Final config: {config}")
    
    # Run backtest
    print("Running backtest...")
    results = run_backtest(config)
    
    # Save results
    print("Saving results...")
    save_results(results, config)
    
    print("Backtest job completed successfully!")


if __name__ == "__main__":
    main()
