"""
financial_analyst.py

Financial Analyst - AI Financial Analyst
Personal financial situation analysis and risk profile assessment using Calculator tool
"""

import json
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands_tools import calculator
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

class Config:
    """Financial Analyst Configuration"""
    MODEL_ID = "openai.gpt-oss-120b-1:0"
    TEMPERATURE = 0.1
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

class FinancialAnalyst:
    """AI Financial Analyst using Calculator tool"""
    
    def __init__(self):
        self.agent = Agent(
            name="financial_analyst",
            model=BedrockModel(
                model_id=Config.MODEL_ID,
                temperature=Config.TEMPERATURE,
                max_tokens=Config.MAX_TOKENS
            ),
            tools=[calculator],
            system_prompt=self._get_prompt()
        )
        
    def _get_prompt(self) -> str:
        return """As a financial analysis expert, perform personalized investment analysis.

Input Data:
- total_investable_amount: Available investment amount
- target_amount: Target amount after 1 year
- age: Age  
- stock_investment_experience_years: Years of investment experience
- investment_purpose: Investment purpose
- preferred_sectors: Areas of investment interest

Analysis Process:
1. Use the "calculator" tool to calculate return rate: ((target_amount/investment_amount)-1)*100
2. Assess risk profile thoroughly considering age, experience, purpose, and areas of interest.
3. Provide comprehensive evaluation considering return rate and risk profile.

Output:
{
"risk_profile": "Very Conservative|Conservative|Neutral|Aggressive|Very Aggressive",
"risk_profile_reason": "Risk profile assessment reasoning (2-3 sentences)",
"required_annual_return_rate": return_rate_as_number_with_2_decimal_places,
"key_sectors": ["Recommended Investment Sector1", "Recommended Investment Sector2", "Recommended Investment Sector3"],
"summary": "Overall assessment (3-4 sentences)"
}"""

    async def analyze_financial_situation_async(self, user_input):
        """Real-time streaming financial analysis using Calculator tool"""
        try:
            user_input_str = json.dumps(user_input, ensure_ascii=False)

            async for event in self.agent.stream_async(user_input_str):
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

analyst = None

@app.entrypoint
async def financial_analyst(payload):
    """AgentCore Runtime entrypoint"""
    global analyst
    
    if analyst is None:
        analyst = FinancialAnalyst()

    user_input = payload.get("input_data")
    async for chunk in analyst.analyze_financial_situation_async(user_input):
        yield chunk

if __name__ == "__main__":
    app.run()