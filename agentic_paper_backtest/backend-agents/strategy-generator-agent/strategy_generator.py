"""
Strategy Generator Agent - Converts JSON strategy config to executable Backtrader code
With AgentCore Memory integration for cross-session learning
"""

import json
import os
from typing import Dict, Any, Union
from datetime import datetime
from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Version tracking for troubleshooting
VERSION = os.getenv('AGENT_VERSION', datetime.now().strftime('%Y%m%d_%H%M%S'))

# Initialize the AgentCore app
app = BedrockAgentCoreApp()

# Memory globals
_memory_client = None
_memory_id = None
_session_id = None


def save_to_memory(input_config: Dict, generated_code: str):
    """Save generated strategy to AgentCore Memory for future reference"""
    global _memory_client, _memory_id, _session_id
    try:
        strategy_name = input_config.get('name', 'unknown')
        symbol = input_config.get('stock_symbol', 'unknown')
        message = (
            f"Generated strategy '{strategy_name}' for {symbol}. "
            f"Config: {json.dumps(input_config)}. "
            f"Code preview: {generated_code[:500]}"
        )
        _memory_client.create_event(
            memory_id=_memory_id,
            actor_id="StrategyGenerator",
            session_id=_session_id,
            messages=[(message, "ASSISTANT")]
        )
        print(f"💾 Strategy '{strategy_name}' saved to memory")
    except Exception as e:
        print(f"⚠️ Failed to save to memory: {e}")


def get_past_strategies(symbol: str = None) -> list:
    """Retrieve past strategy generations from memory for context"""
    global _memory_client, _memory_id, _session_id
    try:
        events = _memory_client.list_events(
            memory_id=_memory_id,
            actor_id="StrategyGenerator",
            session_id=_session_id
        )
        strategies = []
        events_list = events.get('events', []) if isinstance(events, dict) else events
        for event in events_list:
            for msg in event.get('messages', []):
                content = msg.get('content', '') if isinstance(msg, dict) else str(msg)
                if 'Generated strategy' in content:
                    if symbol is None or symbol.upper() in content.upper():
                        strategies.append(content)
        return strategies[-5:]  # Return last 5 relevant strategies
    except Exception as e:
        print(f"⚠️ Failed to retrieve memory: {e}")
        return []


class StrategyGeneratorAgent():
    """Agent that generates Backtrader strategy code from JSON configuration"""
    
    def __init__(self):
        instructions = """You are a trading strategy code generator. Convert JSON strategy configurations into executable Backtrader Python code.

Generate clean, efficient Backtrader strategy code that:
1. Implements all buy and sell conditions from the JSON
2. Uses proper Backtrader indicators (EMA, SMA, RSI, ROC)
3. Handles stop loss and take profit if specified
4. Includes proper error handling and parameter validation

Always return complete, runnable Python code with proper imports and class structure.

If past strategies are provided as context, learn from them:
- Avoid patterns that previously caused errors
- Reuse successful indicator combinations
- Improve on previous implementations"""
        
        # Get Strategy Generator specific configuration from environment
        aws_region = os.getenv('AWS_REGION', 'us-east-1')
        model_id = os.getenv('STRATEGY_GENERATOR_MODEL_ID', 'us.anthropic.claude-opus-4-7')

        print(f"🔧 Strategy Generator Configuration:")
        print(f"   Version: {VERSION}")
        print(f"   Model ID: {model_id}")
        print(f"   Region: {aws_region}")

        # Create dedicated model for Strategy Generator
        strategy_model = BedrockModel(
            model_id=model_id,
            region_name=aws_region,
        )

        self.agent = Agent(
            name="StrategyGenerator",
            model=strategy_model,
            system_prompt=instructions
        )
        
    def process(self, input_data: Union[str, Dict]) -> str:
        """Convert query and market data to Backtrader code"""
        if isinstance(input_data, str):
            strategy_config = json.loads(input_data)
        else:
            strategy_config = input_data

        prompt = self._create_strategy_prompt(strategy_config)

        # Get past strategies from memory for context
        past = get_past_strategies(strategy_config.get('stock_symbol'))
        if past:
            context = "\n\nPreviously generated strategies for reference:\n" + "\n---\n".join(past[-3:])
            prompt += context

        # Generate strategy
        result = self.agent(prompt)

        # Save to memory
        result_str = str(result) if result else ""
        save_to_memory(strategy_config, result_str)

        return result
    
    def _create_strategy_prompt(self, config: Dict[str, Any]) -> str:
        """Create detailed prompt for strategy generation """
        
        database_config = config.get('database', {})
        backtest_window = config.get('backtest_window', '1Y')
        
        return f"""
Generate a complete Backtrader strategy class from this JSON configuration:

{json.dumps(config, indent=2)}

Requirements:
1. Class name: {config['name'].replace(' ', '')}Strategy
2. Stock symbol: {config['stock_symbol']}
3. Max positions: {config['max_positions']}
4. Stop loss: {config.get('stop_loss', 'None')}% if specified
5. Take profit: {config.get('take_profit', 'None')}% if specified


Buy Conditions : {config['buy_conditions']}

Sell Conditions : {config['sell_conditions']}

Example RSI strategy code:
```python
import backtrader as bt
import backtrader.indicators as btind
import backtrader.analyzers as btanalyzers

class RSIStrategy(bt.Strategy):
    params = (
        ('stop_loss', 5.0),  # 5% stop loss
        ('take_profit', 10.0),  # 10% take profit
    )
    
    def __init__(self):
        self.rsi = btind.RSI(self.data.close, period=14)
        self.buy_price = None
        
    def next(self):
        if not self.position:
            if self.rsi < 30:  # Buy when RSI < 30
                self.buy()
                self.buy_price = self.data.close[0]
        else:
            # Stop loss and take profit
            if self.buy_price:
                pct_change = (self.data.close[0] - self.buy_price) / self.buy_price * 100
                if pct_change <= -self.params.stop_loss or pct_change >= self.params.take_profit:
                    self.sell()
                    self.buy_price = None
            # RSI sell signal
            if self.rsi > 70:  # Sell when RSI > 70
                self.sell()
                self.buy_price = None

```

Generate complete Python code with:
- Proper imports (backtrader, indicators)
- Strategy class with __init__ and next methods
- All required indicators initialized
- Buy logic: ALL conditions must be true
- Sell logic: ANY condition can trigger
- Stop loss/take profit implementation if specified
- Proper position management

Return only the Python code, no explanations.
"""


# Lazy initialization to avoid cold start timeout
_initialized = False
_agent = None

def _ensure_initialized():
    """Initialize the agent and memory on first call to avoid cold start timeout"""
    global _initialized, _agent, _memory_client, _memory_id, _session_id
    if _initialized:
        return

    # Initialize memory client
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    _memory_client = MemoryClient(region_name=aws_region)
    _memory_id = os.getenv('STRATEGY_GENERATOR_MEMORY_ID')
    _session_id = f"strategy_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if _memory_id:
        print(f"🧠 Memory enabled: {_memory_id}")
        print(f"🔑 Session ID: {_session_id}")
    else:
        print("⚠️ STRATEGY_GENERATOR_MEMORY_ID not set — memory disabled")

    _agent = StrategyGeneratorAgent()
    _initialized = True

@app.entrypoint
def invoke(payload, context=None):
    """Main entrypoint for the backtesting agent

    payload: expected json or str:
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
    """
    _ensure_initialized()
    # Handle both direct strategy JSON and {"prompt": "..."} wrapper from invoke_agent_runtime
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass
    if isinstance(payload, dict) and "prompt" in payload:
        payload = payload["prompt"]
    strategy_code = _agent.process(payload)
    return {
        "code": str(strategy_code),
        "version": VERSION
    }


if __name__ == "__main__":
    print("\n🌐 Starting server on port 8080...")
    try:
        app.run(port=8080)
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        import traceback
        traceback.print_exc()
