#!/usr/bin/env python3
"""
Test script to verify AgentCore Gateway connection with Cognito authentication
"""

import os
import sys
import asyncio
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_gateway_connection():
    """Test the gateway connection"""
    print("🧪 Testing AgentCore Gateway Connection")
    print("=" * 50)
    
    try:
        # Import the functions from agent.py
        from agent import call_gateway_market_data_with_cognito, authenticate_with_cognito
        
        print("✅ Successfully imported gateway functions")
        
        # Test Cognito authentication first
        print("\n🔐 Testing Cognito Authentication...")
        try:
            access_token = await authenticate_with_cognito()
            print(f"✅ Cognito authentication successful")
            print(f"   Token length: {len(access_token)} characters")
        except Exception as e:
            print(f"❌ Cognito authentication failed: {e}")
            return
        
        # Test gateway call with AMZN
        print("\n🌐 Testing Gateway Call with AMZN...")
        try:
            result = await call_gateway_market_data_with_cognito("AMZN", "symbol")
            print("✅ Gateway call successful!")
            print(f"   Symbol: {result.get('symbol', 'N/A')}")
            print(f"   Data Points: {result.get('data_points', 'N/A')}")
            print(f"   Period: {result.get('period_start', 'N/A')} to {result.get('period_end', 'N/A')}")
            print(f"   Source: {result.get('source', 'N/A')}")
            
            # Show price data if available
            price_data = result.get('price_data', {})
            if price_data:
                print(f"   Initial Price: ${price_data.get('initial_price', 0):.2f}")
                print(f"   Final Price: ${price_data.get('final_price', 0):.2f}")
                print(f"   Min Price: ${price_data.get('min_price', 0):.2f}")
                print(f"   Max Price: ${price_data.get('max_price', 0):.2f}")
            
        except Exception as e:
            print(f"❌ Gateway call failed: {e}")
            print("   This might be expected if Cognito credentials are not configured")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure agent.py is in the same directory")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

def test_environment_variables():
    """Test if required environment variables are set"""
    print("\n🔧 Checking Environment Variables")
    print("-" * 30)
    
    required_vars = [
        'AGENTCORE_GATEWAY_URL',
        'COGNITO_USER_POOL_ID',
        'COGNITO_CLIENT_ID',
        'COGNITO_CLIENT_SECRET',
        'COGNITO_USERNAME',
        'COGNITO_PASSWORD'
    ]
    
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if 'PASSWORD' in var or 'SECRET' in var:
                print(f"✅ {var}: {'*' * min(len(value), 8)}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️ Missing environment variables: {', '.join(missing_vars)}")
        print("   Please update your .env file with the correct values")
        return False
    else:
        print("\n✅ All required environment variables are set")
        return True

async def main():
    """Main test function"""
    print("🚀 AgentCore Gateway Connection Test")
    print("=" * 60)
    
    # Check environment variables first
    env_ok = test_environment_variables()
    
    if env_ok:
        # Test gateway connection
        await test_gateway_connection()
    else:
        print("\n❌ Cannot proceed with gateway test due to missing environment variables")
    
    print("\n🏁 Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())