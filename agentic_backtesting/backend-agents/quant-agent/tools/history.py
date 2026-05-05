"""
Backtest History Tool
Retrieves historical backtest results from AgentCore Memory
"""

import json
from strands import tool
import config


@tool
def get_backtest_history(symbol: str = None, limit: int = 10) -> dict:
    """
    Retrieve historical backtest results from AgentCore Memory.
    Returns trades, strategy code, and performance metrics for past backtests.

    Args:
        symbol: Optional stock symbol to filter by (e.g., AMZN, AAPL)
        limit: Maximum number of records to return (default: 10)

    Returns:
        List of historical backtest records with trades and performance data
    """
    try:
        print(f"📖 Retrieving backtest history from AgentCore Memory (symbol={symbol}, limit={limit})...")

        events = config._memory_client.list_events(
            memory_id=config._memory_id,
            actor_id=config._actor_id,
            session_id=config._session_id
        )

        # Handle both list and dict response formats
        if isinstance(events, dict):
            events_list = events.get('events', [])
        elif isinstance(events, list):
            events_list = events
        else:
            events_list = []

        records = []
        for event in reversed(events_list):  # Most recent first
            try:
                messages = event.get('messages', [])
                for msg in messages:
                    content = msg.get('content', '') if isinstance(msg, dict) else str(msg)
                    if 'Backtest result:' in content:
                        json_part = content.split('Backtest result:', 1)[1].strip()
                        record = json.loads(json_part)

                        # Filter by symbol if specified
                        if symbol and record.get('symbol', '').upper() != symbol.upper():
                            continue

                        records.append(record)
                        if len(records) >= limit:
                            break
            except Exception as e:
                print(f"⚠️ Error parsing event: {e}")
                continue
            if len(records) >= limit:
                break

        print(f"✅ Found {len(records)} backtest records in AgentCore Memory")
        return {'records': records, 'count': len(records)}

    except Exception as e:
        print(f"❌ Failed to retrieve backtest history: {e}")
        import traceback
        traceback.print_exc()
        return {'records': [], 'count': 0, 'error': str(e)}
