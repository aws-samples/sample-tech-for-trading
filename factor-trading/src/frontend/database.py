import os
import pandas as pd
import clickhouse_connect
from typing import List, Dict, Any, Optional
from datetime import datetime
import streamlit as st

class ClickHouseConnection:
    def __init__(self):
        self.host = os.getenv('CLICKHOUSE_HOST', '44.222.122.134')
        self.port = int(os.getenv('CLICKHOUSE_PORT', 8123))  # Use HTTP port 8123
        self.user = os.getenv('CLICKHOUSE_USER', 'default')
        self.password = os.getenv('CLICKHOUSE_PASSWORD', 'clickhouse@aws')
        self.database = os.getenv('CLICKHOUSE_DATABASE', 'factor_model_tick_data_database')
        self.client = None
        
    def connect(self):
        """Establish connection to ClickHouse"""
        try:
            # Try HTTP connection first (port 8123)
            self.client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                database=self.database
            )
            # Test the connection
            self.client.command('SELECT 1')
            return True
        except Exception as e:
            st.error(f"HTTP connection failed: {str(e)}")
            try:
                # Fallback to native TCP connection (port 9000)
                st.info("Trying native TCP connection...")
                self.client = clickhouse_connect.get_client(
                    host=self.host,
                    port=9000,
                    username=self.user,
                    password=self.password,
                    database=self.database
                )
                # Test the connection
                self.client.command('SELECT 1')
                return True
            except Exception as e2:
                st.error(f"Native TCP connection also failed: {str(e2)}")
                st.error("Please check your ClickHouse server configuration and network connectivity")
                return False
    
    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute query and return results as DataFrame"""
        if not self.client:
            if not self.connect():
                return pd.DataFrame()
        
        try:
            result = self.client.query_df(query)
            return result
        except Exception as e:
            st.error(f"Query execution failed: {str(e)}")
            st.error(f"Query: {query}")
            return pd.DataFrame()
    
    def get_backtests(self, 
                     strategy_filter: Optional[str] = None,
                     start_date_filter: Optional[str] = None,
                     end_date_filter: Optional[str] = None,
                     factors_filter: Optional[List[str]] = None) -> pd.DataFrame:
        """Get backtest results with optional filters"""
        
        query = """
        SELECT 
            backtest_id,
            strategy_id,
            start_date,
            end_date,
            initial_capital,
            final_capital,
            rebalance_period,
            take_profit_pct,
            stop_loss_pct,
            cooldown_period,
            max_position_size,
            factors,
            weighting_method,
            sharpe_ratio,
            max_drawdown,
            max_drawdown_date,
            total_return,
            annual_return,
            num_trades,
            win_rate,
            profit_factor,
            strategy_parameters,
            created_at,
            run_by,
            notes
        FROM backtests
        WHERE 1=1
        """
        
        conditions = []
        
        if strategy_filter:
            conditions.append(f"strategy_id IN (SELECT strategy_id FROM strategy_definitions WHERE strategy_name = '{strategy_filter}')")
        
        if start_date_filter:
            conditions.append(f"start_date >= '{start_date_filter}'")
            
        if end_date_filter:
            conditions.append(f"end_date <= '{end_date_filter}'")
            
        if factors_filter and len(factors_filter) > 0:
            # Assuming factors is stored as an array in ClickHouse
            factors_condition = " OR ".join([f"has(factors, '{factor}')" for factor in factors_filter])
            conditions.append(f"({factors_condition})")
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
            
        query += " ORDER BY created_at DESC"
        
        return self.execute_query(query)
    
    def get_strategy_definitions(self) -> pd.DataFrame:
        """Get all strategy definitions"""
        query = "SELECT * FROM strategy_definitions ORDER BY strategy_name"
        return self.execute_query(query)
    
    def get_available_factors(self) -> List[str]:
        """Get all unique factors used in backtests"""
        query = """
        SELECT DISTINCT arrayJoin(factors) as factor 
        FROM backtests 
        WHERE factors IS NOT NULL AND length(factors) > 0
        ORDER BY factor
        """
        result = self.execute_query(query)
        return result['factor'].tolist() if not result.empty else []
    
    def get_backtest_orders(self, backtest_id: str) -> pd.DataFrame:
        """Get orders for a specific backtest"""
        query = f"""
        SELECT 
            order_id,
            date,
            symbol,
            order_type,
            order_price,
            order_size,
            order_value,
            execution_status,
            execution_price,
            reason
        FROM backtest_orders 
        WHERE backtest_id = '{backtest_id}'
        ORDER BY date, symbol
        """
        return self.execute_query(query)
    
    def get_backtest_trades(self, backtest_id: str) -> pd.DataFrame:
        """Get trades for a specific backtest"""
        query = f"""
        SELECT 
            trade_id,
            symbol,
            entry_date,
            entry_price,
            entry_size,
            entry_value,
            exit_date,
            exit_price,
            exit_size,
            exit_value,
            pnl,
            pnl_pct,
            duration_days,
            exit_reason
        FROM backtest_trades 
        WHERE backtest_id = '{backtest_id}'
        ORDER BY entry_date, symbol
        """
        return self.execute_query(query)
    
    def get_best_backtests(self, metric: str, limit: int = 10) -> pd.DataFrame:
        """Get best performing backtests by specified metric"""
        
        metric_mapping = {
            'annual_return': 'annual_return DESC',
            'sharpe_ratio': 'sharpe_ratio DESC',
            'win_rate': 'win_rate DESC',
            'max_drawdown': 'max_drawdown ASC',  # Lower is better for drawdown
            'profit_factor': 'profit_factor DESC',
            'total_return': 'total_return DESC'
        }
        
        if metric not in metric_mapping:
            return pd.DataFrame()
        
        query = f"""
        SELECT 
            backtest_id,
            strategy_id,
            start_date,
            end_date,
            initial_capital,
            final_capital,
            {metric},
            strategy_parameters,
            factors,
            weighting_method,
            created_at,
            run_by
        FROM backtests
        WHERE {metric} IS NOT NULL
        ORDER BY {metric_mapping[metric]}
        LIMIT {limit}
        """
        
        return self.execute_query(query)
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection and return connection info"""
        try:
            if not self.client:
                if not self.connect():
                    return {"status": "failed", "error": "Could not establish connection"}
            
            # Test basic query
            result = self.client.command('SELECT version()')
            
            # Get table info
            tables_query = "SHOW TABLES"
            tables = self.client.query_df(tables_query)
            
            return {
                "status": "success",
                "version": result,
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "tables": tables['name'].tolist() if not tables.empty else []
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def close(self):
        """Close the connection"""
        if self.client:
            self.client.close()
