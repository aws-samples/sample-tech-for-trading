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
    message = username + client_id
    dig = hmac.new(
        client_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()

def get_access_token():
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

def test_market_data():
    print("🚀 Market Data MCP Gateway - Final Test")
    print("=" * 50)
    
    access_token = get_access_token()
    if not access_token:
        return
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "market-data-lambda-target___get_market_data",
            "arguments": {"symbol": "AMZN"}
        }
    }
    
    try:
        response = requests.post(GATEWAY_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'result' in result:
                content = result['result'].get('content', [])
                if content and len(content) > 0:
                    text_content = content[0].get('text', '')
                    
                    # Parse the Lambda response
                    lambda_response = json.loads(text_content)
                    if lambda_response.get('statusCode') == 200:
                        # Parse the body
                        body = json.loads(lambda_response['body'])
                        
                        if body.get('success'):
                            metadata = body['metadata']
                            data_points = body['data']
                            
                            print("✅ SUCCESS! Market data retrieved through MCP Gateway")
                            print(f"📈 Symbol: {metadata['symbol']}")
                            print(f"📊 Total rows: {metadata['total_rows']}")
                            print(f"📋 Columns: {', '.join(metadata['columns'])}")
                            
                            print(f"\n📅 Sample data (first 3 rows):")
                            for i, row in enumerate(data_points[:3]):
                                print(f"  {i+1}. {row['date']}: ${row['close_price']:.2f} (Vol: {row['volume']:,})")
                            
                            print(f"\n📅 Latest data (last 3 rows):")
                            for i, row in enumerate(data_points[-3:]):
                                print(f"  {len(data_points)-2+i}. {row['date']}: ${row['close_price']:.2f} (Vol: {row['volume']:,})")
                            
                            print(f"\n🎉 COMPLETE SUCCESS!")
                            print(f"🌐 Gateway URL: {GATEWAY_URL}")
                            print(f"🔑 Authentication: Cognito (User Pool: {COGNITO_USER_POOL_ID})")
                            print(f"⚡ Lambda Function: market-data-mcp")
                            print(f"🗄️  Data Source: S3 Tables (market-data-1762323186)")
                            print(f"📊 Tool Name: market-data-lambda-target___get_market_data")
                            
                            return True
                        
            print(f"❌ Unexpected response format: {result}")
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return False

if __name__ == "__main__":
    success = test_market_data()
    if success:
        print(f"\n💡 You can now use this MCP gateway in your applications!")
        print(f"   Just authenticate with Cognito and call the tools.")
    else:
        print(f"\n❌ Test failed. Check the logs above for details.")
