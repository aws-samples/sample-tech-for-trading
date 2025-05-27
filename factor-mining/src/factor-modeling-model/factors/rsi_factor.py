import pandas as pd
import numpy as np
from factors.base_factor import BaseFactor

class RSIFactor(BaseFactor):
    """RSI (Relative Strength Index) factor implementation"""
    
    def __init__(self, window=14):
        """
        Initialize the RSI factor
        
        Parameters:
        - window: RSI calculation window (default: 14)
        """
        self.window = window
        super().__init__(
            name=f"RSI{window}",
            factor_type="Technical",
            description=f"Relative Strength Index with {window}-day window. Measures momentum by comparing recent gains to recent losses."
        )
    
    def calculate(self, price_data):
        """
        Calculate RSI values from price data
        
        Parameters:
        - price_data: Dictionary of DataFrames with price data (key=ticker, value=DataFrame)
        
        Returns:
        - DataFrame with RSI values (index=dates, columns=tickers)
        """
        # Get all unique dates from price data
        all_dates = set()
        for ticker, df in price_data.items():
            all_dates.update(df.index)
        
        all_dates = sorted(list(all_dates))
        rsi_df = pd.DataFrame(index=all_dates)
        
        for ticker, df in price_data.items():
            if 'adjusted_close' in df.columns:
                # Calculate daily price changes
                delta = df['adjusted_close'].diff()
                
                # Separate gains and losses
                gain = delta.copy()
                loss = delta.copy()
                gain[gain < 0] = 0
                loss[loss > 0] = 0
                loss = abs(loss)
                
                # Calculate average gain and loss over the window
                avg_gain = gain.rolling(window=self.window).mean()
                avg_loss = loss.rolling(window=self.window).mean()
                
                # Calculate RS (Relative Strength)
                rs = avg_gain / avg_loss
                
                # Calculate RSI
                rsi = 100 - (100 / (1 + rs))
                
                # Add to DataFrame
                rsi_df[ticker] = rsi
        
        return rsi_df
