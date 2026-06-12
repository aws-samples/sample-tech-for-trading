"""Strategy Generator A2A Tool - Calls Strategy Generator via A2A Protocol (JSON-RPC 2.0).

Uses SigV4-signed HTTP POST to the AgentCore A2A endpoint, implementing the
open A2A standard for inter-agent communication.
"""

import json
import os
import time
import uuid
from urllib.parse import quote

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from strands import tool

import config


def _build_a2a_url(agent_arn: str, region: str) -> str:
    """Build the AgentCore A2A invocation URL from an agent ARN."""
    encoded_arn = quote(agent_arn, safe="")
    return f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations"


def _sigv4_sign_request(url: str, body: bytes, region: str, session_id: str) -> dict:
    """Sign an HTTP POST request with SigV4 for bedrock-agentcore service."""
    session = boto3.Session()
    credentials = session.get_credentials().get_frozen_credentials()

    headers = {
        "Content-Type": "application/json",
        "x-bedrock-agentcore-session-id": session_id,
    }

    aws_request = AWSRequest(
        method="POST",
        url=url,
        data=body,
        headers=headers,
    )

    SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(aws_request)
    return dict(aws_request.headers)


@tool
def generate_trading_strategy_a2a(query: str) -> str:
    """Generate executable trading strategy code using the A2A protocol.

    This tool calls the Strategy Generator A2A agent via the standardized
    Agent-to-Agent protocol (JSON-RPC 2.0) over SigV4-signed HTTP.

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
    agent_name = "STRATEGY GENERATOR (A2A Protocol)"
    print(f"\n{'='*50}")
    print(agent_name)
    print("="*50)

    print(f"INPUT: {query[:200]}...")
    print("Calling Strategy Generator via A2A protocol (JSON-RPC 2.0)...")

    start_time = time.time()

    try:
        agent_arn = os.getenv("STRATEGY_GENERATOR_A2A_ARN")
        region = os.getenv("AWS_REGION", "us-east-1")

        if not agent_arn:
            raise ValueError("STRATEGY_GENERATOR_A2A_ARN not set")

        a2a_url = _build_a2a_url(agent_arn, region)
        print(f"A2A URL: {a2a_url[:80]}...")

        # Construct the A2A JSON-RPC 2.0 request (message/send per A2A v0.3 spec)
        session_id = str(uuid.uuid4())
        a2a_request = {
            "jsonrpc": "2.0",
            "id": f"strategy-{int(time.time())}",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "messageId": str(uuid.uuid4()),
                    "parts": [
                        {
                            "type": "text",
                            "text": query if isinstance(query, str) else json.dumps(query)
                        }
                    ]
                }
            }
        }

        body = json.dumps(a2a_request).encode("utf-8")

        # Sign the request with SigV4
        signed_headers = _sigv4_sign_request(a2a_url, body, region, session_id)
        print("Sending SigV4-signed A2A request (method: message/send)...")

        # Send the HTTP POST request
        response = requests.post(
            a2a_url,
            data=body,
            headers=signed_headers,
            timeout=180,
        )
        response.raise_for_status()

        # Parse the A2A JSON-RPC 2.0 response
        a2a_response = response.json()
        processing_time = time.time() - start_time
        print(f"A2A call completed in {processing_time:.2f}s")

        # Extract strategy code from response
        strategy_code = _extract_strategy_from_response(a2a_response)

        if not strategy_code or len(strategy_code.strip()) < 50:
            print("A2A response returned insufficient content")
            return "Error: Strategy generation via A2A failed - insufficient content"

        print("Strategy generation via A2A completed successfully")
        print("="*50)

        config._generated_strategy_code = strategy_code
        return strategy_code

    except Exception as e:
        processing_time = time.time() - start_time
        print(f"A2A strategy generation failed after {processing_time:.2f}s: {e}")
        print("="*50)
        raise


def _extract_strategy_from_response(a2a_response: dict) -> str:
    """Extract strategy code from A2A JSON-RPC 2.0 response."""
    if "error" in a2a_response:
        error = a2a_response["error"]
        raise Exception(f"A2A error {error.get('code')}: {error.get('message')}")

    if "result" not in a2a_response:
        return str(a2a_response)

    result = a2a_response["result"]

    # Try artifacts first (A2A compliant streaming response)
    artifacts = result.get("artifacts", [])
    if artifacts:
        parts = artifacts[0].get("parts", [])
        if parts:
            return "".join(p.get("text", "") for p in parts)

    # Try history messages (streaming response concatenation)
    history = result.get("history", [])
    if history:
        code_parts = []
        for msg in history:
            if msg.get("role") == "agent":
                for part in msg.get("parts", []):
                    text = part.get("text", "")
                    if text:
                        code_parts.append(text)
        if code_parts:
            return "".join(code_parts)

    return str(result)
