#!/usr/bin/env python3

import requests
import json
import sys

# Gateway configuration from deployment
GATEWAY_URL = "https://market-data-mcp-gateway-lryjsuyell.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
COGNITO_CLIENT_ID = "5jajojm4ullslg0cqu98ffcfaa"

def test_mcp_gateway(symbol="AMZN"):
    """Test the MCP gateway endpoint directly"""
    
    # MCP protocol request
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_market_data",
            "arguments": {
                "symbol": symbol
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {COGNITO_CLIENT_ID}"  # Using client ID as bearer token
    }
    
    try:
        print(f"Testing MCP gateway with symbol: {symbol}")
        print(f"Gateway URL: {GATEWAY_URL}")
        
        response = requests.post(
            GATEWAY_URL,
            json=mcp_request,
            headers=headers,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(json.dumps(result, indent=2))
        else:
            print("❌ Error!")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AMZN"
    test_mcp_gateway(symbol)
