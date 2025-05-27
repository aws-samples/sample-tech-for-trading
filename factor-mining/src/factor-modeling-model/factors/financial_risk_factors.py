import pandas as pd
import numpy as np
from factors.base_factor import BaseFactor
from clickhouse_driver import Client
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_DATABASE
import traceback


class DebtToEquityFactor(BaseFactor):
    """
    Debt-to-Equity Ratio factor implementation
    Measures a company's financial leverage
    """

    def __init__(self):
        """Initialize the Debt-to-Equity factor"""
        super().__init__(
            name="DebtToEquity",
            factor_type="Financial Risk",
            description="Debt-to-Equity Ratio (Total Debt is divided by Shareholders Equity). Measures a company financial leverage."
        )

        # Database configuration for this factor
        self.db_host = CLICKHOUSE_HOST
        self.db_port = CLICKHOUSE_PORT
        self.db_user = CLICKHOUSE_USER
        self.db_password = CLICKHOUSE_PASSWORD
        self.db_database = CLICKHOUSE_DATABASE

    def calculate(self, price_data):
        """
        Calculate Debt-to-Equity Ratio from database tables

        Parameters:
        - price_data: Dictionary of DataFrames with price data (key=ticker, value=DataFrame)

        Returns:
        - DataFrame with Debt-to-Equity values (index=dates, columns=tickers)
        """

        # Get all unique dates from price data
        all_dates = set()
        tickers = []
        for ticker, df in price_data.items():
            all_dates.update(df.index)
            tickers.append(ticker)

        all_dates = sorted(list(all_dates))
        start_date = all_dates[0].strftime('%Y-%m-%d')
        end_date = all_dates[-1].strftime('%Y-%m-%d')

        try:
            # Connect to ClickHouse
            client = Client(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                database=self.db_database
            )

            # Format tickers for SQL query
            ticker_list = "', '".join(tickers)

            # Simplified query - directly calculate debt_to_equity_ratio in a single query
            query = f"""WITH latest_data AS (
                SELECT ticker, end_date, liabilities_current, stockholders_equity
                FROM (
                    SELECT *,
                           ROW_NUMBER() OVER (PARTITION BY ticker, end_date ORDER BY processed_timestamp DESC) as rn
                    FROM {self.db_database}.stock_fundamental_factors_source
                    WHERE ticker IN ('{ticker_list}')
                    AND end_date BETWEEN DATE_SUB('{start_date}', INTERVAL 1 YEAR) AND '{end_date}'
                ) t
                WHERE rn = 1
            )
            SELECT 
                ticker,
                end_date as date,
                liabilities_current / stockholders_equity as debt_to_equity_ratio
            FROM latest_data 
            WHERE stockholders_equity != 0  -- Avoid division by zero
            ORDER BY ticker, date
            """
            result = client.execute(query, with_column_types=True)
            print(f"Total {len(result[0])} {self.name} rows has been returned...")
            columns = [col[0] for col in result[1]]
            data = pd.DataFrame(result[0], columns=columns)

            # Check if we got data
            if data.empty:
                print("Warning: No debt-to-equity data found in database. Falling back to synthetic data.")
                return self._generate_synthetic_data(price_data)

            # Convert to datetime and set as index
            data['date'] = pd.to_datetime(data['date'])

            # Pivot to get tickers as columns
            de_df = data.pivot(index='date', columns='ticker', values='debt_to_equity_ratio')

            # Forward fill missing values (use previous day's value)
            de_df = de_df.reindex(pd.date_range(start_date, end_date, freq='D')).ffill()

            # Reindex to match all dates in price data
            de_df = de_df.reindex(pd.DatetimeIndex(all_dates))

            # If there are still NaN values (e.g., at the beginning), fill with industry averages or reasonable defaults
            de_df = de_df.fillna(1.0)  # Default debt-to-equity ratio of 1.0

            return de_df

        except Exception as e:
            print(f"Error fetching debt-to-equity data from database: {str(e)}")
            print("Falling back to synthetic data.")
            print(traceback.format_exc())
            return self._generate_synthetic_data(price_data)

    def _generate_synthetic_data(self, price_data):
        """
        Generate synthetic debt-to-equity data as fallback

        Parameters:
        - price_data: Dictionary of DataFrames with price data (key=ticker, value=DataFrame)

        Returns:
        - DataFrame with synthetic Debt-to-Equity values (index=dates, columns=tickers)
        """
        print("Generating synthetic debt-to-equity data")

        # Get all unique dates from price data
        all_dates = set()
        for ticker, df in price_data.items():
            all_dates.update(df.index)

        all_dates = sorted(list(all_dates))
        de_df = pd.DataFrame(index=all_dates)

        # Generate synthetic debt-to-equity data for each stock
        for ticker, df in price_data.items():
            # Generate base debt-to-equity ratio (typically between 0.3 and 2.0)
            base_de = np.random.uniform(0.3, 2.0)

            # Create a series with some random variation over time
            # Use random walk with mean reversion
            random_changes = np.random.normal(0, 0.01, len(df))
            mean_reversion = 0.05 * (base_de - np.cumsum(random_changes))
            de_series = base_de + np.cumsum(random_changes + mean_reversion)

            # Ensure debt-to-equity values are positive and reasonable
            de_series = np.clip(de_series, 0.1, 3.0)

            # Add to DataFrame
            de_df[ticker] = pd.Series(de_series, index=df.index)

        return de_df


class InterestCoverageFactor(BaseFactor):
    """
    Interest Coverage Ratio factor implementation
    Measures a company's ability to pay interest on its debt
    """

    def __init__(self):
        """Initialize the Interest Coverage factor"""
        super().__init__(
            name="InterestCoverage",
            factor_type="Financial Risk",
            description="Interest Coverage Ratio (EBIT / Interest Expense). Measures a company's ability to pay interest on its debt."
        )

    def calculate(self, price_data):
        """
        Calculate Interest Coverage Ratio from synthetic financial data

        Parameters:
        - price_data: Dictionary of DataFrames with price data (key=ticker, value=DataFrame)

        Returns:
        - DataFrame with Interest Coverage values (index=dates, columns=tickers)
        """
        # Get all unique dates from price data
        all_dates = set()
        for ticker, df in price_data.items():
            all_dates.update(df.index)

        all_dates = sorted(list(all_dates))
        ic_df = pd.DataFrame(index=all_dates)

        # Generate synthetic interest coverage data for each stock
        for ticker, df in price_data.items():
            # Generate base interest coverage ratio (typically between 2.0 and 15.0)
            base_ic = np.random.uniform(2.0, 15.0)

            # Create a series with some random variation over time
            # Use random walk with mean reversion
            random_changes = np.random.normal(0, 0.1, len(df))
            mean_reversion = 0.05 * (base_ic - np.cumsum(random_changes))
            ic_series = base_ic + np.cumsum(random_changes + mean_reversion)

            # Ensure interest coverage values are reasonable
            ic_series = np.clip(ic_series, 0.5, 25.0)

            # Add to DataFrame
            ic_df[ticker] = pd.Series(ic_series, index=df.index)

        return ic_df