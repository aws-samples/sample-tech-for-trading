#!/usr/bin/env python3
"""
Script to insert random sentiment data for DJIA 30 stocks into ClickHouse.
"""

import random
import datetime
from clickhouse_driver import Client
import pandas as pd
import numpy as np

# ClickHouse connection parameters
CLICKHOUSE_HOST = 'localhost'
CLICKHOUSE_PORT = 9000
CLICKHOUSE_USER = 'default'
CLICKHOUSE_PASSWORD = 'password'
CLICKHOUSE_DATABASE = 'factor_modelling'

# DJIA 30 tickers
tickers = [
    'AAPL', 'AMGN', 'AMZN', 'AXP', 'BA', 'CAT', 'CRM', 'CSCO', 'CVX', 'DIS',
    'GS', 'HD', 'HON', 'IBM', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM', 'MRK',
    'MSFT', 'NKE', 'NVDA', 'PG', 'SHW', 'TRV', 'UNH', 'V', 'VZ', 'WMT'
]

# Date range
start_date = datetime.date(2020, 1, 2)
end_date = datetime.date(2025, 4, 26)

def generate_data():
    """Generate random sentiment data for all tickers and dates."""
    data = []
    
    # Generate a date range (business days only)
    date_range = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # For each ticker and date, generate a random sentiment value
    for ticker in tickers:
        for date in date_range:
            # Generate a random value between -1.0 and 1.0
            sentiment_value = random.uniform(-1.0, 1.0)
            
            # Add the data point
            data.append({
                'factor_type': 'Sentiment',
                'factor_name': 'NewsSentiment',
                'ticker': ticker,
                'date': date.date(),
                'value': sentiment_value
            })
    
    return data

def insert_data(data):
    """Insert data into ClickHouse."""
    # Connect to ClickHouse
    client = Client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DATABASE
    )
    
    # Insert data in batches to avoid memory issues
    batch_size = 10000
    total_records = len(data)
    batches = (total_records + batch_size - 1) // batch_size  # Ceiling division
    
    for i in range(batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, total_records)
        
        batch_data = data[start_idx:end_idx]
        
        # Format data as a list of tuples, where each tuple is a row
        rows = [(
            item['factor_type'],
            item['factor_name'],
            item['ticker'],
            item['date'],
            item['value']
        ) for item in batch_data]
        
        # Insert the batch
        client.execute(
            'INSERT INTO factor_values (factor_type, factor_name, ticker, date, value) VALUES',
            rows
        )
        
        print(f"Inserted batch {i+1}/{batches} ({len(rows)} records)")

def main():
    """Main function."""
    print("Generating random sentiment data...")
    data = generate_data()
    
    print(f"Generated {len(data)} records. Inserting into ClickHouse...")
    insert_data(data)
    
    print("Data insertion complete!")

if __name__ == "__main__":
    main()
