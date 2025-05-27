import pandas as pd
import numpy as np
import traceback
from datetime import datetime, date
from clickhouse_driver import Client
import os

final_start_date = os.getenv('START_DATE', '2020-01-01')
final_end_date = os.getenv('END_DATE', '2020-12-31')


class ClickHouseUtils:
    """Utility class for ClickHouse operations"""

    def __init__(self, host='44.222.122.134', port=9000, user='user', password='password',
                 database='factor_model_tick_data_database'):
        """Initialize ClickHouse connection"""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

        try:
            self.client = Client(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            print(f"Connected to ClickHouse at {self.host}:{self.port}")
        except Exception as e:
            print(f"Error connecting to ClickHouse: {str(e)}")
            print(traceback.format_exc())
            self.client = None

    def close(self):
        """Close ClickHouse connection"""
        if self.client:
            self.client = None
            print("ClickHouse connection closed")

    def create_factor_tables(self):
        """Create tables for storing factor analysis results"""
        try:
            # Create factor_summary table
            self.client.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.database}.factor_summary (
                factor_name String,
                factor_type String,
                test_date Date,
                start_date Date,
                end_date Date,
                avg_beta Float64,
                avg_tstat Float64,
                avg_rsquared Float64,
                significant_stocks Int32,
                total_stocks Int32,
                annualized_return Float64,
                annualized_volatility Float64,
                sharpe_ratio Float64,
                max_drawdown Float64,
                description String,
                update_time DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (factor_type, factor_name, test_date)
            """)

            # Create factor_details table
            self.client.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.database}.factor_details (
                factor_name String,
                factor_type String,
                test_date Date,
                ticker String,
                beta Float64,
                tstat Float64,
                pvalue Float64,
                rsquared Float64,
                conf_int_lower Float64,
                conf_int_upper Float64,
                update_time DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (factor_name, factor_type, test_date, ticker)
            """)

            # Create factor_timeseries table
            self.client.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.database}.factor_timeseries (
                factor_name String,
                factor_type String,
                date Date,
                factor_value Float64,
                high_portfolio_return Float64,
                low_portfolio_return Float64,
                update_time DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (factor_name, factor_type, date)
            """)

            # Create factor_values table for storing raw factor values
            self.client.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.database}.factor_values (
                factor_type String,
                factor_name String,
                ticker String,
                date Date,
                value Float64,
                update_time DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (factor_type, factor_name, ticker, date)
            """)

            # Create temporary table for stock returns
            self.client.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.database}.temp_stock_returns (
                ticker String,
                date Date,
                return_value Float64,
                update_time DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (ticker, date)
            """)

            # Create stock fundamental factors source table
            self.client.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.database}.stock_fundamental_factors_source (
                ticker String,
                cik String,
                accession_number String,
                end_date Date,
                filed_date Date,
                form String,
                fiscal_year Int32,
                fiscal_quarter Int32,
                assets_current Float64,
                liabilities_current Float64,
                cash_and_equivalents Float64,
                inventory_net Float64,
                inventory_net_prev_year Float64,
                stockholders_equity Float64,
                sales_revenue_net Float64,
                sales_revenue_net_prev_year Float64,
                cost_of_goods_sold Float64,
                interest_expense Float64,
                income_before_taxes Float64,
                source_file String,
                processed_timestamp DateTime,
                create_datetime DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (ticker, end_date, filed_date)
            """)

            print("Factor tables created successfully")
            return True

        except Exception as e:
            print(f"Error creating factor tables: {str(e)}")
            print(traceback.format_exc())
            return False

    def store_factor_values(self, factor_type, factor_name, factor_df):
        """
        Store raw factor values in the database

        Parameters:
        - factor_type: Type of factor (e.g., 'Technical', 'Fundamental')
        - factor_name: Name of the factor (e.g., 'RSI14', 'PEG')
        - factor_df: DataFrame with factor values (index=dates, columns=tickers)

        Returns:
        - success: Boolean indicating if operation was successful
        """
        try:
            print(f"Storing {factor_name} values in ClickHouse...")

            # Prepare data for insertion
            data = []
            for date in factor_df.index:
                date_str = datetime.today()
                for ticker in factor_df.columns:
                    value = factor_df.loc[date, ticker]
                    if pd.notna(value):
                        data.append((
                            factor_type,
                            factor_name,
                            ticker,
                            date_str,
                            float(value)
                        ))

            if data:
                # Insert data into factor_values table
                self.client.execute(
                    f"INSERT INTO {self.database}.factor_values "
                    "(factor_type, factor_name, ticker, date, value) VALUES",
                    data
                )
                print(f"Successfully stored {len(data)} {factor_name} values")
                return True
            else:
                print(f"No valid {factor_name} values to store")
                return False

        except Exception as e:
            print(f"Error storing factor values: {str(e)}")
            print(traceback.format_exc())
            return False

    def store_factor_summary(self, factor_name, factor_type, results_dict, start_date, end_date, description=""):
        """
        Store factor summary statistics in ClickHouse

        Parameters:
        - factor_name: Name of the factor
        - factor_type: Type of factor (e.g., 'Technical', 'Fundamental')
        - results_dict: Dictionary containing test results
        - description: Optional description of the factor

        Returns:
        - success: Boolean indicating if operation was successful
        """
        try:
            print(f"Storing {factor_name} factor summary in ClickHouse...")

            # Extract data from results_dict
            factor_test_results = results_dict.get('factor_test_results', pd.DataFrame())
            performance_results = results_dict.get('performance_results', pd.DataFrame())

            # Prepare summary data
            test_date = datetime.today()

            # Calculate summary statistics
            avg_beta = float(factor_test_results['beta'].mean()) if 'beta' in factor_test_results else 0.0
            avg_tstat = float(factor_test_results['tstat'].mean()) if 'tstat' in factor_test_results else 0.0
            avg_rsquared = float(factor_test_results['rsquared'].mean()) if 'rsquared' in factor_test_results else 0.0

            significant_stocks = int(
                (abs(factor_test_results['tstat']) > 1.96).sum()) if 'tstat' in factor_test_results else 0
            total_stocks = len(factor_test_results) if not factor_test_results.empty else 0

            # Get performance metrics
            factor_col = f'{factor_name}_Factor'
            if not performance_results.empty and 'Annualized Return' in performance_results and factor_col in \
                    performance_results['Annualized Return']:
                ann_return = float(performance_results['Annualized Return'][factor_col])
                ann_vol = float(performance_results['Annualized Volatility'][factor_col])
                sharpe = float(performance_results['Sharpe Ratio'][factor_col])
                max_dd = float(performance_results['Maximum Drawdown'][factor_col])
            else:
                ann_return = 0.0
                ann_vol = 0.0
                sharpe = 0.0
                max_dd = 0.0

            # Insert summary into database using SQL directly
            self.client.execute(f"""
            INSERT INTO {self.database}.factor_summary 
            (factor_name, factor_type, test_date, start_date, end_date, avg_beta, avg_tstat, avg_rsquared, 
             significant_stocks, total_stocks, annualized_return, annualized_volatility, 
             sharpe_ratio, max_drawdown, description)
            VALUES
            ('{factor_name}', '{factor_type}', '{test_date}', '{start_date}', '{end_date}', 
             {avg_beta}, {avg_tstat}, {avg_rsquared}, {significant_stocks}, {total_stocks}, 
             {ann_return}, {ann_vol}, {sharpe}, {max_dd}, 
             '{description or f"{factor_name} factor analysis results"}')
            """)
            print(f"Insert data into factor_summary table has DONE")
            return True

        except Exception as e:
            print(f"Error storing factor summary: {str(e)}")
            print(traceback.format_exc())
            return False

    def store_stock_returns(self, returns_df):
        """
        Store stock returns data to ClickHouse

        Parameters:
        - returns_df: DataFrame with stock returns (index=dates, columns=tickers)

        Returns:
        - success: Boolean indicating if operation was successful
        """
        try:
            print("Storing stock returns data to ClickHouse...")

            if returns_df.empty:
                print("Empty returns DataFrame provided")
                return False

            # Get list of unique tickers in the data
            tickers = returns_df.columns.tolist()

            # Prepare data for insertion - store all data without filtering
            data = []
            for date in returns_df.index:
                for ticker in returns_df.columns:
                    return_value = returns_df.loc[date, ticker]
                    if pd.notna(return_value):
                        data.append((
                            ticker,
                            date,
                            float(return_value),
                            datetime.now()  # Add update_time for tracking latest records
                        ))

            if not data:
                print("No stock return data to store")
                return False

            print(f"Inserting {len(data)} stock return records")

            # Insert data in batches to avoid memory issues
            self.client.execute(
                f"INSERT INTO {self.database}.temp_stock_returns "
                "(ticker, date, return_value, update_time) VALUES",
                data
            )

            print(f"Successfully stored {len(data)} stock return records")
            return True

        except Exception as e:
            print(f"Error storing stock returns: {str(e)}")
            print(traceback.format_exc())
            return False

    def store_portfolio_returns(self, factor_name, factor_type, portfolio_returns):
        """
        Store portfolio returns in ClickHouse

        Parameters:
        - factor_name: Name of the factor
        - factor_type: Type of factor (e.g., 'Technical', 'Fundamental')
        - portfolio_returns: DataFrame with portfolio returns

        Returns:
        - success: Boolean indicating if operation was successful
        """
        try:
            print(f"Storing {factor_name} portfolio returns in ClickHouse...")

            factor_col = f'{factor_name}_Factor'

            if portfolio_returns.empty or factor_col not in portfolio_returns.columns:
                print(f"No portfolio returns to store for {factor_name}")
                return False

            timeseries_data = []

            for date, row in portfolio_returns.iterrows():
                factor_value = float(row.get(factor_col, 0.0))
                high_return = float(row.get(f'High_{factor_name}', 0.0))
                low_return = float(row.get(f'Low_{factor_name}', 0.0))

                timeseries_data.append(
                    (factor_name, factor_type, date, factor_value, high_return, low_return)
                )

            # Execute for bulk insert
            query = f"""
            INSERT INTO {self.database}.factor_timeseries 
            (factor_name, factor_type, date, factor_value, high_portfolio_return, low_portfolio_return)
            VALUES
            """
            self.client.execute(query, timeseries_data)
            print(f"Insert data into factor_timeseries table has DONE")

            return True

        except Exception as e:
            print(f"Error storing portfolio returns: {str(e)}")
            print(traceback.format_exc())
            return False

    def store_factor_details(self, factor_name, factor_type, factor_test_results):
        """
        Store factor test results in ClickHouse

        Parameters:
        - factor_name: Name of the factor
        - factor_type: Type of factor (e.g., 'Technical', 'Fundamental')
        - factor_test_results: DataFrame with factor test results

        Returns:
        - success: Boolean indicating if operation was successful
        """
        try:
            print(f"Storing {factor_name} factor test results in ClickHouse...")

            # Check if factor_test_results is empty based on its type
            if isinstance(factor_test_results, dict) and not factor_test_results:
                print(f"No test results to store for {factor_name}")
                return False
            elif hasattr(factor_test_results, 'empty') and factor_test_results.empty:
                print(f"No test results to store for {factor_name}")
                return False

            test_date = datetime.today()
            detail_data = []

            # Handle dictionary input for factor_test_results
            if isinstance(factor_test_results, dict):
                for ticker, row in factor_test_results.items():
                    beta = float(row.get('Beta', 0.0))
                    tstat = float(row.get('T-stat', 0.0))
                    pvalue = float(row.get('P-value', 0.0))
                    rsquared = float(row.get('R-squared', 0.0))
                    conf_int_lower = float(row.get('Conf_Int_Lower', 0.0))
                    conf_int_upper = float(row.get('Conf_Int_Upper', 0.0))

                    # Data for factor_details table
                    detail_data.append(
                        (factor_name, factor_type, test_date, ticker, beta, tstat, pvalue, rsquared, conf_int_lower,
                         conf_int_upper)
                    )
            else:
                # Handle DataFrame input
                for ticker, row in factor_test_results.iterrows():
                    beta = float(row.get('Beta', 0.0))
                    tstat = float(row.get('T-stat', 0.0))
                    pvalue = float(row.get('P-value', 0.0))
                    rsquared = float(row.get('R-squared', 0.0))
                    conf_int_lower = float(row.get('Conf_Int_Lower', 0.0))
                    conf_int_upper = float(row.get('Conf_Int_Upper', 0.0))

                    # Data for factor_details table
                    detail_data.append(
                        (factor_name, factor_type, test_date, ticker, beta, tstat, pvalue, rsquared, conf_int_lower,
                         conf_int_upper)
                    )

            # Execute for bulk insert into factor_details
            query = f"""
            INSERT INTO {self.database}.factor_details
            (factor_name, factor_type, test_date, ticker, beta, tstat, pvalue, rsquared, conf_int_lower, conf_int_upper)
            VALUES
            """
            self.client.execute(query, detail_data)
            print("Insert into factor_details DONE")

            return True

        except Exception as e:
            print(f"Error storing factor test results: {str(e)}")
            print(traceback.format_exc())
            return False

    def get_all_factors(self):
        """Get summary of all factors in the database"""
        try:
            query = """
            SELECT 
                factor_name,
                factor_type,
                test_date,
                start_date,
                end_date,
                avg_beta,
                avg_tstat,
                avg_rsquared,
                significant_stocks,
                total_stocks,
                annualized_return,
                annualized_volatility,
                sharpe_ratio,
                max_drawdown,
                description,
                update_time
            FROM factor_summary
            ORDER BY factor_type, sharpe_ratio DESC
            """

            result = self.client.execute(query, with_column_types=True)
            columns = [col[0] for col in result[1]]
            df = pd.DataFrame(result[0], columns=columns)

            return df

        except Exception as e:
            print(f"Error getting factors: {str(e)}")
            print(traceback.format_exc())
            return pd.DataFrame()

    def execute_query(self, query):
        """
        Execute a raw SQL query and return the results

        Parameters:
        - query: SQL query string

        Returns:
        - List of tuples with query results
        """
        try:
            result = self.client.execute(query)
            return result
        except Exception as e:
            print(f"Error executing query: {str(e)}")
            print(traceback.format_exc())
            return []

    def get_factor_test_results(self, factor_name, factor_type, tickers=None):
        """
        Get detailed results for a specific factor

        Parameters:
        - factor_name: Name of the factor
        - tickers: List of tickers to filter (optional)
        - factor_type: Type of factor (optional)\

        Returns:
        - DataFrame with factor test results
        """
        try:
            # Build query conditions
            conditions = [f"factor_name = '{factor_name}'"]

            if factor_type:
                conditions.append(f"factor_type = '{factor_type}'")

            if tickers:
                ticker_list = "', '".join(tickers)
                conditions.append(f"ticker IN ('{ticker_list}')")

            # Build complete query with latest update_time
            where_clause = " AND ".join(conditions)
            query = f"""
            SELECT
                fd.factor_name,
                fd.factor_type,
                fd.test_date,
                fd.ticker,
                fd.beta,
                fd.tstat,
                fd.pvalue,
                fd.rsquared,
                fd.conf_int_lower,
                fd.conf_int_upper,
                fd.update_time
            FROM {self.database}.factor_details fd
            INNER JOIN (
                SELECT
                    factor_name,
                    ticker,
                    MAX(update_time) as latest_update_time
                FROM {self.database}.factor_details
                WHERE {where_clause}
                GROUP BY factor_name, ticker
            ) latest ON fd.factor_name = latest.factor_name
                AND fd.ticker = latest.ticker
                AND fd.update_time = latest.latest_update_time
            WHERE {where_clause}
            ORDER BY fd.ticker
            """

            # Execute query
            result = self.client.execute(query, with_column_types=True)
            columns = [col[0] for col in result[1]]
            details = pd.DataFrame(result[0], columns=columns)

            if details.empty:
                print(f"No factor details found for {factor_name}")
            else:
                print(f"Successfully retrieved factor details for {factor_name} with {len(details)} records")

            return details

        except Exception as e:
            print(f"Error getting factor details: {str(e)}")
            print(traceback.format_exc())
            return pd.DataFrame()

    def get_factor_values(self, factor_name, factor_type, start_date=None, end_date=None):
        """Get raw factor values for a specific factor"""
        try:
            where_clauses = [f"factor_name = '{factor_name}'", f"factor_type = '{factor_type}'"]

            if start_date:
                where_clauses.append(f"date >= '{start_date}'")

            if end_date:
                where_clauses.append(f"date <= '{end_date}'")

            where_clause = f"WHERE {' AND '.join(where_clauses)}"

            query = f"""
            SELECT ticker, date, value
            FROM factor_values
            {where_clause}
            ORDER BY ticker, date
            """

            result = self.client.execute(query, with_column_types=True)
            columns = [col[0] for col in result[1]]
            df = pd.DataFrame(result[0], columns=columns)

            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                # Pivot to get tickers as columns
                pivot_df = df.pivot(index='date', columns='ticker', values='value')
                return pivot_df

            return pd.DataFrame()

        except Exception as e:
            print(f"Error getting factor values: {str(e)}")
            print(traceback.format_exc())
            return pd.DataFrame()

    def get_factor_details(self, factor_name, factor_type, test_date):
        """Get detailed results for a specific factor"""
        try:
            # Get summary
            summary_query = f"""
            SELECT * FROM factor_summary 
            WHERE factor_name = '{factor_name}' 
            AND factor_type = '{factor_type}' 
            AND test_date = '{test_date}'
            """
            summary_result = self.client.execute(summary_query, with_column_types=True)
            summary_columns = [col[0] for col in summary_result[1]]
            summary = pd.DataFrame(summary_result[0], columns=summary_columns)

            # Get details
            details_query = f"""
            SELECT * FROM factor_details 
            WHERE factor_name = '{factor_name}' 
            AND factor_type = '{factor_type}' 
            AND test_date = '{test_date}'
            """
            details_result = self.client.execute(details_query, with_column_types=True)
            details_columns = [col[0] for col in details_result[1]]
            details = pd.DataFrame(details_result[0], columns=details_columns)

            # Get time series
            ts_query = f"""
            SELECT * FROM factor_timeseries 
            WHERE factor_name = '{factor_name}' 
            AND factor_type = '{factor_type}'
            ORDER BY date
            """
            ts_result = self.client.execute(ts_query, with_column_types=True)
            ts_columns = [col[0] for col in ts_result[1]]
            timeseries = pd.DataFrame(ts_result[0], columns=ts_columns)

            if not timeseries.empty:
                timeseries['date'] = pd.to_datetime(timeseries['date'])
                timeseries.set_index('date', inplace=True)

            return {
                'summary': summary,
                'details': details,
                'timeseries': timeseries
            }

        except Exception as e:
            print(f"Error getting factor details: {str(e)}")
            print(traceback.format_exc())
            return {
                'summary': pd.DataFrame(),
                'details': pd.DataFrame(),
                'timeseries': pd.DataFrame()
            }

    def get_stock_returns(self, tickers=None, start_date=None, end_date=None):
        """
        Retrieve stock returns data from ClickHouse

        Parameters:
        - tickers: List of stock tickers (optional)
        - start_date: Start date (optional, format: YYYY-MM-DD)
        - end_date: End date (optional, format: YYYY-MM-DD)

        Returns:
        - DataFrame: Stock returns data (index=dates, columns=tickers)
        """
        try:
            # Build query conditions
            conditions = []

            if tickers:
                ticker_list = "', '".join(tickers)
                conditions.append(f"ticker IN ('{ticker_list}')")

            if start_date:
                conditions.append(f"date >= '{start_date}'")

            if end_date:
                conditions.append(f"date <= '{end_date}'")

            # Build complete query with latest update_time
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            # query = f"""
            # SELECT
            #     sr.ticker,
            #     sr.date,
            #     sr.return_value
            # FROM {self.database}.temp_stock_returns sr
            # INNER JOIN (
            #     SELECT
            #         ticker,
            #         date,
            #         MAX(update_time) as latest_update_time
            #     FROM {self.database}.temp_stock_returns
            #     WHERE {where_clause}
            #     GROUP BY ticker, date
            # ) latest ON sr.ticker = latest.ticker
            #     AND sr.date = latest.date
            #     AND sr.update_time = latest.latest_update_time
            # WHERE {where_clause}
            # ORDER BY sr.date, sr.ticker
            # """
            query = f"""
            SELECT
                sr.ticker,
                sr.date,
                argMax(sr.return_value, sr.update_time) AS return_value
            FROM {self.database}.temp_stock_returns sr
            WHERE {where_clause}        
            GROUP BY
                sr.ticker,
                sr.date   
            ORDER BY
                sr.date,
                sr.ticker
            """

            # Execute query
            result = self.client.execute(query, with_column_types=True)
            columns = [col[0] for col in result[1]]
            df = pd.DataFrame(result[0], columns=columns)

            if df.empty:
                print("No stock return data found")
                return pd.DataFrame()

            # Convert date to datetime
            df['date'] = pd.to_datetime(df['date'])

            # Pivot table to get desired format
            pivot_df = df.pivot(index='date', columns='ticker', values='return_value')

            print(f"Successfully retrieved stock returns for {len(pivot_df)} days and {len(pivot_df.columns)} stocks")
            return pivot_df

        except Exception as e:
            print(f"Error retrieving stock returns: {str(e)}")
            print(traceback.format_exc())
            return pd.DataFrame()

    def get_portfolio_returns(self, factor_name, tickers, factor_type=None, start_date=None, end_date=None):
        """
        Retrieve portfolio returns data from ClickHouse factor_timeseries table

        Parameters:
        - factor_name: Name of the factor
        - start_date: Start date (optional, format: YYYY-MM-DD)
        - end_date: End date (optional, format: YYYY-MM-DD)
        - tickers: List of tickers to filter factor values (optional)

        Returns:
        - DataFrame: Portfolio returns data
        """
        try:
            # Build query conditions
            conditions = [f"factor_name = '{factor_name}'"]
            tickers = tickers

            if start_date:
                conditions.append(f"date >= '{start_date}'")

            if end_date:
                conditions.append(f"date <= '{end_date}'")

            if factor_type:
                conditions.append(f"factor_type = '{factor_type}'")

            # Build complete query
            where_clause = " AND ".join(conditions)
            # query = f"""
            # SELECT
            #     ft.date,
            #     ft.high_portfolio_return,
            #     ft.low_portfolio_return,
            #     ft.factor_value,
            #     ft.factor_name
            # FROM {self.database}.factor_timeseries ft
            # INNER JOIN (
            #     SELECT
            #         factor_name,
            #         factor_type,
            #         date,
            #         MAX(update_time) as latest_update_time
            #     FROM {self.database}.factor_timeseries
            #     WHERE {where_clause}
            #     GROUP BY factor_name, factor_type, date
            # ) latest ON ft.factor_name = latest.factor_name
            #     AND ft.factor_type = latest.factor_type
            #     AND ft.date = latest.date
            #     AND ft.update_time = latest.latest_update_time
            # WHERE {where_clause}
            # ORDER BY ft.date
            # """
            query = f"""
            SELECT
                date,
                argMax(high_portfolio_return,  update_time) AS high_portfolio_return,
                argMax(low_portfolio_return,   update_time) AS low_portfolio_return,
                argMax(factor_value,           update_time) AS factor_value
            FROM {self.database}.factor_timeseries
            WHERE {where_clause}
            GROUP BY factor_name, factor_type, date
            ORDER BY date
            """

            # Execute query
            result = self.client.execute(query, with_column_types=True)
            columns = [col[0] for col in result[1]]
            df = pd.DataFrame(result[0], columns=columns)

            if df.empty:
                print(f"No portfolio return data found for {factor_name}")
                return pd.DataFrame()

            # Convert date to datetime and set as index
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)

            # Rename columns to match expected format
            df.rename(columns={
                'high_portfolio_return': f'High_{factor_name}',
                'low_portfolio_return': f'Low_{factor_name}',
                'factor_value': f'{factor_name}_Factor'
            }, inplace=True)

            print(f"Successfully retrieved {len(df)} {factor_name} portfolio return records")
            return df

        except Exception as e:
            print(f"Error retrieving portfolio returns: {str(e)}")
            print(traceback.format_exc())
            return pd.DataFrame()

    def compare_factors(self, factor_names=None, factor_types=None):
        """
        Compare multiple factors

        Parameters:
        - factor_names: List of factor names to compare. If None, compare all factors.
        - factor_types: List of factor types to compare. If None, compare all types.

        Returns:
        - DataFrame with comparison metrics
        """
        try:
            where_clauses = []

            if factor_names:
                factor_list = "', '".join(factor_names)
                where_clauses.append(f"factor_name IN ('{factor_list}')")

            if factor_types:
                type_list = "', '".join(factor_types)
                where_clauses.append(f"factor_type IN ('{type_list}')")

            where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            query = f"""
            SELECT 
                factor_name,
                factor_type,
                test_date,
                avg_beta,
                avg_tstat,
                avg_rsquared,
                significant_stocks,
                total_stocks,
                annualized_return,
                annualized_volatility,
                sharpe_ratio,
                max_drawdown,
                update_time
            FROM factor_summary
            {where_clause}
            ORDER BY sharpe_ratio DESC
            """

            result = self.client.execute(query, with_column_types=True)
            columns = [col[0] for col in result[1]]
            df = pd.DataFrame(result[0], columns=columns)

            return df

        except Exception as e:
            print(f"Error comparing factors: {str(e)}")
            print(traceback.format_exc())
            return pd.DataFrame()

    def delete_factor(self, factor_name, factor_type, test_date=None):
        """Delete a factor from all tables"""
        try:
            print(f"Deleting factor: {factor_name}, type: {factor_type}")

            where_clauses = [f"factor_name = '{factor_name}'", f"factor_type = '{factor_type}'"]

            if test_date:
                where_clauses.append(f"test_date = '{test_date}'")

            where_clause = f"WHERE {' AND '.join(where_clauses)}"

            # Delete from factor_summary
            self.client.execute(f"DELETE FROM {self.database}.factor_summary {where_clause}")

            # Delete from factor_details
            self.client.execute(f"DELETE FROM {self.database}.factor_details {where_clause}")

            # Delete from factor_test_results
            self.client.execute(f"DELETE FROM {self.database}.factor_test_results {where_clause}")

            # Delete from factor_timeseries (no test_date column)
            where_clause_ts = f"WHERE factor_name = '{factor_name}' AND factor_type = '{factor_type}'"
            self.client.execute(f"DELETE FROM {self.database}.factor_timeseries {where_clause_ts}")

            # Delete from factor_values (no test_date column)
            self.client.execute(f"DELETE FROM {self.database}.factor_values {where_clause_ts}")

            print(f"Successfully deleted factor: {factor_name}, type: {factor_type}")
            return True

        except Exception as e:
            print(f"Error deleting factor: {str(e)}")
            print(traceback.format_exc())
            return False
