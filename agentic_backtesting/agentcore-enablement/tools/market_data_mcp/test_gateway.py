#!/usr/bin/env python3
import requests
import json
import boto3

# Gateway configuration
GATEWAY_ARN = "arn:aws:bedrock-agentcore:us-east-1:600627331406:gateway/market-data-mcp-gateway-fdgazieozc"
REGION = "us-east-1"

# Get gateway URL from ARN
session = boto3.Session(profile_name='factor')
client = session.client('bedrock-agentcore-control', region_name=REGION)

try:
    # Get gateway details
    gateway_id = GATEWAY_ARN.split('/')[-1]  # Extract gateway ID from ARN
    response = client.get_gateway(gatewayIdentifier=gateway_id)
    gateway_url = response['gatewayUrl']
    
    print(f"🌐 Gateway URL: {gateway_url}")
    
    # Test payload
    payload = {"symbol": "AMZN"}
    
    print(f"📤 Sending request: {json.dumps(payload)}")
    
    # Make request to gateway
    response = requests.post(
        gateway_url,
        json=payload,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    
    print(f"📊 Status Code: {response.status_code}")
    print(f"📋 Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Error: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
