"""
Backtest History Tool
Retrieves historical backtest results from AgentCore Memory.

Two complementary paths:
1. Long-term memory (semantic): retrieve_memories() over the /backtests namespace —
   cross-session, natural-language queries, powered by the SEMANTIC strategy on the
   memory resource.
2. Raw events (short-term): list_events() across ALL sessions of the actor — returns
   the full structured records (all input parameters, trades, performance metrics).
"""

import json
from strands import tool
import config


def _extract_text(msg) -> str:
    """Pull plain text out of the various event message shapes."""
    if isinstance(msg, str):
        return msg
    if isinstance(msg, dict):
        conv = msg.get('conversational', {})
        if conv:
            content = conv.get('content', {})
            return content.get('text', '') if isinstance(content, dict) else str(content)
        content = msg.get('content', msg.get('text', ''))
        return content.get('text', str(content)) if isinstance(content, dict) else str(content)
    return str(msg)


def _parse_backtest_records(events_list, symbol=None, limit=10):
    """Extract structured 'Backtest result:' records from memory events."""
    records = []
    for event in reversed(events_list):  # Most recent first
        try:
            messages = event.get('payload', event.get('messages', []))
            for msg in messages:
                content = _extract_text(msg)
                if 'Backtest result:' in content:
                    json_part = content.split('Backtest result:', 1)[1].strip()
                    record = json.loads(json_part)
                    if symbol and record.get('symbol', '').upper() != symbol.upper():
                        continue
                    records.append(record)
                    if len(records) >= limit:
                        return records
        except Exception as e:
            print(f"⚠️ Error parsing event: {e}")
            continue
    return records


@tool
def get_backtest_history(symbol: str = None, limit: int = 10, query: str = None) -> dict:
    """
    Retrieve historical backtest results from AgentCore Memory across ALL past
    sessions. Returns full records: strategy config, generated code, trades, and
    performance metrics (total return, Sharpe, drawdown, win rate).

    Args:
        symbol: Optional stock symbol to filter by (e.g., AMZN, AAPL)
        limit: Maximum number of records to return (default: 10)
        query: Optional natural-language query for semantic long-term memory search
               (e.g. "strategies with positive Sharpe ratio")

    Returns:
        Historical backtest records plus any semantic long-term memories matched
    """
    result = {'records': [], 'count': 0, 'semantic_memories': []}

    # --- Path 1: semantic long-term memory (cross-session by design) ---
    if query:
        try:
            namespace = f"/backtests/{config._actor_id}"
            memories = config._memory_client.retrieve_memories(
                memory_id=config._memory_id,
                namespace=namespace,
                query=query,
                top_k=min(limit, 10)
            )
            for m in (memories or []):
                content = m.get('content', {})
                text = content.get('text', str(content)) if isinstance(content, dict) else str(content)
                result['semantic_memories'].append(text)
            print(f"🧠 Semantic LTM returned {len(result['semantic_memories'])} memories for query: {query!r}")
        except Exception as e:
            print(f"⚠️ Semantic retrieval failed (strategy may still be indexing): {e}")

    # --- Path 2: raw events across ALL sessions of this actor ---
    try:
        print(f"📖 Listing sessions for actor '{config._actor_id}'...")
        sessions_resp = config._memory_client.list_sessions(
            memory_id=config._memory_id,
            actor_id=config._actor_id
        )
        if isinstance(sessions_resp, dict):
            sessions = sessions_resp.get('sessionSummaries', sessions_resp.get('sessions', []))
        else:
            sessions = sessions_resp or []

        session_ids = []
        for s in sessions:
            sid = s.get('sessionId') if isinstance(s, dict) else str(s)
            if sid:
                session_ids.append(sid)
        # Fall back to the current session if listing yields nothing
        if not session_ids:
            session_ids = [config._session_id]

        print(f"📖 Scanning {len(session_ids)} session(s) for backtest records...")
        records = []
        # Newest sessions first (ids are date-based: quant_session_YYYYMMDD)
        for sid in sorted(session_ids, reverse=True):
            events = config._memory_client.list_events(
                memory_id=config._memory_id,
                actor_id=config._actor_id,
                session_id=sid
            )
            events_list = events.get('events', []) if isinstance(events, dict) else (events or [])
            records.extend(_parse_backtest_records(events_list, symbol=symbol,
                                                   limit=limit - len(records)))
            if len(records) >= limit:
                break

        result['records'] = records
        result['count'] = len(records)
        print(f"✅ Found {len(records)} backtest records across sessions")

    except Exception as e:
        print(f"❌ Failed to retrieve backtest history: {e}")
        import traceback
        traceback.print_exc()
        result['error'] = str(e)

    return result
