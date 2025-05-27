#!/usr/bin/env python3
"""
Lambda function for processing SEC financial data from S3 and storing in ClickHouse.
This function is triggered when a new JSON file is uploaded to the S3 bucket.
"""

import os
import json
import boto3
import logging
from datetime import datetime
import clickhouse_driver
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Ensure set to INFO level



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

# Get ClickHouse client
def get_clickhouse_client():
    """Get a connection to the ClickHouse database."""
    try:
        CLICKHOUSE_SECRET_ARN = os.environ.get('CLICKHOUSE_SECRET_ARN', '')
        secret = get_secret(CLICKHOUSE_SECRET_ARN)
        client = clickhouse_driver.Client(
            host=os.environ.get('CLICKHOUSE_HOST', 'localhost'),
            port=int(os.environ.get('CLICKHOUSE_PORT', 9000)),
            user=os.environ.get('CLICKHOUSE_USER', 'default'),
            password=secret.get('password', ''),
            database=os.environ.get('CLICKHOUSE_DATABASE', 'default')
        )
        return client
    except Exception as e:
        logger.error(f"Error connecting to ClickHouse: {str(e)}")
        raise

def extract_financial_data(json_data, ticker, source_file):
    """
    Extract structured financial data from SEC JSON file.
    Only processes new data since last processing.
    Returns a list of dictionaries with financial data for each reporting period.
    """
    financial_data = []

    try:
        # Extract CIK from the JSON data
        cik = json_data.get('cik', '')
        # Convert to string if it's an integer
        if isinstance(cik, int):
            cik = str(cik)
        cik_padded = cik.zfill(10)  # Ensure CIK has leading zeros

        # Get facts data
        facts = json_data.get('facts', {})
        us_gaap = facts.get('us-gaap', {})

        # Define the financial metrics we want to extract
        metrics = {
            'AssetsCurrent': None,
            'LiabilitiesCurrent': None,
            'CashAndCashEquivalentsAtCarryingValue': None,
            'InventoryNet': None,
            'StockholdersEquity': None,
            'SalesRevenueNet': None,
            'CostOfGoodsAndServicesSold': None,
            'InterestExpense': None,
            'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments': None
        }

        # Extract data for each metric
        for metric_name in metrics:
            metric_data = us_gaap.get(metric_name, {})
            units = metric_data.get('units', {})

            # Most financial data is in USD
            usd_data = units.get('USD', [])
            if not usd_data:
                logger.warning(f"No USD data found for {metric_name} in {ticker}")
                continue

            # Process each reporting period
            for idx, item in enumerate(usd_data):

                logger.info(f"Processing new data for {ticker}.{metric_name} at index {idx}")

                end_date = item.get('end', '')
                # Convert end_date string to datetime object if it's a string
                if end_date and isinstance(end_date, str):
                    try:
                        end_date = datetime.strptime(end_date, '%Y-%m-%d')
                    except ValueError as e:
                        logger.warning(f"Invalid date format for end_date: {end_date}. Error: {e}")
                        # If conversion fails, keep as string but ensure it's in the right format
                        if '-' not in end_date:
                            continue  # Skip this record if date format is invalid

                value = item.get('val', 0)
                filed_date = item.get('filed', '')
                # Convert filed_date string to datetime object if it's a string
                if filed_date and isinstance(filed_date, str):
                    try:
                        filed_date = datetime.strptime(filed_date, '%Y-%m-%d')
                    except ValueError as e:
                        logger.warning(f"Invalid date format for filed_date: {filed_date}. Error: {e}")
                        # If conversion fails, keep as string but ensure it's in the right format
                        if '-' not in filed_date:
                            continue  # Skip this record if date format is invalid

                form = item.get('form', '')
                # Only process 10-K (annual) and 10-Q (quarterly) reports
                if form not in ['10-K', '10-Q', '10-K/A']:
                    continue

                # Find or create a record for this reporting period
                # period_key = (end_date, filed_date, form)
                accession_number = item.get('accn', '')
                # Get fiscal year
                fiscal_year = item.get('fy', 0)

                # Get fiscal quarter
                fiscal_quarter = item.get('fp', '')

                # Find existing record or create new one
                record = None
                for rec in financial_data:
                    if rec['end_date'] == end_date:
                        record = rec
                        break

                if record is None:
                    record = {
                        'ticker': ticker,
                        'cik': cik_padded,
                        'accession_number': accession_number,
                        'end_date': end_date,
                        'filed_date': filed_date,
                        'form': form,
                        'fiscal_year': fiscal_year,
                        'fiscal_quarter': fiscal_quarter,
                        'assets_current': None,
                        'liabilities_current': None,
                        'cash_and_equivalents': None,
                        'inventory_net': None,
                        'inventory_net_prev_year': None,
                        'stockholders_equity': None,
                        'sales_revenue_net': None,
                        'sales_revenue_net_prev_year': None,
                        'cost_of_goods_sold': None,
                        'interest_expense': None,
                        'income_before_taxes': None,
                        'source_file': source_file,
                        'processed_timestamp': datetime.now()
                    }
                    logger.info(f"Created new record with fiscal_year: {fiscal_year}, type: {type(fiscal_year)}")
                    financial_data.append(record)

                # Update the record with the metric value
                if metric_name == 'AssetsCurrent':
                    record['assets_current'] = value
                elif metric_name == 'LiabilitiesCurrent':
                    record['liabilities_current'] = value
                elif metric_name == 'CashAndCashEquivalentsAtCarryingValue':
                    record['cash_and_equivalents'] = value
                elif metric_name == 'InventoryNet':
                    record['inventory_net'] = value
                    # Store previous year's inventory for turnover calculation
                    # This is a simplification; in a real system, you'd need to find the actual previous year's value
                    record['inventory_net_prev_year'] = value
                elif metric_name == 'StockholdersEquity':
                    record['stockholders_equity'] = value
                elif metric_name == 'SalesRevenueNet':
                    record['sales_revenue_net'] = value
                    # Store previous year's revenue for growth calculation
                    # This is a simplification; in a real system, you'd need to find the actual previous year's value
                    record['sales_revenue_net_prev_year'] = value
                elif metric_name == 'CostOfGoodsAndServicesSold':
                    record['cost_of_goods_sold'] = value
                elif metric_name == 'InterestExpense':
                    record['interest_expense'] = value
                elif metric_name == 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments':
                    record['income_before_taxes'] = value

        return financial_data

    except Exception as e:
        logger.error(f"Error extracting financial data for {ticker}: {str(e)}")
        return []


def calculate_factors(financial_data):
    """
    Calculate financial factors based on the extracted financial data.
    Returns a list of dictionaries with calculated factors for each reporting period.
    """
    factors = []
    logger.info(f"Starting factor calculation for {len(financial_data)} records")

    for i, record in enumerate(financial_data):
        try:
            # Basic identifiers
            factor = {
                'ticker': record['ticker'],
                'cik': record['cik'],
                'end_date': record['end_date'],
                'accession_number': record['accession_number'],
                'filed_date': record['filed_date'],
                'form': record['form'],
                'fiscal_year': record['fiscal_year'],
                'fiscal_quarter': record['fiscal_quarter'],
                'current_ratio': None,
                'cash_ratio': None,
                'inventory_turnover': None,
                'gross_profit_margin': None,
                'debt_to_equity': None,
                'interest_coverage': None,
                'revenue_growth': None,
                'equity_per_share': None,
                'book_value_per_share': None,
                'board_age_avg': None,
                'exec_comp_revenue_ratio': None,
                'esg_env_rating': None
            }

            factors.append(factor)

        except Exception as e:
            logger.error(f"Error calculating factors for {record['ticker']} on {record['end_date']}: {str(e)}")
            continue

    return factors


def store_in_clickhouse(client, financial_data):
    """Store extracted financial data and calculated factors in ClickHouse."""
    try:
        # Store financial data in stock_fundamental_factors_source table
        if financial_data:
            source_data = []
            for i, record in enumerate(financial_data):
                # Convert None values to appropriate defaults
                row = (
                    record['ticker'],
                    record['cik'],
                    record['accession_number'],
                    record['end_date'],
                    record['filed_date'],
                    record['form'],
                    record['fiscal_year'],
                    record['fiscal_quarter'],
                    record['assets_current'] or 0,
                    record['liabilities_current'] or 0,
                    record['cash_and_equivalents'] or 0,
                    record['inventory_net'] or 0,
                    record['inventory_net_prev_year'] or 0,
                    record['stockholders_equity'] or 0,
                    record['sales_revenue_net'] or 0,
                    record['sales_revenue_net_prev_year'] or 0,
                    record['cost_of_goods_sold'] or 0,
                    record['interest_expense'] or 0,
                    record['income_before_taxes'] or 0,
                    record['source_file'],
                    record['processed_timestamp'],
                    datetime.now()
                )
                source_data.append(row)
                logger.info(f"Added row with fiscal_year: {record['fiscal_year']}, type: {type(record['fiscal_year'])}")

            # Insert data into stock_fundamental_factors_source table
            for i, record in enumerate(source_data):
                logger.info(f"Record {i} fiscal_year: {record[6]}, type: {type(record[6])}")
            
            client.execute(
                """
                INSERT INTO stock_fundamental_factors_source (
                    ticker, cik, accession_number, end_date, filed_date, form, fiscal_year, fiscal_quarter,
                    assets_current, liabilities_current, cash_and_equivalents, inventory_net,
                    inventory_net_prev_year, stockholders_equity, sales_revenue_net,
                    sales_revenue_net_prev_year, cost_of_goods_sold, interest_expense,
                    income_before_taxes, source_file, processed_timestamp, create_datetime
                ) VALUES
                """,
                source_data
            )
            logger.info(f"Inserted {len(source_data)} records into stock_fundamental_factors_source table")

    except Exception as e:
        logger.error(f"Error storing data in ClickHouse: {str(e)}")
        raise


def lambda_handler(event, context):
    """
    Lambda function handler.
    This function is triggered when a new JSON file is uploaded to the S3 bucket.
    """
    try:
        logger.info(f"Processing S3 event: {json.dumps(event)}")

        # Get the S3 bucket and key from the event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']

        logger.info(f"Processing file: s3://{bucket}/{key}")

        # Extract ticker from the filename
        ticker = key.split('/')[0]
        logger.info(f"Processing data for ticker: {ticker}")

        # Initialize S3 client
        s3_client = boto3.client('s3')

        # Download the JSON file from S3
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            json_data = json.loads(response['Body'].read().decode('utf-8'))
            logger.info(f"Successfully downloaded file: s3://{bucket}/{key}")
        except Exception as e:
            logger.error(f"Error downloading file from S3: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps(f"Error: {str(e)}")
            }


        # Extract structured financial data (only new data)
        financial_data = extract_financial_data(json_data, ticker, f"s3://{bucket}/{key}")
        logger.info(f"Extracted {len(financial_data)} financial records for {ticker}")

        if financial_data:
            try:
                clickhouse_client = get_clickhouse_client()
                store_in_clickhouse(clickhouse_client, financial_data)
                logger.info(f"Successfully stored data in ClickHouse for {ticker}")
            except Exception as e:
                logger.error(f"Error storing data in ClickHouse: {str(e)}")
                return {
                    'statusCode': 500,
                    'body': json.dumps(f"Error: {str(e)}")
                }
        else:
            logger.info(f"No new data to process for {ticker}")

        return {
            'statusCode': 200,
            'body': json.dumps('Processing completed successfully')
        }

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }
