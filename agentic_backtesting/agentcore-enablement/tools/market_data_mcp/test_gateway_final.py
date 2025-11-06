#!/usr/bin/env python3

import boto3
import requests
import json
import hmac
import hashlib
import base64
from botocore.exceptions import ClientError

# Configuration
GATEWAY_URL = "https://market-data-mcp-gateway-lryjsuyell.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
COGNITO_USER_POOL_ID = "us-east-1_eAn2oP0lv"
COGNITO_CLIENT_ID = "5jajojm4ullslg0cqu98ffcfaa"
COGNITO_CLIENT_SECRET = "c1n9f62buh5vu8dlpt9ras6qeggn2agpr52inmnulunp18ke1av"
REGION = "us-east-1"
TEST_USERNAME = "mcp-test-user"
TEST_PASSWORD = "TempPass123!"

def calculate_secret_hash(username, client_id, client_secret):
    """Calculate the secret hash for Cognito authentication"""
    message = username + client_id
    dig = hmac.new(
        client_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()

def get_access_token():
    """Get access token using admin authentication"""
    
    cognito_client = boto3.client('cognito-idp', region_name=REGION)
    
    try:
        secret_hash = calculate_secret_hash(TEST_USERNAME, COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET)
        
        response = cognito_client.admin_initiate_auth(
            UserPoolId=COGNITO_USER_POOL_ID,
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow='ADMIN_USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': TEST_USERNAME,
                'PASSWORD': TEST_PASSWORD,
                'SECRET_HASH': secret_hash
            }
        )
        
        if 'AuthenticationResult' in response:
            return response['AuthenticationResult']['AccessToken']
        return None
            
    except ClientError as e:
        print(f"❌ Authentication failed: {e}")
        return None

def test_market_data_gateway():
    """Test the market data MCP gateway end-to-end"""
    
    print("🚀 Testing Market Data MCP Gateway")
    print("=" * 50)
    
    # Get access token
    print("🔑 Getting Cognito access token...")
    access_token = get_access_token()
    
    if not access_token:
        print("❌ Failed to get access token")
        return
    
    print("✅ Access token obtained")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    # Test market data retrieval
    print("\n📊 Testing market data retrieval for AMZN...")
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "market-data-lambda-target___get_market_data",  # Correct tool name
            "arguments": {"symbol": "AMZN"}
        }
    }
    
    try:
        response = requests.post(GATEWAY_URL, json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if 'result' in result:
                print("✅ Market data retrieved successfully!")
                
                # Extract and parse the content
                content = result['result'].get('content', [])
                if content and len(content) > 0:
                    text_content = content[0].get('text', '')
                    if text_content:
                        try:
                            data = json.loads(text_content)
                            
                            if 'metadata' in data:
                                metadata = data['metadata']
                                print(f"📈 Symbol: {metadata['symbol']}")
                                print(f"📊 Total rows: {metadata['total_rows']}")
                                print(f"📋 Columns: {', '.join(metadata['columns'])}")
                                
                                # Show first few data points
                                if 'data' in data and len(data['data']) > 0:
                                    print(f"\n📅 Sample data (first 3 rows):")
                                    for i, row in enumerate(data['data'][:3]):
                                        print(f"  {i+1}. {row['date']}: ${row['close_price']:.2f} (Vol: {row['volume']:,})")
                                
                                print(f"\n🎉 SUCCESS! MCP Gateway is fully operational!")
                                print(f"💡 Gateway URL: {GATEWAY_URL}")
                                print(f"🔑 Authentication: Cognito User Pool")
                                print(f"⚡ Lambda Function: market-data-mcp")
                                print(f"🗄️  Data Source: S3 Tables (market-data-1762323186)")
                                
                            else:
                                print(f"📄 Raw response: {text_content[:200]}...")
                                
                        except json.JSONDecodeError:
                            print(f"📄 Response text: {text_content[:200]}...")
                else:
                    print(f"📄 Full result: {json.dumps(result, indent=2)[:300]}...")
            else:
                print(f"❌ Error in result: {result}")
        else:
            print(f"❌ HTTP Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_market_data_gateway()
