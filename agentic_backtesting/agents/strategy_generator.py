"""
Strategy Generator Agent - Converts trading ideas to executable strategies
"""

from .base_agent import BaseAgent
from typing import Dict, Any

class StrategyGeneratorAgent(BaseAgent):
    """Agent that generates trading strategy code from natural language descriptions"""
    
    def __init__(self):
        super().__init__("StrategyGenerator")
        self.strategy_templates = {
            'rsi': self._rsi_template,
            'momentum': self._momentum_template,
            'mean_reversion': self._mean_reversion_template
        }
    
    def generate_strategy(self, trading_idea: str) -> str:
        """Generate strategy code from trading idea"""
        # Simple keyword-based strategy selection
        idea_lower = trading_idea.lower()
        
        if 'rsi' in idea_lower:
            return self._rsi_template(trading_idea)
        elif 'momentum' in idea_lower:
            return self._momentum_template(trading_idea)
        elif 'mean reversion' in idea_lower or 'revert' in idea_lower:
            return self._mean_reversion_template(trading_idea)
        else:
            return self._default_template(trading_idea)
    
    def process(self, input_data: Any) -> Any:
        """Process trading idea and return strategy code"""
        return self.generate_strategy(input_data)
    
    def _rsi_template(self, idea: str) -> str:
        """Generate RSI-based strategy"""
        return '''
import backtrader as bt
import backtrader.indicators as btind

class RSIStrategy(bt.Strategy):
    params = (
        ('rsi_period', 14),
        ('rsi_upper', 70),
        ('rsi_lower', 30),
    )
    
    def __init__(self):
        self.rsi = btind.RSI(self.data.close, period=self.params.rsi_period)
        
    def next(self):
        if not self.position:
            if self.rsi < self.params.rsi_lower:
                self.buy()
        else:
            if self.rsi > self.params.rsi_upper:
                self.sell()
'''
    
    def _momentum_template(self, idea: str) -> str:
        """Generate momentum-based strategy"""
        return '''
import backtrader as bt
import backtrader.indicators as btind

class MomentumStrategy(bt.Strategy):
    params = (
        ('period', 20),
        ('momentum_threshold', 0.02),
    )
    
    def __init__(self):
        self.momentum = btind.Momentum(self.data.close, period=self.params.period)
        
    def next(self):
        if not self.position:
            if self.momentum[0] > self.params.momentum_threshold:
                self.buy()
        else:
            if self.momentum[0] < -self.params.momentum_threshold:
                self.sell()
'''
    
    def _mean_reversion_template(self, idea: str) -> str:
        """Generate mean reversion strategy"""
        return '''
import backtrader as bt
import backtrader.indicators as btind

class MeanReversionStrategy(bt.Strategy):
    params = (
        ('period', 20),
        ('devfactor', 2.0),
    )
    
    def __init__(self):
        self.boll = btind.BollingerBands(self.data.close, 
                                       period=self.params.period,
                                       devfactor=self.params.devfactor)
        
    def next(self):
        if not self.position:
            if self.data.close < self.boll.lines.bot:
                self.buy()
        else:
            if self.data.close > self.boll.lines.top:
                self.sell()
'''
    
    def _default_template(self, idea: str) -> str:
        """Generate default simple strategy"""
        return '''
import backtrader as bt
import backtrader.indicators as btind

class SimpleStrategy(bt.Strategy):
    params = (
        ('ma_period', 20),
    )
    
    def __init__(self):
        self.ma = btind.SimpleMovingAverage(self.data.close, period=self.params.ma_period)
        
    def next(self):
        if not self.position:
            if self.data.close > self.ma:
                self.buy()
        else:
            if self.data.close < self.ma:
                self.sell()
'''
