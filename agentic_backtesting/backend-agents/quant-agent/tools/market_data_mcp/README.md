# Market Data MCP Tool

A comprehensive market data tool for AgentCore MCP Gateway that provides historical stock data, technical indicators, and market statistics for backtesting and analysis.

## Overview

This tool provides:
- **Historical Price Data**: 1 year of business day stock prices
- **Technical Indicators**: Simple Moving Averages (SMA 20, SMA 50)
- **Market Statistics**: Volatility, returns, max drawdown
- **Volume Data**: Daily trading volumes
- **Multi-Symbol Support**: Individual stocks and sector-based queries

## Core Files

- **`lambda_function.py`** - Main Lambda function that serves market data
- **`requirements.txt`** - Python dependencies for the Lambda function
- **`deployment/`** - All deployment and infrastructure scripts

## Supported Symbols

### Individual Stocks
- **Technology**: AAPL, MSFT, GOOGL, NVDA
- **Healthcare**: JNJ, PFE
- **Finance**: JPM, BAC
- **Energy**: XOM, CVX

### Sector Queries (Legacy)
- Technology, Healthcare, Finance, Energy

## Data Sources

1. **S3 Tables (Primary)**: Iceberg format tables for scalable analytics
2. **Fallback Generation**: Realistic mock data when S3 Tables is empty

## API Interface

### Input Parameters
```json
{
  "symbol": "AAPL"           // Preferred: specific stock symbol
  // OR
  "investment_area": "Technology"  // Legacy: sector-based query
}
```

### Output Format
```json
{
  "success": true,
  "data": {
    "symbol": "AAPL",
    "data_points": 252,
    "period_start": "2024-01-01T00:00:00",
    "period_end": "2024-12-31T00:00:00",
    "price_data": {
      "dates": ["2024-01-01", "..."],
      "prices": [150.25, 151.30, "..."],
      "volumes": [2000000, 1800000, "..."],
      "initial_price": 150.00,
      "final_price": 165.50,
      "min_price": 145.20,
      "max_price": 175.80
    },
    "technical_indicators": {
      "sma_20": [null, null, "...", 160.25],
      "sma_50": [null, null, "...", 158.75],
      "current_sma_20": 160.25,
      "current_sma_50": 158.75
    },
    "statistics": {
      "total_return_pct": 10.33,
      "volatility_annualized": 25.4,
      "max_drawdown_pct": 12.5,
      "avg_daily_volume": 1900000
    },
    "metadata": {
      "generated_at": "2024-01-01T12:00:00Z",
      "data_source": "fallback_tick_data_generator",
      "symbol_base_price": 150
    }
  }
}
```

## Local Testing

```bash
# Test the Lambda function locally
python3 lambda_function.py

# Test with specific symbol
python3 -c "
import lambda_function
import json
result = lambda_function.lambda_handler({'symbol': 'AAPL'}, None)
print(json.dumps(result, indent=2))
"
```

## Integration with AgentCore

This tool is designed to work with:
- **AgentCore Gateway**: Exposes the Lambda as an MCP tool
- **AgentCore Runtime**: Executes within agent workflows
- **AgentCore Memory**: Stores results for analysis
- **Strands Framework**: Orchestrates with other tools

## Deployment

See the `deployment/` directory for:
- Infrastructure setup scripts
- AWS Lambda deployment
- AgentCore Gateway configuration
- S3 Tables setup

## Environment Variables

The Lambda function uses these environment variables:
- `S3_TABLES_BUCKET`: S3 Tables bucket name
- `S3_TABLES_NAMESPACE`: Table namespace (default: "stock_data")
- `S3_TABLES_TABLE`: Table name (default: "stock_prices")

## Error Handling

- **S3 Tables Unavailable**: Automatically falls back to mock data generation
- **Invalid Symbol**: Returns error with supported symbols list
- **Network Issues**: Graceful degradation with cached/fallback data

## Future Enhancements

- Real-time market data integration
- Additional technical indicators (RSI, MACD, Bollinger Bands)
- Options data and volatility surface
- Fundamental data (P/E ratios, earnings)
- Economic indicators integration