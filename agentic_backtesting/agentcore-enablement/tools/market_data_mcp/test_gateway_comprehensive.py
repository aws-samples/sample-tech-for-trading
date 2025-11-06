#!/usr/bin/env python3

import requests
import json
import boto3
import time
from datetime import datetime

GATEWAY_URL = "https://market-data-mcp-gateway-lryjsuyell.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"

def test_gateway_health():
    """Test basic gateway connectivity"""
    try:
        print("🔍 Testing gateway connectivity...")
        response = requests.get(GATEWAY_URL.replace('/mcp', '/health'), timeout=5)
        print(f"Health check status: {response.status_code}")
        if response.text:
            print(f"Health response: {response.text}")
    except Exception as e:
        print(f"Health check failed: {e}")

def test_mcp_methods():
    """Test different MCP methods to understand what's supported"""
    
    methods_to_test = [
        "initialize",
        "tools/list", 
        "tools/call"
    ]
    
    for method in methods_to_test:
        print(f"\n🧪 Testing MCP method: {method}")
        
        if method == "initialize":
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            }
        elif method == "tools/list":
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": {}
            }
        else:  # tools/call
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": {
                    "name": "get_market_data",
                    "arguments": {"symbol": "AMZN"}
                }
            }
        
        try:
            response = requests.post(GATEWAY_URL, json=payload, timeout=10)
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text[:200]}...")
        except Exception as e:
            print(f"  Error: {e}")

def test_with_aws_credentials():
    """Test using AWS credentials in different ways"""
    
    session = boto3.Session()
    credentials = session.get_credentials()
    
    # Test 1: Access key as bearer token
    print("\n🧪 Testing with AWS access key as bearer token...")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {credentials.access_key}"
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
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")

def test_without_auth_detailed():
    """Test without auth to get detailed error info"""
    print("\n🧪 Testing without authentication (detailed)...")
    
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
        response = requests.post(GATEWAY_URL, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response: {response.text}")
        
        # Check for authentication hints in headers
        if 'WWW-Authenticate' in response.headers:
            print(f"Auth hint: {response.headers['WWW-Authenticate']}")
            
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("🚀 Comprehensive MCP Gateway Testing")
    print(f"Gateway URL: {GATEWAY_URL}")
    print(f"Time: {datetime.now()}")
    print("=" * 60)
    
    # Test basic connectivity
    test_gateway_health()
    
    # Test without auth for detailed error
    test_without_auth_detailed()
    
    # Test different MCP methods
    test_mcp_methods()
    
    # Test with AWS credentials
    test_with_aws_credentials()
    
    print("\n" + "=" * 60)
    print("💡 Next steps:")
    print("1. Check if gateway status is 'ACTIVE' (not 'CREATING')")
    print("2. Verify authentication configuration")
    print("3. Check AgentCore documentation for proper token format")

if __name__ == "__main__":
    main()
