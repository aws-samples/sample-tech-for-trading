"""
MCP server entrypoint for the quant agent.

Exposes the backtesting capabilities as MCP tools so registry consumers
(e.g. Amazon Quick via AWS Agent Registry) can call them directly:

- get_backtest_history: fast query over past backtests (cross-session memory)
- run_manual_backtest: full 4-step workflow from plain-English buy/sell conditions
- run_paper_backtest: extract the trading idea from a research paper PDF
  (URL or base64) and backtest it

Deployed as its own AgentCore Runtime (protocol MCP) alongside the HTTP
runtime (quant_agent.py). All business logic is shared: initialization and
the PDF/extraction pipeline are delegated to the quant_agent module.

AgentCore MCP contract: stateless streamable-HTTP server on 0.0.0.0:8000
at path /mcp.
"""

import base64
import json

from mcp.server.fastmcp import FastMCP

import config
import quant_agent  # shared init, PDF parsing, idea extraction, workflow agent

mcp = FastMCP("paper-quant-backtest", host="0.0.0.0", port=8000, stateless_http=True)

MAX_PDF_BYTES = 15 * 1024 * 1024


def _run_workflow(strategy_config: dict) -> dict:
    """Drive the shared 4-step workflow agent and collect structured results."""
    config._generated_strategy_code = None
    config._last_backtest_result = None

    result = config._quant_agent(f"how is the strategy performance: {json.dumps(strategy_config)}")

    response = {
        "summary": str(result),
        "strategy_config": strategy_config,
    }
    if config._last_backtest_result and "error" not in config._last_backtest_result:
        r = config._last_backtest_result
        response["metrics"] = {
            "initial_value": r.get("initial_value"),
            "final_value": r.get("final_value"),
            "total_return": r.get("total_return"),
            **(r.get("metrics") or {}),
        }
        response["trade_summary"] = r.get("trade_summary", {})
    return response


@mcp.tool()
def get_backtest_history(symbol: str = "", limit: int = 10, query: str = "") -> str:
    """Retrieve historical backtest results across all past sessions.

    Returns full records: strategy config, trades, and performance metrics
    (total return, Sharpe ratio, max drawdown, win rate).

    Args:
        symbol: Optional stock symbol filter (e.g. AMZN). Empty = all symbols.
        limit: Maximum number of records to return (default 10).
        query: Optional natural-language query for semantic long-term memory
               search (e.g. "strategies with positive Sharpe ratio").
    """
    quant_agent._ensure_initialized()
    import importlib
    history_mod = importlib.import_module('tools.history')
    fn = getattr(history_mod.get_backtest_history, '__wrapped__', history_mod.get_backtest_history)
    result = fn(symbol=symbol or None, limit=limit, query=query or None)
    return json.dumps(result, default=str)


@mcp.tool()
def run_manual_backtest(
    buy_conditions: str,
    sell_conditions: str,
    stock_symbol: str = "AMZN",
    backtest_window: str = "1Y",
    max_positions: int = 1000,
    stop_loss: float = 10.0,
    take_profit: float = 30.0,
    strategy_name: str = "MCP Strategy",
) -> str:
    """Run a full trading-strategy backtest from plain-English buy/sell conditions.

    Executes the complete workflow: generate Backtrader code, fetch historical
    market data, run the backtest in a sandbox, and summarize results.
    Takes 1-2 minutes. Market data currently covers AMZN daily OHLCV.

    Args:
        buy_conditions: Entry rules in plain English, e.g. "RSI(14) below 30".
        sell_conditions: Exit rules in plain English, e.g. "RSI(14) above 70".
        stock_symbol: Ticker to backtest (currently AMZN has data).
        backtest_window: Lookback period: 1M, 3M, 6M, 1Y, 2Y, 5Y, 10Y, 20Y.
        max_positions: Max shares per position (drives position sizing).
        stop_loss: Stop loss percent.
        take_profit: Take profit percent.
        strategy_name: A short name for the strategy.
    """
    quant_agent._ensure_initialized()

    strategy_config = {
        "name": strategy_name,
        "stock_symbol": stock_symbol,
        "backtest_window": backtest_window,
        "max_positions": max_positions,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "buy_conditions": buy_conditions,
        "sell_conditions": sell_conditions,
    }
    return json.dumps(_run_workflow(strategy_config), default=str)


@mcp.tool()
def run_paper_backtest(
    pdf_url: str = "",
    pdf_base64: str = "",
    stock_symbol: str = "AMZN",
    backtest_window: str = "1Y",
    max_positions: int = 1000,
    stop_loss: float = 10.0,
    take_profit: float = 30.0,
) -> str:
    """Extract the trading strategy from a research paper (PDF) and backtest it.

    An AI analyst reads the paper, derives buy/sell rules expressed with daily
    OHLCV indicators (approximating ML/fundamental signals with price/volume
    proxies when needed), then runs the complete backtest workflow.
    Takes 2-3 minutes. Provide the paper either as a public URL or as base64.

    Args:
        pdf_url: Public URL of the paper PDF (e.g. an arXiv or S3 link).
                 Used if pdf_base64 is empty.
        pdf_base64: Base64-encoded PDF content. Takes precedence over pdf_url.
        stock_symbol: Ticker to backtest (currently AMZN has data).
        backtest_window: Lookback period: 1M, 3M, 6M, 1Y, 2Y, 5Y, 10Y, 20Y.
        max_positions: Max shares per position (drives position sizing).
        stop_loss: Stop loss percent.
        take_profit: Take profit percent.
    """
    quant_agent._ensure_initialized()

    if not pdf_base64 and not pdf_url:
        return json.dumps({"error": "Provide either pdf_url or pdf_base64"})

    if not pdf_base64:
        import urllib.request
        req = urllib.request.Request(pdf_url, headers={"User-Agent": "paper-quant-backtest/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            pdf_bytes = resp.read(MAX_PDF_BYTES + 1)
        if len(pdf_bytes) > MAX_PDF_BYTES:
            return json.dumps({"error": f"PDF exceeds {MAX_PDF_BYTES // (1024*1024)}MB limit"})
        if not pdf_bytes.startswith(b"%PDF"):
            return json.dumps({"error": "URL did not return a PDF document"})
        pdf_base64 = base64.b64encode(pdf_bytes).decode()

    # Shared pipeline from quant_agent: pypdf text extraction -> idea extraction
    paper_text = quant_agent.extract_pdf_text(pdf_base64)
    if not paper_text.strip():
        return json.dumps({"error": "Could not extract text from the PDF (scanned/image PDFs are not supported)"})

    idea = quant_agent.extract_trading_idea(
        paper_text, stock_symbol, backtest_window, max_positions, stop_loss, take_profit)

    strategy_config = {k: v for k, v in idea.items() if k != "paper_summary"}
    response = _run_workflow(strategy_config)
    response["extracted_strategy"] = idea
    return json.dumps(response, default=str)


if __name__ == "__main__":
    print("🚀 Starting Quant Backtest MCP server on 0.0.0.0:8000/mcp")
    mcp.run(transport="streamable-http")
