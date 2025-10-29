"""
Results Summary Agent - Analyzes and summarizes backtest results
"""

from .base_agent import BaseAgent
from typing import Dict, Any

class ResultsSummaryAgent(BaseAgent):
    """Agent that analyzes backtest results and provides summaries"""
    
    def __init__(self):
        super().__init__("ResultsSummary")
    
    def analyze_results(self, backtest_results: Dict[str, Any]) -> str:
        """Analyze backtest results and generate summary"""
        if 'error' in backtest_results:
            return f"❌ **Backtest Error**: {backtest_results['error']}"
        
        try:
            initial_value = backtest_results.get('initial_value', 0)
            final_value = backtest_results.get('final_value', 0)
            total_return = backtest_results.get('total_return', 0)
            symbol = backtest_results.get('symbol', 'Unknown')
            strategy_name = backtest_results.get('strategy_class', 'Unknown Strategy')
            
            # Generate performance assessment
            performance_assessment = self._assess_performance(total_return)
            
            summary = f"""
## 📊 Backtest Results Summary

**Strategy**: {strategy_name}  
**Symbol**: {symbol}  
**Initial Capital**: ${initial_value:,.2f}  
**Final Value**: ${final_value:,.2f}  
**Total Return**: {total_return:.2f}%  

### Performance Assessment
{performance_assessment}

### Key Metrics
"""
            
            metrics = backtest_results.get('metrics', {})
            for metric, value in metrics.items():
                summary += f"- **{metric}**: {value}\n"
            
            summary += "\n### Recommendations\n"
            summary += self._generate_recommendations(backtest_results)
            
            return summary
            
        except Exception as e:
            return f"❌ **Analysis Error**: {str(e)}"
    
    def process(self, input_data: Any) -> Any:
        """Process backtest results and return analysis"""
        return self.analyze_results(input_data)
    
    def _assess_performance(self, total_return: float) -> str:
        """Assess strategy performance based on returns"""
        if total_return > 20:
            return "🚀 **Excellent Performance** - Strategy significantly outperformed!"
        elif total_return > 10:
            return "✅ **Good Performance** - Strategy showed solid returns"
        elif total_return > 0:
            return "📈 **Positive Performance** - Strategy generated modest gains"
        elif total_return > -10:
            return "⚠️ **Underperformance** - Strategy had minor losses"
        else:
            return "❌ **Poor Performance** - Strategy had significant losses"
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> str:
        """Generate optimization recommendations"""
        total_return = results.get('total_return', 0)
        
        recommendations = []
        
        if total_return < 0:
            recommendations.append("- Consider adjusting entry/exit thresholds")
            recommendations.append("- Add stop-loss mechanisms to limit downside")
            recommendations.append("- Test on different time periods or symbols")
        elif total_return < 10:
            recommendations.append("- Optimize strategy parameters for better performance")
            recommendations.append("- Consider adding position sizing rules")
            recommendations.append("- Test with different market conditions")
        else:
            recommendations.append("- Strategy shows promise - consider live testing")
            recommendations.append("- Implement risk management features")
            recommendations.append("- Test on multiple symbols for diversification")
        
        recommendations.append("- Backtest on longer time periods for validation")
        recommendations.append("- Consider transaction costs in real trading")
        
        return "\n".join(recommendations)
