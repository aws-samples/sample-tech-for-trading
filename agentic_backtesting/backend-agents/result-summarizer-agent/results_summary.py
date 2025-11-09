"""
Results Summary Agent - Analyzes and summarizes backtest results
"""

from base_agent import BaseAgent, AWS_REGION
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


class ResultsSummaryAgent(BaseAgent):
    """Agent that analyzes backtest results and provides summaries"""
    
    def __init__(self):
         instructions = """
         You are an expert quantitative analyst with 20+ years of experience in algorithmic trading, portfolio management, and strategy optimization. Your role is to review Backtrader backtesting results and provide professional, actionable advice to improve trading strategies.

## Your Expertise Includes:
- Trading strategies
- Risk management and position sizing
- Market microstructure and execution

## When Analyzing Backtrader Results, You Will:

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

## Your Response Format:

### 📊 EXECUTIVE SUMMARY
[2-3 sentences on overall strategy viability]

### ⚠️ CONCERNS & RED FLAGS
[Critical issues that need attention]

### 🔍 DETAILED ANALYSIS
[Deep dive into metrics with specific numbers and interpretations]

### 💡 RECOMMENDATIONS
[Prioritized, actionable suggestions for improvement]
1. High Priority: [Critical fixes]
2. Medium Priority: [Optimizations]
3. Consider Testing: [Experimental ideas]

## Your Communication Style:
- Be direct but constructive
- Use specific numbers and references from the results
- Always consider real-world implementation challenges
- When uncertain, acknowledge limitations and suggest additional tests

## Red Flags to Always Check:
- Sharpe ratio >3 (potential overfitting)
- Win rate >70% (suspicious for most strategies)
- Smooth equity curves without realistic drawdowns
- Very few trades (<30 over entire backtest)
- Returns that seem "too good to be true"
- Strategies that only work in specific years
- Ignoring transaction costs or using unrealistic assumptions

When the user provides results, ask clarifying questions if needed, then deliver your analysis with the authority and insight of a senior quant reviewing a junior trader's work.
         """
         
         # Get Results Summary specific configuration from environment
         model_id = os.getenv('RESULTS_SUMMARY_MODEL_ID', 'us.amazon.nova-pro-v1:0')
         temperature = float(os.getenv('RESULTS_SUMMARY_TEMPERATURE', '0.3'))
         
         print(f"🔧 Results Summary Configuration:")
         print(f"   Model ID: {model_id}")
         print(f"   Region: {AWS_REGION}")
         print(f"   Temperature: {temperature}")
         
         # Create dedicated model for Results Summary
         results_model = BedrockModel(
             model_id=model_id,
             region_name=AWS_REGION,
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
            prompt = f"""Please analyze the following Backtrader backtest results and provide your expert assessment:

## Backtest Results Data

**Strategy Name**: {strategy_name}
**Symbol Traded**: {symbol}
**Initial Capital**: ${initial_value:,.2f}
**Final Portfolio Value**: ${final_value:,.2f}
**Total Return**: {total_return:.2f}%
**Profit/Loss**: ${final_value - initial_value:,.2f}

### Performance Metrics:
{json.dumps(metrics, indent=2)}

### Raw Results:
{json.dumps(backtest_results, indent=2)}
"""
            
            # Use AI to analyze the results
            print("🤖 Invoking AI analysis for backtest results...")
            print(prompt)
            analysis = self.agent(prompt)
            
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