"""
risk_manager.py

Risk Manager - AI Risk Manager
Risk scenario analysis based on real-time news and market data through MCP Gateway integration
"""

import json
import os
import requests
from pathlib import Path
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

class Config:
    """Risk Manager Configuration"""
    MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    TEMPERATURE = 0.2
    MAX_TOKENS = 4000

def extract_json_from_text(text_content):
    """Extract only JSON part from AI response"""
    if not isinstance(text_content, str):
        return text_content
    
    start_idx = text_content.find('{')
    end_idx = text_content.rfind('}') + 1
    
    if start_idx != -1 and end_idx > start_idx:
        return text_content[start_idx:end_idx]
    
    return text_content

class RiskManager:
    """AI Risk Manager - MCP Gateway Integration"""
    
    def __init__(self, gateway_info):
        self.gateway_info = gateway_info
        self._setup_auth()
        self._init_mcp_client()
        self._create_agent()
    
    def _setup_auth(self):
        """Acquire Cognito OAuth2 token"""
        info = self.gateway_info
        self.gateway_url = info['gateway_url']
        
        pool_domain = info['user_pool_id'].replace("_", "").lower()
        token_url = f"https://{pool_domain}.auth.{info['region']}.amazoncognito.com/oauth2/token"
        
        response = requests.post(
            token_url,
            data=f"grant_type=client_credentials&client_id={info['client_id']}&client_secret={info['client_secret']}",
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        self.access_token = response.json()['access_token']
    
    def _init_mcp_client(self):
        """Initialize MCP client"""
        self.mcp_client = MCPClient(
            lambda: streamablehttp_client(
                self.gateway_url, 
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
        )
    
    def _create_agent(self):
        """Create AI agent"""
        with self.mcp_client as client:
            tools = client.list_tools_sync()
            
            self.agent = Agent(
                name="risk_manager",
                model=BedrockModel(
                    model_id=Config.MODEL_ID,
                    temperature=Config.TEMPERATURE,
                    max_tokens=Config.MAX_TOKENS
                ),
                system_prompt=self._get_prompt(),
                tools=tools
            )
    
    def _get_prompt(self):
        return """You are a risk management expert. You need to perform risk analysis on the proposed portfolio and provide portfolio adjustment guidance according to major economic scenarios.

Input Data:
The proposed portfolio composition is provided in the following JSON format:
{{
  "portfolio_allocation": {{
    "ticker1": allocation1,
    "ticker2": allocation2,
    "ticker3": allocation3
  }},
  "reason": "Portfolio composition reasoning and investment strategy explanation",
  "portfolio_scores": {{
    "profitability": {{"score": score, "reason": "assessment reasoning"}},
    "risk_management": {{"score": score, "reason": "assessment reasoning"}},
    "diversification": {{"score": score, "reason": "assessment reasoning"}}
  }}
}}

Your Tasks:
Use the given tools freely to achieve the following objectives:

1. Comprehensive risk analysis of the given portfolio
2. Derive 2 economic scenarios with high probability of occurrence
3. Present portfolio adjustment plans for each scenario

You must respond in the following format:
{{
  "scenario1": {{
    "name": "Scenario 1 Name",
    "description": "Scenario 1 detailed description",
    "probability": "Probability of occurrence (e.g., 30%)",
    "allocation_management": {{
      "ticker1": new_allocation1,
      "ticker2": new_allocation2,
      "ticker3": new_allocation3
    }},
    "reason": "Adjustment reasoning and strategy"
  }},
  "scenario2": {{
    "name": "Scenario 2 Name", 
    "description": "Scenario 2 detailed description",
    "probability": "Probability of occurrence (e.g., 25%)",
    "allocation_management": {{
      "ticker1": new_allocation1,
      "ticker2": new_allocation2,
      "ticker3": new_allocation3
    }},
    "reason": "Adjustment reasoning and strategy"
  }}
}}

When responding, you must adhere to the following:
1. Use only the tickers received as input when adjusting the portfolio
2. Do not add new products or remove existing products
3. Ensure that the total of adjusted allocations for each scenario equals 100%
4. Provide detailed explanations of scenario descriptions and adjustment reasoning"""
    
    async def analyze_risk_async(self, portfolio_data):
        try:
            portfolio_str = json.dumps(portfolio_data, ensure_ascii=False)
            
            with self.mcp_client:
                async for event in self.agent.stream_async(portfolio_str):
                    if "data" in event:
                        yield {"type": "text_chunk", "data": event["data"]}
                    
                    if "message" in event:
                        message = event["message"]
                        
                        if message.get("role") == "assistant":
                            for content in message.get("content", []):
                                if "toolUse" in content:
                                    tool_use = content["toolUse"]
                                    yield {
                                        "type": "tool_use",
                                        "tool_name": tool_use.get("name"),
                                        "tool_use_id": tool_use.get("toolUseId"),
                                        "tool_input": tool_use.get("input", {})
                                    }
                        
                        if message.get("role") == "user":
                            for content in message.get("content", []):
                                if "toolResult" in content:
                                    tool_result = content["toolResult"]
                                    yield {
                                        "type": "tool_result",
                                        "tool_use_id": tool_result["toolUseId"],
                                        "status": tool_result["status"],
                                        "content": tool_result["content"]
                                    }
                    
                    if "result" in event:
                        raw_result = str(event["result"])
                        clean_json = extract_json_from_text(raw_result)
                        yield {"type": "streaming_complete", "result": clean_json}

        except Exception as e:
            yield {"type": "error", "error": str(e), "status": "error"}

# Global instance
manager = None

@app.entrypoint
async def risk_manager(payload):
    """AgentCore Runtime entrypoint"""
    global manager
    
    if manager is None:
        # Configure Gateway information from environment variables
        gateway_info = {
            "client_id": os.getenv("MCP_CLIENT_ID"),
            "client_secret": os.getenv("MCP_CLIENT_SECRET"), 
            "gateway_url": os.getenv("MCP_GATEWAY_URL"),
            "user_pool_id": os.getenv("MCP_USER_POOL_ID"),
            "region": os.getenv("AWS_REGION", "us-west-2"),
            "target_id": os.getenv("MCP_TARGET_ID", "target-risk-manager")
        }
        
        manager = RiskManager(gateway_info)

    input_data = payload.get("input_data")
    async for chunk in manager.analyze_risk_async(input_data):
        yield chunk

if __name__ == "__main__":
    app.run()