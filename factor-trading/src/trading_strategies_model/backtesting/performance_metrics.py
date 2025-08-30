"""
Performance metrics calculation for trading strategies.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

def calculate_performance_metrics(returns: pd.Series, benchmark: Optional[pd.Series] = None,
                                risk_free_rate: float = 0.0) -> Dict:
    """
    Calculate performance metrics for a strategy.
    
    Args:
        returns: Series of strategy returns
        benchmark: Optional series of benchmark returns
        risk_free_rate: Annual risk-free rate (default: 0.0)
        
    Returns:
        Dictionary of performance metrics
    """
    # Convert annual risk-free rate to match the frequency of returns
    if len(returns) > 0:
        period_risk_free = (1 + risk_free_rate) ** (1 / 252) - 1
    else:
        period_risk_free = 0.0
    
    # Basic return metrics
    total_return = (1 + returns).prod() - 1
    annualized_return = (1 + total_return) ** (252 / len(returns)) - 1 if len(returns) > 0 else 0
    
    # Risk metrics
    volatility = returns.std() * np.sqrt(252)  # Annualized volatility
    downside_returns = returns[returns < 0]
    downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
    
    # Maximum drawdown
    cum_returns = (1 + returns).cumprod()
    running_max = cum_returns.cummax()
    drawdowns = (cum_returns / running_max - 1)
    max_drawdown = drawdowns.min()
    
    # Sharpe and Sortino ratios
    excess_return = annualized_return - risk_free_rate
    sharpe_ratio = excess_return / volatility if volatility > 0 else 0
    sortino_ratio = excess_return / downside_volatility if downside_volatility > 0 else 0
    
    # Win rate and profit factor
    winning_days = returns[returns > 0]
    losing_days = returns[returns < 0]
    win_rate = len(winning_days) / len(returns) if len(returns) > 0 else 0
    profit_factor = abs(winning_days.sum() / losing_days.sum()) if losing_days.sum() < 0 else np.inf
    
    # Benchmark comparison metrics
    alpha, beta = 0.0, 0.0
    tracking_error = 0.0
    information_ratio = 0.0
    
    if benchmark is not None:
        # Align benchmark with returns
        aligned_returns = returns.copy()
        aligned_benchmark = benchmark.reindex(returns.index)
        
        # Calculate beta and alpha
        covariance = np.cov(aligned_returns, aligned_benchmark)[0, 1]
        benchmark_variance = aligned_benchmark.var()
        beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
        
        benchmark_return = (1 + aligned_benchmark).prod() - 1
        benchmark_annualized = (1 + benchmark_return) ** (252 / len(aligned_benchmark)) - 1 if len(aligned_benchmark) > 0 else 0
        alpha = annualized_return - (risk_free_rate + beta * (benchmark_annualized - risk_free_rate))
        
        # Tracking error and information ratio
        tracking_diff = aligned_returns - aligned_benchmark
        tracking_error = tracking_diff.std() * np.sqrt(252)
        information_ratio = (annualized_return - benchmark_annualized) / tracking_error if tracking_error > 0 else 0
    
    # Compile metrics
    metrics = {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'volatility': volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'alpha': alpha,
        'beta': beta,
        'tracking_error': tracking_error,
        'information_ratio': information_ratio
    }
    
    return metrics
