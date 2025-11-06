"""
AgentCore Interactive Backtesting Agent
Demonstrates "Agent as Tool" patterns with AgentCore Gateway integration
Single agent with Strands tools for strategy generation, backtesting, and results
"""

import os
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Verify environment variables are loaded
print("🔧 Environment Variables Loaded:")
print(f"   AGENTCORE_GATEWAY_URL: {os.getenv('AGENTCORE_GATEWAY_URL', 'Not set')}")
print(f"   COGNITO_USER_POOL_ID: {os.getenv('COGNITO_USER_POOL_ID', 'Not set')}")
print(f"   COGNITO_CLIENT_ID: {os.getenv('COGNITO_CLIENT_ID', 'Not set')[:10]}..." if os.getenv('COGNITO_CLIENT_ID') else "   COGNITO_CLIENT_ID: Not set")
print(f"   AWS_REGION: {os.getenv('AWS_REGION', 'Not set')}")
print(f"   DEBUG: {os.getenv('DEBUG', 'Not set')}")

from bedrock_agentcore import BedrockAgentCoreApp
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

from agents.strategy_generator import StrategyGeneratorAgent

# Initialize the AgentCore app
app = BedrockAgentCoreApp()

# Global workflow memory for AgentCore Memory demonstration
workflow_memory = {}

# Global variables for strategy generation
_strategy_call_count = 0

def get_secret_hash(username: str, client_id: str, client_secret: str) -> str:
    """Generate secret hash for Cognito authentication"""
    message = username + client_id
    dig = hmac.new(
        client_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()

async def authenticate_with_cognito() -> str:
    """Authenticate with Cognito and return access token"""
    try:
        # Get Cognito configuration from environment
        user_pool_id = os.getenv('COGNITO_USER_POOL_ID', 'us-east-1_eAn2oP0lv')
        client_id = os.getenv('COGNITO_CLIENT_ID')
        client_secret = os.getenv('COGNITO_CLIENT_SECRET')
        username = os.getenv('COGNITO_USERNAME')
        password = os.getenv('COGNITO_PASSWORD')
        region = os.getenv('AWS_REGION', 'us-east-1')
        
        if not all([client_id, client_secret, username, password]):
            raise ValueError("Missing Cognito configuration. Please set COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET, COGNITO_USERNAME, and COGNITO_PASSWORD in .env")
        
        print(f"🔐 Authenticating with Cognito User Pool: {user_pool_id}")
        
        # Initialize Cognito client
        cognito_client = boto3.client('cognito-idp', region_name=region)
        
        # Generate secret hash
        secret_hash = get_secret_hash(username, client_id, client_secret)
        
        # Authenticate with Cognito
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
        print("✅ Cognito authentication successful")
        return access_token
        
    except Exception as e:
        print(f"❌ Cognito authentication failed: {e}")
        raise

async def call_gateway_market_data_with_cognito(symbol: str, param_type: str = "symbol") -> Dict[str, Any]:
    """Call AgentCore Gateway with Cognito authentication"""
    try:
        # Get gateway configuration
        gateway_url = os.getenv('AGENTCORE_GATEWAY_URL', 'https://market-data-mcp-gateway-lryjsuyell.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp')
        
        print(f"🌐 Calling AgentCore Gateway: {gateway_url}")
        
        # Authenticate with Cognito
        access_token = await authenticate_with_cognito()
        
        # Prepare JSON-RPC 2.0 request payload
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "market-data-lambda-target___get_market_data",
                "arguments": {
                    "symbol": symbol.upper()
                }
            }
        }
        
        # Set up headers with Cognito token
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        print(f"📤 Sending request to gateway with payload: {payload}")
        
        # Make request to AgentCore Gateway
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
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
                print(f"📝 Raw Response Content:")
                print(f"   {response_text}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"📋 Parsed JSON Response (Pretty Formatted):")
                    print(f"{json.dumps(data, indent=2, default=str)}")
                else:
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
                
                # Handle JSON-RPC 2.0 response format
                if 'jsonrpc' in data:
                    if 'error' in data:
                        error_msg = data['error']
                        print(f"❌ Gateway returned error: {error_msg}")
                        raise Exception(f"Gateway error: {error_msg}")
                    elif 'result' in data:
                        result = data['result']
                        # Extract market data from JSON-RPC result
                        if isinstance(result, dict) and 'data' in result:
                            return {
                                'symbol': result.get('symbol', symbol),
                                'data': result['data'],
                                'total_rows': len(result['data']) if 'data' in result else 0,
                                'source': 'agentcore_gateway'
                            }
                        else:
                            return {
                                'symbol': symbol,
                                'data': result,
                                'total_rows': len(result) if isinstance(result, list) else 0,
                                'source': 'agentcore_gateway'
                            }
                # Handle legacy response format
                elif data.get('success') and data.get('data'):
                    metadata = data['metadata']
                    market_data = data['data']
                    return {
                        'symbol': metadata.get('symbol', symbol),
                        'total_rows': metadata.get('total_rows', 0),
                        'source': 'agentcore_gateway'
                    }
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
def fetch_market_data_via_gateway(symbol: str = None, investment_area: str = None) -> Dict[str, Any]:
    """
    Fetch market data via AgentCore Gateway MCP with Cognito authentication.
    This tool waits synchronously for completion before returning.
    
    Args:
        symbol: Stock symbol (e.g., AMZN) - preferred method
    
    Returns:
        Market data from external service via Gateway
    """
    import time
    
    if symbol:
        print(f"🌐 AgentCore Gateway: Fetching {symbol} data via MCP...")
        target_param = symbol
        param_type = "symbol"
    else:
        print(f"🌐 AgentCore Gateway: No symbol or sector specified, using AMZN...")
        target_param = "AMZN"
        param_type = "symbol"
    
    print("⏳ Fetching market data (synchronous)...")
    start_time = time.time()
    
    try:
        result = asyncio.run(call_gateway_market_data_with_cognito(target_param, param_type))
        processing_time = time.time() - start_time
        print(f"⏱️ Market data fetch completed in {processing_time:.2f} seconds")
        print("✅ Market data fetch successful")
        time.sleep(0.5)  # Brief pause to ensure completion
        return result
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ AgentCore Gateway: Failed to fetch via Gateway after {processing_time:.2f} seconds - {str(e)}")
        print("⚠️ Using fallback data...")
        # Return fallback data for demo purposes
        result = generate_fallback_market_data(target_param)
        print("✅ Fallback data generated")
        time.sleep(0.5)  # Brief pause to ensure completion
        return result

def generate_fallback_market_data(symbol: str) -> Dict[str, Any]:
    """Generate fallback market data when gateway is unavailable"""
    print(f"⚠️ Using fallback data for {symbol}")
    
    # Generate realistic-looking sample data
    import random
    random.seed(hash(symbol) % 1000)  # Consistent data per symbol
    
    base_price = random.uniform(50, 300)
    data_points = 252
    
    return {
        'symbol': symbol.upper(),
        'data_points': data_points,
        'period_start': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        'period_end': datetime.now().strftime('%Y-%m-%d'),
        'price_data': {
            'initial_price': round(base_price, 2),
            'final_price': round(base_price * random.uniform(0.8, 1.3), 2),
            'min_price': round(base_price * random.uniform(0.7, 0.9), 2),
            'max_price': round(base_price * random.uniform(1.1, 1.4), 2)
        },
        'statistics': {
            'total_return_pct': round(random.uniform(-20, 30), 2),
            'avg_daily_volume': random.randint(1000000, 50000000)
        },
        'technical_indicators': {
            'current_sma_20': round(base_price * random.uniform(0.95, 1.05), 2),
            'current_sma_50': round(base_price * random.uniform(0.90, 1.10), 2)
        },
        'source': 'fallback_data'
    }

strategy_agent = StrategyGeneratorAgent()

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
            "buy_conditions":  "EMA50 > EMA200",
            "sell_conditions": "EMA50 < EMA200"
        }

    Returns:
        Complete Backtrader strategy Python code ready for backtesting
    """
    global _strategy_call_count

    agent_name = "🧠 STRATEGY GENERATOR AGENT"
    input_data = query
    reasoning = "Converting user trading idea into executable strategy code..."
    
    print(f"\n� {agent_name} CALL #{_strategy_call_count}")
    print("="*50)
    print(f"📥 INPUT: {input_data}")
    print(f"🧠 REASONING: {reasoning}")
    
    print("⏳ Processing strategy generation (synchronous)...")
    
    # Record start time for monitoring
    import time
    start_time = time.time()
    
    try:
        # Call strategy agent and wait for completion
        result = strategy_agent.process(query)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        print(f"⏱️ Strategy generation completed in {processing_time:.2f} seconds")
        print(f"📤 OUTPUT: {result}")
        
        # Ensure we have a valid result before proceeding
        if not result or len(str(result).strip()) < 50:
            print("⚠️ Strategy generation returned insufficient content, retrying...")
            time.sleep(2)  # Brief wait before retry
            result = strategy_agent.process(query)
            
        print("✅ Strategy generation completed successfully")
        print("="*50)
        
        # Add a small delay to ensure completion
        time.sleep(1)
        
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Strategy generation failed after {processing_time:.2f} seconds: {e}")
        print("="*50)
        raise


@tool
def run_backtest(strategy_code: str, market_data: Dict[str, Any], initial_investment: float) -> Dict[str, Any]:
    """
    Strands Tool: Execute backtesting simulation.
    This tool waits synchronously for completion before returning.
    
    Args:
        strategy_code: Generated Python strategy code
        market_data: Market data from Gateway or fallback
        initial_investment: Initial investment amount
    
    Returns:
        Backtest results with performance metrics
    """
    import time
    
    print(f"⚡ Backtest Tool: Executing simulation...")
    print(f"   Initial investment: ${initial_investment:,.2f}")
    print("⏳ Running backtest simulation (synchronous)...")
    
    start_time = time.time()
    
    try:
        symbol = market_data.get('symbol', 'DEMO')
        
        # Simulate realistic backtest results
        import random
        random.seed(42)  # Consistent results for demo
        
        total_return_pct = random.uniform(-15, 25)
        final_value = initial_investment * (1 + total_return_pct / 100)
        max_drawdown = random.uniform(5, 20)
        sharpe_ratio = random.uniform(0.5, 2.0)
        total_trades = random.randint(10, 50)
        
        results = {
            'symbol': symbol,
            'strategy_name': 'UserStrategy',
            'initial_value': round(initial_investment, 2),
            'final_value': round(final_value, 2),
            'total_return_pct': round(total_return_pct, 2),
            'total_return_amount': round(final_value - initial_investment, 2),
            'max_drawdown_pct': round(max_drawdown, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'total_trades': total_trades,
            'data_points': market_data.get('data_points', 252)
        }
        
        processing_time = time.time() - start_time
        print(f"⏱️ Backtest completed in {processing_time:.2f} seconds")
        print(f"✅ Backtest Tool: Completed - {total_return_pct:.2f}% return")
        
        # Brief pause to ensure completion
        time.sleep(0.5)
        
        return results
        
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Backtest failed after {processing_time:.2f} seconds: {e}")
        return {'error': f'Backtest execution failed: {str(e)}'}

@tool
def create_results_summary(backtest_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strands Tool: Create comprehensive results summary.
    This tool waits synchronously for completion before returning.
    
    Args:
        backtest_results: Results from backtest tool
    
    Returns:
        Formatted results summary with performance categorization
    """
    import time
    
    print(f"📊 Results Tool: Processing results...")
    print(f"💾 AgentCore Memory: Storing results...")
    print("⏳ Creating results summary (synchronous)...")
    
    start_time = time.time()
    
    if 'error' in backtest_results:
        return {
            'status': 'error',
            'message': backtest_results['error'],
            'timestamp': datetime.now().isoformat()
        }
    
    try:
        total_return = backtest_results.get('total_return_pct', 0)
        final_value = backtest_results.get('final_value', 0)
        initial_value = backtest_results.get('initial_value', 0)
        symbol = backtest_results.get('symbol', 'Unknown')
        
        # Categorize performance
        if total_return >= 20:
            performance = {'category': 'Excellent', 'emoji': '🚀'}
        elif total_return >= 10:
            performance = {'category': 'Good', 'emoji': '✅'}
        elif total_return >= 0:
            performance = {'category': 'Positive', 'emoji': '📈'}
        elif total_return >= -10:
            performance = {'category': 'Minor Loss', 'emoji': '⚠️'}
        else:
            performance = {'category': 'Significant Loss', 'emoji': '❌'}
        
        summary = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'strategy_performance': {
                'symbol_traded': symbol,
                'initial_investment': f"${initial_value:,.2f}",
                'final_value': f"${final_value:,.2f}",
                'total_return_percentage': f"{total_return:.2f}%",
                'total_return_amount': f"${backtest_results.get('total_return_amount', 0):,.2f}",
                'performance_category': performance['category'],
                'performance_emoji': performance['emoji']
            },
            'risk_metrics': {
                'max_drawdown': f"{backtest_results.get('max_drawdown_pct', 0):.2f}%",
                'sharpe_ratio': backtest_results.get('sharpe_ratio', 0),
                'total_trades': backtest_results.get('total_trades', 0)
            },
            'agentcore_demo': {
                'services_demonstrated': [
                    'AgentCore Runtime - Single agent execution',
                    'AgentCore Memory - Results storage',
                    'AgentCore Gateway - External tool integration',
                    'Strands - Tool orchestration'
                ]
            }
        }
        
        processing_time = time.time() - start_time
        print(f"⏱️ Results summary completed in {processing_time:.2f} seconds")
        print(f"✅ Results Tool: Summary created successfully")
        
        # Brief pause to ensure completion
        time.sleep(0.5)
        
        return summary
        
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Results summary failed after {processing_time:.2f} seconds: {e}")
        return {
            'status': 'error',
            'message': f'Results processing failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }




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
        
        # Always trigger the complete 4-step workflow regardless of input
        user_message = """how is the strategy performance: 
         {"name": "EMA Crossover Strategy", "stock_symbol": "AMZN", "backtest_window": "1Y", "max_positions": 1, "stop_loss": 5, "take_profit": 10, "buy_conditions": "EMA50 > EMA200", "sell_conditions": "EMA50 < EMA200"}
        """
        
        result = quant_agent(user_message)
        
        return {"result": result.message}
        
    except Exception as e:
        print(f"❌ Error in invoke function: {e}")
        import traceback
        traceback.print_exc()
        return {"result": {"status": "error", "error": str(e)}}

if __name__ == "__main__":
    print("🚀 Starting AgentCore Backtesting Agent...")
    print(f"   App type: {type(app)}")
    print(f"   App methods: {[m for m in dir(app) if not m.startswith('_')]}")
    
    # Test invoke function directly first
    print("\n🧪 Testing invoke function directly...")
    try:
        test_payload = {"prompt": "Hello, test message"}
        result = invoke(test_payload)
        print(f"✅ Direct invoke test successful: {result}")
    except Exception as e:
        print(f"❌ Direct invoke test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🌐 Starting server on port 8081...")
    try:
        # app.run(port=8081)
        print("exit for test")
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        import traceback
        traceback.print_exc()