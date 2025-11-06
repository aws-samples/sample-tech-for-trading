#!/usr/bin/env python3

import requests
import json
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

# Gateway URL from .env
GATEWAY_URL = "https://market-data-mcp-gateway-lryjsuyell.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"

def test_gateway_no_auth():
    """Test gateway without authentication to see what error we get"""
    
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_market_data",
            "arguments": {"symbol": "AMZN"}
        }
    }
    
    try:
        print("🧪 Testing gateway without authentication...")
        response = requests.post(GATEWAY_URL, json=mcp_request, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")

def test_gateway_with_sigv4():
    """Test with AWS SigV4 authentication"""
    
    session = boto3.Session()
    credentials = session.get_credentials()
    
    mcp_request = {
        "jsonrpc": "2.0", 
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_market_data",
            "arguments": {"symbol": "AMZN"}
        }
    }
    
    # Create signed request
    request = AWSRequest(
        method='POST',
        url=GATEWAY_URL,
        data=json.dumps(mcp_request),
        headers={'Content-Type': 'application/json'}
    )
    
    SigV4Auth(credentials, 'bedrock', 'us-east-1').add_auth(request)
    
    try:
        print("🧪 Testing gateway with SigV4 auth...")
        response = requests.post(
            request.url,
            data=request.body,
            headers=dict(request.headers),
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_gateway_no_auth()
    print()
    test_gateway_with_sigv4()
