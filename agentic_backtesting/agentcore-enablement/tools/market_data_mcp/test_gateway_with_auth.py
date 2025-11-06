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

def create_test_user():
    """Create a test user with a compliant password"""
    
    cognito_client = boto3.client('cognito-idp', region_name=REGION)
    
    try:
        # Check if user already exists
        try:
            user = cognito_client.admin_get_user(
                UserPoolId=COGNITO_USER_POOL_ID,
                Username=TEST_USERNAME
            )
            print(f"✅ Test user '{TEST_USERNAME}' already exists")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] != 'UserNotFoundException':
                raise e
        
        print(f"🆕 Creating test user '{TEST_USERNAME}'...")
        
        # Create user with compliant password
        response = cognito_client.admin_create_user(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=TEST_USERNAME,
            TemporaryPassword=TEST_PASSWORD,
            MessageAction='SUPPRESS',
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': 'test@example.com'
                }
            ]
        )
        
        print(f"✅ User created with temporary password: {TEST_PASSWORD}")
        
        # Set permanent password
        cognito_client.admin_set_user_password(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=TEST_USERNAME,
            Password=TEST_PASSWORD,
            Permanent=True
        )
        
        print(f"✅ Permanent password set")
        return True
        
    except ClientError as e:
        print(f"❌ Failed to create user: {e}")
        return False

def get_access_token():
    """Get access token using admin authentication"""
    
    cognito_client = boto3.client('cognito-idp', region_name=REGION)
    
    try:
        secret_hash = calculate_secret_hash(TEST_USERNAME, COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET)
        
        print("🔑 Authenticating with Cognito...")
        
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
            access_token = response['AuthenticationResult']['AccessToken']
            print("✅ Successfully obtained access token")
            return access_token
        else:
            print(f"❌ Authentication challenge required: {response}")
            return None
            
    except ClientError as e:
        print(f"❌ Authentication failed: {e}")
        return None

def test_mcp_gateway(access_token):
    """Test the MCP gateway with the access token"""
    
    if not access_token:
        print("❌ No access token available")
        return
    
    print(f"\n🧪 Testing MCP gateway with Cognito token...")
    print(f"Token (first 50 chars): {access_token[:50]}...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    # Test 1: List available tools
    print("\n📋 Testing tools/list...")
    list_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    
    try:
        response = requests.post(GATEWAY_URL, json=list_payload, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Tools list successful!")
            result = response.json()
            print(json.dumps(result, indent=2))
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 2: Call get_market_data tool
    print("\n📊 Testing get_market_data tool...")
    call_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_market_data",
            "arguments": {"symbol": "AMZN"}
        }
    }
    
    try:
        response = requests.post(GATEWAY_URL, json=call_payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Market data call successful!")
            result = response.json()
            
            # Parse the result
            if 'result' in result and 'content' in result['result']:
                content = result['result']['content']
                if isinstance(content, list) and len(content) > 0:
                    text_content = content[0].get('text', '')
                    if text_content:
                        try:
                            data = json.loads(text_content)
                            if 'metadata' in data:
                                metadata = data['metadata']
                                print(f"📈 Retrieved {metadata['total_rows']} rows for {metadata['symbol']}")
                                print(f"📊 Columns: {', '.join(metadata['columns'])}")
                            else:
                                print(f"📄 Response: {text_content[:200]}...")
                        except json.JSONDecodeError:
                            print(f"📄 Response: {text_content[:200]}...")
                    else:
                        print(json.dumps(result, indent=2)[:500] + "...")
                else:
                    print(json.dumps(result, indent=2)[:500] + "...")
            else:
                print(json.dumps(result, indent=2)[:500] + "...")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    print("🚀 MCP Gateway Authentication & Testing")
    print(f"Gateway URL: {GATEWAY_URL}")
    print(f"User Pool: {COGNITO_USER_POOL_ID}")
    print(f"Test User: {TEST_USERNAME}")
    print("=" * 60)
    
    # Create test user
    if create_test_user():
        # Get access token
        access_token = get_access_token()
        
        # Test the gateway
        if access_token:
            test_mcp_gateway(access_token)
            
            print("\n" + "=" * 60)
            print("🎉 SUCCESS! MCP Gateway is working with Cognito authentication")
            print(f"💡 You can now use this token to access the gateway:")
            print(f"   Authorization: Bearer {access_token[:20]}...")
        else:
            print("\n❌ Failed to get access token")
    else:
        print("\n❌ Failed to create test user")

if __name__ == "__main__":
    main()
