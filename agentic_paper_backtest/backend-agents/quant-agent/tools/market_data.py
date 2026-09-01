"""
Market Data Tool
Fetches historical market data via AgentCore Gateway with Cognito authentication
"""

import os
import json
import time
import base64
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, Any
import httpx
from strands import tool
import config


def extract_market_data_from_gateway_response(gateway_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and transform market data from AgentCore Gateway JSON-RPC response.
    sample: {"jsonrpc":"2.0","id":1,"result":{"isError":false,"content":[{"type":"text","text":"{\"statusCode\":200,\"body\":\"{\\\"success\\\": true, \\\"metadata\\\": {\\\"symbol\\\": \\\"AMZN\\\", \\\"total_rows\\\": 100, \\\"columns\\\": [\\\"date\\\", \\\"symbol\\\", \\\"open_price\\\", \\\"high_price\\\", \\\"low_price\\\", \\\"close_price\\\", \\\"volume\\\", \\\"adj_close\\\"]}, \\\"data\\\": [{\\\"date\\\": \\\"2000-01-03\\\", \\\"symbol\\\": \\\"AMZN\\\", \\\"open_price\\\": 4.074999809265137, \\\"high_price\\\": 4.478125095367432, \\\"low_price\\\": 3.9523439407348633, \\\"close_price\\\": 4.46875, \\\"volume\\\": 322352000, \\\"adj_close\\\": 4.46875}, {\\\"date\\\": \\\"2000-01-04\\\", \\\"symbol\\\": \\\"AMZN\\\", \\\"open_price\\\": 4.268750190734863, \\\"high_price\\\": 4.574999809265137, \\\"low_price\\\": 4.087500095367432, \\\"close_price\\\": 4.096875190734863, \\\"volume\\\": 349748000, \\\"adj_close\\\": 4.096875190734863}, {\\\"date\\\": \\\"2025-06-03\\\", \\\"symbol\\\": \\\"AMZN\\\", \\\"open_price\\\": 207.11000061035156, \\\"high_price\\\": 208.9499969482422, \\\"low_price\\\": 205.02999877929688, \\\"close_price\\\": 205.7100067138672, \\\"volume\\\": 33139100, \\\"adj_close\\\": 205.7100067138672}, {\\\"date\\\": \\\"2025-06-04\\\", \\\"symbol\\\": \\\"AMZN\\\", \\\"open_price\\\": 206.5500030517578, \\\"high_price\\\": 208.17999267578125, \\\"low_price\\\": 205.17999267578125, \\\"close_price\\\": 207.22999572753906, \\\"volume\\\": 29866400, \\\"adj_close\\\": 207.22999572753906}]}\",\"headers\":{\"Content-Type\":\"application/json\"}}"}]}}

    Handles the hierarchy: result -> content -> text -> body -> data
    Transforms field names for Backtrader compatibility:
    - open_price -> open
    - high_price -> high
    - low_price -> low
    - close_price -> close
    - adj_close -> adj_close (kept as is)
    - volume -> volume (kept as is)

    Args:
        gateway_response: Raw JSON-RPC response from AgentCore Gateway

    Returns:
        Structured market data ready for Backtrader
    """
    try:
        # print("🔍 Extracting market data from gateway response...")

        # Navigate through JSON-RPC hierarchy: result -> content -> text
        result = gateway_response.get('result', {})
        content = result.get('content', [])

        if not content or not isinstance(content, list):
            raise ValueError("No content found in gateway response")

        # Extract text from first content item
        text_content = content[0].get('text', '')
        if not text_content:
            raise ValueError("No text content found in gateway response")

        # Parse the nested JSON in text content
        nested_data = json.loads(text_content)

        # Extract body from statusCode response
        body_str = nested_data.get('body', '')
        if not body_str:
            raise ValueError("No body found in nested response")

        # Parse the body JSON
        body_data = json.loads(body_str)

        # Verify success and extract data
        if not body_data.get('success', False):
            raise ValueError("Gateway response indicates failure")

        raw_data = body_data.get('data', [])
        metadata = body_data.get('metadata', {})

        if not raw_data:
            raise ValueError("No market data found in response")

        print(f"📊 Found {len(raw_data)} data points for {metadata.get('symbol', 'UNKNOWN')}")

        # Transform data for Backtrader compatibility
        transformed_data = []
        for item in raw_data:
            transformed_item = {
                'date': item.get('date'),
                'symbol': item.get('symbol'),
                'open': float(item.get('open_price', 0)),
                'high': float(item.get('high_price', 0)),
                'low': float(item.get('low_price', 0)),
                'close': float(item.get('close_price', 0)),
                'volume': int(item.get('volume', 0)),
                'adj_close': float(item.get('adj_close', 0))
            }
            transformed_data.append(transformed_item)

        # Structure as symbol -> daily data mapping
        symbol = metadata.get('symbol', 'UNKNOWN')
        result_data = {
            symbol: {
                'daily_data': transformed_data,
                'metadata': {
                    'symbol': symbol,
                    'total_rows': metadata.get('total_rows', len(transformed_data)),
                    'columns': metadata.get('columns', []),
                    'source': 'agentcore_gateway',
                    'timestamp': datetime.now().isoformat()
                }
            }
        }

        # print(f"✅ Successfully extracted and transformed {len(transformed_data)} data points")
        return result_data

    except Exception as e:
        print(f"❌ Error extracting market data from gateway response: {e}")
        # Return fallback structure
        return {
            'UNKNOWN': {
                'daily_data': [],
                'metadata': {
                    'symbol': 'UNKNOWN',
                    'total_rows': 0,
                    'source': 'extraction_error',
                    'error': str(e)
                }
            }
        }


def authenticate_with_cognito() -> str:
    """Authenticate with Cognito using client_credentials flow and return access token"""
    try:
        client_id = os.getenv('COGNITO_CLIENT_ID')
        client_secret = os.getenv('COGNITO_CLIENT_SECRET')
        cognito_domain = os.getenv('COGNITO_DOMAIN')
        region = config._region_name

        if not all([client_id, client_secret, cognito_domain]):
            raise ValueError(
                "Missing Cognito configuration. "
                "Please set COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET, and COGNITO_DOMAIN in .env"
            )

        # Token endpoint
        token_url = f"https://{cognito_domain}.auth.{region}.amazoncognito.com/oauth2/token"

        # client_credentials flow: Basic auth with client_id:client_secret
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        data = urllib.parse.urlencode({
            'grant_type': 'client_credentials',
        }).encode()

        req = urllib.request.Request(token_url, data=data, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        req.add_header('Authorization', f'Basic {credentials}')

        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())

        access_token = result['access_token']
        return access_token

    except Exception as e:
        print(f"❌ Cognito authentication failed: {e}")
        raise


def call_gateway_market_data_with_cognito(symbol: str, start_date: str = None, end_date: str = None, limit: int = 252) -> Dict[str, Any]:
    """Call AgentCore Gateway with Cognito authentication (synchronous)"""
    try:
        # Get gateway configuration
        gateway_url = os.getenv('AGENTCORE_GATEWAY_URL')

        print(f"🌐 Calling AgentCore Gateway: {gateway_url}")

        # Authenticate with Cognito (now synchronous)
        access_token = authenticate_with_cognito()

        # Build arguments with optional date range
        arguments = {
            "symbol": symbol.upper(),
            "limit": limit
        }

        if start_date:
            arguments["start_date"] = start_date

        if end_date:
            arguments["end_date"] = end_date

        # Prepare JSON-RPC 2.0 request payload
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "market-data-lambda-target___get_market_data",
                "arguments": arguments
            }
        }

        # Set up headers with Cognito token
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        print(f"📤 Sending request to gateway with payload: {payload}")

        # Make request to AgentCore Gateway using synchronous client
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                gateway_url,
                json=payload,
                headers=headers
            )

            print(f"📥 Gateway response status: {response.status_code}")

            # Print full response content for debugging
            try:
                response_text = response.text
                print(f"📄 Full Gateway Response Details:")
                print(f"   Status Code: {response.status_code}")
                print(f"   Response Headers: {dict(response.headers)}")
                print(f"   Response Length: {len(response_text)} characters")
                print(f"   Content Type: {response.headers.get('content-type', 'Unknown')}")
                # print(f"📝 Raw Response Content:")
                # print(f"   {response_text}")

                if response.status_code != 200:
                    print(f"❌ Non-200 Status Code Response:")
                    print(f"   Status: {response.status_code}")
                    print(f"   Reason: {response.reason_phrase if hasattr(response, 'reason_phrase') else 'Unknown'}")
                    print(f"   Content: {response_text}")

            except json.JSONDecodeError as e:
                print(f"⚠️ JSON Decode Error: {e}")
                print(f"   Raw response text: {response.text}")
            except Exception as e:
                print(f"⚠️ Error processing response: {e}")
                print(f"   Raw response text: {response.text}")

            if response.status_code == 200:
                data = response.json()
                print("✅ Successfully fetched data from AgentCore Gateway")

                # Return the raw JSON-RPC response for proper extraction
                if 'jsonrpc' in data:
                    if 'error' in data:
                        error_msg = data['error']
                        print(f"❌ Gateway returned error: {error_msg}")
                        raise Exception(f"Gateway error: {error_msg}")
                    else:
                        # Return the complete response for extraction
                        return data
                else:
                    error_msg = data.get('error', 'Unknown error from gateway')
                    print(f"❌ Gateway returned error: {error_msg}")
                    raise Exception(f"Gateway error: {error_msg}")
            else:
                error_text = response.text
                print(f"❌ Gateway request failed: {response.status_code} - {error_text}")
                raise Exception(f"Gateway request failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Error calling AgentCore Gateway: {e}")
        raise


@tool
def fetch_market_data_via_gateway(symbol: str, start_date: str = None, end_date: str = None, limit: int = 252) -> Dict[str, Any]:
    """
    Fetch market data via AgentCore Gateway MCP with Cognito authentication.
    This tool waits synchronously for completion before returning.

    Args:
        symbol: Stock symbol to get tick data for. Examples: AAPL, MSFT, GOOGL, NVDA, JNJ, PFE, JPM, BAC, XOM, CVX
        start_date: Start date for data retrieval in format YYYY-MM-DD (e.g., 2024-01-15). Use 01 for January, not 1. Use 01 for single digit days, not 1.
        end_date: End date for data retrieval in format YYYY-MM-DD (e.g., 2024-12-31). Use 01 for January, not 1. Use 01 for single digit days, not 1.
        limit: Maximum number of data points to return (default: 252)

    Returns:
        Market data from external service via Gateway
    """
    if not symbol:
        print(f"🌐 AgentCore Gateway: No symbol specified, using AMZN...")
        symbol = "AMZN"

    print(f"🌐 AgentCore Gateway: Fetching {symbol} data via MCP (start: {start_date}, end: {end_date}, limit: {limit})...")

    start_time = time.time()

    try:
        # Call synchronous function directly with date range parameters
        gateway_response = call_gateway_market_data_with_cognito(symbol, start_date, end_date, limit)

        # Extract structured data from gateway response
        config._stored_market_data = extract_market_data_from_gateway_response(gateway_response)

        processing_time = time.time() - start_time
        print(f"⏱️ Market data fetch completed in {processing_time:.2f} seconds")
        time.sleep(0.5)  # Brief pause to ensure completion

        # Extract metadata for detailed success message
        symbol_key = list(config._stored_market_data.keys())[0] if config._stored_market_data else symbol
        if symbol_key in config._stored_market_data:
            metadata = config._stored_market_data[symbol_key].get('metadata', {})
            total_rows = metadata.get('total_rows', 0)
            columns = metadata.get('columns', [])
            source = metadata.get('source', 'unknown')
            timestamp = metadata.get('timestamp', 'unknown')

            columns_str = ', '.join(columns)
            info = f"✅ Market data fetch successfully for {symbol_key} to have {total_rows} total_rows with columns [{columns_str}] from {source} at {timestamp}"
            print(info)
            return info

    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ AgentCore Gateway: Failed to fetch via Gateway after {processing_time:.2f} seconds - {str(e)}")

    return "Failed to get market data"
