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

# Define the orchestrator system prompt for automatic pipeline execution
MAIN_SYSTEM_PROMPT = """
You are a quant researcher that automatically executes complete trading strategy backtesting.

For any trading strategy request, ALWAYS execute this full pipeline:
1. Use market_data to fetch required data - WAIT AT LEAST 30 SECONDS after calling market_data before proceeding to next step
2. Use strategy_generator to create the strategy with the market_data as data feed - WAIT AT LEAST 60 SECONDS after each step
3. CHECK if market data is successfully fetched
4. ONLY if market data exists, use backtest to test the strategy - WAIT AT LEAST 10 SECONDS
5. Use results_summary to analyze and present final results - WAIT AT LEAST 10 SECONDS

IMPORTANT: 
- Each step takes at least 10 seconds to complete - always wait between steps
- Strategy generation and Market data fetching takes time - always wait at least 60 seconds after calling the agent 
- If market_data returns None or empty, DO NOT proceed with backtest. Inform user that market data fetch failed.

Execute all steps automatically and provide the final summary to the user.
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

@tool
def market_data(symbols: str, period: str = "1y"):
    """Fetch market data, stock prices, and financial data"""
    global _stored_market_data
    
    print("\n" + "="*50)
    print("📊 MARKET DATA AGENT")
    print("="*50)
    print(f"📥 INPUT: {symbols}, period: {period}")
    print("🧠 REASONING: Fetching historical market data for backtesting...")
    
    # Convert symbols string to list and create proper input dict
    symbols_list = [s.strip() for s in symbols.split(',')]
    input_dict = {'symbols': symbols_list, 'period': period}
    
    result = market_data_agent.process(input_dict)
    
    print(f"📤 OUTPUT: Market data for {list(result.keys()) if result else 'No data'}")
    
    # Validate market data before returning
    if not result or len(result) == 0:
        print("❌ NO MARKET DATA FETCHED - Cannot proceed with backtest")
        return None
    
    # Store market data globally
    _stored_market_data = result.copy()
    print(f"💾 STORED market data with keys: {list(_stored_market_data.keys())}")
    
    print(f"✅ Successfully fetched market data for: {list(result.keys())}")
    return f"Market data fetched for {list(result.keys())} - {sum(len(df) for df in result.values())} total rows"


@tool
def strategy_generator(query: str):
    """Generate trading strategies and algorithms"""
    
    _strategy_call_count += 1
    print(f"\n🔄 STRATEGY GENERATOR CALL #{_strategy_call_count}")
    print("="*50)
    print("🔧 STRATEGY GENERATOR AGENT")
    print("="*50)
    print(f"📥 INPUT: {query}")
    print("🧠 REASONING: Converting user trading idea into executable strategy code...")
    
    result = strategy_agent.process(query)
    
    print(f"📤 OUTPUT: {result}")
    print("="*50)
    return result

@tool
def backtest(strategy_code: str, market_data_info: str = None, params: dict = None):
    """Run backtests and performance testing"""
    global _stored_market_data
    
    print("\n" + "="*50)
    print("⚡ BACKTEST AGENT")
    print("="*50)
    
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
    
    print(f"📥 INPUT: strategy_code length: {len(strategy_code)}, symbols: {list(market_data.keys())}, total_rows: {total_rows}")
    print("🧠 REASONING: Running strategy backtest with historical data...")
    
    backtest_input = {
        'strategy_code': strategy_code,
        'market_data': market_data,
        'params': params or {'initial_cash': 100000, 'commission': 0.001}
    }
    
    result = backtest_agent.process(backtest_input)
    
    print(f"📤 OUTPUT: {result}")
    print("="*50)
    return result

@tool
def results_summary(backtest_results: dict):
    """Analyze results and generate reports"""
    print("\n" + "="*50)
    print("📈 RESULTS SUMMARY AGENT")
    print("="*50)
    print(f"📥 INPUT: {list(backtest_results.keys()) if isinstance(backtest_results, dict) else 'Invalid format'}")
    print("🧠 REASONING: Analyzing backtest performance and generating summary...")
    
    result = results_agent.process(backtest_results)
    
    print(f"📤 OUTPUT: {result}")
    print("="*50)
    return result

class OrchestratorAgent:
    def __init__(self):
        # Create Strands orchestrator with tool functions
        self.orchestrator = Agent(
            system_prompt=MAIN_SYSTEM_PROMPT,
            callback_handler=None,
            tools=[market_data, strategy_generator, backtest, results_summary]
        )
    
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
