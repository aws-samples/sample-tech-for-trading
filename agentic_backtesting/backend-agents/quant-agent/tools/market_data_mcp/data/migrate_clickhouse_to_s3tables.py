#!/usr/bin/env python3
"""
Complete ClickHouse to S3 Tables Migration
Creates S3 Tables infrastructure and migrates data in one script
"""

import os
import sys
import boto3
import pandas as pd
import requests
import json
from pyiceberg.catalog import load_catalog
import pyarrow as pa
from datetime import datetime

# ClickHouse Configuration
CLICKHOUSE_CONFIG = {
    'host': '44.222.122.134',
    'port': '8123',
    'user': 'default',
    'password': 'clickhouse@aws',
    'database': 'factor_model_tick_data_database'
}

def setup_aws_session():
    """Setup AWS session with 'factor' profile"""
    try:
        session = boto3.Session(profile_name='factor', region_name='us-east-1')
        return session
    except Exception as e:
        print(f"❌ Failed to setup AWS session: {e}")
        sys.exit(1)

def create_s3_tables_infrastructure(session: boto3.Session) -> tuple:
    """Create S3 Tables bucket, namespace, and table"""
    try:
        s3tables_client = session.client('s3tables')
        
        # Configuration
        bucket_name = f"market-data-{int(datetime.now().timestamp())}"
        namespace = "tick_data"
        table_name = "tick_data"
        
        print("🚀 Creating S3 Tables Infrastructure")
        print("=" * 40)
        print(f"📦 Bucket: {bucket_name}")
        print(f"📂 Namespace: {namespace}")
        print(f"📊 Table: {table_name}")
        
        # Create table bucket
        print("\n📦 Creating table bucket...")
        bucket_response = s3tables_client.create_table_bucket(name=bucket_name)
        bucket_arn = bucket_response['arn']
        print(f"✅ Created bucket: {bucket_name}")
        
        # Create namespace
        print("📂 Creating namespace...")
        s3tables_client.create_namespace(
            tableBucketARN=bucket_arn,
            namespace=[namespace]  # namespace should be a list
        )
        print(f"✅ Created namespace: {namespace}")
        
        # Note: Table will be created by PyIceberg during data migration
        print("📊 Table will be created during data migration")
        
        return bucket_name, namespace, table_name
        
    except Exception as e:
        print(f"❌ Failed to create S3 Tables infrastructure: {e}")
        return None, None, None

def query_clickhouse(query: str) -> pd.DataFrame:
    """Execute query against ClickHouse and return DataFrame"""
    url = f"http://{CLICKHOUSE_CONFIG['host']}:{CLICKHOUSE_CONFIG['port']}"
    formatted_query = f"{query} FORMAT JSONEachRow"
    
    params = {
        'user': CLICKHOUSE_CONFIG['user'],
        'password': CLICKHOUSE_CONFIG['password'],
        'database': CLICKHOUSE_CONFIG['database'],
        'query': formatted_query
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        lines = response.text.strip().split('\n')
        if not lines or lines == ['']:
            return pd.DataFrame()
        
        data = [json.loads(line) for line in lines if line.strip()]
        df = pd.DataFrame(data)
        print(f"✅ Retrieved {len(df)} rows from ClickHouse")
        return df
        
    except Exception as e:
        print(f"❌ ClickHouse query failed: {e}")
        return pd.DataFrame()

def setup_s3_tables_catalog(session: boto3.Session, bucket_name: str) -> object:
    """Setup PyIceberg catalog for S3 Tables"""
    try:
        sts_client = session.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        region = session.region_name
        
        catalog_config = {
            "type": "rest",
            "warehouse": f"arn:aws:s3tables:{region}:{account_id}:bucket/{bucket_name}",
            "uri": f"https://s3tables.{region}.amazonaws.com/iceberg",
            "rest.sigv4-enabled": "true",
            "rest.signing-name": "s3tables",
            "rest.signing-region": region
        }
        
        catalog = load_catalog("s3tables", **catalog_config)
        print(f"✅ Connected to S3 Tables catalog: {bucket_name}")
        return catalog
        
    except Exception as e:
        print(f"❌ Failed to setup S3 Tables catalog: {e}")
        return None

def migrate_data_to_s3_tables(df: pd.DataFrame, catalog: object, namespace: str, table_name: str) -> bool:
    """Migrate DataFrame to S3 Tables using PyIceberg"""
    if df.empty:
        print("⚠️  No data to migrate")
        return False
    
    try:
        # Map ClickHouse columns to S3 Tables schema
        df_mapped = pd.DataFrame()
        column_mappings = {
            'date': 'timestamp',
            'symbol': 'symbol',
            'open_price': 'open',
            'high_price': 'high', 
            'low_price': 'low',
            'close_price': 'close',
            'volume': 'volume',
            'adj_close': 'adjusted_close'
        }
        
        for table_col, df_col in column_mappings.items():
            if df_col in df.columns:
                if table_col == 'date':
                    df_mapped[table_col] = pd.to_datetime(df[df_col]).dt.date
                elif table_col == 'symbol':
                    df_mapped[table_col] = df[df_col].astype(str)
                elif table_col == 'volume':
                    df_mapped[table_col] = pd.to_numeric(df[df_col], errors='coerce').astype('Int64')
                elif 'price' in table_col or table_col == 'adj_close':
                    df_mapped[table_col] = pd.to_numeric(df[df_col], errors='coerce').astype('float64')
                else:
                    df_mapped[table_col] = df[df_col]
        
        # Remove rows with null required fields
        df_mapped = df_mapped.dropna(subset=['date', 'symbol'])
        
        # Create PyArrow schema
        arrow_schema = pa.schema([
            pa.field('date', pa.date32(), nullable=False),
            pa.field('symbol', pa.string(), nullable=False),
            pa.field('open_price', pa.float64(), nullable=True),
            pa.field('high_price', pa.float64(), nullable=True),
            pa.field('low_price', pa.float64(), nullable=True),
            pa.field('close_price', pa.float64(), nullable=True),
            pa.field('volume', pa.int64(), nullable=True),
            pa.field('adj_close', pa.float64(), nullable=True)
        ])
        
        arrow_table = pa.Table.from_pandas(df_mapped, schema=arrow_schema, preserve_index=False)
        
        # Create table with schema and insert data
        table = catalog.create_table(f"{namespace}.{table_name}", schema=arrow_schema)
        print(f"✅ Created table with schema: {namespace}.{table_name}")
        
        table.append(arrow_table)
        print(f"✅ Successfully migrated {len(df_mapped)} rows to S3 Tables")
        return True
        
    except Exception as e:
        print(f"❌ Failed to migrate data to S3 Tables: {e}")
        return False

def main():
    """Main function - creates infrastructure and migrates data"""
    print("🚀 ClickHouse to S3 Tables Complete Migration")
    print("=" * 50)
    
    session = setup_aws_session()
    
    # Step 1: Create S3 Tables infrastructure
    bucket_name, namespace, table_name = create_s3_tables_infrastructure(session)
    if not bucket_name:
        sys.exit(1)
    
    # Step 2: Setup catalog
    print(f"\n🔗 Setting up S3 Tables catalog...")
    catalog = setup_s3_tables_catalog(session, bucket_name)
    if not catalog:
        sys.exit(1)
    
    # Step 3: Query ClickHouse
    print(f"\n📈 Querying ClickHouse for tick data...")
    query = "SELECT * FROM tick_data WHERE symbol = 'AMZN' LIMIT 100"
    df = query_clickhouse(query)
    
    if df.empty:
        print("⚠️  No data retrieved from ClickHouse")
        sys.exit(1)
    
    # Step 4: Migrate data
    print(f"\n📊 Migrating data to S3 Tables...")
    success = migrate_data_to_s3_tables(df, catalog, namespace, table_name)
    
    if success:
        print(f"\n🎉 Complete migration successful!")
        print("=" * 30)
        print(f"📦 S3 Tables Bucket: {bucket_name}")
        print(f"📂 Namespace: {namespace}")
        print(f"📊 Table: {table_name}")
        print(f"📈 Records migrated: {len(df)}")
    else:
        print(f"\n❌ Migration failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
