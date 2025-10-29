"""
Base Agent Class for Multi-Agent Trading System
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseAgent(ABC):
    """Base class for all trading system agents"""
    
    def __init__(self, name: str):
        self.name = name
        self.context = {}
    
    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """Process input data and return result"""
        pass
    
    def update_context(self, key: str, value: Any):
        """Update agent context"""
        self.context[key] = value
    
    def get_context(self, key: str) -> Any:
        """Get value from agent context"""
        return self.context.get(key)
