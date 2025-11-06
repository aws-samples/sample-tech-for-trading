#!/usr/bin/env python3

import boto3
import requests
import json
import base64

GATEWAY_URL = "https://market-data-mcp-gateway-lryjsuyell.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"

def get_aws_token():
    """Get AWS session token"""
    try:
        sts = boto3.client('sts', region_name='us-east-1')
        response = sts.get_session_token()
        return response['Credentials']['SessionToken']
    except Exception as e:
        print(f"Failed to get STS token: {e}")
        return None

def get_caller_identity_token():
    """Get caller identity as token"""
    try:
        sts = boto3.client('sts', region_name='us-east-1')
        response = sts.get_caller_identity()
        # Create a simple token from account info
        token_data = {
            "account": response['Account'],
            "arn": response['Arn'],
            "user_id": response['UserId']
        }
        return base64.b64encode(json.dumps(token_data).encode()).decode()
    except Exception as e:
        print(f"Failed to get caller identity: {e}")
        return None

def test_with_token(token, token_type):
    """Test gateway with a specific token"""
    
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_market_data",
            "arguments": {"symbol": "AMZN"}
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    try:
        print(f"🧪 Testing with {token_type} token...")
        print(f"Token (first 20 chars): {token[:20]}...")
        
        response = requests.post(GATEWAY_URL, json=mcp_request, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Success!")
            result = response.json()
            print(json.dumps(result, indent=2)[:500] + "...")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    print("Testing MCP Gateway with different token types...\n")
    
    # Try STS session token
    sts_token = get_aws_token()
    if sts_token:
        test_with_token(sts_token, "STS session")
        print()
    
    # Try caller identity token
    identity_token = get_caller_identity_token()
    if identity_token:
        test_with_token(identity_token, "caller identity")
        print()
    
    # Try using account ID as token (sometimes works for testing)
    try:
        sts = boto3.client('sts')
        account_id = sts.get_caller_identity()['Account']
        test_with_token(account_id, "account ID")
    except Exception as e:
        print(f"Failed to get account ID: {e}")

if __name__ == "__main__":
    main()
