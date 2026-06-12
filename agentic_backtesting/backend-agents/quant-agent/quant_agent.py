"""
AgentCore Interactive Backtesting Agent
Demonstrates "Agent as Tool" patterns with AgentCore Gateway integration
Single agent with Strands tools for strategy generation, backtesting, and results
"""

import os
from bedrock_agentcore import BedrockAgentCoreApp
import config
from tools import (
    fetch_market_data_via_gateway,
    generate_trading_strategy,
    run_backtest,
    create_results_summary,
    get_backtest_history
)

# Initialize the AgentCore app (lightweight)
app = BedrockAgentCoreApp()


def _ensure_initialized():
    """
    Lazy initialization of heavy resources.
    Called on first invoke() to defer expensive operations.
    """
    if config._initialized:
        return

    print("🔧 Initializing heavy resources (lazy init)...")

    # Initialize AWS clients and memory
    config.initialize_clients()

    # Create the Strands agent with BedrockModel
    from strands import Agent
    from strands.models.bedrock import BedrockModel

    _quant_model_id = os.getenv('QUANT_AGENT_MODEL_ID', 'us.anthropic.claude-sonnet-4-6')
    print(f"   Quant Agent Model ID: {_quant_model_id}")

    _quant_model = BedrockModel(
        model_id=_quant_model_id,
        region_name=config._region_name,
    )

    config._quant_agent = Agent(
        model=_quant_model,
        system_prompt="""You are the Quant Backtesting Agent. When you receive ANY request, you MUST automatically execute ALL 4 steps in this EXACT sequence:

STEP 1: ALWAYS call generate_trading_strategy first
- Use the user's request to create a JSON strategy format
- If no specific strategy is provided, create a default EMA crossover strategy for AMZN
- Pass the JSON strategy to generate_trading_strategy tool

STEP 2: ALWAYS call fetch_market_data_via_gateway
- Use the symbol from the strategy (default to AMZN if not specified)
- IMPORTANT: Parse the backtest_window field (e.g. "10Y", "5Y", "1Y", "6M", "3M", "1M") and convert it to start_date and end_date:
  - end_date = today's date in YYYY-MM-DD format
  - start_date = end_date minus the backtest_window duration (e.g. "10Y" means 10 years ago, "6M" means 6 months ago)
  - Set limit to the approximate number of trading days: 1M=21, 3M=63, 6M=126, 1Y=252, 2Y=504, 5Y=1260, 10Y=2520, 20Y=5040
- Call fetch_market_data_via_gateway with symbol, start_date, end_date, and limit

STEP 3: ALWAYS call run_backtest
- Use the strategy code from Step 1 and market data from Step 2
- Use initial investment of $10,000 if not specified
- Call run_backtest with all required parameters

STEP 4: ALWAYS call create_results_summary
- Use the backtest results from Step 3
- Call create_results_summary to format the final results
- Output the JSON from create_results_summary direct to users

CRITICAL RULES:
- Execute ALL 4 steps in sequence for EVERY request
- WAIT for each tool to complete before calling the next tool
- Do NOT call multiple tools simultaneously
- Do NOT ask for clarification - proceed with defaults AMZN 1-year if information is missing
- Do NOT explain what you're going to do - just DO all 4 steps
- Complete the entire workflow automatically and synchronously
- Output the JSON output directly from create_results_summary to users """,
        tools=[
            fetch_market_data_via_gateway,
            generate_trading_strategy,
            run_backtest,
            create_results_summary,
            get_backtest_history
        ]
    )

    # Create chat mode agent for analyzing historical backtests
    config._chat_agent = Agent(
        model=_quant_model,
        system_prompt="""You are the Quant Research Assistant. You help quants analyze their historical backtesting results and suggest strategy improvements.

You have access to the get_backtest_history tool which retrieves past backtest records including:
- Strategy description (plain English)
- Generated strategy code (Backtrader Python code)
- Trade records (entry/exit dates, prices, P&L)
- Performance metrics (Sharpe ratio, max drawdown, total return, win rate)

When users ask about their strategies:
1. Use get_backtest_history to retrieve relevant historical runs
2. Analyze patterns across multiple backtests
3. Identify strengths and weaknesses (focus on risk-adjusted returns, drawdowns, consistency)
4. Suggest specific improvements with rationale (e.g., parameter adjustments, risk management, position sizing)
5. Compare performance across different strategies/parameters when applicable

Be quantitative in your analysis. Reference specific metrics and trades. When suggesting improvements, explain the expected impact on risk-adjusted returns.

If no historical data is found, inform the user that no backtest history exists yet and suggest running a backtest first.

Always be concise but thorough. Prioritize actionable insights over generic advice.""",
        tools=[get_backtest_history]
    )

    print("✅ Lazy initialization complete")


@app.entrypoint
def invoke(payload, context=None):
    """Main entrypoint for the backtesting agent"""
    try:
        # Lazy initialization on first call
        _ensure_initialized()

        print(f"🚀 AgentCore Runtime: Backtesting Agent processing request")
        print(f"📥 Payload received: {payload}")

        # Parse payload if it's a string
        if isinstance(payload, str):
            import json
            payload = json.loads(payload)

        # Check if this is a chat mode request
        mode = payload.get("mode", "backtest")

        if mode == "chat":
            print("💬 Chat mode: Using chat agent for historical analysis")
            result = config._chat_agent(payload.get("prompt"))
            return {
                "result": result.message
            }

        # Default: backtest execution mode
        print("🔬 Backtest mode: Using quant agent for 4-step backtest execution")

        # Reset before each run
        config._generated_strategy_code = None
        config._last_backtest_result = None

        result = config._quant_agent(payload.get("prompt"))

        # Use _last_backtest_result directly (set by run_backtest tool)
        # This is more reliable than reading from Memory which may return stale data
        trades = []
        trade_summary = {}
        if config._last_backtest_result:
            trades = config._last_backtest_result.get('trades', [])
            trade_summary = config._last_backtest_result.get('trade_summary', {})
            print(f"📊 invoke() returning {len(trades)} trades from _last_backtest_result")
        else:
            print(f"⚠️ invoke() _last_backtest_result is None, falling back to Memory")
            latest = config.get_backtest_results_from_memory()
            if latest:
                trades = latest.get('trades', [])
                trade_summary = latest.get('trade_summary', {})
                print(f"📊 invoke() returning {len(trades)} trades from Memory")

        # Build backtest_metrics from _last_backtest_result for frontend
        backtest_metrics = None
        if config._last_backtest_result and "error" not in config._last_backtest_result:
            backtest_metrics = {
                "initial_value": config._last_backtest_result.get("initial_value"),
                "final_value": config._last_backtest_result.get("final_value"),
                "total_return": config._last_backtest_result.get("total_return"),
                "metrics": config._last_backtest_result.get("metrics", {}),
            }
            print(f"backtest_metrics: {backtest_metrics}")

        return {
            "result": result.message,
            "strategy_code": config._generated_strategy_code,
            "trades": trades,
            "trade_summary": trade_summary,
            "backtest_metrics": backtest_metrics,
            "versions": {
                "quant_agent": config.VERSION,
                "strategy_generator": config._strategy_generator_version,
                "results_summary": config._results_summary_version
            }
        }

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
