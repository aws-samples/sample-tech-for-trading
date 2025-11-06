"""
Base Agent Class using Strands SDK
"""

from strands import Agent
from typing import Any, Dict

import boto3
from strands.models import BedrockModel

# Create a BedrockModel
bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-east-1",
    temperature=0.3,
)

class BaseAgent():
    """Base class for all trading system agents using Strands SDK"""

    def __init__(self, name: str, instructions: str = "", model=bedrock_model):
        self.agent = Agent(
            name=name,
            model=model,
            system_prompt=instructions
        )

        self.instructions = instructions
        self.context = {}

    def invoke_sync(self, prompt=None, **kwargs):
        return self.agent(prompt)


    def update_context(self, key: str, value: Any):
        """Update agent context"""
        self.context[key] = value

    def get_context(self, key: str) -> Any:
        """Get value from agent context"""
        return self.context.get(key)
