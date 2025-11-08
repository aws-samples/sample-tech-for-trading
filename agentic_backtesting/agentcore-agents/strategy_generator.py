"""
Strategy Generator Agent - Converts JSON strategy config to executable Backtrader code
"""

from base_agent import BaseAgent, AWS_REGION
import json
import os
from typing import Dict, Any, Union
from strands.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the AgentCore app
app = BedrockAgentCoreApp()


class StrategyGeneratorAgent(BaseAgent):
    """Agent that generates Backtrader strategy code from JSON configuration"""
    
    def __init__(self):
        instructions = """You are a trading strategy code generator. Convert JSON strategy configurations into executable Backtrader Python code.

Generate clean, efficient Backtrader strategy code that:
1. Implements all buy and sell conditions from the JSON
2. Uses proper Backtrader indicators (EMA, SMA, RSI, ROC)
3. Handles stop loss and take profit if specified
4. Includes proper error handling and parameter validation

Always return complete, runnable Python code with proper imports and class structure."""
        
        # Get Strategy Generator specific configuration from environment
        model_id = os.getenv('STRATEGY_GENERATOR_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0')
        temperature = float(os.getenv('STRATEGY_GENERATOR_TEMPERATURE', '0.3'))
        
        print(f"🔧 Strategy Generator Configuration:")
        print(f"   Model ID: {model_id}")
        print(f"   Region: {AWS_REGION}")
        print(f"   Temperature: {temperature}")
        
        # Create dedicated model for Strategy Generator
        strategy_model = BedrockModel(
            model_id=model_id,
            region_name=AWS_REGION,
            temperature=temperature,
        )
        
        super().__init__("StrategyGenerator", instructions, strategy_model)
    

    def process(self, input_data: Union[str, Dict]) -> str:
        """Convert query and market data to Backtrader code"""
        if isinstance(input_data, str):
            strategy_config = json.loads(input_data)
            prompt = self._create_strategy_prompt(strategy_config)
        else:
            prompt = self._create_strategy_prompt(input_data)
            
        # print(f"FULL prompt: {prompt}")
        return self.invoke_sync(prompt)
    
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


agent = StrategyGeneratorAgent()

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
            "buy_conditions":  "EMA50 > EMA200",
            "sell_conditions": "EMA50 < EMA200"
        }
    """  
    return agent.process(payload)


if __name__ == "__main__":
    print("\n🌐 Starting server on port 8080...")
    try:
        app.run(port=8080)
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        import traceback
        traceback.print_exc()