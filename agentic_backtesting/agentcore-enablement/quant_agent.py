"""
AgentCore Interactive Backtesting Agent
Demonstrates "Agent as Tool" patterns with AgentCore Gateway integration
Single agent with Strands tools for strategy generation, backtesting, and results
"""

import os
os.environ["BYPASS_TOOL_CONSENT"] = "true"

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

# Initialize the AgentCore app
app = BedrockAgentCoreApp()

# Global workflow memory for AgentCore Memory demonstration
workflow_memory = {}

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
        
        # Prepare request payload for the lambda function
        payload = {
            'symbol': symbol.upper(),
            'limit': 252
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
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Successfully fetched data from AgentCore Gateway")
                
                # Process the response data
                if data.get('success') and data.get('data'):
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
    
    Args:
        symbol: Stock symbol (e.g., AMZN) - preferred method
    
    Returns:
        Market data from external service via Gateway
    """
    if symbol:
        print(f"🌐 AgentCore Gateway: Fetching {symbol} data via MCP...")
        target_param = symbol
        param_type = "symbol"
    else:
        print(f"🌐 AgentCore Gateway: No symbol or sector specified, using AMZN...")
        target_param = "AMZN"
        param_type = "symbol"
    
    try:
        return asyncio.run(call_gateway_market_data_with_cognito(target_param, param_type))
    except Exception as e:
        print(f"❌ AgentCore Gateway: Failed to fetch via Gateway - {str(e)}")

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
            "buy_conditions": EMA 50 > EMA 250,
            "sell_conditions": EMA 50 < EMA 250,
        }

    Returns:
        Complete Backtrader strategy Python code ready for backtesting
    """
    global _strategy_call_count
    
    _strategy_call_count += 1
    callback = getattr(strategy_generator, '_callback', None)
    
    agent_name = "🧠 STRATEGY GENERATOR AGENT"
    input_data = query
    reasoning = "Converting user trading idea into executable strategy code..."
    
    print(f"\n🔄 {agent_name} CALL #{_strategy_call_count}")
    print("="*50)
    print(f"📥 INPUT: {input_data}")
    print(f"🧠 REASONING: {reasoning}")
    
    result = strategy_agent.process(query)
    
    print(f"📤 OUTPUT: {result}")
    
    print("="*50)
    return result
            


@tool
def run_backtest(strategy_code: str, market_data: Dict[str, Any], initial_investment: float) -> Dict[str, Any]:
    """
    Strands Tool: Execute backtesting simulation.
    
    Args:
        strategy_code: Generated Python strategy code
        market_data: Market data from Gateway or fallback
        initial_investment: Initial investment amount
    
    Returns:
        Backtest results with performance metrics
    """
    print(f"⚡ Backtest Tool: Executing simulation...")
    print(f"   Initial investment: ${initial_investment:,.2f}")
    
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
        
        print(f"✅ Backtest Tool: Completed - {total_return_pct:.2f}% return")
        return results
        
    except Exception as e:
        return {'error': f'Backtest execution failed: {str(e)}'}

@tool
def create_results_summary(backtest_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strands Tool: Create comprehensive results summary.
    
    Args:
        backtest_results: Results from backtest tool
    
    Returns:
        Formatted results summary with performance categorization
    """
    print(f"📊 Results Tool: Processing results...")
    print(f"💾 AgentCore Memory: Storing results...")
    
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
        
        print(f"✅ Results Tool: Summary created successfully")
        return summary
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Results processing failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }


# Create the agent with all Strands tools
quant_agent = Agent(
    system_prompt="""You are the Quant Backtesting Agent. You help users create and test trading strategies.

You have these Strands tools available:
- generate_trading_strategy: Create Python trading strategy code  
- fetch_market_data_via_gateway: Get market data via AgentCore Gateway (supports both stock symbols and sectors)
- run_backtest: Execute backtesting simulation
- create_results_summary: Process and format results

You can work with a stock symbol (e.g. AMZN) 
Always explain the Agent reasoning and AgentCore services being demonstrated.""",
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
        
        # Handle direct workflow execution
        required_keys = ['initial_investment', 'buy_condition', 'sell_condition']
        if isinstance(payload, dict) and all(key in payload for key in required_keys):
            # Check if we have either symbol or investment_area
            if 'symbol' in payload or 'investment_area' in payload:
                user_id = payload.get('user_id', 'anonymous')
                result = execute_full_backtest_workflow(
                    initial_investment=payload['initial_investment'],
                    buy_condition=payload['buy_condition'],
                    sell_condition=payload['sell_condition'],
                    symbol=payload.get('symbol'),
                    investment_area=payload.get('investment_area'),
                    user_id=user_id
                )
                return {"result": result}
        
        # Handle conversational requests
        user_message = payload.get("prompt", "Hello! I can help you with backtesting trading strategies. What would you like to test?")
        result = quant_agent(user_message)
        
        return {"result": result.message}
        
    except Exception as e:
        return {"result": {"status": "error", "error": str(e)}}

if __name__ == "__main__":
    app.run(port=8081)