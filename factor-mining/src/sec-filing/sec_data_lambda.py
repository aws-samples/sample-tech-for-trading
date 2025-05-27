import json
import boto3
import urllib.request
import urllib.error
import os
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configure S3 client
s3_client = boto3.client('s3')


def lambda_handler(event, context):
    """
    Retrieve company financial data from SEC API and upload to S3 bucket

    Parameters:
        event (dict): Lambda event (not used for configuration)
        context: Lambda context

    Returns:
        dict: Processing results
    """
    try:
        # Get configuration from environment variables
        tickers = os.environ.get('DJIA_TICKERS', '').split(',')
        cik_mapping = json.loads(os.environ.get('CIK_MAPPING', ''))
        email = os.environ.get('EMAIL', 'youremail@email.com')
        bucket_name = os.environ.get('BUCKET_NAME', 'djia-tickers')

        # Get current date for filename prefix
        current_date = datetime.now().strftime('%Y%m%d')
        file_name = f"{current_date}_companyfacts.json"

        results = {
            'successful': [],
            'failed': []
        }

        # Process each ticker
        for ticker in tickers:
            try:
                # Get CIK number from the mapping
                cik = cik_mapping.get(ticker)

                if not cik:
                    logger.warning(f"CIK number for {ticker} not found in mapping, skipping")
                    results['failed'].append({
                        'ticker': ticker,
                        'reason': 'CIK number not found'
                    })
                    continue

                # Ensure CIK is 10 digits, pad with leading zeros
                cik = cik.zfill(10)

                # Build SEC API URL
                url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

                # Set request headers (SEC API requires User-Agent)
                headers = {
                    'User-Agent': f'Company Financial Data Collector ({email})'
                }

                # Send request to get data
                logger.info(f"Retrieving data for {ticker} (CIK: {cik})")

                # Create a request with headers
                req = urllib.request.Request(url, headers=headers)

                # Send the request and get the response
                with urllib.request.urlopen(req) as response:
                    # Read and decode the response data
                    data = response.read().decode('utf-8')
                    company_data = json.loads(data)

                # Build S3 object key (path)
                s3_key = f"{ticker}/{file_name}"

                # Upload to S3
                logger.info(f"Uploading {ticker} data to S3: {bucket_name}/{s3_key}")
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=json.dumps(company_data),
                    ContentType='application/json'
                )

                results['successful'].append({
                    'ticker': ticker,
                    'cik': cik,
                    's3_location': f"s3://{bucket_name}/{s3_key}"
                })
            except Exception as e:
                logger.error(f"Error processing {ticker}: {str(e)}")
                results['failed'].append({
                    'ticker': ticker,
                    'reason': str(e)
                })

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f"Processed {len(tickers)} tickers, successful: {len(results['successful'])}, failed: {len(results['failed'])}",
                'results': results
            })
        }

    except Exception as e:
        logger.error(f"Lambda execution error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f"Execution error: {str(e)}"
            })
        }