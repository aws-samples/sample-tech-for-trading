import json
import os
import boto3
import pyarrow as pa
import pyarrow.compute as pc
from datetime import datetime
from pyiceberg.catalog import load_catalog

# S3 Tables Configuration from environment variables
S3_TABLES_CONFIG = {
    'bucket_name': os.environ.get('S3_TABLES_BUCKET', 'market-data-1762323186'),
    'namespace': os.environ.get('S3_TABLES_NAMESPACE', 'daily_data'),
    'table_name': os.environ.get('S3_TABLES_TABLE', 'daily_data'),
    'region': 'us-east-1'
}

def setup_s3_tables_catalog():
    """Setup PyIceberg catalog for S3 Tables"""
    try:
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        
        config = S3_TABLES_CONFIG
        catalog_config = {
            "type": "rest",
            "warehouse": f"arn:aws:s3tables:{config['region']}:{account_id}:bucket/{config['bucket_name']}",
            "uri": f"https://s3tables.{config['region']}.amazonaws.com/iceberg",
            "rest.sigv4-enabled": "true",
            "rest.signing-name": "s3tables",
            "rest.signing-region": config['region']
        }
        
        catalog = load_catalog("s3tables", **catalog_config)
        return catalog
        
    except Exception as e:
        print(f"Failed to setup S3 Tables catalog: {e}")
        return None

def query_s3_tables_data(symbol=None, limit=252):
    """Query data from S3 Tables using PyIceberg"""
    try:
        catalog = setup_s3_tables_catalog()
        if not catalog:
            return None
        
        config = S3_TABLES_CONFIG
        table = catalog.load_table(f"{config['namespace']}.{config['table_name']}")
        
        # Scan data to PyArrow table
        scan = table.scan()
        arrow_table = scan.to_arrow()
        
        # Filter by symbol if provided
        if symbol:
            symbol_filter = pc.equal(arrow_table['symbol'], symbol.upper())
            arrow_table = arrow_table.filter(symbol_filter)
        
        # Sort by date and limit results
        indices = pc.sort_indices(arrow_table, sort_keys=[('date', 'ascending')])
        arrow_table = pc.take(arrow_table, indices)
        
        if len(arrow_table) > limit:
            arrow_table = arrow_table.slice(len(arrow_table) - limit)
        
        return arrow_table
        
    except Exception as e:
        print(f"Failed to query S3 Tables: {e}")
        return None


def format_market_data_response(arrow_table, symbol):
    """Format PyArrow table into market data response"""
    if arrow_table is None or len(arrow_table) == 0:
        return {
            "success": False,
            "error": f"No data found for symbol {symbol}",
            "data": None
        }

    # Convert arrow table to Python dictionaries without pandas
    data_dict = arrow_table.to_pydict()
    
    # Convert date column to string for JSON serialization
    if 'date' in data_dict:
        data_dict['date'] = [str(d) for d in data_dict['date']]
    
    # Convert to list of records format
    num_rows = len(next(iter(data_dict.values())))
    records = []
    for i in range(num_rows):
        record = {col: data_dict[col][i] for col in data_dict.keys()}
        records.append(record)
    
    return {
        "success": True,
        "metadata": {
            "symbol": symbol.upper(),
            "total_rows": num_rows,
            "columns": list(data_dict.keys())
        },
        "data": records
    }
    

def lambda_handler(event, context):
    """Lambda function handler"""
    try:
        symbol = event.get('symbol', 'AMZN')
        print(f"Querying S3 Tables for symbol: {symbol}")
        
        # Query S3 Tables data
        arrow_table = query_s3_tables_data(symbol=symbol, limit=252)
        
        # Format response
        response = format_market_data_response(arrow_table, symbol)
        
        return {
            'statusCode': 200,
            'body': json.dumps(response),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                "success": False,
                "error": str(e),
                "data": None
            }),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
