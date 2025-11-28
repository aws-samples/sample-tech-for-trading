#!/usr/bin/env python3
"""
Query S3 Tables data content
"""

import boto3
from pyiceberg.catalog import load_catalog

def query_s3_table(bucket_name, namespace, table_name):
    """Query data from S3 Tables"""
    try:
        # Setup AWS session
        session = boto3.Session(region_name='us-east-1')
        sts_client = session.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        region = session.region_name
        
        # Setup catalog
        catalog_config = {
            "type": "rest",
            "warehouse": f"arn:aws:s3tables:{region}:{account_id}:bucket/{bucket_name}",
            "uri": f"https://s3tables.{region}.amazonaws.com/iceberg",
            "rest.sigv4-enabled": "true",
            "rest.signing-name": "s3tables",
            "rest.signing-region": region
        }
        
        catalog = load_catalog("s3tables", **catalog_config)
        
        # Load table and scan data
        table = catalog.load_table(f"{namespace}.{table_name}")
        
        print(f"📊 Table: {namespace}.{table_name}")
        print(f"📋 Schema: {table.schema()}")
        print("\n📈 Data (first 10 rows):")
        
        # Scan and convert to pandas for display
        scan = table.scan()
        df = scan.to_pandas()
        
        print(df.head(10))
        print(f"\n📊 Total rows: {len(df)}")
        
    except Exception as e:
        print(f"❌ Failed to query table: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python3 query_s3_table.py <bucket_name> <namespace> <table_name>")
        print("Example: python3 query_s3_table.py market-data-1234567890 tick_data tick_data")
        sys.exit(1)
    
    bucket_name = sys.argv[1]
    namespace = sys.argv[2] 
    table_name = sys.argv[3]
    
    query_s3_table(bucket_name, namespace, table_name)
