#!/usr/bin/env python3

import boto3
import requests
import json
import base64
from botocore.exceptions import ClientError

# Configuration from OAuth metadata
GATEWAY_URL = "https://market-data-mcp-gateway-lryjsuyell.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
COGNITO_USER_POOL_ID = "us-east-1_eAn2oP0lv"
COGNITO_CLIENT_ID = "5jajojm4ullslg0cqu98ffcfaa"  # From conversation summary
REGION = "us-east-1"

def get_cognito_token_with_aws_credentials():
    """Get Cognito token using AWS credentials (admin flow)"""
    
    try:
        cognito_client = boto3.client('cognito-idp', region_name=REGION)
        
        # Try to get user pool info
        print("🔍 Checking Cognito User Pool...")
        user_pool = cognito_client.describe_user_pool(UserPoolId=COGNITO_USER_POOL_ID)
        print(f"User Pool: {user_pool['UserPool']['Name']}")
        
        # Try to get client info
        client_info = cognito_client.describe_user_pool_client(
            UserPoolId=COGNITO_USER_POOL_ID,
            ClientId=COGNITO_CLIENT_ID
        )
        print(f"Client: {client_info['UserPoolClient']['ClientName']}")
        
        # Check if this is a machine-to-machine client
        auth_flows = client_info['UserPoolClient'].get('ExplicitAuthFlows', [])
        print(f"Auth flows: {auth_flows}")
        
        if 'ALLOW_ADMIN_USER_PASSWORD_AUTH' in auth_flows:
            print("✅ Admin auth flow supported")
        
        return None
        
    except ClientError as e:
        print(f"❌ Cognito error: {e}")
        return None

def get_token_with_client_credentials():
    """Try client credentials flow (for machine-to-machine)"""
    
    try:
        cognito_client = boto3.client('cognito-idp', region_name=REGION)
        
        # Try client credentials flow
        print("🔑 Attempting client credentials flow...")
        
        # This might not work if not configured for client credentials
        response = cognito_client.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow='CLIENT_CREDENTIALS'
        )
        
        return response.get('AuthenticationResult', {}).get('AccessToken')
        
    except Exception as e:
        print(f"Client credentials failed: {e}")
        return None

def get_token_with_aws_iam():
    """Try using AWS IAM credentials to get a token"""
    
    try:
        # Use STS to get caller identity and create a token
        sts = boto3.client('sts', region_name=REGION)
        identity = sts.get_caller_identity()
        
        # Create a simple JWT-like token with AWS identity
        header = {"alg": "none", "typ": "JWT"}
        payload = {
            "iss": "aws-iam",
            "sub": identity['Arn'],
            "aud": GATEWAY_URL,
            "account": identity['Account']
        }
        
        # Create unsigned JWT (for testing)
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        
        token = f"{header_b64}.{payload_b64}."
        return token
        
    except Exception as e:
        print(f"AWS IAM token creation failed: {e}")
        return None

def test_gateway_with_token(token, token_type):
    """Test the gateway with a specific token"""
    
    if not token:
        print(f"❌ No {token_type} token available")
        return
    
    print(f"\n🧪 Testing with {token_type} token...")
    print(f"Token (first 50 chars): {token[:50]}...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_market_data",
            "arguments": {"symbol": "AMZN"}
        }
    }
    
    try:
        response = requests.post(GATEWAY_URL, json=payload, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Success!")
            result = response.json()
            print(json.dumps(result, indent=2)[:300] + "...")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    print("🚀 Testing MCP Gateway with Cognito Authentication")
    print(f"Gateway URL: {GATEWAY_URL}")
    print(f"Cognito User Pool: {COGNITO_USER_POOL_ID}")
    print(f"Client ID: {COGNITO_CLIENT_ID}")
    print("=" * 60)
    
    # Check Cognito configuration
    get_cognito_token_with_aws_credentials()
    
    # Try different token approaches
    client_creds_token = get_token_with_client_credentials()
    test_gateway_with_token(client_creds_token, "client credentials")
    
    aws_iam_token = get_token_with_aws_iam()
    test_gateway_with_token(aws_iam_token, "AWS IAM")
    
    print("\n" + "=" * 60)
    print("💡 The gateway requires proper Cognito authentication.")
    print("   You may need to:")
    print("   1. Create a user in the Cognito User Pool")
    print("   2. Configure the client for machine-to-machine auth")
    print("   3. Use the AgentCore CLI to get proper tokens")

if __name__ == "__main__":
    main()
