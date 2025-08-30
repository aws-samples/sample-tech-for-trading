"""
Airflow Backtest Framework - A framework for orchestrating trading strategy backtests using Apache Airflow and AWS Batch.
"""

from .config import BacktestConfig
from .dag_factory import BacktestDAGFactory

__version__ = '0.1.0'