import datetime
import pandas as pd
from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """Base class for all trading strategies."""
    
    def __init__(self, 
                 take_profit_pct=None, 
                 stop_loss_pct=None, 
                 cooldown_period=0):
        """
        Initialize the base strategy.
        
        Args:
            take_profit_pct (float, optional): Take profit percentage threshold.
            stop_loss_pct (float, optional): Stop loss percentage threshold.
            cooldown_period (int, optional): Number of days to wait before re-entering 
                                            a position after take-profit or stop-loss.
        """
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.cooldown_period = cooldown_period
        self.cooldown_tracker = {}  # Dictionary to track securities in cooldown {symbol: exit_date}
        
    @abstractmethod
    def generate_signals(self, data, factors, date):
        """
        Generate trading signals based on factor data.
        
        Args:
            data (pd.DataFrame): Historical price data.
            factors (pd.DataFrame): Factor data.
            date (datetime.date): Current date.
            
        Returns:
            pd.DataFrame: DataFrame with trading signals.
        """
        pass
    
    def apply_risk_management(self, positions, current_prices, entry_prices, date):
        """
        Apply risk management rules like stop-loss and take-profit.
        
        Args:
            positions (dict): Current positions {symbol: quantity}.
            current_prices (dict): Current prices {symbol: price}.
            entry_prices (dict): Entry prices for positions {symbol: entry_price}.
            date (datetime.date): Current date.
            
        Returns:
            dict: Updated positions after applying risk management.
        """
        updated_positions = positions.copy()
        
        for symbol, quantity in positions.items():
            if quantity == 0 or symbol not in current_prices or symbol not in entry_prices:
                continue
                
            current_price = current_prices[symbol]
            entry_price = entry_prices[symbol]
            pnl_pct = (current_price - entry_price) / entry_price * 100
            
            # Check take profit
            if self.take_profit_pct is not None and pnl_pct >= self.take_profit_pct:
                updated_positions[symbol] = 0
                self.cooldown_tracker[symbol] = date
                print(f"Take profit triggered for {symbol} at {current_price} (PnL: {pnl_pct:.2f}%)")
                
            # Check stop loss
            elif self.stop_loss_pct is not None and pnl_pct <= -self.stop_loss_pct:
                updated_positions[symbol] = 0
                self.cooldown_tracker[symbol] = date
                print(f"Stop loss triggered for {symbol} at {current_price} (PnL: {pnl_pct:.2f}%)")
                
        return updated_positions
    
    def check_cooldown(self, symbol, current_date):
        """
        Check if a symbol is in cooldown period.
        
        Args:
            symbol (str): Security symbol.
            current_date (datetime.date): Current date.
            
        Returns:
            bool: True if symbol is in cooldown, False otherwise.
        """
        if symbol not in self.cooldown_tracker:
            return False
            
        exit_date = self.cooldown_tracker[symbol]
        cooldown_end_date = exit_date + datetime.timedelta(days=self.cooldown_period)
        
        if current_date <= cooldown_end_date:
            return True
        else:
            # Remove from cooldown tracker once cooldown period is over
            del self.cooldown_tracker[symbol]
            return False
    
    @abstractmethod
    def rebalance(self, current_positions, signals, prices, date):
        """
        Rebalance the portfolio based on signals.
        
        Args:
            current_positions (dict): Current positions {symbol: quantity}.
            signals (pd.DataFrame): Trading signals.
            prices (dict): Current prices {symbol: price}.
            date (datetime.date): Current date.
            
        Returns:
            dict: New positions after rebalancing.
        """
        pass
