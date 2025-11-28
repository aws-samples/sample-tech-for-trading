#!/usr/bin/env python3
"""
Populate S3 Tables with Market Data from CSV
Creates S3 Tables infrastructure and loads data from CSV file
"""

import os
import sys
import boto3
import pandas as pd
from pyiceberg.catalog import load_catalog
import pyarrow as pa
from datetime import datetime

# CSV file path
CSV_FILE_PATH = os.path.join(os.path.dirname(__file__), 'amzn.daily.csv')

def setup_aws_session():
    """Setup AWS session"""
    try:
        session = boto3.Session()
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
        namespace = "daily_data"
        table_name = "daily_data"
        
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

def read_csv_data(csv_path: str) -> pd.DataFrame:
    """Read market data from CSV file"""
    try:
        if not os.path.exists(csv_path):
            print(f"❌ CSV file not found: {csv_path}")
            return pd.DataFrame()
        
        print(f"📂 Reading CSV file: {csv_path}")
        df = pd.read_csv(csv_path)
        
        # Display column info
        print(f"✅ Loaded {len(df)} rows from CSV")
        print(f"📋 Columns: {list(df.columns)}")
        
        return df
        
    except Exception as e:
        print(f"❌ Failed to read CSV file: {e}")
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
        # Map CSV columns to S3 Tables schema
        df_mapped = pd.DataFrame()
        
        # Expected CSV columns: symbol, timestamp, open, high, low, close, volume, adjusted_close
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
        
        for table_col, csv_col in column_mappings.items():
            if csv_col in df.columns:
                if table_col == 'date':
                    # Convert timestamp to date
                    df_mapped[table_col] = pd.to_datetime(df[csv_col]).dt.date
                elif table_col == 'symbol':
                    df_mapped[table_col] = df[csv_col].astype(str)
                elif table_col == 'volume':
                    df_mapped[table_col] = pd.to_numeric(df[csv_col], errors='coerce').astype('Int64')
                else:
                    # All price columns
                    df_mapped[table_col] = pd.to_numeric(df[csv_col], errors='coerce').astype('float64')
        
        # Remove rows with null required fields
        df_mapped = df_mapped.dropna(subset=['date', 'symbol'])
        
        print(f"📊 Prepared {len(df_mapped)} rows for migration")
        print(f"📋 Mapped columns: {list(df_mapped.columns)}")
        
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
        print(f"📊 Creating table: {namespace}.{table_name}")
        table = catalog.create_table(f"{namespace}.{table_name}", schema=arrow_schema)
        print(f"✅ Created table with schema")
        
        print(f"📤 Uploading data to S3 Tables...")
        table.append(arrow_table)
        print(f"✅ Successfully migrated {len(df_mapped)} rows to S3 Tables")
        return True
        
    except Exception as e:
        print(f"❌ Failed to migrate data to S3 Tables: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function - creates infrastructure and loads CSV data"""
    print("🚀 CSV to S3 Tables Data Population")
    print("=" * 50)
    
    # Step 1: Setup AWS session
    session = setup_aws_session()
    
    # Step 2: Read CSV data
    print(f"\n📂 Reading CSV data...")
    df = read_csv_data(CSV_FILE_PATH)
    
    if df.empty:
        print("⚠️  No data loaded from CSV")
        sys.exit(1)
    
    # Display sample data
    print(f"\n📊 Sample data (first 3 rows):")
    print(df.head(3).to_string())
    
    # Step 3: Create S3 Tables infrastructure
    print(f"\n🏗️  Creating S3 Tables infrastructure...")
    bucket_name, namespace, table_name = create_s3_tables_infrastructure(session)
    if not bucket_name:
        sys.exit(1)
    
    # Step 4: Setup catalog
    print(f"\n🔗 Setting up S3 Tables catalog...")
    catalog = setup_s3_tables_catalog(session, bucket_name)
    if not catalog:
        sys.exit(1)
    
    # Step 5: Migrate data
    print(f"\n📊 Migrating data to S3 Tables...")
    success = migrate_data_to_s3_tables(df, catalog, namespace, table_name)
    
    if success:
        print(f"\n🎉 Data population successful!")
        print("=" * 50)
        print(f"📦 S3 Tables Bucket: {bucket_name}")
        print(f"📂 Namespace: {namespace}")
        print(f"📊 Table: {table_name}")
        print(f"📈 Records migrated: {len(df)}")
        print(f"\n💡 Update your Lambda function environment variables:")
        print(f"   S3_TABLES_BUCKET={bucket_name}")
        print(f"   S3_TABLES_NAMESPACE={namespace}")
        print(f"   S3_TABLES_TABLE={table_name}")
    else:
        print(f"\n❌ Data population failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
