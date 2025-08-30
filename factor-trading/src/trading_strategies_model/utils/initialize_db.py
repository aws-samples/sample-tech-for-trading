"""
Script to initialize the ClickHouse database schema.
"""

import os
import argparse
import sys
from dotenv import load_dotenv

from .db_manager import DBManager


def main():
    """
    Initialize the ClickHouse database schema.
    """
    parser = argparse.ArgumentParser(description='Initialize ClickHouse database schema')
    parser.add_argument('--host', help='ClickHouse host')
    parser.add_argument('--port', type=int, help='ClickHouse port')
    parser.add_argument('--user', help='ClickHouse user')
    parser.add_argument('--password', help='ClickHouse password')
    parser.add_argument('--database', help='ClickHouse database')
    
    args = parser.parse_args()
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Use command line arguments if provided, otherwise use environment variables
    host = args.host or os.getenv('CLICKHOUSE_HOST')
    port = args.port or int(os.getenv('CLICKHOUSE_PORT', 9000))
    user = args.user or os.getenv('CLICKHOUSE_USER', 'default')
    password = args.password or os.getenv('CLICKHOUSE_PASSWORD', '')
    database = args.database or os.getenv('CLICKHOUSE_DATABASE')
    
    if not host or not database:
        print("Error: ClickHouse host and database must be provided")
        return
    
    print(f"Initializing ClickHouse schema on {host}:{port}, database: {database}")
    
    # Initialize database manager
    db_manager = DBManager(host, port, user, password, database)
    
    # Create tables
    db_manager.initialize_schema()
    
    print("Database schema initialized successfully")


if __name__ == "__main__":
    main()
