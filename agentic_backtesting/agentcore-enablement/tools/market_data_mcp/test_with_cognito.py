#!/usr/bin/env python3

import boto3
import requests
import json
import sys

# Configuration from deployment
GATEWAY_URL = "https://market-data-mcp-gateway-lryjsuyell.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
COGNITO_CLIENT_ID = "5jajojm4ullslg0cqu98ffcfaa"

def get_cognito_token():
    """Get Cognito token using AWS credentials"""
    try:
        # Use AWS CLI credentials to get Cognito token
        cognito_client = boto3.client('cognito-identity', region_name='us-east-1')
        
        # Get identity ID
        identity_response = cognito_client.get_id(
            IdentityPoolId='us-east-1:' + COGNITO_CLIENT_ID  # Assuming this format
        )
        
        # Get credentials
        credentials_response = cognito_client.get_credentials_for_identity(
            IdentityId=identity_response['IdentityId']
        )
        
        return credentials_response['Credentials']['SessionToken']
        
    except Exception as e:
        print(f"Cognito auth failed: {e}")
        return None

def test_with_aws_auth(symbol="AMZN"):
    """Test using AWS SigV4 authentication"""
    
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    import boto3
    
    # Create AWS session
    session = boto3.Session()
    credentials = session.get_credentials()
    
    # MCP request
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_market_data",
            "arguments": {"symbol": symbol}
        }
    }
    
    # Create AWS request
    request = AWSRequest(
        method='POST',
        url=GATEWAY_URL,
        data=json.dumps(mcp_request),
        headers={'Content-Type': 'application/json'}
    )
    
    # Sign request
    SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)
    
    try:
        print(f"Testing with AWS SigV4 auth, symbol: {symbol}")
        
        response = requests.post(
            request.url,
            data=request.body,
            headers=dict(request.headers),
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Success!")
            print(json.dumps(response.json(), indent=2))
        else:
            print("❌ Error!")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AMZN"
    test_with_aws_auth(symbol)
