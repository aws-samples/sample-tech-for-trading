"""
Database manager for interacting with ClickHouse database.
"""

import json
import uuid
import datetime
import os
import sys
import traceback
from clickhouse_driver import Client

from .db_schema import CREATE_TABLES


class DBManager:
    """
    Database manager for interacting with ClickHouse database.
    """
    
    def __init__(self, host, port, user, password, database):
        """
        Initialize the database manager.
        
        Args:
            host (str): ClickHouse host.
            port (int): ClickHouse port.
            user (str): ClickHouse user.
            password (str): ClickHouse password.
            database (str): ClickHouse database.
        """
        try:
            self.client = Client(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error connecting to ClickHouse database: {e}")
            print(f"Stack trace:\n{error_trace}")
            raise
        
    def initialize_schema(self):
        """
        Initialize the database schema by creating all required tables.
        """
        try:
            for create_table_sql in CREATE_TABLES:
                self.client.execute(create_table_sql)
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error initializing database schema: {e}")
            print(f"Stack trace:\n{error_trace}")
            raise
            
    def save_strategy(self, strategy_name, strategy_class, strategy_description, strategy_parameters, created_by):
        """
        Save a strategy definition to the database.
        
        Args:
            strategy_name (str): Name of the strategy.
            strategy_class (str): Class name of the strategy.
            strategy_description (str): Description of the strategy.
            strategy_parameters (dict): Parameters of the strategy.
            created_by (str): User who created the strategy.
            
        Returns:
            str: ID of the created strategy.
        """
        try:
            strategy_id = str(uuid.uuid4())
            parameters_json = json.dumps(strategy_parameters)
            
            query = """
            INSERT INTO strategy_definitions 
            (strategy_id, strategy_name, strategy_class, strategy_description, strategy_parameters, created_by)
            VALUES
            """
            
            self.client.execute(
                query,
                [
                    (
                        strategy_id,
                        strategy_name,
                        strategy_class,
                        strategy_description,
                        parameters_json,
                        created_by
                    )
                ]
            )
            
            return strategy_id
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error saving strategy: {e}")
            print(f"Stack trace:\n{error_trace}")
            raise
    
    def save_backtest(self, strategy_id, start_date, end_date, initial_capital, final_capital,
                     rebalance_period, take_profit_pct, stop_loss_pct, cooldown_period,
                     max_position_size, factors, weighting_method, metrics, strategy_parameters,
                     run_by, notes=""):
        """
        Save backtest results to the database.
        
        Args:
            strategy_id (str): ID of the strategy.
            start_date (datetime.date): Start date of the backtest.
            end_date (datetime.date): End date of the backtest.
            initial_capital (float): Initial capital for the backtest.
            final_capital (float): Final capital after the backtest.
            rebalance_period (int): Rebalance period in days.
            take_profit_pct (float): Take profit percentage.
            stop_loss_pct (float): Stop loss percentage.
            cooldown_period (int): Cooldown period in days.
            max_position_size (float): Maximum position size as percentage.
            factors (list): List of factors used.
            weighting_method (str): Method used to weight factors.
            metrics (dict): Performance metrics.
            strategy_parameters (dict): Strategy-specific parameters.
            run_by (str): User who ran the backtest.
            notes (str): Additional notes.
            
        Returns:
            str: ID of the created backtest.
        """
        try:
            backtest_id = str(uuid.uuid4())
            strategy_params_json = json.dumps(strategy_parameters)
            
            query = """
            INSERT INTO backtests 
            (backtest_id, strategy_id, start_date, end_date, initial_capital, final_capital,
             rebalance_period, take_profit_pct, stop_loss_pct, cooldown_period, max_position_size,
             factors, weighting_method, sharpe_ratio, max_drawdown, max_drawdown_date, total_return,
             annual_return, num_trades, win_rate, profit_factor, strategy_parameters, run_by, notes)
            VALUES
            """
            
            # Extract metrics
            sharpe_ratio_raw = metrics.get('sharpe_ratio', 0.0)
            sharpe_ratio = 0 if sharpe_ratio_raw is None else float(sharpe_ratio_raw)
            max_drawdown = float(metrics.get('max_drawdown', 0.0))
            max_drawdown_date = datetime.datetime.now().date()  # Default to today if not available
            total_return = float(metrics.get('total_return', 0.0))
            annual_return = float(metrics.get('annual_return', 0.0))
            num_trades = int(metrics.get('num_trades', 0))
            win_rate = float(metrics.get('win_rate', 0.0))
            profit_factor = float(metrics.get('profit_factor', 0.0))
            
            self.client.execute(
                query,
                [
                    (
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
                        strategy_params_json,
                        run_by,
                        notes
                    )
                ]
            )
            
            return backtest_id
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error saving backtest: {e}")
            print(f"Stack trace:\n{error_trace}")
            raise
    
    def save_portfolio_snapshot(self, backtest_id, date, portfolio_value, cash, equity, 
                               portfolio_positions, is_initial=False, is_final=False):
        """
        Save a portfolio snapshot to the database.
        
        Args:
            backtest_id (str): ID of the backtest.
            date (datetime.date): Date of the snapshot.
            portfolio_value (float): Total portfolio value.
            cash (float): Cash amount.
            equity (float): Equity value.
            portfolio_positions (dict): Dictionary of portfolio positions.
            is_initial (bool): Whether this is the initial portfolio.
            is_final (bool): Whether this is the final portfolio.
            
        Returns:
            str: ID of the created portfolio snapshot.
        """
        try:
            portfolio_id = str(uuid.uuid4())
            positions_json = json.dumps(portfolio_positions)
            
            query = """
            INSERT INTO backtest_portfolios 
            (portfolio_id, backtest_id, date, portfolio_value, cash, equity, 
             is_initial, is_final, portfolio_snapshot)
            VALUES
            """
            
            self.client.execute(
                query,
                [
                    (
                        portfolio_id,
                        backtest_id,
                        date,
                        portfolio_value,
                        cash,
                        equity,
                        1 if is_initial else 0,
                        1 if is_final else 0,
                        positions_json
                    )
                ]
            )
            
            return portfolio_id
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error saving portfolio snapshot: {e}")
            print(f"Stack trace:\n{error_trace}")
            raise
    
    def save_order(self, backtest_id, date, symbol, order_type, order_price, order_size, 
                  order_value, execution_status="PENDING", execution_price=None, reason=""):
        """
        Save an order to the database.
        
        Args:
            backtest_id (str): ID of the backtest.
            date (datetime.datetime): Date and time of the order.
            symbol (str): Symbol of the security.
            order_type (str): Type of order ('BUY' or 'SELL').
            order_price (float): Price of the order.
            order_size (float): Size of the order.
            order_value (float): Value of the order.
            execution_status (str): Status of the order.
            execution_price (float): Execution price of the order.
            reason (str): Reason for the order.
            
        Returns:
            str: ID of the created order.
        """
        try:
            order_id = str(uuid.uuid4())
            
            query = """
            INSERT INTO backtest_orders 
            (order_id, backtest_id, date, symbol, order_type, order_price, order_size, 
             order_value, execution_status, execution_price, reason)
            VALUES
            """
            
            self.client.execute(
                query,
                [
                    (
                        order_id,
                        backtest_id,
                        date,
                        symbol,
                        order_type,
                        order_price,
                        order_size,
                        order_value,
                        execution_status,
                        execution_price,
                        reason
                    )
                ]
            )
            
            return order_id
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error saving order: {e}")
            print(f"Stack trace:\n{error_trace}")
            raise
    
    def save_trade(self, backtest_id, symbol, entry_date, entry_price, entry_size, entry_value,
                  exit_date, exit_price, exit_size, exit_value, pnl, pnl_pct, exit_reason):
        """
        Save a trade to the database.
        
        Args:
            backtest_id (str): ID of the backtest.
            symbol (str): Symbol of the security.
            entry_date (datetime.datetime): Date and time of entry.
            entry_price (float): Entry price.
            entry_size (float): Entry size.
            entry_value (float): Entry value.
            exit_date (datetime.datetime): Date and time of exit.
            exit_price (float): Exit price.
            exit_size (float): Exit size.
            exit_value (float): Exit value.
            pnl (float): Profit and loss.
            pnl_pct (float): Profit and loss percentage.
            exit_reason (str): Reason for exit.
            
        Returns:
            str: ID of the created trade.
        """
        try:
            trade_id = str(uuid.uuid4())
            duration_days = (exit_date - entry_date).total_seconds() / (24 * 3600)
            
            query = """
            INSERT INTO backtest_trades 
            (trade_id, backtest_id, symbol, entry_date, entry_price, entry_size, entry_value,
             exit_date, exit_price, exit_size, exit_value, pnl, pnl_pct, duration_days, exit_reason)
            VALUES
            """
            
            self.client.execute(
                query,
                [
                    (
                        trade_id,
                        backtest_id,
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
                    )
                ]
            )
            
            return trade_id
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error saving trade: {e}")
            print(f"Stack trace:\n{error_trace}")
            raise
    
    def save_portfolio_snapshots_batch(self, backtest_id, snapshots, batch_size=1000):
        """
        Save multiple portfolio snapshots to the database in batches.
        
        Args:
            backtest_id (str): ID of the backtest.
            snapshots (list): List of portfolio snapshot dictionaries.
            batch_size (int): Number of records per batch.
            
        Returns:
            int: Number of snapshots saved.
        """
        try:
            if not snapshots:
                return 0
                
            total_saved = 0
            
            # Process in batches of batch_size
            for i in range(0, len(snapshots), batch_size):
                batch = snapshots[i:i+batch_size]
                values = []
                
                for snapshot in batch:
                    portfolio_id = str(uuid.uuid4())
                    positions_json = json.dumps(snapshot['positions'])
                    
                    values.append((
                        portfolio_id,
                        backtest_id,
                        snapshot['date'],
                        snapshot['portfolio_value'],
                        snapshot['cash'],
                        snapshot['equity'],
                        1 if snapshot.get('is_initial', False) else 0,
                        1 if snapshot.get('is_final', False) else 0,
                        positions_json
                    ))
                
                query = """
                INSERT INTO backtest_portfolios 
                (portfolio_id, backtest_id, date, portfolio_value, cash, equity, 
                 is_initial, is_final, portfolio_snapshot)
                VALUES
                """
                
                self.client.execute(query, values)
                total_saved += len(values)
                print(f"Saved batch of {len(values)} portfolio snapshots ({total_saved}/{len(snapshots)})")
            
            return total_saved
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error saving portfolio snapshots batch: {e}")
            print(f"Stack trace:\n{error_trace}")
            raise
    
    def save_orders_batch(self, backtest_id, orders, batch_size=1000):
        """
        Save multiple orders to the database in batches.
        
        Args:
            backtest_id (str): ID of the backtest.
            orders (list): List of order dictionaries.
            batch_size (int): Number of records per batch.
            
        Returns:
            int: Number of orders saved.
        """
        try:
            if not orders:
                return 0
                
            total_saved = 0
            
            # Process in batches of batch_size
            for i in range(0, len(orders), batch_size):
                batch = orders[i:i+batch_size]
                values = []
                
                for order in batch:
                    order_id = str(uuid.uuid4())
                    
                    values.append((
                        order_id,
                        backtest_id,
                        order['date'],
                        order['symbol'],
                        order['order_type'],
                        order['order_price'],
                        order['order_size'],
                        order['order_value'],
                        order.get('execution_status', 'PENDING'),
                        order.get('execution_price'),
                        order.get('reason', '')
                    ))
                
                query = """
                INSERT INTO backtest_orders 
                (order_id, backtest_id, date, symbol, order_type, order_price, order_size, 
                 order_value, execution_status, execution_price, reason)
                VALUES
                """
                
                self.client.execute(query, values)
                total_saved += len(values)
                print(f"Saved batch of {len(values)} orders ({total_saved}/{len(orders)})")
            
            return total_saved
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error saving orders batch: {e}")
            print(f"Stack trace:\n{error_trace}")
            raise
    
    def save_trades_batch(self, backtest_id, trades, batch_size=1000):
        """
        Save multiple trades to the database in batches.
        
        Args:
            backtest_id (str): ID of the backtest.
            trades (list): List of trade dictionaries.
            batch_size (int): Number of records per batch.
            
        Returns:
            int: Number of trades saved.
        """
        try:
            if not trades:
                return 0
                
            total_saved = 0
            
            # Process in batches of batch_size
            for i in range(0, len(trades), batch_size):
                batch = trades[i:i+batch_size]
                values = []
                
                for trade in batch:
                    trade_id = str(uuid.uuid4())
                    
                    # Calculate duration in days
                    entry_date = trade.get('entry_date')
                    exit_date = trade.get('exit_date')
                    if entry_date and exit_date:
                        duration_days = (exit_date - entry_date).total_seconds() / (24 * 3600)
                    else:
                        duration_days = 0
                    
                    values.append((
                        trade_id,
                        backtest_id,
                        trade.get('symbol', 'UNKNOWN'),
                        trade.get('entry_date'),
                        trade.get('entry_price', 0.0),
                        trade.get('entry_size', 0),
                        trade.get('entry_value', 0.0),
                        trade.get('exit_date'),
                        trade.get('exit_price', 0.0),
                        trade.get('exit_size', 0),
                        trade.get('exit_value', 0.0),
                        trade.get('pnl', 0.0),
                        trade.get('pnl_pct', 0.0),
                        duration_days,
                        trade.get('exit_reason', 'UNKNOWN')
                    ))
                
                query = """
                INSERT INTO backtest_trades 
                (trade_id, backtest_id, symbol, entry_date, entry_price, entry_size, entry_value,
                 exit_date, exit_price, exit_size, exit_value, pnl, pnl_pct, duration_days, exit_reason)
                VALUES
                """
                
                self.client.execute(query, values)
                total_saved += len(values)
                print(f"Saved batch of {len(values)} trades ({total_saved}/{len(trades)})")
            
            return total_saved
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error saving trades batch: {e}")
            print(f"Stack trace:\n{error_trace}")
            raise
    
    def get_backtest_results(self, backtest_id=None, strategy_id=None, start_date=None, end_date=None, limit=100):
        """
        Get backtest results from the database.
        
        Args:
            backtest_id (str, optional): ID of the backtest.
            strategy_id (str, optional): ID of the strategy.
            start_date (datetime.date, optional): Start date for filtering.
            end_date (datetime.date, optional): End date for filtering.
            limit (int, optional): Maximum number of results to return.
            
        Returns:
            list: List of backtest results.
        """
        try:
            conditions = []
            params = {}
            
            if backtest_id:
                conditions.append("backtest_id = %(backtest_id)s")
                params['backtest_id'] = backtest_id
                
            if strategy_id:
                conditions.append("strategy_id = %(strategy_id)s")
                params['strategy_id'] = strategy_id
                
            if start_date:
                conditions.append("start_date >= %(start_date)s")
                params['start_date'] = start_date
                
            if end_date:
                conditions.append("end_date <= %(end_date)s")
                params['end_date'] = end_date
                
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
            SELECT 
                b.backtest_id,
                b.strategy_id,
                s.strategy_name,
                b.start_date,
                b.end_date,
                b.initial_capital,
                b.final_capital,
                b.rebalance_period,
                b.take_profit_pct,
                b.stop_loss_pct,
                b.cooldown_period,
                b.max_position_size,
                b.factors,
                b.weighting_method,
                b.sharpe_ratio,
                b.max_drawdown,
                b.total_return,
                b.annual_return,
                b.num_trades,
                b.win_rate,
                b.profit_factor,
                b.created_at,
                b.run_by,
                b.notes
            FROM backtests b
            JOIN strategy_definitions s ON b.strategy_id = s.strategy_id
            WHERE {where_clause}
            ORDER BY b.created_at DESC
            LIMIT %(limit)s
            """
            
            params['limit'] = limit
            
            return self.client.execute(query, params)
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error getting backtest results: {e}")
            print(f"Stack trace:\n{error_trace}")
            raise
    
    def get_backtest_trades(self, backtest_id):
        """
        Get trades for a specific backtest.
        
        Args:
            backtest_id (str): ID of the backtest.
            
        Returns:
            list: List of trades.
        """
        try:
            query = """
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
            WHERE backtest_id = %(backtest_id)s
            ORDER BY entry_date
            """
            
            return self.client.execute(query, {'backtest_id': backtest_id})
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error getting backtest trades: {e}")
            print(f"Stack trace:\n{error_trace}")
            raise
    
    def get_backtest_portfolio_snapshots(self, backtest_id):
        """
        Get portfolio snapshots for a specific backtest.
        
        Args:
            backtest_id (str): ID of the backtest.
            
        Returns:
            list: List of portfolio snapshots.
        """
        try:
            query = """
            SELECT 
                portfolio_id,
                date,
                portfolio_value,
                cash,
                equity,
                is_initial,
                is_final,
                portfolio_snapshot
            FROM backtest_portfolios
            WHERE backtest_id = %(backtest_id)s
            ORDER BY date
            """
            
            return self.client.execute(query, {'backtest_id': backtest_id})
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error getting portfolio snapshots: {e}")
            print(f"Stack trace:\n{error_trace}")
            raise
    
    def get_backtest_orders(self, backtest_id):
        """
        Get orders for a specific backtest.
        
        Args:
            backtest_id (str): ID of the backtest.
            
        Returns:
            list: List of orders.
        """
        try:
            query = """
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
            WHERE backtest_id = %(backtest_id)s
            ORDER BY date
            """
            
            return self.client.execute(query, {'backtest_id': backtest_id})
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error getting backtest orders: {e}")
            print(f"Stack trace:\n{error_trace}")
            raise
