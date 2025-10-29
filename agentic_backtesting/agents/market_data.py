"""
Market Data Agent - Fetches and processes market data from Redshift
"""

import pandas as pd
import os
from datetime import datetime, timedelta
import psycopg2
from .base_agent import BaseAgent
from typing import Dict, Any, List

class MarketDataAgent(BaseAgent):
    """Agent that handles market data fetching from Redshift"""
    
    def __init__(self):
        super().__init__("MarketData")
        self.connection = self._init_redshift_connection()
        self.cache = {}
    
    def _init_redshift_connection(self):
        """Initialize Redshift connection from environment variables"""
        try:
            connection = psycopg2.connect(
                host=os.getenv('PGHOST', 'localhost'),
                port=int(os.getenv('PGPORT', 5439)),
                user=os.getenv('PGUSER', 'admin'),
                password=os.getenv('PGPASSWORD', ''),
                database=os.getenv('PGDATABASE', 'trading')
            )
            print(f"✅ Redshift connection successful")
            return connection
        except Exception as e:
            print(f"❌ Redshift connection failed: {e}")
            return None
    
    def get_data(self, symbols: List[str] = None, period: str = '2y') -> Dict[str, pd.DataFrame]:
        """Fetch market data from Redshift"""
        print(f"🔍 get_data called with symbols: {symbols}, period: {period}")
        
        if self.connection is None:
            print("❌ No Redshift connection, using fallback")

        if symbols is None:
            symbols = ['AMZN']
        
        print(f"📅 Calculating date range for period: {period}")
        # Calculate date range
        end_date = datetime.now().date()
        if period == '1y':
            start_date = end_date - timedelta(days=365)
        elif period == '2y':
            start_date = end_date - timedelta(days=730)
        elif period == '5y':
            start_date = end_date - timedelta(days=1825)
        elif period == '3y':
            start_date = end_date - timedelta(days=1095)
        else:
            start_date = end_date - timedelta(days=730)  # Default 2y
        
        print(f"📊 Date range: {start_date} to {end_date}")
        
        data = {}
        for symbol in symbols:
            print(f"🔄 Processing symbol: {symbol}")
            try:
                df = self._fetch_symbol_data(symbol, start_date, end_date)
                if not df.empty:
                    data[symbol] = df
                    print(f"✅ Successfully fetched data for {symbol}")
                else:
                    print(f"⚠️ No data returned for {symbol}")
            except Exception as e:
                print(f"❌ Error fetching data for {symbol}: {e}")
        
        print(f"📋 Final data keys: {list(data.keys())}")
        return data
    
    def _fetch_symbol_data(self, symbol: str, start_date, end_date) -> pd.DataFrame:
        """Fetch data for a single symbol from Redshift"""
        query = """
        SELECT 
            "timestamp" as "Date",
            "open" as "Open",
            "high" as "High",
            "low" as "Low",
            "close" as "Close",
            "volume" as "Volume"
        FROM daily_data
        WHERE symbol = %s
        AND timestamp >= %s
        AND timestamp <= %s
        ORDER BY timestamp
        """
        
        df = pd.read_sql_query(query, self.connection, params=[symbol, start_date, end_date])
        if not df.empty and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
        
        print(f"📊 Fetched {len(df)} rows of market data for {symbol}")
        return df
    
    def process(self, input_data: Any) -> Any:
        """Process data request and return market data"""
        print(f"🎯 MarketDataAgent.process called with: {input_data}")
        
        if isinstance(input_data, dict):
            symbols = input_data.get('symbols', ['AMZN'])
            period = input_data.get('period', '2y')
        else:
            symbols = ['AMZN']
            period = '2y'
        
        print(f"🔧 Processed params - symbols: {symbols}, period: {period}")
        result = self.get_data(symbols, period)
        print(f"📤 Returning result with keys: {list(result.keys()) if result else 'None'}")
        return result
