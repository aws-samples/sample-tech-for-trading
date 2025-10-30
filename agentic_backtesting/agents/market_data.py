"""
Market Data Agent - Fetches and processes market data from Redshift using MCP
"""

import pandas as pd
from datetime import datetime, timedelta
from .base_agent import BaseAgent
from typing import Dict, Any, List
import boto3
import json

class MarketDataAgent(BaseAgent):
    """Agent that handles market data fetching from Redshift via MCP"""
    
    def __init__(self, mcp_client=None):
        super().__init__("MarketData")
        self.mcp_client = mcp_client
        self.schema_prompt = """
        Database Schema:
        Table: daily_data
        Columns:
        - symbol (varchar): Stock symbol (e.g., 'AMZN', 'AAPL')
        - timestamp (date): Trading date
        - open (decimal): Opening price
        - high (decimal): Highest price
        - low (decimal): Lowest price  
        - close (decimal): Closing price
        - volume (bigint): Trading volume
        """
    
    def _generate_sql_query(self, symbols: List[str], start_date, end_date) -> str:
        """Generate SQL query using Bedrock OpenAI GPT-OSS-120B"""
        prompt = f"""
        {self.schema_prompt}
        
        Generate a SQL query to:
        - Select timestamp as Date, open as Open, high as High, low as Low, close as Close, volume as Volume
        - From daily_data table
        - Filter by symbols: {symbols}
        - Date range: {start_date} to {end_date}
        - Order by timestamp ascending

        because Open High Low Close Volume Date are keywords, please use double quotatation to include them, such as open as "Open"
        
        Return only the SQL query without explanation.
        """
        
        try:
            sql = self.invoke_sync(prompt)
            return sql
            
        except Exception as e:
            print(f"❌ Error generating SQL with Bedrock: {e}")
            # Fallback to hardcoded query
            symbols_str = "', '".join(symbols)
            return f"""
            SELECT 
                timestamp as "Date",
                open as "Open", 
                high as "High",
                low as "Low",
                close as "Close",
                volume as "Volume"
            FROM daily_data
            WHERE symbol IN ('{symbols_str}')
            AND timestamp >= '{start_date}'
            AND timestamp <= '{end_date}'
            ORDER BY timestamp
            """
    
    def get_data(self, symbols: List[str] = None, period: str = '2y') -> Dict[str, pd.DataFrame]:
        """Fetch market data using MCP Redshift server"""
        if symbols is None:
            symbols = ['AMZN']
        
        # Calculate date range
        end_date = datetime.now().date()
        days_map = {'1y': 365, '2y': 730, '3y': 1095, '5y': 1825}
        start_date = end_date - timedelta(days=days_map.get(period, 730))
        
        # Generate SQL query
        query = self._generate_sql_query(symbols, start_date, end_date)
        print(f"USE query: {query}")
        
        try:
            # Execute query via MCP
            if self.mcp_client:
                result = self.mcp_client.call_tool("execute_query", {"query": query})
                df = pd.DataFrame(result.get('data', []))
            else:
                # Fallback for testing
                df = pd.DataFrame()
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                
                # Split by symbol
                data = {}
                for symbol in symbols:
                    symbol_data = df[df.index.isin(df.index)]  # Placeholder logic
                    if not symbol_data.empty:
                        data[symbol] = symbol_data
                
                return data
            
        except Exception as e:
            print(f"❌ Error fetching data: {e}")
        
        return {}
    
    def process(self, input_data: Any) -> Any:
        """Process data request and return market data"""
        if isinstance(input_data, dict):
            symbols = input_data.get('symbols', ['AMZN'])
            period = input_data.get('period', '2y')
        else:
            symbols = ['AMZN']
            period = '2y'
        
        return self.get_data(symbols, period)
