"""
Results Summary Agent - Analyzes and summarizes backtest results
"""

import os
from typing import Dict, Any
from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the AgentCore app
app = BedrockAgentCoreApp()


class ResultsSummaryAgent():
    """Agent that analyzes backtest results and provides summaries"""
    
    def __init__(self):
         instructions = """
         You are an expert quantitative analyst with 20+ years of experience in algorithmic trading, portfolio management, and strategy optimization. Your role is to review Backtrader backtesting results and provide professional, actionable advice to improve trading strategies.

When Analyzing Backtrader Results, You Will:

- Evaluate total return and risk-adjusted returns (Sharpe, Sortino, etc)
- Assess consistency across different market regimes
- Identify periods of outperformance and underperformance
- Compare against relevant benchmarks
- Analyze maximum drawdown, drawdown duration, and recovery periods
- Evaluate volatility patterns and tail risk
- Check for overfitting indicators (too many parameters, perfect equity curve)
- Evaluate sample size adequacy
- Look for survivorship bias, look-ahead bias, or data snooping
- Assess statistical significance of results

Red Flags to Always Check:
- Sharpe ratio >3 (potential overfitting)
- Win rate >70% (suspicious for most strategies)
- Smooth equity curves without realistic drawdowns
- Very few trades (<30 over entire backtest)
- Returns that seem "too good to be true"
- Strategies that only work in specific years
- Ignoring transaction costs or using unrealistic assumptions


Analyze the trading strategy results provided and output your analysis in the following JSON format:

{
  "backtestResult": {"repeat all the results here in key pair format"},
  "executiveSummary": "A 2-3 sentence overview of the strategy's viability",
  "detailedAnalysis": "In-depth examination of metrics with specific numbers and interpretations",
  "concernsAndRecommendations": {
    "highPriority": [
      "Critical fix 1",
      "Critical fix 2"
    ],
    "mediumPriority": [
      "Optimization 1",
      "Optimization 2"
    ],
    "considerTesting": [
      "Experimental idea 1",
      "Experimental idea 2"
    ]
  }
}

Deliver your analysis with the insight of a senior quant reviewing a junior trader's work. 
Ensure all output is in valid JSON format with executiveSummary, detailedAnalysis and concernsAndRecommendations.
         """
         
         # Get Results Summary specific configuration from environment
         aws_region = os.getenv('AWS_REGION', 'us-east-1')
         model_id = os.getenv('RESULTS_SUMMARY_MODEL_ID', 'us.amazon.nova-pro-v1:0')
         temperature = float(os.getenv('RESULTS_SUMMARY_TEMPERATURE', '0.3'))
         
         print(f"🔧 Results Summary Configuration:")
         print(f"   Model ID: {model_id}")
         print(f"   Region: {aws_region}")
         print(f"   Temperature: {temperature}")
         
         # Create dedicated model for Results Summary
         results_model = BedrockModel(
             model_id=model_id,
             region_name=aws_region,
             temperature=temperature,
         )

         self.agent = Agent(
            name="ResultsSummary",
            model=results_model,
            system_prompt=instructions
        )
    
    def analyze_results(self, backtest_results: Dict[str, Any]) -> str:
        """Analyze backtest results and generate summary using AI"""
        if 'error' in backtest_results:
            return f"❌ **Backtest Error**: {backtest_results['error']}"
        
        try:
            import json
            
            # Extract key information from backtest results
            initial_value = backtest_results.get('initial_value', 0)
            final_value = backtest_results.get('final_value', 0)
            total_return = backtest_results.get('total_return', 0)
            symbol = backtest_results.get('symbol', 'Unknown')
            strategy_name = backtest_results.get('strategy_class', 'Unknown Strategy')
            metrics = backtest_results.get('metrics', {})
            
            # Create a comprehensive prompt for AI analysis
            prompt = f"""Please analyze the following Backtrader backtest results:

**Strategy Name**: {strategy_name}
**Symbol Traded**: {symbol}
**Initial Capital**: ${initial_value:,.2f}
**Final Portfolio Value**: ${final_value:,.2f}
**Total Return**: {total_return:.2f}%
**Profit/Loss**: ${final_value - initial_value:,.2f}

Performance Metrics:
{json.dumps(metrics, indent=2)}

"""
            
            # Use AI to analyze the results
            print("🤖 Invoking AI analysis for backtest results...")
            print(prompt)
            analysis = self.agent(prompt)
            print(f"output: {analysis}")
            
            return analysis
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return f"❌ **Analysis Error**: {str(e)}\n\nDetails:\n{error_details}"
    
    def process(self, input_data: Any) -> Any:
        """Process backtest results and return analysis"""
        return self.analyze_results(input_data)


agent = ResultsSummaryAgent()

@app.entrypoint
def invoke(payload, context=None):
    """Main entrypoint for the backtesting agent"""  
    return agent.process(payload)


if __name__ == "__main__":
    print("\n🌐 Starting server on port 8080...")
    try:
        app.run(port=8080)
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        import traceback
        traceback.print_exc()