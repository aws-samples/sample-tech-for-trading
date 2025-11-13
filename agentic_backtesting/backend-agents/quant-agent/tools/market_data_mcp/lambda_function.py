import json
import boto3
import pyarrow as pa
import pyarrow.compute as pc
from datetime import datetime
from pyiceberg.catalog import load_catalog

# S3 Tables Configuration
S3_TABLES_CONFIG = {
    'bucket_name': 'market-data-1762323186',
    'namespace': 'tick_data',
    'table_name': 'tick_data',
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

def calculate_moving_average(prices, window):
    """Calculate simple moving average"""
    if len(prices) < window:
        return [None] * len(prices)
    
    result = []
    for i in range(len(prices)):
        if i < window - 1:
            result.append(None)
        else:
            window_values = prices[i - window + 1:i + 1]
            avg = sum(v for v in window_values if v is not None) / len([v for v in window_values if v is not None])
            result.append(round(avg, 2))
    
    return result

def format_market_data_response(arrow_table, symbol):
    """Format PyArrow table into market data response"""
    if arrow_table is None or len(arrow_table) == 0:
        return {
            "success": False,
            "error": f"No data found for symbol {symbol}",
            "data": None
        }
    
    # Convert PyArrow columns to Python lists
    dates = [str(date) for date in arrow_table['date'].to_pylist()]
    prices = [float(p) if p is not None else 0.0 for p in arrow_table['close_price'].to_pylist()]
    volumes = [int(v) if v is not None else 0 for v in arrow_table['volume'].to_pylist()]
    
    # Calculate statistics
    valid_prices = [p for p in prices if p > 0]
    initial_price = valid_prices[0] if valid_prices else 0
    final_price = valid_prices[-1] if valid_prices else 0
    min_price = min(valid_prices) if valid_prices else 0
    max_price = max(valid_prices) if valid_prices else 0
    
    total_return_pct = ((final_price - initial_price) / initial_price * 100) if initial_price > 0 else 0
    avg_daily_volume = sum(volumes) // len(volumes) if volumes else 0
    
    # Calculate technical indicators
    sma_20_values = calculate_moving_average(prices, 20)
    sma_50_values = calculate_moving_average(prices, 50)
    current_sma_20 = sma_20_values[-1] if sma_20_values and sma_20_values[-1] is not None else None
    current_sma_50 = sma_50_values[-1] if sma_50_values and sma_50_values[-1] is not None else None
    
    return {
        "success": True,
        "data": {
            "symbol": symbol.upper(),
            "data_points": len(arrow_table),
            "period_start": dates[0] if dates else None,
            "period_end": dates[-1] if dates else None,
            "price_data": {
                "dates": dates,
                "prices": prices,
                "volumes": volumes,
                "initial_price": initial_price,
                "final_price": final_price,
                "min_price": min_price,
                "max_price": max_price
            },
            "technical_indicators": {
                "sma_20": sma_20_values,
                "sma_50": sma_50_values,
                "current_sma_20": current_sma_20,
                "current_sma_50": current_sma_50
            },
            "statistics": {
                "total_return_pct": round(total_return_pct, 2),
                "avg_daily_volume": avg_daily_volume
            },
            "metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "data_source": "s3_tables_pyiceberg_container",
                "s3_tables_bucket": S3_TABLES_CONFIG['bucket_name']
            }
        }
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
