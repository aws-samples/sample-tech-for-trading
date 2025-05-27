import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import statsmodels.api as sm
from datetime import datetime
import traceback
import os

class BaseFactor:
    """Base class for all factors"""
    
    def __init__(self, name, factor_type, description=""):
        """Initialize the factor"""
        self.name = name
        self.factor_type = factor_type
        self.description = description
        self.results = {}
    
    def calculate(self, data):
        """
        Calculate factor values
        
        Parameters:
        - data: Dictionary containing necessary data for factor calculation
        
        Returns:
        - DataFrame with factor values (index=dates, columns=tickers)
        """
        raise NotImplementedError("Subclasses must implement calculate method")
    
    def construct_portfolios(self, factor_df, returns_df, market_cap_df, n_groups=3):
        """
        Construct portfolios based on factor values
        
        Parameters:
        - factor_df: DataFrame with factor values (index=dates, columns=tickers)
        - returns_df: DataFrame with daily returns (index=dates, columns=tickers)
        - market_cap_df: DataFrame with market cap values (index=dates, columns=tickers)
        - n_groups: Number of groups to divide stocks into
        
        Returns:
        - DataFrame with portfolio returns (index=dates, columns=[High_Factor, Low_Factor, Factor_Factor])
        """
        portfolio_returns = pd.DataFrame(index=returns_df.index)
        
        for i, date in enumerate(returns_df.index):
            #print(f"!!!Processing {self.name} factor with round {i} for date: {date}")
            if date not in factor_df.index or date == returns_df.index[0]:
                continue
            
            # Get factor values for previous day to avoid look-ahead bias
            prev_dates = factor_df.index[factor_df.index < date]
            #print(f"!!!Processing prev_dates: {prev_dates} with round{i}")

            if len(prev_dates) == 0:
                #print(f"Skipping date {date}: Not enough stocks ({len(factor_values)}) for {n_groups} groups")
                continue
                
            prev_date = prev_dates[-1]
            #print(f"!!!Processing prev_date: {prev_date} with round{i}")
            factor_values = factor_df.loc[prev_date].dropna()
            #print(f"!!!Processing factor_values: {factor_values} with round{i}")
            #print(f"Number of stocks with factor data: {len(factor_values)}")
            
            if len(factor_values) < n_groups:
                #print(f"Skipping date {date}: Not enough stocks ({len(factor_values)}) for {n_groups} groups")
                continue

            # Sort stocks by factor
            sorted_stocks = factor_values.sort_values(ascending=False)
            
            # Divide into groups
            group_size = max(1, len(sorted_stocks) // n_groups)
            
            # High factor group (top group)
            high_factor_stocks = sorted_stocks.iloc[:group_size].index.tolist()
            
            # Low factor group (bottom group)
            low_factor_stocks = sorted_stocks.iloc[-group_size:].index.tolist()
            
            # Calculate market cap weights for each group
            if prev_date in market_cap_df.index:
                high_group_mcap = market_cap_df.loc[prev_date, high_factor_stocks].dropna()
                if not high_group_mcap.empty:
                    high_weights = high_group_mcap / high_group_mcap.sum()
                else:
                    high_weights = pd.Series(1.0/len(high_factor_stocks), index=high_factor_stocks)
                
                low_group_mcap = market_cap_df.loc[prev_date, low_factor_stocks].dropna()
                if not low_group_mcap.empty:
                    low_weights = low_group_mcap / low_group_mcap.sum()
                else:
                    low_weights = pd.Series(1.0/len(low_factor_stocks), index=low_factor_stocks)
            else:
                # Equal weights if market cap not available
                high_weights = pd.Series(1.0/len(high_factor_stocks), index=high_factor_stocks)
                low_weights = pd.Series(1.0/len(low_factor_stocks), index=low_factor_stocks)
            
            # Calculate weighted returns for each group
            high_factor_return = (returns_df.loc[date, high_factor_stocks] * high_weights).sum()
            low_factor_return = (returns_df.loc[date, low_factor_stocks] * low_weights).sum()
            
            # Store portfolio returns
            portfolio_returns.loc[date, f'High_{self.name}'] = high_factor_return
            portfolio_returns.loc[date, f'Low_{self.name}'] = low_factor_return
            portfolio_returns.loc[date, f'{self.name}_Factor'] = high_factor_return - low_factor_return
        
        return portfolio_returns.fillna(0)
    
    def test_factor(self, returns_df, factor_returns):
        """
        Test factor effectiveness using regression analysis
        
        Parameters:
        - returns_df: DataFrame with daily returns (index=dates, columns=tickers)
        - factor_returns: Series with factor returns (index=dates)
        
        Returns:
        - DataFrame with regression results (index=tickers, columns=[Alpha, Beta, T-stat, P-value, R-squared, etc.])
        """
        results = {}
        
        # For each stock, run regression against the factor
        for ticker in returns_df.columns:
            stock_returns = returns_df[ticker].dropna()
            aligned_factor = factor_returns.loc[stock_returns.index].dropna()
            
            # Skip if not enough data
            if len(aligned_factor) < 30:
                continue
                
            # Add constant for intercept
            X = sm.add_constant(aligned_factor)
            
            # Run regression
            model = sm.OLS(stock_returns.loc[aligned_factor.index], X).fit()
            
            # Store results
            results[ticker] = {
                'Alpha': model.params.iloc[0] if len(model.params) > 0 else np.nan,
                'Beta': model.params.iloc[1] if len(model.params) > 1 else np.nan,
                'T-stat': model.tvalues.iloc[1] if len(model.tvalues) > 1 else np.nan,
                'P-value': model.pvalues.iloc[1] if len(model.pvalues) > 1 else np.nan,
                'R-squared': model.rsquared,
                'Conf_Int_Lower': model.conf_int().iloc[1, 0] if len(model.conf_int()) > 1 else np.nan,
                'Conf_Int_Upper': model.conf_int().iloc[1, 1] if len(model.conf_int()) > 1 else np.nan
            }
        
        return pd.DataFrame(results).T
    
    def evaluate_portfolio(self, portfolio_returns):
        """
        Evaluate portfolio performance metrics
        
        Parameters:
        - portfolio_returns: DataFrame with portfolio returns (index=dates, columns=[High_Factor, Low_Factor, Factor_Factor])
        
        Returns:
        - Tuple of (performance_results, cumulative_returns)
        """
        # Calculate cumulative returns
        # Ensure all values are numeric before calculation
        portfolio_returns = portfolio_returns.apply(pd.to_numeric, errors='coerce')
        cumulative_returns = (1 + portfolio_returns).cumprod()
        
        # Calculate annualized return
        total_days = len(portfolio_returns)
        trading_days_per_year = 252
        years = total_days / trading_days_per_year
        
        annualized_return = {}
        for col in portfolio_returns.columns:
            if cumulative_returns[col].iloc[-1] > 0:
                annualized_return[col] = (cumulative_returns[col].iloc[-1] ** (1/years)) - 1
            else:
                annualized_return[col] = -1  # Handle negative cumulative returns
        
        # Calculate volatility (annualized)
        volatility = {col: portfolio_returns[col].std() * np.sqrt(trading_days_per_year) for col in portfolio_returns.columns}
        
        # Calculate Sharpe ratio (assuming risk-free rate of 0.02)
        risk_free_rate = 0.02
        sharpe_ratio = {
            col: (annualized_return[col] - risk_free_rate) / volatility[col] if volatility[col] > 0 else 0
            for col in portfolio_returns.columns
        }
        
        # Calculate maximum drawdown
        max_drawdown = {}
        for col in portfolio_returns.columns:
            cum_returns = cumulative_returns[col]
            running_max = cum_returns.cummax()
            drawdown = (cum_returns / running_max) - 1
            max_drawdown[col] = drawdown.min()
        
        # Compile results
        results = pd.DataFrame({
            'Annualized Return': annualized_return,
            'Annualized Volatility': volatility,
            'Sharpe Ratio': sharpe_ratio,
            'Maximum Drawdown': max_drawdown
        })
        
        return results, cumulative_returns

    def plot_results(self, save_dir='.'):
        """
        Plot factor analysis results

        Parameters:
        - save_dir: Directory to save plots
        """
        if not self.results:
            print("No results to plot. Run analyze() first.")
            return

        # Create directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)

        # Plot cumulative returns
        plt.figure(figsize=(12, 6))
        self.results['cumulative_returns'].plot()
        plt.title(f'Cumulative Returns of {self.name} Factor Portfolios')
        plt.xlabel('Date')
        plt.ylabel('Cumulative Return')
        plt.grid(True)
        plt.savefig(f'{save_dir}/{self.name.lower()}_factor_cumulative_returns_real_data.png')

        # Plot factor test results distribution
        plt.figure(figsize=(15, 10))

        plt.subplot(2, 2, 1)
        sns.histplot(self.results['factor_test_results']['beta'], kde=True)
        plt.title('Distribution of Beta Coefficients')
        plt.axvline(x=0, color='r', linestyle='--')

        plt.subplot(2, 2, 2)
        sns.histplot(self.results['factor_test_results']['tstat'], kde=True)
        plt.title('Distribution of T-statistics')
        plt.axvline(x=1.96, color='r', linestyle='--')
        plt.axvline(x=-1.96, color='r', linestyle='--')

        plt.subplot(2, 2, 3)
        sns.histplot(self.results['factor_test_results']['rsquared'], kde=True)
        plt.title('Distribution of R-squared Values')

        plt.subplot(2, 2, 4)
        rolling_factor = self.results['portfolio_returns'][f'{self.name}_Factor'].rolling(
            window=min(252, len(self.results['portfolio_returns']))).mean()
        rolling_factor.plot()
        plt.title(
            f'{min(252, len(self.results["portfolio_returns"]))}-Day Rolling Average of {self.name} Factor Returns')
        plt.axhline(y=0, color='r', linestyle='--')

        plt.tight_layout()
        plt.savefig(f'{save_dir}/{self.name.lower()}_factor_statistics_real_data.png')

        plt.close('all')

    # def analyze(self, price_data, market_cap_df, additional_data=None, output_dir='.'):
    #     """
    #     Run full factor analysis
    #
    #     Parameters:
    #     - price_data: Dictionary of DataFrames with price data (key=ticker, value=DataFrame)
    #     - market_cap_df: DataFrame with market cap values (index=dates, columns=tickers)
    #     - factor_action: Function to calculate factor values
    #     - additional_data: Dictionary with additional data needed for factor calculation
    #     - output_dir: Directory to save output files
    #
    #     Returns:
    #     - Dictionary with analysis results
    #     """
    #     try:
    #         print(f"Running {self.name} factor analysis...")
    #
    #         # Calculate daily returns
    #         print("Calculating daily returns...")
    #         returns_df = pd.DataFrame()
    #         for symbol, df in price_data.items():
    #             if 'adjusted_close' in df.columns:
    #                 returns_df[symbol] = df['adjusted_close'].pct_change().fillna(0)
    #
    #         if factor_action in (0, 1):
    #             # Calculate factor values
    #             print(f"Calculating {self.name} factor values...")
    #             factor_df = self.calculate(price_data if additional_data is None else additional_data)
    #
    #             # Construct portfolios
    #             print(f"Constructing high and low {self.name} portfolios...")
    #             portfolio_returns = self.construct_portfolios(factor_df, returns_df, market_cap_df)
    #
    #             if factor_action == 1:
    #                 print(f"Calculating && Constructing {self.name} factor values are done...")
    #
    #         if factor_action in (0, 2):
    #             # Test factor effectiveness
    #             print(f"Testing {self.name} factor effectiveness...")
    #             factor_test_results = self.test_factor(returns_df, portfolio_returns[f'{self.name}_Factor'])
    #
    #             if factor_action == 2:
    #                 print(f"Testing {self.name} factor effectiveness are done...")
    #
    #         if factor_action in (0, 3):
    #             # Evaluate portfolio performance
    #             print("Evaluating portfolio performance...")
    #             performance_results, cumulative_returns = self.evaluate_portfolio(portfolio_returns)
    #
    #         # Store results
    #         self.results = {
    #             'factor_values': factor_df,
    #             'returns': returns_df,
    #             'portfolio_returns': portfolio_returns,
    #             'factor_test_results': factor_test_results,
    #             'performance_results': performance_results,
    #             'cumulative_returns': cumulative_returns
    #         }
    #
    #         # Print results
    #         print(f"\n--- {self.name} Factor Test Results ---")
    #         print("\nAverage Factor Test Statistics:")
    #         print(f"Average Beta: {factor_test_results['Beta'].mean():.4f}")
    #         print(f"Average T-stat: {factor_test_results['T-stat'].mean():.4f}")
    #         print(f"Average R-squared: {factor_test_results['R-squared'].mean():.4f}")
    #         print(f"Significant stocks (|T-stat| > 1.96): {(abs(factor_test_results['T-stat']) > 1.96).sum()} out of {len(factor_test_results)}")
    #
    #         print("\n--- Portfolio Performance ---")
    #         print(performance_results)
    #
    #         # Plot results
    #         self.plot_results(output_dir)
    #
    #         return self.results
    #
    #     except Exception as e:
    #         print(f"Error in {self.name} factor analysis: {str(e)}")
    #         print(traceback.format_exc())
    #         return None

    def analyze_calculate_construct(self, price_data, market_cap_df, additional_data=None):
        #Calculate factor values and build portfolios
        print(f"Begin to calculate {self.name} factor values and construct portfolios...")

        try:
            # Calculate daily returns
            print("Calculating daily returns...")
            returns_df = pd.DataFrame()
            for symbol, df in price_data.items():
                if 'adjusted_close' in df.columns:
                    returns_df[symbol] = df['adjusted_close'].pct_change().fillna(0)

            # Calculate factor values
            print(f"Calculating {self.name} factor values...")
            factor_df = self.calculate(price_data if additional_data is None else additional_data)

            # Construct portfolios
            print(f"Constructing high and low {self.name} portfolios...")
            portfolio_returns = self.construct_portfolios(factor_df, returns_df, market_cap_df)
            print(f"Calculating && Constructing {self.name} factor values are done...")

            # Store results
            self.results = {
                'factor_values': factor_df,
                'returns_df': returns_df,
                'portfolio_returns': portfolio_returns
            }

            return self.results

        except Exception as e:
            print(f"Error in {self.name} factor analysis: {str(e)}")
            print(traceback.format_exc())
            return None

    def analyze_test_factor(self, returns_df, portfolio_returns):
        print(f"Begin to test {self.name} factor values...")
        # Test factor effectiveness
        try:
            factor_test_results = self.test_factor(returns_df, portfolio_returns[f'{self.name}_Factor'])

            print(f"Testing {self.name} factor effectiveness are done...")

            # Store results
            self.results['factor_test_results'] = factor_test_results
            self.results['portfolio_returns'] = portfolio_returns

            # Print results
            print(f"\n--- {self.name} Factor Test Results ---")
            print("\nAverage Factor Test Statistics:")
            
            # Check if the DataFrame is empty
            if factor_test_results.empty:
                print("No factor test results available.")
                return None
                
            # Check for required columns and print statistics safely
            if 'Beta' in factor_test_results.columns:
                print(f"Average Beta: {factor_test_results['Beta'].mean():.4f}")
            else:
                print("Beta column not found in factor test results")
                
            if 'T-stat' in factor_test_results.columns:
                print(f"Average T-stat: {factor_test_results['T-stat'].mean():.4f}")
                if 'T-stat' in factor_test_results.columns:
                    significant_count = (abs(factor_test_results['T-stat']) > 1.96).sum()
                    print(f"Significant stocks (|T-stat| > 1.96): {significant_count} out of {len(factor_test_results)}")
            else:
                print("T-stat column not found in factor test results")
                
            if 'R-squared' in factor_test_results.columns:
                print(f"Average R-squared: {factor_test_results['R-squared'].mean():.4f}")
            else:
                print("R-squared column not found in factor test results")

            return self.results

        except Exception as e:
            print(f"Error in {self.name} factor analysis: {str(e)}")
            print(traceback.format_exc())
            return None

    def analyze_evaluate_portfolio(self, factor_test_results, portfolio_returns, output_dir):
        print(f"Begin to evaluate {self.name} factor portfolios...")
        try:
            performance_results, cumulative_returns = self.evaluate_portfolio(portfolio_returns)
            print(f"Evaluating {self.name} factor portfolios are done...")

            # Store results
            self.results['performance_results'] = performance_results
            self.results['cumulative_returns'] = cumulative_returns
            self.results['factor_test_results'] = factor_test_results

            print("\n--- Portfolio Performance ---")
            print(performance_results)

            # Plot results
            # self.plot_results(output_dir)

            return self.results

        except Exception as e:
            print(f"Error in {self.name} factor analysis: {str(e)}")
            print(traceback.format_exc())
            return None