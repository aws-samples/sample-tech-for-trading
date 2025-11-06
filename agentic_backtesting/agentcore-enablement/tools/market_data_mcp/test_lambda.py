#!/usr/bin/env python3
"""
Test script for lambda_function.py
Tests the lambda_handler with AMZN symbol
"""

import json
import os
import sys
from datetime import datetime, timedelta

# Add the current directory to Python path to import lambda_function
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from lambda_function import lambda_handler
except ImportError as e:
    print(f"❌ Error importing lambda_function: {e}")
    print("Make sure lambda_function.py is in the same directory")
    sys.exit(1)

def test_basic_amzn_query():
    """Test basic AMZN data query"""
    print("🧪 Testing Basic AMZN Query")
    print("=" * 50)
    
    event = {
        'symbol': 'AMZN'
    }
    
    context = {} 
    
    try:
        result = lambda_handler(event, context)
        
        print(f"Status Code: {result['statusCode']}")
        print(f"Headers: {result['headers']}")
        
        # Parse response body
        body = json.loads(result['body'])
        
        if body['success']:
            metadata = body['metadata']
            data = body['data']
            print(f"✅ Success!")
            print(f"Symbol: {metadata['symbol']}")
            print(f"Total Rows: {metadata['total_rows']}")
            print(f"Columns: {metadata['columns']}")
            
            if data and len(data) > 0:
                first_row = data[0]
                last_row = data[-1]
                print(f"Date Range: {first_row.get('date', 'N/A')} to {last_row.get('date', 'N/A')}")
                print(f"First Close: ${first_row.get('close_price', 0):.2f}")
                print(f"Last Close: ${last_row.get('close_price', 0):.2f}")
            
        else:
            print(f"❌ Failed: {body['error']}")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests"""
    print("🚀 Starting Lambda Function Tests")
    print("=" * 60)
    
    # Check if we can import required modules
    try:
        import boto3
        import pyarrow
        from pyiceberg.catalog import load_catalog
        print("✅ All required modules available")
    except ImportError as e:
        print(f"⚠️ Warning: Missing module {e}")
        print("Some tests may fail due to missing dependencies")
    
    # Run tests
    test_basic_amzn_query()
    
    print("\n🏁 All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()