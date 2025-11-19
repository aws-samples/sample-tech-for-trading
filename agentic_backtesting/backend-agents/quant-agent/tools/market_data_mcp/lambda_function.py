import json
import os
import boto3
import pyarrow as pa
import pyarrow.compute as pc
from datetime import datetime
from pyiceberg.catalog import load_catalog
from pyiceberg.expressions import And, EqualTo, GreaterThanOrEqual, LessThanOrEqual

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"Loaded environment variables from {env_path}")
except ImportError:
    print("python-dotenv not installed, using system environment variables only")

# S3 Tables Configuration from environment variables
S3_TABLES_CONFIG = {
    'bucket_name': os.environ.get('S3_TABLES_BUCKET', 'market-data-123'),
    'namespace': os.environ.get('S3_TABLES_NAMESPACE', 'daily_data'),
    'table_name': os.environ.get('S3_TABLES_TABLE', 'daily_data'),
    'region': os.environ.get('S3_TABLES_REGION', 'us-east-1')
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

def query_s3_tables_data(symbol=None, start_date=None, end_date=None, limit=10000):
    """Query data from S3 Tables using PyIceberg with filters"""
    try:
        catalog = setup_s3_tables_catalog()
        if not catalog:
            return None
        
        config = S3_TABLES_CONFIG
        table = catalog.load_table(f"{config['namespace']}.{config['table_name']}")
        
        # Build filter expressions for scan
        filters = []
        
        # Add symbol filter
        if symbol:
            filters.append(EqualTo("symbol", symbol.upper()))
        
        # Add date range filters
        if start_date:
            filters.append(GreaterThanOrEqual("date", start_date))
        
        if end_date:
            filters.append(LessThanOrEqual("date", end_date))
        
        # Scan data with filters
        if filters:
            if len(filters) == 1:
                scan = table.scan(row_filter=filters[0])
            else:
                scan = table.scan(row_filter=And(*filters))
        else:
            scan = table.scan()
        
        arrow_table = scan.to_arrow()
        
        # Sort by date
        if len(arrow_table) > 0:
            indices = pc.sort_indices(arrow_table, sort_keys=[('date', 'ascending')])
            arrow_table = pc.take(arrow_table, indices)
            
            # Apply limit if specified
            if limit and len(arrow_table) > limit:
                arrow_table = arrow_table.slice(len(arrow_table) - limit)
        
        return arrow_table
        
    except Exception as e:
        print(f"Failed to query S3 Tables: {e}")
        return None


def format_market_data_response(arrow_table, symbol):
    """Format PyArrow table into market data response compatible with gateway processing"""
    if arrow_table is None or len(arrow_table) == 0:
        return {
            "success": False,
            "error": f"No data found for symbol {symbol}",
            "data": [],
            "metadata": {
                "symbol": symbol.upper(),
                "total_rows": 0,
                "columns": [],
                "source": "s3_tables_pyiceberg_container",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
    
    # Get column names from arrow table
    column_names = arrow_table.column_names
    
    # Convert PyArrow table to list of dictionaries (one per row)
    raw_data = []
    for i in range(len(arrow_table)):
        row_dict = {}
        for col_name in column_names:
            value = arrow_table[col_name][i].as_py()
            
            # Convert date to string if needed
            if col_name == 'date':
                row_dict['date'] = str(value) if value else None
            elif col_name == 'symbol':
                row_dict['symbol'] = str(value).upper() if value else symbol.upper()
            elif col_name in ['open_price', 'high_price', 'low_price', 'close_price', 'adj_close']:
                row_dict[col_name] = float(value) if value is not None else 0.0
            elif col_name == 'volume':
                row_dict[col_name] = int(value) if value is not None else 0
            else:
                row_dict[col_name] = value
        
        raw_data.append(row_dict)
    
    # Build metadata
    metadata = {
        "symbol": symbol.upper(),
        "total_rows": len(raw_data),
        "columns": column_names,
        "source": "s3_tables_pyiceberg_container",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "s3_tables_bucket": S3_TABLES_CONFIG['bucket_name']
    }
    
    return {
        "success": True,
        "data": raw_data,
        "metadata": metadata
    }

def lambda_handler(event, context):
    """Lambda function handler"""
    try:
        # Extract parameters from event
        symbol = event.get('symbol', 'AMZN')
        start_date = event.get('start_date')
        end_date = event.get('end_date')
        limit = event.get('limit', 252)
        
        print(f"Querying S3 Tables for symbol: {symbol}, start_date: {start_date}, end_date: {end_date}")
        
        # Query S3 Tables data with filters
        arrow_table = query_s3_tables_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
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
