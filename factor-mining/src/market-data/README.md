# Market Data Collector

This module collects market data from Yahoo Finance and stores it in a ClickHouse database for further analysis in the factor modeling platform.

## Features

- Downloads historical stock data from Yahoo Finance
- Configurable via environment variables or event parameters
- Supports batch processing of multiple tickers
- Efficiently handles data deduplication
- Processes data in memory-efficient chunks
- Comprehensive error handling and logging

## Usage

### As AWS Lambda Function

The `market_data_collector.py` file is designed to be deployed as an AWS Lambda function. It can be triggered by:

1. EventBridge scheduled events
2. Manual invocation
3. Step Functions workflows

### Configuration

The function can be configured using environment variables or event parameters:

| Parameter | Environment Variable | Event Parameter | Description |
|-----------|---------------------|-----------------|-------------|
| ClickHouse Host | CLICKHOUSE_HOST | clickhouse_host | Hostname of the ClickHouse server |
| Secret Name | SECRET_NAME | secret_name | AWS Secrets Manager secret containing ClickHouse credentials |
| Database | DATABASE | - | ClickHouse database name (default: factor_model_tick_data_database) |
| Tickers | TICKERS | tickers | Comma-separated list of tickers or array in event |
| Start Date | - | start_date | Start date for data collection (default: first day of current month) |
| End Date | - | end_date | End date for data collection (default: current date) |

### Example Event

```json
{
  "tickers": ["AAPL", "MSFT", "AMZN"],
  "start_date": "2025-01-01",
  "end_date": "2025-04-30",
  "clickhouse_host": "clickhouse.example.com"
}
```

## Database Schema

The data is stored in a ClickHouse table with the following schema:

```sql
CREATE TABLE IF NOT EXISTS factor_model_tick_data_database.tick_data
(
    symbol String,
    timestamp DateTime,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64,
    adjusted_close Float64
)
ENGINE = MergeTree()
ORDER BY (symbol, timestamp)
```

## Dependencies

- yfinance: For downloading stock data
- clickhouse_driver: For connecting to ClickHouse
- pandas: For data manipulation
- boto3: For AWS services integration

## Deployment

This module should be deployed as part of the market-data component in the factor modeling platform. See the main README for deployment instructions.

### Lambda Layer

This module uses the pre-built Lambda layer `yf-clickhouse-Lambda-layer-20May.zip` which contains all the required dependencies:
- numpy
- pandas==2.2.3
- clickhouse_driver==0.2.9
- yfinance==0.2.55
- boto3

The layer is included in this directory.

### Python Runtime

This module is designed to run with Python 3.12.
