"""
AgentCore Quant Backtesting Agent
Two strategy sources, one workflow:
- Plain strategy prompt (manual buy/sell conditions), or
- Research paper PDF: pypdf extracts text, an extractor agent derives the
  trading idea, then the same 4-step quant workflow runs:
  strategy generation -> market data -> backtest -> results summary
Also serves chat mode for analyzing historical backtests.
"""

import base64
import io
import json
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

# Idea extraction agent (lazy initialized)
_extractor_agent = None

# Cap paper text sent to the LLM (roughly 15k tokens)
MAX_PAPER_CHARS = 60000


def extract_pdf_text(pdf_base64: str) -> str:
    """Decode a base64 PDF and extract plain text with pypdf."""
    from pypdf import PdfReader

    pdf_bytes = base64.b64decode(pdf_base64)
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
    full_text = "\n\n".join(pages)
    print(f"📄 Extracted {len(full_text)} chars from {len(reader.pages)} PDF pages")
    return full_text[:MAX_PAPER_CHARS]


def extract_trading_idea(paper_text: str, stock_symbol: str, backtest_window: str,
                         max_positions: int, stop_loss: float, take_profit: float) -> dict:
    """Use the extractor agent to convert paper text into a strategy JSON config."""
    prompt = f"""Below is the text of a trading research paper. Extract the core trading strategy
and express it as a JSON strategy configuration.

User-specified parameters (use these exact values):
- stock_symbol: {stock_symbol}
- backtest_window: {backtest_window}
- max_positions: {max_positions}
- stop_loss: {stop_loss}
- take_profit: {take_profit}

PAPER TEXT:
{paper_text}
"""
    result = _extractor_agent(prompt)
    raw = str(result).strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    idea = json.loads(raw)

    # Enforce user-specified parameters over anything the LLM produced
    idea["stock_symbol"] = stock_symbol
    idea["backtest_window"] = backtest_window
    idea["max_positions"] = max_positions
    idea["stop_loss"] = stop_loss
    idea["take_profit"] = take_profit

    print(f"💡 Extracted trading idea: {json.dumps(idea, indent=2)}")
    return idea


def _ensure_initialized():
    """
    Lazy initialization of heavy resources.
    Called on first invoke() to defer expensive operations.
    """
    global _extractor_agent

    if config._initialized:
        return

    print("🔧 Initializing heavy resources (lazy init)...")

    # Initialize AWS clients and memory
    config.initialize_clients()

    # Create the Strands agents with BedrockModel
    from strands import Agent
    from strands.models.bedrock import BedrockModel

    _quant_model_id = os.getenv('QUANT_AGENT_MODEL_ID', 'us.anthropic.claude-sonnet-4-6')
    print(f"   Quant Agent Model ID: {_quant_model_id}")

    _quant_model = BedrockModel(
        model_id=_quant_model_id,
        region_name=config._region_name,
    )

    # Paper idea extractor: converts research paper text into a strategy JSON config
    _extractor_agent = Agent(
        name="PaperIdeaExtractor",
        model=_quant_model,
        system_prompt="""You are a quantitative research analyst. You read trading research papers
and extract the core trading strategy as a testable rule set.

Output ONLY a JSON object (no explanations, no markdown) with this exact schema:
{
    "name": "<short strategy name derived from the paper>",
    "paper_summary": "<2-3 sentence summary of the paper's trading idea>",
    "stock_symbol": "<user-specified symbol>",
    "backtest_window": "<user-specified window>",
    "max_positions": <user-specified>,
    "stop_loss": <user-specified>,
    "take_profit": <user-specified>,
    "buy_conditions": "<entry rules in plain English>",
    "sell_conditions": "<exit rules in plain English>"
}

Rules for buy_conditions / sell_conditions:
- Express them using indicators computable from daily OHLCV price data only:
  SMA, EMA, RSI, ROC, momentum, moving average crossovers, price breakouts, volume filters.
- If the paper uses data unavailable in daily OHLCV (fundamentals, sentiment, options),
  approximate the idea with the closest price/volume-based proxy and note it in paper_summary.
- Include concrete parameter values (periods, thresholds) from the paper; if the paper
  gives none, choose sensible defaults.
- Keep each condition under 300 characters."""
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


def _run_quant_workflow(prompt: str) -> dict:
    """Run the 4-step quant workflow and collect structured results."""
    # Reset before each run
    config._generated_strategy_code = None
    config._last_backtest_result = None

    result = config._quant_agent(prompt)

    # Use _last_backtest_result directly (set by run_backtest tool)
    trades = []
    trade_summary = {}
    if config._last_backtest_result:
        trades = config._last_backtest_result.get('trades', [])
        trade_summary = config._last_backtest_result.get('trade_summary', {})
        print(f"📊 Returning {len(trades)} trades from _last_backtest_result")
    else:
        print(f"⚠️ _last_backtest_result is None, falling back to Memory")
        latest = config.get_backtest_results_from_memory()
        if latest:
            trades = latest.get('trades', [])
            trade_summary = latest.get('trade_summary', {})
            print(f"📊 Returning {len(trades)} trades from Memory")

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


@app.entrypoint
def invoke(payload, context=None):
    """Main entrypoint for the paper backtesting agent.

    Paper mode payload:
    {
        "pdf_base64": "<base64-encoded PDF of a trading research paper>",
        "paper_name": "momentum.pdf",
        "stock_symbol": "AMZN",
        "backtest_window": "5Y",
        "max_positions": 1,
        "stop_loss": 5,
        "take_profit": 10
    }

    Also supports {"mode": "chat", "prompt": "..."} for historical analysis,
    and {"prompt": "..."} pass-through for plain strategy backtests (used by deploy smoke test).
    """
    try:
        _ensure_initialized()

        print(f"🚀 AgentCore Runtime: Quant Backtesting Agent processing request")

        if isinstance(payload, str):
            payload = json.loads(payload)

        mode = payload.get("mode", "backtest")

        if mode == "chat":
            print("💬 Chat mode: Using chat agent for historical analysis")
            result = config._chat_agent(payload.get("prompt"))
            return {"result": result.message}

        pdf_base64 = payload.get("pdf_base64")

        if not pdf_base64:
            # Pass-through: plain strategy prompt without a paper
            print("🔬 No PDF provided: running plain strategy prompt")
            return _run_quant_workflow(payload.get("prompt"))

        # Paper mode: parse PDF -> extract idea -> run standard workflow
        paper_name = payload.get("paper_name", "research paper")
        stock_symbol = payload.get("stock_symbol", "AMZN")
        backtest_window = payload.get("backtest_window", "1Y")
        max_positions = payload.get("max_positions", 1)
        stop_loss = payload.get("stop_loss", 5)
        take_profit = payload.get("take_profit", 10)

        print(f"📄 Paper mode: {paper_name} | symbol={stock_symbol} window={backtest_window}")

        paper_text = extract_pdf_text(pdf_base64)
        if not paper_text.strip():
            return {"result": {"status": "error",
                               "error": "Could not extract any text from the PDF (scanned image PDFs are not supported)"}}

        idea = extract_trading_idea(paper_text, stock_symbol, backtest_window,
                                    max_positions, stop_loss, take_profit)

        strategy_config = {k: v for k, v in idea.items() if k != "paper_summary"}
        prompt = f"how is the strategy performance: {json.dumps(strategy_config)}"

        response = _run_quant_workflow(prompt)
        response["extracted_strategy"] = idea
        return response

    except Exception as e:
        print(f"❌ Error in invoke function: {e}")
        import traceback
        traceback.print_exc()
        return {"result": {"status": "error", "error": str(e)}}


if __name__ == "__main__":
    print("🚀 Starting Quant Backtesting Agent on AgentCore")
    print("\n🌐 Starting server on port 8080...")
    try:
        app.run(port=8080)
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        import traceback
        traceback.print_exc()
