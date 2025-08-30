"""
Portfolio management utilities.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
import logging

logger = logging.getLogger(__name__)

class Portfolio:
    """
    Portfolio management class.
    
    This class handles portfolio tracking, rebalancing, and performance analysis.
    """
    
    def __init__(self, initial_cash: float = 1000000.0):
        """
        Initialize the portfolio.
        
        Args:
            initial_cash: Initial cash amount
        """
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {}  # {ticker: quantity}
        self.history = []  # List of portfolio snapshots
        
    def calculate_value(self, prices: pd.Series) -> float:
        """
        Calculate the current portfolio value.
        
        Args:
            prices: Series of current prices (index=tickers)
            
        Returns:
            Current portfolio value
        """
        position_value = sum(self.positions.get(ticker, 0) * prices.get(ticker, 0) 
                            for ticker in self.positions)
        return position_value + self.cash
    
    def rebalance(self, target_weights: Dict[str, float], prices: pd.Series, 
                 transaction_costs: float = 0.001) -> Dict[str, float]:
        """
        Rebalance the portfolio to target weights.
        
        Args:
            target_weights: Dictionary mapping tickers to target weights
            prices: Series of current prices (index=tickers)
            transaction_costs: Transaction costs as a percentage
            
        Returns:
            Dictionary of executed trades {ticker: quantity}
        """
        current_value = self.calculate_value(prices)
        
        # Calculate target position values
        target_positions = {ticker: weight * current_value 
                           for ticker, weight in target_weights.items()}
        
        # Calculate current position values
        current_position_values = {ticker: self.positions.get(ticker, 0) * prices[ticker]
                                  for ticker in target_weights if ticker in prices}
        
        # Calculate trades needed
        trades = {}
        total_transaction_cost = 0.0
        
        for ticker, target_value in target_positions.items():
            if ticker not in prices:
                logger.warning(f"No price data for {ticker}, skipping")
                continue
                
            current_value = current_position_values.get(ticker, 0.0)
            trade_value = target_value - current_value
            
            if abs(trade_value) > 0:
                # Calculate quantity to trade
                price = prices[ticker]
                quantity = trade_value / price
                trades[ticker] = quantity
                
                # Apply transaction costs
                cost = abs(trade_value) * transaction_costs
                total_transaction_cost += cost
                
                # Update positions
                self.positions[ticker] = self.positions.get(ticker, 0) + quantity
                
                # Remove positions with zero quantity
                if abs(self.positions[ticker]) < 1e-6:
                    del self.positions[ticker]
        
        # Update cash
        trade_values_sum = sum(trades[ticker] * prices[ticker] for ticker in trades if ticker in prices)
        self.cash -= (trade_values_sum + total_transaction_cost)
        
        # Record portfolio snapshot
        self._record_snapshot(prices)
        
        return trades
    
    def _record_snapshot(self, prices: pd.Series):
        """
        Record current portfolio state.
        
        Args:
            prices: Series of current prices (index=tickers)
        """
        snapshot = {
            'cash': self.cash,
            'positions': self.positions.copy(),
            'value': self.calculate_value(prices)
        }
        self.history.append(snapshot)
    
    def get_returns(self) -> pd.Series:
        """
        Calculate historical returns.
        
        Returns:
            Series of portfolio returns
        """
        if len(self.history) < 2:
            return pd.Series()
        
        values = [snapshot['value'] for snapshot in self.history]
        returns = pd.Series(values).pct_change().fillna(0)
        
        return returns
    
    def get_weights(self, prices: pd.Series) -> Dict[str, float]:
        """
        Calculate current portfolio weights.
        
        Args:
            prices: Series of current prices (index=tickers)
            
        Returns:
            Dictionary mapping tickers to current weights
        """
        total_value = self.calculate_value(prices)
        
        if total_value == 0:
            return {}
        
        weights = {ticker: self.positions[ticker] * prices.get(ticker, 0) / total_value
                  for ticker in self.positions if ticker in prices}
        
        # Add cash weight
        weights['cash'] = self.cash / total_value
        
        return weights
    
    def reset(self):
        """Reset the portfolio to initial state."""
        self.cash = self.initial_cash
        self.positions = {}
        self.history = []
