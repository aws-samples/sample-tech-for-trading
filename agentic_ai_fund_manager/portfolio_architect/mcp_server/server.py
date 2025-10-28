"""
server.py

ETF Data MCP Server - Real-time ETF Data Retrieval
"""

import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(host="0.0.0.0", stateless_http=True)

@mcp.tool()
def calculate_correlation(tickers: list) -> dict:
    """Calculate correlation matrix between selected ETFs"""
    try:
        import numpy as np
        from datetime import datetime, timedelta
        
        # Calculate correlation with 2 years of data
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=504)
        
        # Collect all ETF data
        etf_data = {}
        for ticker in tickers:
            etf = yf.Ticker(ticker)
            hist = etf.history(start=start_date, end=end_date)
            if not hist.empty:
                etf_data[ticker] = hist['Close'].pct_change().dropna()
        
        # Generate correlation matrix
        correlation_matrix = {}
        for ticker1 in tickers:
            correlation_matrix[ticker1] = {}
            for ticker2 in tickers:
                if ticker1 == ticker2:
                    correlation_matrix[ticker1][ticker2] = 1.0
                elif ticker1 in etf_data and ticker2 in etf_data:
                    # Find common dates
                    common_dates = etf_data[ticker1].index.intersection(etf_data[ticker2].index)
                    if len(common_dates) > 100:  # Only when sufficient data is available
                        returns1 = etf_data[ticker1][common_dates]
                        returns2 = etf_data[ticker2][common_dates]
                        
                        correlation = np.corrcoef(returns1, returns2)[0, 1]
                        correlation_matrix[ticker1][ticker2] = round(correlation, 3)
                    else:
                        correlation_matrix[ticker1][ticker2] = 0.0
                else:
                    correlation_matrix[ticker1][ticker2] = 0.0
        
        return {
            "correlation_matrix": correlation_matrix
        }
        
    except Exception as e:
        return {"error": f"Correlation calculation failed: {str(e)}"}

@mcp.tool()
def analyze_etf_performance(ticker: str) -> dict:
    """Individual ETF performance analysis (including Monte Carlo simulation)"""
    try:
        # Collect 2 years of data
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=504)  # Approximately 2 years
        
        etf = yf.Ticker(ticker)
        hist = etf.history(start=start_date, end=end_date)
        
        if hist.empty:
            return {"error": f"No data available for ticker: {ticker}"}
        
        # Calculate daily returns
        daily_returns = hist['Close'].pct_change().dropna()
        
        # Calculate annual return and volatility
        annual_return = np.mean(daily_returns) * 252
        annual_volatility = np.std(daily_returns) * np.sqrt(252)
        
        # Monte Carlo simulation (simplified to 1000 iterations)
        n_simulations = 1000
        n_days = 252  # 1 year
        
        # Calculate return distribution after 1 year (based on 1 million base amount)
        base_amount = 1000000
        final_values = []
        
        for _ in range(n_simulations):
            # Sample daily returns from normal distribution
            simulated_returns = np.random.normal(
                annual_return / 252, 
                annual_volatility / np.sqrt(252), 
                n_days
            )
            
            # Calculate compound returns
            final_value = base_amount * np.prod(1 + simulated_returns)
            final_values.append(final_value)
        
        final_values = np.array(final_values)
        
        # Calculate simple indicators only
        expected_return_pct = (np.mean(final_values) / base_amount - 1) * 100
        loss_probability = np.sum(final_values < base_amount) / n_simulations * 100
        
        # Calculate return distribution by range
        return_percentages = (final_values / base_amount - 1) * 100
        
        distribution = {
            "-20% and below": int(np.sum(return_percentages <= -20)),
            "-20% ~ -10%": int(np.sum((return_percentages > -20) & (return_percentages <= -10))),
            "-10% ~ 0%": int(np.sum((return_percentages > -10) & (return_percentages <= 0))),
            "0% ~ 10%": int(np.sum((return_percentages > 0) & (return_percentages <= 10))),
            "10% ~ 20%": int(np.sum((return_percentages > 10) & (return_percentages <= 20))),
            "20% ~ 30%": int(np.sum((return_percentages > 20) & (return_percentages <= 30))),
            "30% and above": int(np.sum(return_percentages > 30))
        }
        
        return {
            "ticker": ticker,
            "expected_annual_return": round(expected_return_pct, 1),
            "loss_probability": round(loss_probability, 1),
            "historical_annual_return": round(annual_return * 100, 1),
            "volatility": round(annual_volatility * 100, 1),
            "return_distribution": distribution
        }
        
    except Exception as e:
        return {"error": f"ETF analysis failed for {ticker}: {str(e)}"}

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
