"""Strategy Generator A2A Agent - Serves via Agent-to-Agent (A2A) Protocol.

Uses serve_a2a from bedrock_agentcore.runtime for A2A JSON-RPC 2.0 support.
The agent publishes an Agent Card and handles message/send requests.
"""

import os

from strands import Agent
from strands.models import BedrockModel
from strands.multiagent.a2a import StrandsA2AExecutor
from bedrock_agentcore.runtime import serve_a2a
from dotenv import load_dotenv

load_dotenv()


def create_agent() -> Agent:
    """Create the Strategy Generator agent."""
    instructions = """You are a Python code generator specializing in Backtrader trading strategies.

Given a JSON configuration with trading parameters (stock symbol, buy/sell conditions,
stop loss, take profit), generate a complete, executable Backtrader strategy class.

Rules:
1. Generate clean, efficient Backtrader strategy code
2. Implement buy and sell conditions from JSON input
3. Use proper Backtrader indicators (EMA, SMA, RSI, ROC, MACD, Bollinger Bands)
4. Handle stop loss and take profit parameters
5. Include proper position management
6. Always return complete, runnable Python code - no explanations
7. Class name should be derived from the strategy name field
"""

    aws_region = os.getenv("AWS_REGION", "us-east-1")
    model_id = os.getenv("STRATEGY_GENERATOR_MODEL_ID", "us.anthropic.claude-sonnet-4-6")

    print(f"Strategy Generator A2A Configuration:")
    print(f"   Model ID: {model_id}")
    print(f"   Region: {aws_region}")
    print(f"   Protocol: A2A (JSON-RPC 2.0)")

    strategy_model = BedrockModel(
        model_id=model_id,
        region_name=aws_region,
    )

    return Agent(
        name="StrategyGeneratorA2A",
        description="Converts natural language trading strategy descriptions into executable Backtrader Python code. Accepts JSON strategy configurations and returns complete, runnable strategy classes.",
        model=strategy_model,
        system_prompt=instructions,
    )


if __name__ == "__main__":
    print("Starting Strategy Generator A2A Agent (JSON-RPC 2.0 protocol)...")
    agent = create_agent()
    executor = StrandsA2AExecutor(agent, enable_a2a_compliant_streaming=True)
    serve_a2a(executor, port=9000, access_log=True, log_level="debug")
