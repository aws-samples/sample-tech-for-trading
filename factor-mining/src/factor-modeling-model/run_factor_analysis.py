import os
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import traceback
from datetime import datetime
from clickhouse_utils import ClickHouseUtils
from config import CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_DATABASE
from config import DJIA_TICKERS, START_DATE, END_DATE
from factors.peg_factor import PEGFactor
from factors.rsi_factor import RSIFactor
from factors.fama_french_factors import SMBFactor, HMLFactor, MarketFactor
from factors.valuation_factors import PBFactor
from factors.liquidity_factors import TradingVolumeFactor
from factors.technical_factors import ROCFactor
from factors.financial_health_factors import CurrentRatioFactor, CashRatioFactor
from factors.operational_factors import InventoryTurnoverFactor, GrossProfitMarginFactor
from factors.financial_risk_factors import DebtToEquityFactor, InterestCoverageFactor
from factors.growth_factors import RevenueGrowthFactor
from factors.esg_factors import BoardAgeFactor, ExecutiveCompensationFactor, EnvironmentRatingFactor
from factors.sentiment_factors import AverageSentimentFactor, NewsSentimentFactor


# Get the latest outstanding shares from the database
def get_latest_outstanding_shares(tickers):
    """
    Fetch the latest outstanding shares for the given tickers from the database
    """
    ch_utils = ClickHouseUtils(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DATABASE
    )

    # Query to get the latest outstanding shares for each ticker
    query = f"""
            SELECT ticker, value
            FROM factor_model_tick_data_database.factor_values
            WHERE factor_name = 'OutstandingShares'
              AND ticker IN ({', '.join([f"'{t}'" for t in tickers])})
              AND (ticker, update_time) IN (
                SELECT ticker, MAX(update_time) as max_date
                FROM factor_model_tick_data_database.factor_values
                WHERE factor_name = 'OutstandingShares'
                  AND ticker IN ({', '.join([f"'{t}'" for t in tickers])})
                GROUP BY ticker
              )
            """

    result = ch_utils.execute_query(query)

    # Convert to dictionary for easy lookup
    shares_dict = {row[0]: row[1] for row in result}
    print(f"Retrieved outstanding shares for {len(shares_dict)} tickers")
    return shares_dict


def run_factor_analysis(factor_obj, batch_no, tickers, start_date, end_date, output_dir='factor_results'):
    """
    Run factor analysis using the provided factor object

    Parameters:
    - factor_obj: Factor object (instance of BaseFactor subclass)
    - batch_no: The no of batch (1: Run all batch 2: Run calculate and construct 3:Run testing 4:Run evaluation)
    - start_date: Start date for analysis (YYYY-MM-DD)
    - end_date: End date for analysis (YYYY-MM-DD)
    - tickers: List of stock tickers to analyze (default: None, uses DJIA_TICKERS)
    - output_dir: Directory to store output files

    Returns:
    - Results dictionary
    """
    try:
        print(f"Running {factor_obj.name} factor analysis from {start_date} to {end_date}...")

        # Use provided tickers or default to DJIA_TICKERS
        tickers = tickers or DJIA_TICKERS

        # Create ClickHouse utils
        ch_utils = ClickHouseUtils(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            user=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD,
            database=CLICKHOUSE_DATABASE
        )

        # Fetch stock price data
        print(f"Fetching stock data for {len(tickers)} symbols...")
        price_data = {}

        # Convert dates to ClickHouse format
        start_date_formatted = f"{start_date} 00:00:00"
        end_date_formatted = f"{end_date} 23:59:59"

        for symbol in tickers:
            try:
                # Query to get daily OHLCV data
                query = f"""
                SELECT 
                    symbol,
                    toDate(timestamp) as date,
                    argMin(open, timestamp) as open,
                    max(high) as high,
                    min(low) as low,
                    argMax(close, timestamp) as close,
                    sum(volume) as volume,
                    argMax(adjusted_close, timestamp) as adjusted_close
                FROM {CLICKHOUSE_DATABASE}.tick_data
                WHERE symbol = '{symbol}'
                AND timestamp BETWEEN toDateTime('{start_date_formatted}') AND toDateTime('{end_date_formatted}')
                GROUP BY symbol, toDate(timestamp)
                ORDER BY date
                """

                # Execute query
                data = ch_utils.client.execute(query, with_column_types=True)

                # Convert to DataFrame
                columns = [col[0] for col in data[1]]
                df = pd.DataFrame(data[0], columns=columns)

                # Convert date to datetime
                df['date'] = pd.to_datetime(df['date'])

                # Set date as index
                df.set_index('date', inplace=True)

                # Store in result dictionary
                price_data[symbol] = df

                print(f"Fetched {len(df)} days of data for {symbol}")

            except Exception as e:
                print(f"Error fetching data for {symbol}: {str(e)}")

        # Generate market cap data (mock data for now)
        print("Generating market cap data...")
        all_dates = set()
        for symbol in tickers:
            if symbol in price_data:
                all_dates.update(price_data[symbol].index)

        all_dates = sorted(list(all_dates))
        market_cap_df = pd.DataFrame(index=all_dates)

        # Get actual outstanding shares from the database
        outstanding_shares_dict = get_latest_outstanding_shares(tickers)

        # Generate market cap for each stock
        for symbol in tickers:
            if symbol in price_data:
                # Use actual shares outstanding from database or fallback to a default value
                shares_outstanding = outstanding_shares_dict.get(symbol, 5e9)  # Default to 5B if not found

                # Calculate market cap as price * shares outstanding
                market_cap = price_data[symbol]['adjusted_close'] * shares_outstanding

                # Add to DataFrame
                market_cap_df[symbol] = market_cap

                # Log the shares outstanding used
                print(f"{symbol}: Using {shares_outstanding:,.0f} outstanding shares")

        # For PEG factor, we need additional fundamental data
        additional_data = None
        if factor_obj.name == "PEG":
            # Generate mock fundamental data
            print("Generating fundamental data for PEG factor...")
            pe_df = pd.DataFrame(index=all_dates)
            growth_df = pd.DataFrame(index=all_dates)

            # Generate data for each stock
            for symbol in tickers:
                if symbol in price_data:
                    # Base P/E on price with some randomness
                    base_pe = np.random.uniform(10, 30)
                    pe_volatility = np.random.uniform(0.005, 0.015)
                    pe_changes = np.random.normal(0, pe_volatility, len(price_data[symbol]))
                    pe_series = base_pe * (1 + pe_changes).cumprod()
                    pe_series = np.clip(pe_series, 5, 100)  # Keep P/E ratios in reasonable range
                    pe_df[symbol] = pe_series

                    # Generate growth rates (varying over time)
                    base_growth = np.random.uniform(0.05, 0.25)
                    growth_volatility = np.random.uniform(0.002, 0.01)
                    growth_changes = np.random.normal(0, growth_volatility, len(price_data[symbol]))
                    growth_series = base_growth * (1 + growth_changes).cumprod()
                    growth_series = np.clip(growth_series, 0.01, 0.5)
                    growth_df[symbol] = growth_series

            additional_data = {
                'pe_ratios': pe_df,
                'growth_rates': growth_df
            }

        # Batch 1: Run factor analysis to get factor_values, df_returns, portfolio_returns
        # results = factor_obj.analyze(price_data, market_cap_df, additional_data, output_dir)
        if batch_no in (0, 1):
            print("Begin running Batch 1...")

            results = factor_obj.analyze_calculate_construct(price_data, market_cap_df, additional_data)
            if results:
                ch_utils.store_stock_returns(
                    returns_df=results['returns_df']
                )

                ch_utils.store_portfolio_returns(
                    factor_name=factor_obj.name,
                    factor_type=factor_obj.factor_type,
                    portfolio_returns=results['portfolio_returns']
                )

        # Batch 2: Run factor testing to get factor_test_results
        if batch_no in (0, 2):
            print("Begin running Batch 2...")

            tickers = tickers or DJIA_TICKERS
            returns_df = ch_utils.get_stock_returns(tickers=tickers, start_date=start_date, end_date=end_date)
            portfolio_returns = ch_utils.get_portfolio_returns(factor_name=factor_obj.name,
                                                               factor_type=factor_obj.factor_type, tickers=tickers,
                                                               start_date=start_date, end_date=end_date)
            results = factor_obj.analyze_test_factor(returns_df, portfolio_returns)

            if results:
                ch_utils.store_factor_details(
                    factor_name=factor_obj.name,
                    factor_type=factor_obj.factor_type,
                    factor_test_results=results['factor_test_results']
                )

        # Batch 3: save factor_test_results and performance_results to factor_summary table
        if batch_no in (0, 3):
            print("Begin running Batch 3...")

            portfolio_returns = ch_utils.get_portfolio_returns(factor_name=factor_obj.name,
                                                               factor_type=factor_obj.factor_type, tickers=DJIA_TICKERS,
                                                               start_date=start_date, end_date=end_date)
            factor_test_results = ch_utils.get_factor_test_results(factor_name=factor_obj.name,
                                                                   factor_type=factor_obj.factor_type,
                                                                   tickers=DJIA_TICKERS)
            results = factor_obj.analyze_evaluate_portfolio(factor_test_results, portfolio_returns,
                                                            output_dir='factor_dashboard')

            # Store results in ClickHouse factor_test_results table
            if results:
                # Store factor analysis results
                ch_utils.store_factor_summary(
                    factor_name=factor_obj.name,
                    factor_type=factor_obj.factor_type,
                    results_dict=results,
                    start_date=start_date,
                    end_date=end_date,
                    description=factor_obj.description
                )

                print(f"{factor_obj.name} factor analysis completed successfully.")

        return results

    except Exception as e:
        print(f"Error in {factor_obj.name} factor analysis: {str(e)}")
        print(traceback.format_exc())
        return None


def create_factor_dashboard(factor_name, factor_type, ch_utils, output_dir='factor_dashboard'):
    """Create a dashboard for factor analysis results"""
    try:
        print(f"Creating dashboard for factor: {factor_name}...")

        # Get latest test date
        test_dates = ch_utils.client.execute(f"""
        SELECT test_date FROM {CLICKHOUSE_DATABASE}.factor_summary 
        WHERE factor_name = '{factor_name}' AND factor_type = '{factor_type}'
        ORDER BY test_date DESC LIMIT 1
        """)

        if not test_dates:
            print(f"No data found for factor: {factor_name}")
            return

        test_date = test_dates[0][0]

        # Get factor details
        factor_data = ch_utils.get_factor_details(factor_name, factor_type, test_date)

        if not factor_data['summary'].empty:
            summary = factor_data['summary']
            details = factor_data['details']
            timeseries = factor_data['timeseries']

            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            dashboard_dir = os.path.join(output_dir, 'dashboard')
            os.makedirs(dashboard_dir, exist_ok=True)

            # Create dashboard HTML
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{factor_name} Factor Analysis Dashboard</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #f0f0f0; padding: 10px; margin-bottom: 20px; }}
                    .section {{ margin-bottom: 30px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .chart {{ margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{factor_name} Factor Analysis Dashboard</h1>
                    <p>Factor Type: {factor_type}</p>
                    <p>Test Date: {test_date}</p>
                    <p>Date Range: {summary['start_date'].iloc[0]} to {summary['end_date'].iloc[0]}</p>
                </div>

                <div class="section">
                    <h2>Summary Statistics</h2>
                    <table>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                        <tr>
                            <td>Average Beta</td>
                            <td>{summary['avg_beta'].iloc[0]:.4f}</td>
                        </tr>
                        <tr>
                            <td>Average T-statistic</td>
                            <td>{summary['avg_tstat'].iloc[0]:.4f}</td>
                        </tr>
                        <tr>
                            <td>Average R-squared</td>
                            <td>{summary['avg_rsquared'].iloc[0]:.4f}</td>
                        </tr>
                        <tr>
                            <td>Significant Stocks</td>
                            <td>{summary['significant_stocks'].iloc[0]} out of {summary['total_stocks'].iloc[0]}</td>
                        </tr>
                        <tr>
                            <td>Annualized Return</td>
                            <td>{summary['annualized_return'].iloc[0]:.2%}</td>
                        </tr>
                        <tr>
                            <td>Annualized Volatility</td>
                            <td>{summary['annualized_volatility'].iloc[0]:.2%}</td>
                        </tr>
                        <tr>
                            <td>Sharpe Ratio</td>
                            <td>{summary['sharpe_ratio'].iloc[0]:.2f}</td>
                        </tr>
                        <tr>
                            <td>Maximum Drawdown</td>
                            <td>{summary['max_drawdown'].iloc[0]:.2%}</td>
                        </tr>
                    </table>
                </div>

                <div class="section">
                    <h2>Factor Performance</h2>
                    <div class="chart">
                        <img src="../{factor_name.lower()}_factor_cumulative_returns_real_data.png" width="100%">
                    </div>
                </div>

                <div class="section">
                    <h2>Factor Statistics</h2>
                    <div class="chart">
                        <img src="../{factor_name.lower()}_factor_statistics_real_data.png" width="100%">
                    </div>
                </div>
            """

            # Add stock-level results if available
            if not details.empty:
                html_content += """
                <div class="section">
                    <h2>Stock-Level Results</h2>
                    <table>
                        <tr>
                            <th>Ticker</th>
                            <th>Beta</th>
                            <th>T-stat</th>
                            <th>P-value</th>
                            <th>R-squared</th>
                            <th>95% Confidence Interval</th>
                        </tr>
                """

                # Add rows for each stock
                for _, row in details.iterrows():
                    html_content += f"""
                        <tr>
                            <td>{row['ticker']}</td>
                            <td>{row['beta']:.4f}</td>
                            <td>{row['tstat']:.4f}</td>
                            <td>{row['pvalue']:.4f}</td>
                            <td>{row['rsquared']:.4f}</td>
                            <td>[{row['conf_int_lower']:.4f}, {row['conf_int_upper']:.4f}]</td>
                        </tr>
                    """

                html_content += """
                    </table>
                </div>
                """

            html_content += """
            </body>
            </html>
            """

            # Write HTML to file
            with open(f'{dashboard_dir}/{factor_name.lower()}_factor_dashboard.html', 'w') as f:
                f.write(html_content)

            print(f"Dashboard created at: {dashboard_dir}/{factor_name.lower()}_factor_dashboard.html")
        else:
            print(f"No summary data found for factor: {factor_name}")

    except Exception as e:
        print(f"Error creating dashboard: {str(e)}")
        print(traceback.format_exc())


def create_comparison_dashboard(ch_utils, factor_names=None, output_dir='factor_dashboard'):
    """Create a dashboard comparing multiple factors"""
    try:
        print("Creating factor comparison dashboard...")

        # Get comparison data
        comparison_data = ch_utils.compare_factors(factor_names)

        if comparison_data.empty:
            print("No factor data found for comparison")
            return

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        dashboard_dir = os.path.join(output_dir, 'dashboard')
        os.makedirs(dashboard_dir, exist_ok=True)

        # Create dashboard HTML
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Factor Comparison Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #f0f0f0; padding: 10px; margin-bottom: 20px; }
                .section { margin-bottom: 30px; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                .chart { margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Factor Comparison Dashboard</h1>
                <p>Comparison of factor performance metrics</p>
            </div>

            <div class="section">
                <h2>Factor Performance Comparison</h2>
                <table>
                    <tr>
                        <th>Factor Name</th>
                        <th>Factor Type</th>
                        <th>Test Date</th>
                        <th>Annualized Return</th>
                        <th>Sharpe Ratio</th>
                        <th>Max Drawdown</th>
                        <th>Avg T-stat</th>
                        <th>Significant Stocks</th>
                    </tr>
        """

        # Add rows for each factor
        for _, row in comparison_data.iterrows():
            html_content += f"""
                <tr>
                    <td><a href="factor_dashboard/{row['factor_name'].lower()}_factor_dashboard.html">{row['factor_name']}</a></td>
                    <td>{row['factor_type']}</td>
                    <td>{row['test_date']}</td>
                    <td>{row['annualized_return']:.2%}</td>
                    <td>{row['sharpe_ratio']:.2f}</td>
                    <td>{row['max_drawdown']:.2%}</td>
                    <td>{row['avg_tstat']:.2f}</td>
                    <td>{row['significant_stocks']} / {row['total_stocks']}</td>
                </tr>
            """

        html_content += """
                </table>
            </div>

            <div class="section">
                <h2>Factor Comparison Charts</h2>
                <div class="chart">
                    <!-- Add comparison charts here -->
                </div>
            </div>
        </body>
        </html>
        """

        # Write HTML to file
        with open(f'{dashboard_dir}/factor_comparison_dashboard.html', 'w') as f:
            f.write(html_content)

        print(f"Comparison dashboard created at: {dashboard_dir}/factor_comparison_dashboard.html")

    except Exception as e:
        print(f"Error creating comparison dashboard: {str(e)}")
        print(traceback.format_exc())


def main():
    """Main function to run factor analysis"""
    parser = argparse.ArgumentParser(description='Run factor analysis for DJIA stocks')
    parser.add_argument('--factor', type=str, help='Factor to analyze (PEG, RSI14, RSI28, or ALL)')
    parser.add_argument('--tickers', type=str, default='AAPL,AMGN,AMZN',
                        help='Please input a list of tickers with splitter ","')
    parser.add_argument('--batch-no', type=int, default=0,
                        help='0: All  1:Caluculate and Construct   2:Test   3:Evaluate')
    parser.add_argument('--start-date', type=str, default=START_DATE, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=END_DATE, help='End date (YYYY-MM-DD)')
    parser.add_argument('--dashboard', action='store_true', help='Generate dashboards')
    parser.add_argument('--output-dir', type=str, default='factor_results', help='Directory to store output files')

    args = parser.parse_args()

    # Create ClickHouse utils
    ch_utils = ClickHouseUtils(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DATABASE
    )

    # Create tickers
    tickers = args.tickers.split(',')

    # Create output directory
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # Create factor tables if they don't exist
    ch_utils.create_factor_tables()

    # Initialize factors
    peg_factor = PEGFactor()
    rsi14_factor = RSIFactor(window=14)
    rsi28_factor = RSIFactor(window=28)

    # Initialize Fama-French factors
    smb_factor = SMBFactor()
    hml_factor = HMLFactor()
    market_factor = MarketFactor()

    # Initialize valuation factors
    pb_factor = PBFactor()

    # Initialize liquidity factors
    volume_factor = TradingVolumeFactor()

    # Initialize technical factors
    roc_factor = ROCFactor(window=20)

    # Initialize financial health factors
    current_ratio_factor = CurrentRatioFactor()
    cash_ratio_factor = CashRatioFactor()

    # Initialize operational factors
    inventory_turnover_factor = InventoryTurnoverFactor()
    gross_margin_factor = GrossProfitMarginFactor()

    # Initialize financial risk factors
    debt_equity_factor = DebtToEquityFactor()
    interest_coverage_factor = InterestCoverageFactor()

    # Initialize growth factors
    revenue_growth_factor = RevenueGrowthFactor()

    # Initialize ESG factors
    board_age_factor = BoardAgeFactor()
    exec_comp_factor = ExecutiveCompensationFactor()
    env_rating_factor = EnvironmentRatingFactor()

    # Initialize sentiment factors
    avg_sentiment_factor = AverageSentimentFactor()
    new_sentiment_factor = NewsSentimentFactor()

    # Run factor analysis based on arguments
    factor_arg = args.factor.upper() if args.factor else 'ALL'

    if factor_arg == 'PEG' or factor_arg == 'ALL':
        print("\n=== Running PEG Factor Analysis ===")
        peg_results = run_factor_analysis(peg_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                          output_dir=output_dir)
        if args.dashboard and peg_results:
            create_factor_dashboard("PEG", "Fundamental", ch_utils, output_dir)

    if factor_arg == 'RSI14' or factor_arg == 'ALL':
        print("\n=== Running RSI14 Factor Analysis ===")
        rsi14_results = run_factor_analysis(rsi14_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                            output_dir=output_dir)
        if args.dashboard and rsi14_results:
            create_factor_dashboard("RSI14", "Technical", ch_utils, output_dir)

    if factor_arg == 'RSI28' or factor_arg == 'ALL':
        print("\n=== Running RSI28 Factor Analysis ===")
        rsi28_results = run_factor_analysis(rsi28_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                            output_dir=output_dir)
        if args.dashboard and rsi28_results:
            create_factor_dashboard("RSI28", "Technical", ch_utils, output_dir)

    # Fama-French factors
    if factor_arg == 'SMB' or factor_arg == 'ALL':
        print("\n=== Running SMB Factor Analysis ===")
        smb_results = run_factor_analysis(smb_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                          output_dir=output_dir)
        if args.dashboard and smb_results:
            create_factor_dashboard("SMB", "Fama-French", ch_utils, output_dir)

    if factor_arg == 'HML' or factor_arg == 'ALL':
        print("\n=== Running HML Factor Analysis ===")
        hml_results = run_factor_analysis(hml_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                          output_dir=output_dir)
        if args.dashboard and hml_results:
            create_factor_dashboard("HML", "Fama-French", ch_utils, output_dir)

    if factor_arg == 'MARKET' or factor_arg == 'ALL':
        print("\n=== Running Market Factor Analysis ===")
        market_results = run_factor_analysis(market_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                             output_dir=output_dir)
        if args.dashboard and market_results:
            create_factor_dashboard("Rm_Rf", "Fama-French", ch_utils, output_dir)

    # Valuation factors
    if factor_arg == 'PB' or factor_arg == 'ALL':
        print("\n=== Running PB Factor Analysis ===")
        pb_results = run_factor_analysis(pb_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                         output_dir=output_dir)
        if args.dashboard and pb_results:
            create_factor_dashboard("PB", "Valuation", ch_utils, output_dir)

    # Liquidity factors
    if factor_arg == 'VOLUME' or factor_arg == 'ALL':
        print("\n=== Running Trading Volume Factor Analysis ===")
        volume_results = run_factor_analysis(volume_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                             output_dir=output_dir)
        if args.dashboard and volume_results:
            create_factor_dashboard("TradingVolume", "Liquidity", ch_utils, output_dir)

    # Technical factors
    if factor_arg == 'ROC' or factor_arg == 'ALL':
        print("\n=== Running ROC Factor Analysis ===")
        roc_results = run_factor_analysis(roc_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                          output_dir=output_dir)
        if args.dashboard and roc_results:
            create_factor_dashboard("ROC20", "Technical", ch_utils, output_dir)

    # Financial health factors
    if factor_arg == 'CR' or factor_arg == 'ALL':
        print("\n=== Running Current Ratio Factor Analysis ===")
        cr_results = run_factor_analysis(current_ratio_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                         output_dir=output_dir)
        if args.dashboard and cr_results:
            create_factor_dashboard("CurrentRatio", "Financial Health", ch_utils, output_dir)

    if factor_arg == 'CASH' or factor_arg == 'ALL':
        print("\n=== Running Cash Ratio Factor Analysis ===")
        cash_results = run_factor_analysis(cash_ratio_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                           output_dir=output_dir)
        if args.dashboard and cash_results:
            create_factor_dashboard("CashRatio", "Financial Health", ch_utils, output_dir)

    # Operational factors
    if factor_arg == 'IT' or factor_arg == 'ALL':
        print("\n=== Running Inventory Turnover Factor Analysis ===")
        it_results = run_factor_analysis(inventory_turnover_factor, args.batch_no, tickers, args.start_date,
                                         args.end_date, output_dir=output_dir)
        if args.dashboard and it_results:
            create_factor_dashboard("InventoryTurnover", "Operational", ch_utils, output_dir)

    if factor_arg == 'GPM' or factor_arg == 'ALL':
        print("\n=== Running Gross Profit Margin Factor Analysis ===")
        gpm_results = run_factor_analysis(gross_margin_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                          output_dir=output_dir)
        if args.dashboard and gpm_results:
            create_factor_dashboard("GrossProfitMargin", "Operational", ch_utils, output_dir)

    # Financial risk factors
    if factor_arg == 'DE' or factor_arg == 'ALL':
        print("\n=== Running Debt-to-Equity Factor Analysis ===")
        de_results = run_factor_analysis(debt_equity_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                         output_dir=output_dir)
        if args.dashboard and de_results:
            create_factor_dashboard("DebtToEquity", "Financial Risk", ch_utils, output_dir)

    if factor_arg == 'IC' or factor_arg == 'ALL':
        print("\n=== Running Interest Coverage Factor Analysis ===")
        ic_results = run_factor_analysis(interest_coverage_factor, args.batch_no, tickers, args.start_date,
                                         args.end_date, output_dir=output_dir)
        if args.dashboard and ic_results:
            create_factor_dashboard("InterestCoverage", "Financial Risk", ch_utils, output_dir)

    # Growth factors
    if factor_arg == 'RG' or factor_arg == 'ALL':
        print("\n=== Running Revenue Growth Factor Analysis ===")
        rg_results = run_factor_analysis(revenue_growth_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                         output_dir=output_dir)
        if args.dashboard and rg_results:
            create_factor_dashboard("RevenueGrowth", "Growth", ch_utils, output_dir)

    # ESG factors
    if factor_arg == 'BA' or factor_arg == 'ALL':
        print("\n=== Running Board Age Factor Analysis ===")
        ba_results = run_factor_analysis(board_age_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                         output_dir=output_dir)
        if args.dashboard and ba_results:
            create_factor_dashboard("BoardAge", "Governance", ch_utils, output_dir)

    if factor_arg == 'EC' or factor_arg == 'ALL':
        print("\n=== Running Executive Compensation Factor Analysis ===")
        ec_results = run_factor_analysis(exec_comp_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                         output_dir=output_dir)
        if args.dashboard and ec_results:
            create_factor_dashboard("ExecCompToRevenue", "ESG Governance", ch_utils, output_dir)

    if factor_arg == 'ER' or factor_arg == 'ALL':
        print("\n=== Running Environment Rating Factor Analysis ===")
        er_results = run_factor_analysis(env_rating_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                         output_dir=output_dir)
        if args.dashboard and er_results:
            create_factor_dashboard("EnvRating", "ESG Environmental", ch_utils, output_dir)

    # Sentiment factors
    if factor_arg == 'AVGSENT14' or factor_arg == 'ALL':
        print("\n=== Running Average Sentiment Factor Analysis ===")
        sent_results = run_factor_analysis(avg_sentiment_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                           output_dir=output_dir)
        if args.dashboard and sent_results:
            create_factor_dashboard("AvgSentiment14", "Sentiment", ch_utils, output_dir)

    if factor_arg == 'NEWSENT' or factor_arg == 'ALL':
        print("\n=== Running New Sentiment Factor Analysis ===")
        sent_results = run_factor_analysis(new_sentiment_factor, args.batch_no, tickers, args.start_date, args.end_date,
                                           output_dir=output_dir)
        if args.dashboard and sent_results:
            create_factor_dashboard("NEWSENT", "Sentiment", ch_utils, output_dir)

    # Create comparison dashboard if requested
    if args.dashboard:
        all_factors = [
            "PEG", "RSI14", "RSI28", "SMB", "HML", "Rm_Rf", "PB", "TradingVolume",
            "ROC20", "CurrentRatio", "CashRatio", "InventoryTurnover", "GrossProfitMargin",
            "DebtToEquity", "InterestCoverage", "RevenueGrowth", "BoardAge",
            "ExecCompToRevenue", "EnvRating", "NEWSENT", "AVGSENT14"
        ]
        create_comparison_dashboard(ch_utils, all_factors, output_dir)

    print("\nAll analyses completed.")


if __name__ == "__main__":
    main()
