import pandas as pd
import numpy as np
import os
import datetime
from clickhouse_driver import Client
from enum import Enum


class WeightingMethod(Enum):
    """Enum for factor weighting methods"""
    RSQUARED = 1
    TSTAT = 2
    EQUAL = 3
    BETA = 4


class DataLoader:
    """
    Utility class for loading price and factor data from ClickHouse.
    """
    
    def __init__(self, 
                 host,
                 port,
                 user,
                 password,
                 database):
        """
        Initialize the data loader.
        
        Args:
            host (str): ClickHouse host.
            port (int): ClickHouse port.
            user (str): ClickHouse user.
            password (str): ClickHouse password.
            database (str): ClickHouse database.
        """
        self.client = Client(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
    def load_data(self, start_date, end_date, symbols=None, factors=None, weighting_method=WeightingMethod.RSQUARED):
        """
        Load price and factor data for the specified date range.
        
        Args:
            start_date (datetime.date): Start date.
            end_date (datetime.date): End date.
            symbols (list, optional): List of symbols to load data for.
            factors (list, optional): List of factor names to use (default: ['DebtToEquity', 'NewsSentiment']).
            weighting_method (WeightingMethod, optional): Method to weight factors (default: RSQUARED).
            
        Returns:
            dict: Dictionary with price and factor data.
        """
        # Format dates for SQL query
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Default factors if none provided
        if factors is None:
            factors = ['DebtToEquity', 'NewsSentiment']
        
        # Build symbol filter
        symbol_filter = ""
        if symbols:
            symbol_list = "', '".join(symbols)
            symbol_filter = f"AND ticker IN ('{symbol_list}')"
        
        # Build factor filter
        factor_list = "', '".join(factors)
        factor_filter = f"AND factor_name IN ('{factor_list}')"
        
        # Query price data
        price_query = f"""
        SELECT 
            symbol,
            timestamp,
            open,
            high,
            low,
            close,
            volume
        FROM tick_data
        WHERE timestamp >= '{start_date_str}' AND timestamp <= '{end_date_str}'
        {symbol_filter.replace('ticker', 'symbol')}
        ORDER BY symbol, timestamp
        """
        
        price_data = self.client.execute(price_query)
        
        # Query individual factor data
        factor_query = f"""
        SELECT 
            factor_name,
            ticker,
            date,
            value,
            update_time
        FROM factor_values
        WHERE date >= '{start_date_str}' AND date <= '{end_date_str}'
        {symbol_filter}
        {factor_filter}
        ORDER BY ticker, date, factor_name
        """
        
        factor_data = self.client.execute(factor_query)
        
        # Query factor effectiveness metrics (latest test_date for each factor and ticker)
        factor_details_query = f"""
        WITH latest_tests AS (
            SELECT 
                factor_name,
                ticker,
                MAX(test_date) as latest_test_date
            FROM factor_details
            WHERE 1=1
            {symbol_filter}
            {factor_filter}
            GROUP BY factor_name, ticker
        )
        SELECT 
            fd.factor_name,
            fd.ticker,
            fd.test_date,
            fd.beta,
            fd.tstat,
            fd.rsquared
        FROM factor_details fd
        INNER JOIN latest_tests lt
            ON fd.factor_name = lt.factor_name
            AND fd.ticker = lt.ticker
            AND fd.test_date = lt.latest_test_date
        ORDER BY fd.ticker, fd.factor_name
        """
        
        factor_details = self.client.execute(factor_details_query)
        
        # Process price data
        price_df = pd.DataFrame(
            price_data, 
            columns=['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
        )
        
        # Process factor data
        factor_df = pd.DataFrame(
            factor_data,
            columns=['factor_name', 'ticker', 'date', 'value', 'update_time']
        )
        
        # Process factor details data
        factor_details_df = pd.DataFrame(
            factor_details,
            columns=['factor_name', 'ticker', 'test_date', 'beta', 'tstat', 'rsquared']
        )
        
        # Calculate combined factor values using the specified weighting method
        combined_factors_df = self._calculate_combined_factors(factor_df, factor_details_df, weighting_method)
        
        # Convert to dictionary of DataFrames by symbol
        price_data_dict = {}
        factor_data_dict = {}
        raw_factor_data_dict = {}
        factor_details_dict = {}
        
        # Process price data by symbol
        for symbol in price_df['symbol'].unique():
            # Price data
            symbol_price = price_df[price_df['symbol'] == symbol].copy()
            symbol_price.set_index('date', inplace=True)
            symbol_price.drop('symbol', axis=1, inplace=True)
            price_data_dict[symbol] = symbol_price
        
        # Process factor data by ticker
        for ticker in combined_factors_df['ticker'].unique():
            # Combined factor data
            ticker_factor = combined_factors_df[combined_factors_df['ticker'] == ticker].copy()
            ticker_factor.set_index('date', inplace=True)
            factor_data_dict[ticker] = ticker_factor['combined_factor']
            
            # Raw factor data (individual factors)
            raw_factors = {}
            for factor_name in factors:
                factor_subset = factor_df[(factor_df['ticker'] == ticker) & (factor_df['factor_name'] == factor_name)].copy()
                if not factor_subset.empty:
                    factor_subset.set_index('date', inplace=True)
                    raw_factors[factor_name] = factor_subset['value']
            raw_factor_data_dict[ticker] = raw_factors
            
            # Factor details
            ticker_details = factor_details_df[factor_details_df['ticker'] == ticker].copy()
            if not ticker_details.empty:
                factor_details_dict[ticker] = ticker_details.set_index('factor_name')
        
        return {
            'price_data': price_data_dict,
            'factor_data': factor_data_dict,
            'raw_factor_data': raw_factor_data_dict,
            'factor_details': factor_details_dict
        }
    
    def _calculate_combined_factors(self, factor_df, factor_details_df, weighting_method):
        """
        Calculate combined factor values using the specified weighting method.
        
        Args:
            factor_df (pd.DataFrame): DataFrame with raw factor values.
            factor_details_df (pd.DataFrame): DataFrame with factor effectiveness metrics.
            weighting_method (WeightingMethod): Method to weight factors.
            
        Returns:
            pd.DataFrame: DataFrame with combined factor values.
        """
        # Create a pivot table of factor values
        factor_pivot = factor_df.pivot_table(
            index=['ticker', 'date'],
            columns='factor_name',
            values='value',
            aggfunc='first'
        ).reset_index()
        
        # Get the weight column based on the weighting method
        if weighting_method == WeightingMethod.RSQUARED:
            weight_col = 'rsquared'
        elif weighting_method == WeightingMethod.TSTAT:
            weight_col = 'tstat'
        elif weighting_method == WeightingMethod.BETA:
            weight_col = 'beta'
        else:  # Equal weighting
            weight_col = None
        
        # Calculate combined factor values
        combined_factors = []
        
        for ticker in factor_pivot['ticker'].unique():
            ticker_data = factor_pivot[factor_pivot['ticker'] == ticker].copy()
            ticker_details = factor_details_df[factor_details_df['ticker'] == ticker].copy()
            
            if ticker_details.empty:
                # Skip if no factor details available
                continue
            
            # Get factor names from the pivot table (excluding 'ticker' and 'date')
            factor_names = [col for col in ticker_data.columns if col not in ['ticker', 'date']]
            
            # Calculate weights
            if weight_col is None:
                # Equal weighting
                weights = {factor: 1.0 / len(factor_names) for factor in factor_names}
            else:
                # Get weights from factor details
                weights = {}
                weight_sum = 0
                
                for factor in factor_names:
                    factor_weight = ticker_details[ticker_details['factor_name'] == factor][weight_col].values
                    if len(factor_weight) > 0:
                        weights[factor] = abs(factor_weight[0])  # Use absolute value
                        weight_sum += weights[factor]
                    else:
                        weights[factor] = 0
                
                # Normalize weights
                if weight_sum > 0:
                    for factor in weights:
                        weights[factor] /= weight_sum
            
            # Calculate combined factor values
            for _, row in ticker_data.iterrows():
                combined_value = 0
                for factor in factor_names:
                    if factor in row and not pd.isna(row[factor]) and factor in weights:
                        combined_value += row[factor] * weights[factor]
                
                combined_factors.append({
                    'ticker': row['ticker'],
                    'date': row['date'],
                    'combined_factor': combined_value
                })
        
        return pd.DataFrame(combined_factors)
