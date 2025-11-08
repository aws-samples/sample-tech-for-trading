"""
Base Agent Class using Strands SDK
"""

from strands import Agent
from typing import Any
import os
from strands.models import BedrockModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get configuration from environment variables with defaults
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
BEDROCK_TEMPERATURE = float(os.getenv('BEDROCK_TEMPERATURE', '0.3'))

# Create a BedrockModel with configuration from environment
bedrock_model = BedrockModel(
    model_id=BEDROCK_MODEL_ID,
    region_name=AWS_REGION,
    temperature=BEDROCK_TEMPERATURE,
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
