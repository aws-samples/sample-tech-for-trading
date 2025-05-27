import yfinance as yf
import clickhouse_driver
import pandas as pd
from datetime import datetime
import boto3
import json
import os
import logging
import traceback
import time

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DOW30 stocks as of April 2025
DOW30_TICKERS = [
    'AAPL', 'AMGN', 'AMZN', 'AXP', 'BA', 'CAT', 'CRM', 'CSCO', 'CVX', 'DIS', 
    'GS', 'HD', 'HON', 'IBM', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM', 'MRK', 
    'MSFT', 'NKE', 'NVDA', 'PG', 'SHW', 'TRV', 'UNH', 'V', 'VZ', 'WMT'
]

def get_secret(secret_name):
    """Retrieve secret from AWS Secrets Manager without profile"""
    client = boto3.client(
        service_name='secretsmanager'
    )
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        logger.error(f"Secret retrieval error: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def lambda_handler(event, context):
    """Main Lambda entry point"""
    # Get configuration from environment variables or event
    start_date = event.get('start_date', "2025-04-21")
    end_date = event.get('end_date', "2025-04-30")
    
    # Get ClickHouse connection parameters
    try:
        host = os.environ.get('CLICKHOUSE_HOST') or event.get('clickhouse_host')
        secret_name = os.environ.get('CLICKHOUSE_SECRET_ARN') or event.get('secret_name')
        database = os.environ.get('DATABASE', 'factor_model_tick_data_database')
        
        if not host:
            raise ValueError("CLICKHOUSE_HOST environment variable or clickhouse_host event parameter is required")
        if not secret_name:
            raise ValueError("SECRET_NAME environment variable or secret_name event parameter is required")
            
    except Exception as e:
        logger.error(f"Configuration error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"status": "failed", "error": str(e)})
        }
    
    # Get tickers to process - either from event or use default DOW30
    tickers_to_process = event.get('tickers', DOW30_TICKERS)
    
    # Track results for all tickers
    results = {
        "successful": [],
        "failed": [],
        "skipped": []
    }
    
    # Process each ticker in a loop
    for ticker in tickers_to_process:
        try:
            logger.info(f"Processing {ticker} from {start_date} to {end_date}")
            time.sleep(5)
            
            # Download data from Yahoo Finance
            data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False)
            print(f'data is {data}!!!!!')
            if data.empty:
                logger.warning(f"No data found for {ticker}")
                results["skipped"].append({
                    "ticker": ticker,
                    "reason": "no_data"
                })
                continue
            
            # Use Lambda's ephemeral storage
            temp_csv = f"/tmp/{ticker}_temp.csv"
            data.reset_index().to_csv(temp_csv, index=False)
            
            # Process CSV file
            ticker_result = process_csv_to_clickhouse(
                ticker=ticker,
                csv_path=temp_csv,
                host=host,
                secret_name=secret_name,
                database=database
            )
            
            # Cleanup
            if os.path.exists(temp_csv):
                os.remove(temp_csv)
                
            # Track successful result
            results["successful"].append({
                "ticker": ticker,
                "rows_inserted": ticker_result["rows_inserted"],
                "total_rows": ticker_result["total_rows"]
            })
            
        except Exception as e:
            logger.error(f"Error processing {ticker}: {str(e)}")
            logger.error(traceback.format_exc())
            results["failed"].append({
                "ticker": ticker,
                "error": str(e)
            })
            # Continue with next ticker even if one fails
            continue
    
    # Return summary of all processing
    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "completed",
            "summary": {
                "total_tickers": len(tickers_to_process),
                "successful": len(results["successful"]),
                "failed": len(results["failed"]),
                "skipped": len(results["skipped"])
            },
            "results": results
        })
    }

def process_csv_to_clickhouse(ticker, csv_path, host, secret_name, database):
    """Process CSV and insert into ClickHouse"""
    rows_inserted = 0
    
    try:
        # Get credentials
        secret = get_secret(secret_name)
        client = clickhouse_driver.Client(
            host=host,
            port=9000,
            user=secret.get('username', 'default'),
            password=secret.get('password', '')
        )
        
        # Initialize database
        client.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
        client.execute(f'''
            CREATE TABLE IF NOT EXISTS {database}.tick_data
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
        ''')
        
        # Get existing timestamps
        existing_timestamps = {ts[0] for ts in client.execute(
            f"SELECT timestamp FROM {database}.tick_data WHERE symbol = %(symbol)s",
            {'symbol': ticker}
        )}
        
        # Process CSV in chunks to manage memory
        new_rows = []
        total_rows = 0
        
        for chunk in pd.read_csv(csv_path, chunksize=1000):
            total_rows += len(chunk)
            
            for _, row in chunk.iterrows():
                try:
                    date_obj = datetime.strptime(row['Date'], '%Y-%m-%d')
                    if date_obj in existing_timestamps:
                        continue
                        
                    new_rows.append((
                        ticker,
                        date_obj,
                        float(row['Open']),
                        float(row['High']),
                        float(row['Low']),
                        float(row['Close']),
                        int(row['Volume']),
                        float(row['Adj Close'])
                    ))
                    
                    # Insert in batches to manage memory
                    if len(new_rows) >= 5000:
                        client.execute(
                            f'INSERT INTO {database}.tick_data VALUES',
                            new_rows,
                            types_check=True
                        )
                        rows_inserted += len(new_rows)
                        logger.info(f"Inserted batch of {len(new_rows)} rows for {ticker}")
                        new_rows = []
                        
                except Exception as e:
                    logger.warning(f"Skipping invalid row: {str(e)}")
        
        # Insert any remaining rows
        if new_rows:
            client.execute(
                f'INSERT INTO {database}.tick_data VALUES',
                new_rows,
                types_check=True
            )
            rows_inserted += len(new_rows)
            logger.info(f"Inserted final batch of {len(new_rows)} rows for {ticker}")
        
        # Get final count
        total_count = client.execute(f"SELECT COUNT(*) FROM {database}.tick_data WHERE symbol = '{ticker}'")[0][0]
        logger.info(f"Total of {rows_inserted} new rows inserted for {ticker}. Total in database: {total_count}")
        
        return {
            "rows_inserted": rows_inserted,
            "total_rows": total_count
        }
        
    except Exception as e:
        logger.error(f"ClickHouse processing error: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def get_secret(secret_name):
    """Retrieve secret from AWS Secrets Manager"""
    client = boto3.client(
        service_name='secretsmanager'
    )
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        logger.error(f"Secret retrieval error: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def lambda_handler(event, context):
    """Main Lambda entry point"""
    # Get configuration from environment variables or event
    start_date = event.get('start_date', (datetime.now().replace(day=1)).strftime('%Y-%m-%d'))
    end_date = event.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    # Get ClickHouse connection parameters
    try:
        host = os.environ.get('CLICKHOUSE_HOST') or event.get('clickhouse_host')
        secret_name = os.environ.get('CLICKHOUSE_SECRET_ARN') or event.get('secret_name')
        database = os.environ.get('DATABASE', 'factor_model_tick_data_database')
        
        if not host:
            raise ValueError("CLICKHOUSE_HOST environment variable or clickhouse_host event parameter is required")
        if not secret_name:
            raise ValueError("SECRET_NAME environment variable or secret_name event parameter is required")
            
    except Exception as e:
        logger.error(f"Configuration error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"status": "failed", "error": str(e)})
        }
    
    # Get tickers to process - from environment, event or use default DOW30
    tickers_str = os.environ.get('TICKERS', '')
    tickers_to_process = tickers_str.split(',') if tickers_str else event.get('tickers', DOW30_TICKERS)
    
    # Track results for all tickers
    results = {
        "successful": [],
        "failed": [],
        "skipped": []
    }
    
    # Process each ticker in a loop
    for ticker in tickers_to_process:
        try:
            logger.info(f"Processing {ticker} from {start_date} to {end_date}")
            
            # Download data from Yahoo Finance
            data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False)
            
            if data.empty:
                logger.warning(f"No data found for {ticker}")
                results["skipped"].append({
                    "ticker": ticker,
                    "reason": "no_data"
                })
                continue
            
            # Use Lambda's ephemeral storage
            temp_csv = f"/tmp/{ticker}_temp.csv"
            data.reset_index().to_csv(temp_csv, index=False)
            
            # Process CSV file
            ticker_result = process_csv_to_clickhouse(
                ticker=ticker,
                csv_path=temp_csv,
                host=host,
                secret_name=secret_name,
                database=database
            )
            
            # Cleanup
            if os.path.exists(temp_csv):
                os.remove(temp_csv)
                
            # Track successful result
            results["successful"].append({
                "ticker": ticker,
                "rows_inserted": ticker_result["rows_inserted"],
                "total_rows": ticker_result["total_rows"]
            })
            
        except Exception as e:
            logger.error(f"Error processing {ticker}: {str(e)}")
            logger.error(traceback.format_exc())
            results["failed"].append({
                "ticker": ticker,
                "error": str(e)
            })
            # Continue with next ticker even if one fails
            continue
    
    # Return summary of all processing
    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "completed",
            "summary": {
                "total_tickers": len(tickers_to_process),
                "successful": len(results["successful"]),
                "failed": len(results["failed"]),
                "skipped": len(results["skipped"])
            },
            "results": results
        })
    }

def process_csv_to_clickhouse(ticker, csv_path, host, secret_name, database):
    """Process CSV and insert into ClickHouse"""
    rows_inserted = 0
    
    try:
        # Get credentials
        secret = get_secret(secret_name)
        client = clickhouse_driver.Client(
            host=host,
            port=9000,
            user=secret.get('username', 'default'),
            password=secret.get('password', '')
        )
        
        # Initialize database
        client.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
        client.execute(f'''
            CREATE TABLE IF NOT EXISTS {database}.tick_data
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
        ''')
        
        # Get existing timestamps
        existing_timestamps = {ts[0] for ts in client.execute(
            f"SELECT timestamp FROM {database}.tick_data WHERE symbol = %(symbol)s",
            {'symbol': ticker}
        )}
        
        # Process CSV in chunks to manage memory
        new_rows = []
        total_rows = 0
        
        for chunk in pd.read_csv(csv_path, chunksize=1000):
            total_rows += len(chunk)
            
            for _, row in chunk.iterrows():
                try:
                    date_obj = datetime.strptime(row['Date'], '%Y-%m-%d')
                    if date_obj in existing_timestamps:
                        continue
                        
                    new_rows.append((
                        ticker,
                        date_obj,
                        float(row['Open']),
                        float(row['High']),
                        float(row['Low']),
                        float(row['Close']),
                        int(row['Volume']),
                        float(row['Adj Close'])
                    ))
                    
                    # Insert in batches to manage memory
                    if len(new_rows) >= 5000:
                        client.execute(
                            f'INSERT INTO {database}.tick_data VALUES',
                            new_rows,
                            types_check=True
                        )
                        rows_inserted += len(new_rows)
                        logger.info(f"Inserted batch of {len(new_rows)} rows for {ticker}")
                        new_rows = []
                        
                except Exception as e:
                    logger.warning(f"Skipping invalid row: {str(e)}")
        
        # Insert any remaining rows
        if new_rows:
            client.execute(
                f'INSERT INTO {database}.tick_data VALUES',
                new_rows,
                types_check=True
            )
            rows_inserted += len(new_rows)
            logger.info(f"Inserted final batch of {len(new_rows)} rows for {ticker}")
        
        # Get final count
        total_count = client.execute(f"SELECT COUNT(*) FROM {database}.tick_data WHERE symbol = '{ticker}'")[0][0]
        logger.info(f"Total of {rows_inserted} new rows inserted for {ticker}. Total in database: {total_count}")
        
        return {
            "rows_inserted": rows_inserted,
            "total_rows": total_count
        }
        
    except Exception as e:
        logger.error(f"ClickHouse processing error: {str(e)}")
        logger.error(traceback.format_exc())
        raise
