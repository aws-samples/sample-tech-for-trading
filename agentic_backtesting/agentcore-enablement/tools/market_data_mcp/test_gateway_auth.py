#!/usr/bin/env python3
import requests
import json
import boto3
import base64

# Gateway configuration
GATEWAY_ARN = "arn:aws:bedrock-agentcore:us-east-1:600627331406:gateway/market-data-mcp-gateway-fdgazieozc"
REGION = "us-east-1"

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

# Get gateway URL
session = boto3.Session(profile_name='factor')
client = session.client('bedrock-agentcore-control', region_name=REGION)

try:
    # Get access token
    print("🔐 Getting access token...")
    access_token = get_access_token()
    print("✅ Got access token")
    
    # Get gateway details
    gateway_id = GATEWAY_ARN.split('/')[-1]
    response = client.get_gateway(gatewayIdentifier=gateway_id)
    gateway_url = response['gatewayUrl']
    
    print(f"🌐 Gateway URL: {gateway_url}")
    
    # Test payload
    payload = {"symbol": "AMZN"}
    
    print(f"📤 Sending request: {json.dumps(payload)}")
    
    # Make authenticated request to gateway
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        gateway_url,
        json=payload,
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
