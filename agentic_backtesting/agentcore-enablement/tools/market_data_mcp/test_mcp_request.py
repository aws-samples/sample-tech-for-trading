#!/usr/bin/env python3
import requests
import json
import boto3
import base64

# Gateway configuration
GATEWAY_URL = "https://market-data-mcp-gateway-fdgazieozc.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"

# Cognito configuration from the deployment output
CLIENT_ID = "2e0vuv0re9uc8opnrtb1sjqltl"
CLIENT_SECRET = "1dd2gspfofam0ohcv63abo4ch2asjpuq7j3ong4nki61mus1rqkk"
TOKEN_ENDPOINT = "https://agentcore-bb65edaa.auth.us-east-1.amazoncognito.com/oauth2/token"
SCOPE = "market-data-mcp-gateway/invoke"

def get_access_token():
    """Get access token from Cognito"""
    # Create basic auth header
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'grant_type': 'client_credentials',
        'scope': SCOPE
    }
    
    response = requests.post(TOKEN_ENDPOINT, headers=headers, data=data)
    
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f"Failed to get token: {response.text}")

try:
    # Get access token
    print("🔐 Getting access token...")
    access_token = get_access_token()
    print("✅ Got access token")
    
    # Create proper MCP request
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_market_data",
            "arguments": {
                "symbol": "AMZN"
            }
        }
    }
    
    print(f"📤 Sending MCP request: {json.dumps(mcp_request, indent=2)}")
    
    # Make authenticated request to gateway
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        GATEWAY_URL,
        json=mcp_request,
        headers=headers,
        timeout=30
    )
    
    print(f"📊 Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Error: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
