import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class LongShortEquityStrategy(BaseStrategy):
    """
    Long-Short Equity strategy based on factor rankings.
    
    This strategy ranks securities based on factor values and goes long on the top-ranked
    securities while shorting the bottom-ranked securities.
    """
    
    def __init__(self, 
                 long_pct=0.2, 
                 short_pct=0.2, 
                 max_position_size=0.05,
                 take_profit_pct=None, 
                 stop_loss_pct=None,
                 cooldown_period=0):
        """
        Initialize the Long-Short Equity strategy.
        
        Args:
            long_pct (float): Percentage of universe to go long on (0.0-1.0).
            short_pct (float): Percentage of universe to short (0.0-1.0).
            max_position_size (float): Maximum position size as percentage of portfolio.
            take_profit_pct (float, optional): Take profit percentage threshold.
            stop_loss_pct (float, optional): Stop loss percentage threshold.
            cooldown_period (int, optional): Number of days to wait before re-entering 
                                            a position after take-profit or stop-loss.
        """
        super().__init__(take_profit_pct, stop_loss_pct, cooldown_period)
        self.long_pct = long_pct
        self.short_pct = short_pct
        self.max_position_size = max_position_size
        
    def generate_signals(self, data, factors, date):
        """
        Generate trading signals based on factor rankings.
        
        Args:
            data (pd.DataFrame): Historical price data.
            factors (pd.DataFrame): Factor data for the current date.
            date (datetime.date): Current date.
            
        Returns:
            pd.DataFrame: DataFrame with trading signals.
        """
        # Filter factors for the current date
        current_factors = factors[factors.index == date]
        
        if current_factors.empty:
            return pd.DataFrame(columns=['symbol', 'signal', 'weight'])
            
        # Rank securities based on factor values
        ranked_securities = current_factors.sort_values('combined_factor', ascending=False)
        
        # Determine number of securities for long and short positions
        universe_size = len(ranked_securities)
        long_count = int(universe_size * self.long_pct)
        short_count = int(universe_size * self.short_pct)
        
        # Create signals DataFrame
        signals = []
        
        # Long signals
        for i, (idx, row) in enumerate(ranked_securities.head(long_count).iterrows()):
            symbol = row['symbol'] if 'symbol' in row else row['ticker']
            # Check if symbol is in cooldown period
            if not self.check_cooldown(symbol, date):
                signals.append({
                    'symbol': symbol,
                    'signal': 1,  # Long
                    'weight': min(1.0 / long_count, self.max_position_size)
                })
        
        # Short signals
        for i, (idx, row) in enumerate(ranked_securities.tail(short_count).iterrows()):
            symbol = row['symbol'] if 'symbol' in row else row['ticker']
            # Check if symbol is in cooldown period
            if not self.check_cooldown(symbol, date):
                signals.append({
                    'symbol': symbol,
                    'signal': -1,  # Short
                    'weight': min(1.0 / short_count, self.max_position_size)
                })
        
        return pd.DataFrame(signals)
    
    def rebalance(self, current_positions, signals, prices, date, cash=None):
        """
        Rebalance the portfolio based on signals.
        
        Args:
            current_positions (dict): Current positions {symbol: quantity}.
            signals (pd.DataFrame): Trading signals.
            prices (dict): Current prices {symbol: price}.
            date (datetime.date): Current date.
            cash (float, optional): Current cash balance. Used when calculating total portfolio value.
            
        Returns:
            dict: New positions after rebalancing.
        """
        new_positions = current_positions.copy()
        
        # Calculate current position value
        position_value = sum(current_positions.get(symbol, 0) * prices.get(symbol, 0) 
                            for symbol in current_positions)
        
        # Calculate total portfolio value (positions + cash)
        portfolio_value = position_value
        if cash is not None:
            portfolio_value += cash
        
        # If portfolio value is still zero, we can't proceed with meaningful allocations
        if portfolio_value <= 0:
            return new_positions
        
        # Close positions not in signals
        signal_symbols = set(signals['symbol'])
        for symbol in list(current_positions.keys()):
            if symbol not in signal_symbols and current_positions[symbol] != 0:
                new_positions[symbol] = 0
        
        # Open or adjust positions based on signals
        for _, row in signals.iterrows():
            symbol = row['symbol']
            signal = row['signal']
            weight = row['weight']
            
            if symbol not in prices:
                continue
                
            target_value = portfolio_value * weight * signal
            target_quantity = int(target_value / prices[symbol])
            
            new_positions[symbol] = target_quantity
            
        return new_positions
