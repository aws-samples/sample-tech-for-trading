"""
Configuration and Initialization for Quant Backtesting Agent
Handles environment setup, AWS clients, and memory management
"""

import os
import json
from datetime import datetime
from typing import Dict, Any

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Version tracking for troubleshooting
VERSION = os.getenv('AGENT_VERSION', datetime.now().strftime('%Y%m%d_%H%M%S'))

# Verify environment variables are loaded
print("🔧 Environment Variables Loaded:")
print(f"   Version: {VERSION}")
print(f"   AGENTCORE_GATEWAY_URL: {os.getenv('AGENTCORE_GATEWAY_URL', 'Not set')}")
print(f"   STRATEGY_GENERATOR_RUNTIME_ARN: {os.getenv('STRATEGY_GENERATOR_RUNTIME_ARN', 'Not set')}")
print(f"   COGNITO_DOMAIN: {os.getenv('COGNITO_DOMAIN', 'Not set')}")
print(f"   COGNITO_CLIENT_ID: {os.getenv('COGNITO_CLIENT_ID', 'Not set')}")
print(f"   AWS_REGION: {os.getenv('AWS_REGION', 'us-east-1')}")

# Lazy initialization globals
_initialized = False
_agentcore_runtime_client = None
_memory_client = None
_memory_id = None
_session_id = None
_quant_agent = None
_region_name = None
_generated_strategy_code = None
_last_backtest_result = None  # Store last backtest result directly (trades, trade_summary)
_stored_market_data = {}
_actor_id = "Quant"
_strategy_generator_version = "unknown"  # Track strategy generator version
_results_summary_version = "unknown"  # Track results summary version


def get_memory_id_by_name(name_prefix: str = "quant_agent") -> str:
    """
    Retrieve AgentCore Memory ID by searching for memory with name starting with prefix.

    Args:
        name_prefix: The prefix to search for in memory names (default: "quant_agent")

    Returns:
        Memory ID string, or creates a new memory if not found
    """
    import boto3
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


def save_backtest_results_to_memory_sync(results: Dict[str, Any], strategy_code: str = None):
    """Save backtest results (with trades and strategy code) to AgentCore Memory"""
    global _memory_client, _memory_id, _session_id
    try:
        symbol = results.get('symbol', 'UNKNOWN')
        print(f"💾 Saving backtest results for {symbol} to AgentCore Memory...")

        # Build comprehensive record
        memory_record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'performance': {
                'initial_value': results.get('initial_value'),
                'final_value': results.get('final_value'),
                'total_return': results.get('total_return'),
                'metrics': results.get('metrics', {}),
                'strategy_class': results.get('strategy_class')
            },
            'trade_summary': results.get('trade_summary', {}),
            'trades': results.get('trades', []),
            'strategy_code': strategy_code
        }

        results_message = f"Backtest result: {json.dumps(memory_record)}"

        # Create event using memory_client.create_event
        event = _memory_client.create_event(
            memory_id=_memory_id,
            actor_id=_actor_id,
            session_id=_session_id,
            messages=[(results_message, "ASSISTANT")]
        )

        print(f"✅ Backtest results saved to AgentCore Memory (trades: {len(memory_record['trades'])}, strategy_code: {'yes' if strategy_code else 'no'})")

    except Exception as e:
        print(f"❌ Failed to save backtest results to AgentCore Memory: {e}")
        import traceback
        traceback.print_exc()


def get_backtest_results_from_memory(symbol: str = None) -> Dict[str, Any]:
    """Retrieve backtest results from AgentCore Memory using list_events"""
    global _memory_client, _memory_id, _session_id
    try:
        # List events using memory_client
        events = _memory_client.list_events(
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


def initialize_clients():
    """
    Initialize AWS clients and AgentCore Memory.
    Called by _ensure_initialized() in main agent file.
    """
    global _initialized, _agentcore_runtime_client, _memory_client, _memory_id, _session_id, _region_name

    if _initialized:
        return

    print("🔧 Initializing AWS clients and memory...")

    # Import heavy modules needed for initialization
    import boto3
    from bedrock_agentcore.memory import MemoryClient

    # Set region
    _region_name = os.getenv('AWS_REGION', 'us-east-1')

    # Create boto3 clients
    _agentcore_runtime_client = boto3.client('bedrock-agentcore', region_name=_region_name)

    # Create memory client
    _memory_client = MemoryClient(region_name=_region_name)

    # Get memory ID (makes API call)
    _memory_id = get_memory_id_by_name("quant_agent")

    # Generate session ID
    _session_id = f"quant_session_{datetime.now().strftime('%Y%m%d')}"
    print(f"🔑 Session ID: {_session_id}")

    _initialized = True
    print("✅ AWS clients and memory initialized")
