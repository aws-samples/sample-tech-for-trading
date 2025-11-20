"""
AgentCore Interactive Backtesting Agent
Demonstrates "Agent as Tool" patterns with AgentCore Gateway integration
Single agent with Strands tools for strategy generation, backtesting, and results
"""

import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Verify environment variables are loaded
print("🔧 Environment Variables Loaded:")
print(f"   AGENTCORE_GATEWAY_URL: {os.getenv('AGENTCORE_GATEWAY_URL', 'Not set')}")
print(f"   STRATEGY_GENERATOR_RUNTIME_ARN: {os.getenv('STRATEGY_GENERATOR_RUNTIME_ARN', 'Not set')}")
print(f"   COGNITO_USER_POOL_ID: {os.getenv('COGNITO_USER_POOL_ID', 'Not set')}")
print(f"   COGNITO_CLIENT_ID: {os.getenv('COGNITO_CLIENT_ID', 'Not set')}")
print(f"   AWS_REGION: {os.getenv('AWS_REGION', 'us-east-1')}")

from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole
from strands import Agent, tool
import pandas as pd
import numpy as np
import json
import uuid
import httpx
import asyncio
import boto3
import base64
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any

from tools.backtest import BacktestTool

# Initialize the AgentCore app
app = BedrockAgentCoreApp()

# Global storage for market data
_stored_market_data = {}

_region_name = os.getenv('AWS_REGION', 'us-east-1')

agentcore_runtime_client = boto3.client('bedrock-agentcore', region_name=_region_name)

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


def get_memory_id_by_name(name_prefix: str = "quant_agent") -> str:
    """
    Retrieve AgentCore Memory ID by searching for memory with name starting with prefix.
    
    Args:
        name_prefix: The prefix to search for in memory names (default: "quant_agent")
    
    Returns:
        Memory ID string, or creates a new memory if not found
    """
    try:
        agentcore_client = boto3.client('bedrock-agentcore-control', region_name=_region_name)
        
        # List all memories
        response = agentcore_client.list_memories()
        
        # Search for memory with matching name prefix in the 'id' field
        for memory in response.get('memories', []):
            memory_id = memory.get('id', '')
            # The memory ID format is: {name_prefix}-{random_id}
            if memory_id.startswith(name_prefix):
                print(f"✅ Found existing memory: {memory_id}")
                return memory_id
        
    except Exception as e:
        print(f"❌ Error getting memory ID: {e}")
        return "your_fallback_id"

memory_client = MemoryClient(region_name=_region_name)
_memory_id = get_memory_id_by_name("quant_agent")
_actor_id = "Quant"
_session_id = f"quant_session_{datetime.now().strftime('%Y%m%d')}"  # Changes daily, not per second
print(f"🔑 Start Session ID: {_session_id}")

def save_backtest_results_to_memory_sync(results: Dict[str, Any]):
    """Save backtest results to AgentCore Memory using create_event (synchronous version)"""
    try:
        symbol = results.get('symbol', 'UNKNOWN')
        print(f"💾 Saving backtest results for {symbol} to AgentCore Memory...")
        
        # Format results as ASSISTANT message
        results_message = f"Backtest result: {json.dumps(results)}"
        
        # Create event using memory_client.create_event
        event = memory_client.create_event(
            memory_id=_memory_id,
            actor_id=_actor_id,
            session_id=_session_id,
            messages=[(results_message, "ASSISTANT")]
        )
        
        print(f"✅ Backtest results saved to AgentCore Memory")
        
    except Exception as e:
        print(f"❌ Failed to save backtest results to AgentCore Memory: {e}")
        import traceback
        traceback.print_exc()

def get_backtest_results_from_memory(symbol: str = None) -> Dict[str, Any]:
    """Retrieve backtest results from AgentCore Memory using list_events"""
    try:
        # print(f"🔍 Retrieving backtest results from AgentCore Memory...")
        
        # List events using memory_client
        events = memory_client.list_events(
            memory_id=_memory_id,
            actor_id=_actor_id,
            session_id=_session_id
        )
        
        # Find the most recent backtest results message
        latest_result = None
        
        # Handle both list and dict response formats
        if isinstance(events, dict):
            events_list = events.get('events', [])
        elif isinstance(events, list):
            events_list = events
        else:
            events_list = []
        
        for event in reversed(events_list):  # Start from most recent
            try:
                # Get messages from event
                messages = event.get('messages', [])
                for msg in messages:
                    content = msg.get('content', '') if isinstance(msg, dict) else str(msg)
                    
                    if 'Backtest result:' in content:
                        # Check if this is for the requested symbol (if specified)
                        if symbol is None or f'"symbol": "{symbol.upper()}"' in content:
                            # Extract JSON data from the message content
                            if ':' in content:
                                json_part = content.split(':', 1)[1].strip()
                                latest_result = json.loads(json_part)
                                break
            except Exception as e:
                print(f"⚠️ Error parsing event: {e}")
                continue
            
            if latest_result:
                break
        
        if latest_result:
            print(f"✅ Found backtest results in AgentCore Memory")
            return latest_result
        else:
            print(f"❌ No backtest results found in AgentCore Memory")
            return None
            
    except Exception as e:
        print(f"❌ Failed to retrieve backtest results from AgentCore Memory: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_secret_hash(username: str, client_id: str, client_secret: str) -> str:
    """Generate secret hash for Cognito authentication"""
    message = username + client_id
    dig = hmac.new(
        client_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()

def authenticate_with_cognito() -> str:
    """Authenticate with Cognito and return access token (synchronous)"""
    try:
        # Get Cognito configuration from environment
        user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
        client_id = os.getenv('COGNITO_CLIENT_ID')
        client_secret = os.getenv('COGNITO_CLIENT_SECRET')
        username = os.getenv('COGNITO_USERNAME')
        password = os.getenv('COGNITO_PASSWORD')
        region = _region_name
        
        if not all([client_id, client_secret, username, password]):
            raise ValueError("Missing Cognito configuration. Please set COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET, COGNITO_USERNAME, and COGNITO_PASSWORD in .env")
        
        # print(f"🔐 Authenticating with Cognito User Pool: {user_pool_id}")
        
        # Initialize Cognito client (boto3 is synchronous)
        cognito_client = boto3.client('cognito-idp', region_name=region)
        
        # Generate secret hash
        secret_hash = get_secret_hash(username, client_id, client_secret)
        
        # Authenticate with Cognito (synchronous call)
        response = cognito_client.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password,
                'SECRET_HASH': secret_hash
            }
        )
        
        access_token = response['AuthenticationResult']['AccessToken']
        # print("✅ Cognito authentication successful")
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
    import time
    
    if not symbol:
        print(f"🌐 AgentCore Gateway: No symbol specified, using AMZN...")
        symbol = "AMZN"
    
    print(f"🌐 AgentCore Gateway: Fetching {symbol} data via MCP (start: {start_date}, end: {end_date}, limit: {limit})...")
    
    start_time = time.time()
    
    try:
        # Call synchronous function directly with date range parameters
        gateway_response = call_gateway_market_data_with_cognito(symbol, start_date, end_date, limit)
        
        # Extract structured data from gateway response
        global _stored_market_data
        _stored_market_data = extract_market_data_from_gateway_response(gateway_response)

        processing_time = time.time() - start_time
        print(f"⏱️ Market data fetch completed in {processing_time:.2f} seconds")
        time.sleep(0.5)  # Brief pause to ensure completion

        # Extract metadata for detailed success message
        symbol_key = list(_stored_market_data.keys())[0] if _stored_market_data else symbol
        if symbol_key in _stored_market_data:
            metadata = _stored_market_data[symbol_key].get('metadata', {})
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


@tool
def generate_trading_strategy(query: str) -> str:
    """
    Generate executable trading strategy code from natural language descriptions.
   
    Args:
        query: Natural language trading strategy in JSON format with sample below:
         {
            "name": "EMA Crossover Strategy",
            "stock_symbol": "AMZN",
            "backtest_window": "1Y",
            "max_positions": 1,
            "stop_loss": 5,
            "take_profit": 10,
            "buy_conditions":  "Price above 20-day moving average and RSI below 70",
            "sell_conditions": "Price below 20-day moving average or RSI above 80"
        }

    Returns:
        Complete Backtrader strategy Python code ready for backtesting
    """
    
    agent_name = "🧠 STRATEGY GENERATOR AGENT"
    print("\n" + "="*50)
    print(agent_name)
    print("="*50)

    input_data = query
    reasoning = "Converting user trading idea into executable strategy code..."
    
    print("="*50)
    print(f"📥 INPUT: {input_data}")
    print(f"🧠 REASONING: {reasoning}")
    
    print("⏳ Processing strategy generation (synchronous)...")
    
    # Record start time for monitoring
    import time
    start_time = time.time()
    
    try:
        # Call strategy agent and wait for completion
        result = agentcore_runtime_client.invoke_agent_runtime(
            agentRuntimeArn=os.getenv('STRATEGY_GENERATOR_RUNTIME_ARN'),
            runtimeSessionId=str(uuid.uuid4()),  # Unique session ID
            payload=json.dumps(input_data).encode('utf-8'),
            qualifier="DEFAULT"                  # Optional; version/endpoint control
        )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        print(f"⏱️ Strategy generation completed in {processing_time:.2f} seconds")
        
        # Parse the AgentCore runtime response
        if 'body' in result:
            # Decode the response body
            response_body = result['body'].read().decode('utf-8')
            response_data = json.loads(response_body)
            
            # Extract the actual result from the nested structure
            if 'result' in response_data and 'content' in response_data['result']:
                content = response_data['result']['content']
                if isinstance(content, list) and len(content) > 0:
                    strategy_code = content[0].get('text', '')
                else:
                    strategy_code = str(content)
            else:
                strategy_code = response_body
        else:
            strategy_code = str(result)
        
        # Ensure we have a valid result before proceeding
        if not strategy_code or len(str(strategy_code).strip()) < 50:
            print("⚠️ Strategy generation returned insufficient content")
            return "Error: Strategy generation failed - insufficient content returned"
            
        print("✅ Strategy generation completed successfully")
        print("="*50)
        
        # Add a small delay to ensure completion
        time.sleep(1)
        
        return strategy_code
        
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Strategy generation failed after {processing_time:.2f} seconds: {e}")
        print("="*50)
        raise


backtest_tool = BacktestTool()

@tool
def run_backtest(symbol: str, strategy_code: str, params: dict = None) -> dict:
    """
    Execute trading strategy backtest using historical market data.
    Reads market data from AgentCore Memory and saves results back to memory.

    Args:
        symbol: the strategy equity code, default AMZN
        strategy_code: Complete Backtrader strategy code from strategy_generator
        params: Optional backtest parameters (cash, commission, etc.)

    Returns:
        Comprehensive backtest results with performance metrics and statistics
    """
    import time
    
    agent_name = "⚡ BACKTEST AGENT"
    print("\n" + "="*50)
    print(agent_name)
    print("="*50)

    # Validate strategy code
    if not strategy_code or len(strategy_code.strip()) < 100:
        print("❌ ERROR: Invalid or empty strategy code")
        return {'error': 'Invalid or empty strategy code'}
    
    global _stored_market_data
    
    # Check if market data is available
    if _stored_market_data is None or not _stored_market_data:
        print("⚠️ No market data found in global storage")
        return {'error': 'No market data found in global storage'}
    
    # Extract the first symbol's data (assuming single symbol for now)
    symbol_key = symbol
    symbol_data = _stored_market_data[symbol_key]
    
    # print(f"🔍 DEBUG - Available symbols: {list(_stored_market_data.keys())}")
    print(f"🔍 DEBUG - Using symbol: {symbol_key}")
    
    # Get the transformed daily data
    daily_data = symbol_data.get('daily_data', [])
    
    if not daily_data:
        print("❌ NO MARKET DATA AVAILABLE - Cannot run backtest")
        return {'error': 'No market data available for backtesting'}
    
    df = pd.DataFrame(daily_data)
    
    # Convert date column to datetime and set as index
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # Ensure numeric columns are properly typed for Backtrader
    numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'adj_close']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    print(f"📈 DataFrame created with columns: {list(df.columns)}")
    # print(f"📅 Date range: {df.index.min()} to {df.index.max()}")
    
    # 🔍 COMPREHENSIVE DEBUG INFO FOR BACKTRADER ERROR TROUBLESHOOTING
    print(f"\n�l DEBUG - DataFrame Analysis:")
    print(f"   Shape: {df.shape}")
    print(f"   Index type: {type(df.index)}")
    print(f"   Index name: {df.index.name}")
    print(f"   Columns: {list(df.columns)}")
    print(f"   Data types:")
    for col in df.columns:
        print(f"     {col}: {df[col].dtype}")
    
    # Print sample data for inspection
    print(f"\n📊 Sample data (first 3 rows):")
    try:
        print(df.head(3).to_string())
    except Exception as e:
        print(f"❌ Error displaying sample data: {e}")
    
    # Prepare backtest input
    backtest_input = {
        'strategy_code': strategy_code,
        'market_data': {symbol_key: df},  # Pass DataFrame for Backtrader
        'params': params or {'initial_cash': 100000, 'commission': 0.001}
    }
    
    print(f"📥 INPUT: strategy_code length: {len(strategy_code)}, symbol: {symbol_key}, rows: {len(daily_data)}")
    print(f"🧠 REASONING: Running strategy backtest with historical data...")
    
    # Execute backtest with enhanced error handling
    start_time = time.time()
    print(f"🚀 Starting backtest execution...")
    
    try:
        result = backtest_tool.process(backtest_input)
        
        # Check if result contains detailed error information
        if isinstance(result, dict) and 'error' in result:
            # print(f"❌ BACKTEST FAILED WITH DETAILED ERROR:")
            # print(f"   Error: {result['error']}")
            
            if 'error_location' in result:
                print(f"   Location: {result['error_location']}")
            
            if 'debug_info' in result:
                print(f"   Debug Info: {result['debug_info']}")
            
            if 'traceback' in result:
                print(f"   📋 FULL TRACEBACK:")
                print(result['traceback'])
        else:
            print(f"✅ Backtest execution completed")
            
    except Exception as backtest_error:
        print(f"❌ BACKTEST TOOL EXCEPTION:")
        print(f"   Error type: {type(backtest_error).__name__}")
        print(f"   Error message: {str(backtest_error)}")
        
        # Try to get more detailed error info
        import traceback
        print(f"   Full traceback:")
        traceback.print_exc()
        
        result = {'error': f'Backtest tool exception: {str(backtest_error)}'}
    processing_time = time.time() - start_time
    
    print(f"⏱️ Backtest completed in {processing_time:.2f} seconds")
    print(f"📤 OUTPUT: {result}")
    
    # Save backtest results to AgentCore Memory
    if 'error' not in result:
        # print("💾 Saving backtest results to AgentCore Memory...")
        save_backtest_results_to_memory_sync(result)
    
    print("="*50)
    return result


@tool
def create_results_summary(backtest_results: dict)  -> str:
    """
    Analyze backtest performance and generate comprehensive trading strategy report.

    Args:
        backtest_results: Dictionary containing backtest metrics and performance data

    Returns:
        Formatted analysis report with key statistics and performance assessment
    """
    agent_name = "📈 RESULTS SUMMARY AGENT"    
    print("\n" + "="*50)
    print(agent_name)
    print("="*50)
    
    import time
    start_time = time.time()

    # If no backtest results provided, read from AgentCore Memory
    if backtest_results is None:
        print(f"📖 No backtest results provided, reading from AgentCore Memory...")
        backtest_results = get_backtest_results_from_memory()
        if backtest_results is None:
            return 'No backtest results found in AgentCore Memory'
    
    print(f"💾 AgentCore Memory: Processing stored results...")
    
    if 'error' in backtest_results:
        return f'Results in backtesting: {backtest_results['error']}'

    try:
        reasoning = "Analyzing backtest performance and generating summary..."
        
        print(f"📥 INPUT: {backtest_results}")
        print(f"🧠 REASONING: {reasoning}")
        
        result = agentcore_runtime_client.invoke_agent_runtime(
            agentRuntimeArn=os.getenv('BACKTEST_SUMMARY_RUNTIME_ARN'),
            runtimeSessionId=str(uuid.uuid4()),  # Unique session ID
            payload=json.dumps(backtest_results).encode('utf-8'),
            qualifier="DEFAULT"                  # Optional; version/endpoint control
        )
        
        # Parse the AgentCore runtime response
        if 'body' in result:
            # Decode the response body
            response_body = result['body'].read().decode('utf-8')
            response_data = json.loads(response_body)
            
            # Extract the actual result from the nested structure
            if 'result' in response_data and 'content' in response_data['result']:
                content = response_data['result']['content']
                if isinstance(content, list) and len(content) > 0:
                    summary_text = content[0].get('text', '')
                else:
                    summary_text = str(content)
            else:
                summary_text = response_body
        else:
            summary_text = str(result)

        processing_time = time.time() - start_time
        print(f"⏱️ Results summary completed in {processing_time:.2f} seconds")
        
        # Brief pause to ensure completion
        time.sleep(0.5)
        return summary_text
        
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Results summary failed after {processing_time:.2f} seconds: {e}")
        return f'Results processing failed: {str(e)}'

# Create the agent with all Strands tools
quant_agent = Agent(
    system_prompt="""You are the Quant Backtesting Agent. When you receive ANY request, you MUST automatically execute ALL 4 steps in this EXACT sequence:

STEP 1: ALWAYS call generate_trading_strategy first
- Use the user's request to create a JSON strategy format
- If no specific strategy is provided, create a default EMA crossover strategy for AMZN
- Pass the JSON strategy to generate_trading_strategy tool

STEP 2: ALWAYS call fetch_market_data_via_gateway 
- Use the symbol from the strategy (default to AMZN if not specified)
- Call fetch_market_data_via_gateway with the symbol

STEP 3: ALWAYS call run_backtest
- Use the strategy code from Step 1 and market data from Step 2
- Use initial investment of $10,000 if not specified
- Call run_backtest with all required parameters

STEP 4: ALWAYS call create_results_summary
- Use the backtest results from Step 3
- Call create_results_summary to format the final results

CRITICAL RULES:
- Execute ALL 4 steps in sequence for EVERY request
- WAIT for each tool to complete before calling the next tool
- Do NOT call multiple tools simultaneously
- Do NOT ask for clarification - proceed with defaults if information is missing
- Do NOT explain what you're going to do - just DO all 4 steps
- Always use these default values if not provided:
  * Symbol: AMZN
  * Initial Investment: $10,000
  * Strategy: EMA50 > EMA200 crossover
- Complete the entire workflow automatically and synchronously""",
    tools=[
        fetch_market_data_via_gateway,
        generate_trading_strategy, 
        run_backtest,
        create_results_summary
    ]
)

@app.entrypoint
def invoke(payload, context=None):
    """Main entrypoint for the backtesting agent"""
    try:
        print(f"🚀 AgentCore Runtime: Backtesting Agent processing request")
        print(f"📥 Payload received: {payload}")

        # Parse payload if it's a string
        if isinstance(payload, str):
            import json
            payload = json.loads(payload)
        
        result = quant_agent(payload.get("prompt"))
        
        return {"result": result.message}
        
    except Exception as e:
        print(f"❌ Error in invoke function: {e}")
        import traceback
        traceback.print_exc()
        return {"result": {"status": "error", "error": str(e)}}

if __name__ == "__main__":
    print("🚀 Starting Strands Multi-Agent Quant Backtesting Agent on AgentCore")
    print(f"   App type: {type(app)}")
    print(f"   App methods: {[m for m in dir(app) if not m.startswith('_')]}")
    
    print("\n🌐 Starting server on port 8080...")
    try:
        app.run(port=8080)
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        import traceback
        traceback.print_exc()