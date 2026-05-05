"""
Backtest Execution Tool (Code Interpreter Sandbox Version)
Runs trading strategy backtests in AgentCore Code Interpreter instead of local exec().

Key difference from backtest_tool.py:
- Uses CodeInterpreter writeFiles to upload backtest.py (reused as-is) and market data
- Market data from config._stored_market_data is serialized to CSV file
- Backtrader package is zipped and uploaded (sandbox has no network)
- A runner.py script orchestrates the backtest inside the sandbox
- Maximizes code reuse: backtest.py BacktestTool.process() runs unchanged in sandbox
"""

import os
import time
import json
import zipfile
import base64
import io
import pandas as pd
from strands import tool
import config


def _consume_ci_stream(response):
    """Consume CodeInterpreter EventStream and extract stdout/stderr."""
    stdout = ""
    stderr = ""
    error = None
    stream = response.get("stream")
    if stream:
        for event in stream:
            result = event.get("result", {})
            sc = result.get("structuredContent", {})
            if sc.get("stdout"):
                stdout += sc["stdout"]
            if sc.get("stderr"):
                stderr += sc["stderr"]
            if result.get("isError"):
                content = result.get("content", [])
                error = content[0].get("text", "") if content else "Unknown error"
    return {"stdout": stdout, "stderr": stderr, "error": error}


def _zip_backtrader_package():
    """Zip the backtrader package into a base64 string for sandbox upload."""
    import backtrader
    bt_path = os.path.dirname(backtrader.__file__)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(bt_path):
            for f in files:
                if f.endswith(".py"):
                    full = os.path.join(root, f)
                    arcname = os.path.relpath(full, os.path.dirname(bt_path))
                    zf.write(full, arcname)
    return base64.b64encode(buf.getvalue()).decode("ascii")


@tool
def run_backtest(symbol: str, strategy_code: str, params: dict = None) -> dict:
    """
    Execute trading strategy backtest in AgentCore Code Interpreter sandbox.
    Uploads backtest.py, backtrader package, and market data as files,
    then runs a lightweight runner script.

    Args:
        symbol: the strategy equity code, default AMZN
        strategy_code: Complete Backtrader strategy code from strategy_generator
        params: Optional backtest parameters (cash, commission, etc.)

    Returns:
        Comprehensive backtest results with performance metrics and statistics
    """
    from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter

    print("\n" + "=" * 50)
    print("⚡ BACKTEST (Code Interpreter Sandbox)")
    print("=" * 50)

    # Validate strategy code
    if not strategy_code or len(strategy_code.strip()) < 100:
        return {"error": "Invalid or empty strategy code"}

    # Check if market data is available in agent memory
    if config._stored_market_data is None or not config._stored_market_data:
        return {"error": "No market data found in global storage"}

    symbol_key = symbol
    if symbol_key not in config._stored_market_data:
        return {"error": f"No market data for symbol: {symbol_key}"}

    symbol_data = config._stored_market_data[symbol_key]
    daily_data = symbol_data.get("daily_data", [])

    if not daily_data:
        return {"error": "No market data available for backtesting"}

    # --- Serialize market data to CSV (the sandbox cannot access config) ---
    df = pd.DataFrame(daily_data)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)

    numeric_columns = ["open", "high", "low", "close", "volume", "adj_close"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    market_data_csv = df.to_csv()
    print(f"📊 Serialized {len(df)} rows of market data for {symbol_key} to CSV ({len(market_data_csv)} bytes)")

    # --- Zip backtrader package (sandbox has no network access) ---
    print("📦 Zipping backtrader package for sandbox upload...")
    bt_zip_b64 = _zip_backtrader_package()
    print(f"📦 Backtrader zip: {len(bt_zip_b64)} chars (base64)")

    # --- Read backtest.py source code (reuse existing logic as-is) ---
    backtest_module_path = os.path.join(os.path.dirname(__file__), "backtest.py")
    with open(backtest_module_path, "r", encoding="utf-8") as f:
        backtest_py_source = f.read()

    # --- Build parameters ---
    initial_cash = (params or {}).get("initial_cash", 100000)
    commission = (params or {}).get("commission", 0.001)

    # --- Compose the runner script ---
    runner_script = f'''import base64, zipfile, io, sys
import pandas as pd
import json

# Unzip backtrader package (no network in sandbox)
with open("backtrader_b64.txt", "r") as f:
    bt_zip = base64.b64decode(f.read())
zipfile.ZipFile(io.BytesIO(bt_zip)).extractall(".")
sys.path.insert(0, ".")

from backtest import BacktestTool

df = pd.read_csv("market_data.csv", index_col=0, parse_dates=True)
strategy_code = open("strategy.py", "r", encoding="utf-8").read()

tool = BacktestTool()
result = tool.process({{
    "strategy_code": strategy_code,
    "market_data": {{"{symbol_key}": df}},
    "params": {{"initial_cash": {initial_cash}, "commission": {commission}}}
}})

print(json.dumps(result, default=str))
'''

    # --- Upload files and execute in Code Interpreter sandbox ---
    print("🚀 Sending to Code Interpreter sandbox...")
    start_time = time.time()

    try:
        region = os.getenv("AWS_REGION", "us-east-1")
        ci = CodeInterpreter(region)
        ci.start()

        # Write files into the sandbox
        files = [
            {"path": "backtrader_b64.txt", "text": bt_zip_b64},
            {"path": "backtest.py", "text": backtest_py_source},
            {"path": "market_data.csv", "text": market_data_csv},
            {"path": "strategy.py", "text": strategy_code},
            {"path": "runner.py", "text": runner_script},
        ]
        ci.invoke("writeFiles", {"content": files})
        print(f"📁 Uploaded {len(files)} files to sandbox")

        # Execute the runner script
        exec_resp = ci.invoke("executeCode", {
            "language": "python",
            "clearContext": True,
            "code": 'exec(open("runner.py", "r", encoding="utf-8").read())'
        })
        execution_result = _consume_ci_stream(exec_resp)

        ci.stop()

        processing_time = time.time() - start_time
        print(f"⏱️ Sandbox execution completed in {processing_time:.2f}s")

        stdout = execution_result.get("stdout", "")
        stderr = execution_result.get("stderr", "")

        if stderr:
            print(f"⚠️ Sandbox stderr: {stderr[:500]}")

        if execution_result.get("error"):
            return {
                "error": f"Sandbox execution error: {execution_result['error']}",
                "stderr": stderr[:1000]
            }

        # Parse the JSON output from the sandbox (last line of stdout)
        try:
            lines = [l for l in stdout.strip().split("\n") if l.strip()]
            result = json.loads(lines[-1])
        except (json.JSONDecodeError, IndexError):
            return {
                "error": "Failed to parse sandbox output",
                "stdout": stdout[:1000],
                "stderr": stderr[:500]
            }

        if "error" in result:
            return result

        print(f"✅ Backtest completed: {result.get('total_return', 0):.2f}% return")
        print(f"📊 Trades: {result.get('trade_summary', {}).get('total_trades', 0)}")

        # Store result for downstream tools
        config._last_backtest_result = result

        print("=" * 50)
        return result

    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Code Interpreter error after {processing_time:.2f}s: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Code Interpreter execution failed: {str(e)}"}
