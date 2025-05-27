# DJIA Factor Modeling Analysis

This project implements factor modeling for the DJIA 30 stocks, analyzing the effectiveness of various factors across multiple categories.

## Overview

The analysis follows these steps for each factor:

1. **Sorting and Grouping**: Sort the 30 DJIA stocks by factor value
2. **Portfolio Construction**:
   - High Factor Portfolio: Market-cap weighted portfolio of high factor stocks
   - Low Factor Portfolio: Market-cap weighted portfolio of low factor stocks
3. **Factor Calculation**: Factor Return = Return High Portfolio − Return Low Portfolio
4. **Factor Testing**:
   - Regression model: Ri = α + β⋅Factor + ϵi
   - Significance testing: |T-stat| > 1.96 indicates significant factor
   - R-squared analysis: Measures factor's explanatory power
   - Backtesting: Performance of long-short portfolio based on factor

## Implemented Factors

### Valuation Factors
- **PEG (Price/Earnings to Growth)**: Lower PEG indicates better value relative to growth
- **PB (Price-to-Book)**: Lower P/B indicates potentially undervalued stocks

### Technical Factors
- **RSI-14 (Relative Strength Index, 14-day window)**: Measures momentum by comparing recent gains to recent losses
- **RSI-28 (Relative Strength Index, 28-day window)**: Longer-term momentum indicator with less sensitivity to short-term price changes
- **ROC-20 (Rate of Change, 20-day window)**: Measures price momentum over a 20-day period

### Fama-French Factors
- **SMB (Small Minus Big)**: Measures the excess return of small-cap stocks over large-cap stocks
- **HML (High Minus Low)**: Measures the excess return of value stocks over growth stocks
- **Rm-Rf (Market Factor)**: Measures the excess return of the market over the risk-free rate

### Liquidity Factors
- **Trading Volume**: Measures stock liquidity based on trading volume

### Operational Factors
- **Inventory Turnover**: Measures how efficiently a company manages its inventory

### ESG Factors
- **Board Age**: Average age of a company's board of directors

### Sentiment Factors
- **Average Sentiment**: Measures the average sentiment of news and social media about a company

## Strategy Framework

The project includes both long-short and long-only trading strategies:

### Long-Short Strategy
- Goes long on stocks with high factor scores and short on stocks with low factor scores
- Configurable parameters for position sizing and allocation

### Long-Only Strategy
- Only takes long positions on stocks with high factor scores
- Supports both market-cap and equal weighting

## Data Source

The analysis uses stock price data from a ClickHouse database:
- Host: 44.222.122.134:9000
- Database: jacky_database1
- Table: tick_data
- User: jacky_user

## Project Structure

- `factors/` - Directory containing factor class implementations
  - `base_factor.py` - Base class for all factors
  - `valuation_factors.py` - Valuation factor implementations (PEG, PB, etc.)
  - `technical_factors.py` - Technical factor implementations (RSI, ROC, etc.)
  - `fama_french_factors.py` - Fama-French factor implementations
  - `liquidity_factors.py` - Liquidity factor implementations
  - `financial_health_factors.py` - Financial health factor implementations
  - `operational_factors.py` - Operational factor implementations
  - `financial_risk_factors.py` - Financial risk factor implementations
  - `growth_factors.py` - Growth factor implementations
  - `esg_factors.py` - ESG factor implementations
  - `sentiment_factors.py` - Sentiment factor implementations
- `strategy/` - Directory containing strategy implementations
  - `base_strategy.py` - Base class for all strategies
  - `long_short_strategy.py` - Long-short strategy implementation
  - `long_only_strategy.py` - Long-only strategy implementation
- `clickhouse_utils.py` - Utility functions for ClickHouse operations
- `config.py` - Configuration loader for environment variables
- `run_factor_analysis.py` - Script to run analysis for multiple factors
- `run_backtest.py` - Script to run backtests for trading strategies
- `generate_factor_dashboard.py` - Dashboard generation script
- `factor_weight_optimizer.py` - Script to optimize factor weights
- `analyze_trading_results.py` - Script to analyze trading results
- `requirements.txt` - Required Python packages
- `.env` - Environment variables for configuration

## Database Schema

The project uses the following tables in ClickHouse:

1. **factor_summary** - Summary statistics for each factor
   - factor_name, factor_type, test_date, etc.
   - Performance metrics: annualized_return, sharpe_ratio, etc.
   - update_time: DateTime for tracking record creation

2. **factor_details** - Detailed stock-level results for each factor
   - factor_name, factor_type, test_date, ticker, beta, tstat, etc.

3. **factor_timeseries** - Time series data for factor values
   - factor_name, factor_type, date, factor_value, etc.

4. **factor_values** - Raw factor values for each stock
   - factor_type, factor_name, ticker, date, value

## Getting Started

### Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd factor-modeling-model
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install required packages:
   ```
   pip install -r requirements.txt
   ```

4. Configure the application:
   - Copy `config_example.py` to `config.py`:
     ```
     cp config_example.py config.py
     ```
   - Edit `config.py` and update the ClickHouse connection settings:
     ```python
     CLICKHOUSE_HOST = 'your_clickhouse_host'
     CLICKHOUSE_USER = 'your_username'
     CLICKHOUSE_PASSWORD = 'your_password'
     ```
   - Copy `.env.example` to `.env` (if not already present)
   - Update the values in `.env` with your database credentials and settings

### Running the Analysis

To run the factor analysis for all factors:

```bash
python run_factor_analysis.py --factor ALL
```

To run the analysis for a specific factor:

```bash
python run_factor_analysis.py --factor PEG
python run_factor_analysis.py --factor RSI14
python run_factor_analysis.py --factor RSI28
```

To run the analysis for a specific factor and save results to a custom directory:

```bash
python run_factor_analysis.py --factor PEG --output-dir my_results
```

To specify a date range and output directory:

```bash
python run_factor_analysis.py --factor ALL --start-date 2025-01-01 --end-date 2025-03-31 --output-dir custom_results
```

To run analysis and generate dashboards in a specific directory:

```bash
python run_factor_analysis.py --factor ALL --dashboard --output-dir factor_output
```

### Running Backtests

To run the trading strategy with default settings:

```bash
python run_backtest.py --strategy long_short --output-dir my_backtest_results
```

To run with both long-short and long-only strategies:

```bash
python run_backtest.py --strategy both --output-dir my_backtest_results
```

To run with parallel processing:

```bash
python run_backtest.py --strategy both --parallel --num-processes 4
```

### Generating Dashboards

To generate dashboards from the stored factor data:

```bash
python generate_factor_dashboard.py --factor ALL --comparison --output-dir my_dashboards
```

To generate a dashboard for a specific factor:

```bash
python generate_factor_dashboard.py --factor PEG --output-dir factor_results
```

### Optimizing Factor Weights

To optimize factor weights based on historical performance:

```bash
python factor_weight_optimizer.py --method sharpe --output-dir my_factor_weights
```

Available optimization methods:
- `sharpe`: Weight by Sharpe ratio
- `equal`: Equal weighting
- `information_ratio`: Weight by Information ratio
- `return`: Weight by annualized return

### Analyzing Trading Results

To analyze the results of a backtest:

```bash
python analyze_trading_results.py --results-dir my_backtest_results --output-dir my_analysis
```

## Interpreting Results

- **T-statistic**: |T-stat| > 1.96 indicates the factor has a statistically significant effect
- **R-squared**: Higher values indicate better explanatory power
- **Sharpe Ratio**: Higher values indicate better risk-adjusted returns
- **Confidence Intervals**: Narrower intervals indicate more precise estimates

## Adding New Factors

To add a new factor:

1. Create a new factor class in the appropriate file in the `factors` directory, inheriting from `BaseFactor`:

```python
from factors.base_factor import BaseFactor

class MyNewFactor(BaseFactor):
    """
    My new factor implementation
    """
    
    def __init__(self, param1=default_value, param2=default_value):
        """
        Initialize the factor
        
        Parameters:
        - param1: Description of parameter 1
        - param2: Description of parameter 2
        """
        super().__init__(name="MyNewFactor", factor_type="MyFactorType")
        self.param1 = param1
        self.param2 = param2
    
    def calculate(self, ticker, start_date, end_date):
        """
        Calculate factor values for a ticker
        
        Parameters:
        - ticker: Stock ticker
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
        
        Returns:
        - Series with factor values
        """
        # Implement factor calculation logic here
        # ...
        
        return factor_values
```

2. Update the `__init__.py` file in the `factors` directory to import and expose your new factor:

```python
from factors.base_factor import BaseFactor
# ... other imports ...
from factors.my_factor_file import MyNewFactor

__all__ = ['BaseFactor', ..., 'MyNewFactor']
```

3. Register your factor in `run_factor_analysis.py` by adding it to the factor registry:

```python
FACTOR_REGISTRY = {
    # ... existing factors ...
    'MYNEWFACTOR': MyNewFactor,
}
```

4. Run the analysis with your new factor:

```bash
python run_factor_analysis.py --factor MYNEWFACTOR
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
