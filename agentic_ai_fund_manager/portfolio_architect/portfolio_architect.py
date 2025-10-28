"""
portfolio_architect.py

Portfolio Architect - AI Portfolio Designer
Optimal investment portfolio design using real-time ETF data through MCP Server integration
"""

import json
import os
import requests
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

class Config:
    """Portfolio Architect Configuration"""
    MODEL_ID = "global.anthropic.claude-sonnet-4-20250514-v1:0"
    TEMPERATURE = 0.3
    MAX_TOKENS = 3000

def extract_json_from_text(text_content):
    """Extract only JSON part from AI response"""
    if not isinstance(text_content, str):
        return text_content
    
    start_idx = text_content.find('{')
    end_idx = text_content.rfind('}') + 1
    
    if start_idx != -1 and end_idx > start_idx:
        return text_content[start_idx:end_idx]
    
    return text_content

class PortfolioArchitect:
    def __init__(self, mcp_server_info):
        self.mcp_server_info = mcp_server_info
        self._setup_auth()
        self._init_mcp_client()
        self._create_agent()
    
    def _setup_auth(self):
        """Acquire Cognito OAuth2 token"""
        info = self.mcp_server_info
        self.mcp_url = info['mcp_url']
        
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
                self.mcp_url, 
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
        )
    
    def _create_agent(self):
        """Create AI agent"""
        with self.mcp_client as client:
            tools = client.list_tools_sync()
            
            self.agent = Agent(
                name="portfolio_architect",
                model=BedrockModel(
                    model_id=Config.MODEL_ID,
                    temperature=Config.TEMPERATURE,
                    max_tokens=Config.MAX_TOKENS
                ),
                system_prompt=self._get_prompt(),
                tools=tools
            )
    
    def _get_prompt(self):
        return """You are a professional investment designer. You need to design an optimal investment portfolio based on the client's financial analysis results.

Financial analysis results are provided in the following JSON format:
{
  "risk_profile": <risk profile>,
  "risk_profile_reason": <risk profile assessment reasoning>,
  "required_annual_return_rate": <required annual return rate>,
  "key_sectors": <recommended investment sector list>,
  "summary": <overall assessment>
}

Portfolio Design Process:

1. Candidate ETF Selection: Select 5 ETF candidates considering key_sectors and risk profile.
2. Performance Analysis: Analyze the performance of each of the 5 selected ETFs using the "analyze_etf_performance" tool.
3. Correlation Analysis: Analyze correlations between the 5 ETFs using the "calculate_correlation" tool.
4. Optimal 3 ETF Selection: Select the optimal 3 ETFs by synthesizing performance analysis and correlation results.
   - Balance expected returns and diversification effects.
   - Choose combinations that balance target return achievement potential and risk diversification.
5. Optimal Weight Determination: Determine optimal investment weights based on the performance and correlations of the selected 3 ETFs.
6. Portfolio Evaluation: Evaluate on a 1-10 scale across the following 3 indicators:
   - Profitability: Potential to achieve target returns
   - Risk Management: Volatility and loss probability levels
   - Diversification: Correlation and asset class diversity

Output the final results in the following JSON format:
{
  "portfolio_allocation": {"ticker1": 50, "ticker2": 30, "ticker3": 20},
  "reason": "Portfolio composition reasoning and investment strategy explanation. Must include brief descriptions of each ETF.",
  "portfolio_scores": {
    "profitability": {"score": 9, "reason": "specific reasoning"},
    "risk_management": {"score": 7, "reason": "specific reasoning"},
    "diversification": {"score": 8, "reason": "specific reasoning"}
  }
}

Important Notes:
- Investment weights must be expressed as integers and total 100%."""

    async def design_portfolio_async(self, financial_analysis):
        analysis_str = json.dumps(financial_analysis, ensure_ascii=False)
        
        with self.mcp_client:
            async for event in self.agent.stream_async(analysis_str):
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

# Global instance
architect = None

@app.entrypoint
async def portfolio_architect(payload):
    global architect
    
    if architect is None:
        # Configure MCP Server information from environment variables
        region = os.getenv("AWS_REGION", "us-west-2")
        mcp_agent_arn = os.getenv("MCP_AGENT_ARN")
        encoded_arn = mcp_agent_arn.replace(':', '%3A').replace('/', '%2F')
        
        mcp_server_info = {
            "mcp_url": f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT",
            "region": region,
            "client_id": os.getenv("MCP_CLIENT_ID"),
            "client_secret": os.getenv("MCP_CLIENT_SECRET"),
            "user_pool_id": os.getenv("MCP_USER_POOL_ID")
        }
        
        architect = PortfolioArchitect(mcp_server_info)

    input_data = payload.get("input_data")
    async for chunk in architect.design_portfolio_async(input_data):
        yield chunk

if __name__ == "__main__":
    app.run()