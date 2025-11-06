import os
from dotenv import load_dotenv
from strands import Agent, tool

# Load environment variables first
load_dotenv()

from agents.strategy_generator import StrategyGeneratorAgent
from agents.market_data import MarketDataAgent
from agents.backtest import BacktestAgent
from agents.results_summary import ResultsSummaryAgent
from mcp import RedshiftMCPClient

# Define the orchestrator system prompt 
MAIN_SYSTEM_PROMPT = """
You are a quant researcher that automatically executes complete trading strategy backtesting.

For any trading strategy request, ALWAYS execute this EXACT pipeline in ORDER:

STEP 1: Use strategy_generator to create the strategy 
- Call: strategy_generator(query="user's trading idea in json")
- Verify strategy code is generated and returned

STEP 2: Use market_data to fetch required data
- Call: market_data(symbols="SYMBOL", period="1y")
- Verify market data is successfully fetched

STEP 3: Use run_backtest to test the strategy
- Call: run_backtest(strategy_code="code from step 1")
- Verify backtest results sharpe ratio returned

STEP 4: Use results_summary to analyze results
- Call: results_summary(backtest_results="results from step 3")
- And reply to the user

CRITICAL RULES:
- Execute steps in exact order: strategy_generator → market_data → run_backtest → results_summary
- After all steps and provide the final summary to the user.
"""

# Initialize agent instances after .env is loaded
mcp_client = RedshiftMCPClient()
strategy_agent = StrategyGeneratorAgent()
market_data_agent = MarketDataAgent(mcp_client=mcp_client)
backtest_agent = BacktestAgent()
results_agent = ResultsSummaryAgent()

# Global storage for market data
_stored_market_data = {}
_strategy_call_count = 0

from strands import Agent, tool

@tool
def market_data(symbols: str, period: str = "1y") -> str:
    """
    Fetch historical market data and store in memory
    for trading strategy backtesting.

    Args:
        symbols: Comma-separated stock symbols (e.g., "AMZN,NVDA")
        period: Time period for data retrieval (default: "1y")

    Returns:
        Status message confirming data fetch with symbol count and row totals
    """
    agent_name = "📊 MARKET DATA AGENT"
    
    input_data = f"{symbols}, period: {period}"
    reasoning = "Fetching historical market data for backtesting..."
    
    # Print to console (existing behavior)
    print("\n" + "="*50)
    print(agent_name)
    print("="*50)
    print(f"📥 INPUT: {input_data}")
    print(f"🧠 REASONING: {reasoning}")
    
    # Send to Streamlit if callback available
    # Get callback handler if available
    callback = getattr(market_data, '_callback', None)
    if callback:
        callback.on_agent_start(agent_name, input_data)
        callback.on_agent_reasoning(reasoning)
    
    # Convert symbols string to list and create proper input dict
    symbols_list = [s.strip() for s in symbols.split(',')]
    input_dict = {'symbols': symbols_list, 'period': period}
    
    result = market_data_agent.process(input_dict)
    
    output = f"Market data for {list(result.keys()) if result else 'No data'}"
    print(f"📤 OUTPUT: {output}")
    
    # Send output to Streamlit
    if callback:
        callback.on_agent_output(output)
    
    # Validate market data before returning
    if not result or len(result) == 0:
        print("❌ NO MARKET DATA FETCHED - Cannot proceed with backtest")
        return None
    
    # Store market data globally
    global _stored_market_data
    _stored_market_data = result.copy()
    print(f"💾 STORED market data with keys: {list(_stored_market_data.keys())}")
    
    print(f"✅ Successfully fetched market data for: {list(result.keys())}")
    return f"Market data fetched for {list(result.keys())} - {sum(len(df) for df in result.values())} total rows"


@tool
def strategy_generator(query: str) -> str:
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
            "buy_conditions": [
                {
                "indicator": "EMA",
                "param": 50,
                "operator": ">",
                "compare_type": "indicator",
                "compare_indicator": "EMA",
                "compare_param": 250
                },
                {
                "indicator": "ROC",
                "param": 10,
                "operator": ">",
                "compare_type": "value",
                "compare_value": 2
                }
            ],
            "sell_conditions": [
                {
                "indicator": "EMA",
                "param": 50,
                "operator": "<",
                "compare_type": "indicator",
                "compare_indicator": "EMA",
                "compare_param": 250
                },
                {
                "indicator": "PRICE",
                "param": null,
                "operator": "<",
                "compare_type": "value",
                "compare_value": 200
                }
            ]
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
    
    if callback:
        callback.on_agent_start(agent_name, input_data)
        callback.on_agent_reasoning(reasoning)
    
    result = strategy_agent.process(query)
    
    print(f"📤 OUTPUT: {result}")
    
    if callback:
        callback.on_agent_output(result)
    
    print("="*50)
    return result

@tool
def run_backtest(strategy_code: str, market_data_info: str = None, params: dict = None) -> dict:
    """
    Execute trading strategy backtest using historical market data.

    Args:
        strategy_code: Complete Backtrader strategy code from strategy_generator
        market_data_info: memory stored market data
        params: Optional backtest parameters (cash, commission, etc.)

    Returns:
        Comprehensive backtest results with performance metrics and statistics
    """
    global _stored_market_data, _strategy_call_count
    
    callback = getattr(run_backtest, '_callback', None)
    agent_name = "⚡ BACKTEST AGENT"
    
    print("\n" + "="*50)
    print(agent_name)
    print("="*50)
    
    # Validate that strategy_generator was called first
    if _strategy_call_count == 0:
        print("❌ ERROR: strategy_generator must be called before backtest")
        return {'error': 'strategy_generator must be called before backtest'}
    
    # Validate strategy code
    if not strategy_code or len(strategy_code.strip()) < 100:
        print("❌ ERROR: Invalid or empty strategy code")
        return {'error': 'Invalid or empty strategy code'}
    
    # Use stored market data
    market_data = _stored_market_data
    
    # Validate market data first
    if not market_data or len(market_data) == 0:
        print("❌ NO MARKET DATA AVAILABLE - Cannot run backtest")
        return {'error': 'No market data available for backtesting'}
    
    # Count total rows received
    total_rows = 0
    for symbol, data in market_data.items():
        if hasattr(data, '__len__'):
            rows = len(data)
            total_rows += rows
            print(f"📊 Received {rows} rows for {symbol}")
    
    input_data = f"strategy_code length: {len(strategy_code)}, symbols: {list(market_data.keys())}, total_rows: {total_rows}"
    reasoning = "Running strategy backtest with historical data..."
    
    print(f"📥 INPUT: {input_data}")
    print(f"🧠 REASONING: {reasoning}")
    
    if callback:
        callback.on_agent_start(agent_name, input_data)
        callback.on_agent_reasoning(reasoning)
    
    backtest_input = {
        'strategy_code': strategy_code,
        'market_data': market_data,
        'params': params or {'initial_cash': 100000, 'commission': 0.001}
    }
    
    result = backtest_agent.process(backtest_input)
    
    print(f"📤 OUTPUT: {result}")
    
    if callback:
        callback.on_agent_output(result)
    
    print("="*50)
    return result

@tool
def results_summary(backtest_results: dict) -> str:
    """
    Analyze backtest performance and generate comprehensive trading strategy report.

    Args:
        backtest_results: Dictionary containing backtest metrics and performance data

    Returns:
        Formatted analysis report with key statistics and performance assessment
    """
    callback = getattr(results_summary, '_callback', None)
    agent_name = "📈 RESULTS SUMMARY AGENT"
    
    print("\n" + "="*50)
    print(agent_name)
    print("="*50)
    
    input_data = f"{list(backtest_results.keys()) if isinstance(backtest_results, dict) else 'Invalid format'}"
    reasoning = "Analyzing backtest performance and generating summary..."
    
    print(f"📥 INPUT: {input_data}")
    print(f"🧠 REASONING: {reasoning}")
    
    if callback:
        callback.on_agent_start(agent_name, input_data)
        callback.on_agent_reasoning(reasoning)
    
    result = results_agent.process(backtest_results)
    
    print(f"📤 OUTPUT: {result}")
    
    if callback:
        callback.on_agent_output(result)
    
    print("="*50)
    return result

class OrchestratorAgent:
    def __init__(self, callback_handler=None):
        # Create Strands orchestrator with tool functions
        self.orchestrator = Agent(
            system_prompt=MAIN_SYSTEM_PROMPT,
            callback_handler=callback_handler,
            tools=[market_data, strategy_generator, run_backtest, results_summary]
        )
        
        # Set callback on tools if provided
        if callback_handler:
            market_data._callback = callback_handler
            strategy_generator._callback = callback_handler
            run_backtest._callback = callback_handler
            results_summary._callback = callback_handler
    
    def process(self, user_input: str):
        """Process user request through orchestrator"""
        print("\n" + "🎯 ORCHESTRATOR AGENT")
        print("="*50)
        print(f"📥 USER INPUT: {user_input}")
        print("🧠 REASONING: Determining which agents to call and in what order...")
        print("="*50)
        
        result = self.orchestrator(user_input)
        
        print("\n" + "🏁 FINAL RESULT")
        print("="*50)
        print(f"📤 FINAL OUTPUT: {result}")
        print("="*50)
        
        return result
