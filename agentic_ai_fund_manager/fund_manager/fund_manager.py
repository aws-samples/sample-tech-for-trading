"""
fund_manager.py

Fund Manager - LangGraph-based Multi-Agent Orchestrator
Sequential workflow integration of 3 specialized agents with AgentCore Memory's SUMMARY strategy
for automatic session summarization and long-term context retention
"""

import json
import os
import boto3
from typing import Dict, Any, TypedDict
from pathlib import Path
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.config import get_stream_writer
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient

app = BedrockAgentCoreApp()

class Config:
    """Fund Manager Configuration"""
    REGION = "us-west-2"

class FundManagementState(TypedDict):
    user_input: Dict[str, Any]
    session_id: str
    financial_analysis: str
    portfolio_recommendation: str
    risk_analysis: str

class AgentClient:
    def __init__(self):
        self.client = boto3.client('bedrock-agentcore', region_name=Config.REGION)
        self.memory_client = MemoryClient(region_name=Config.REGION)
        self.arns = self._load_agent_arns()
        self.memory_id = self._load_memory_id()
    
    def _load_agent_arns(self):
        """Load Agent ARNs from environment or deployment files"""
        arns = {
            "financial": os.getenv("FINANCIAL_ANALYST_ARN"),
            "portfolio": os.getenv("PORTFOLIO_ARCHITECT_ARN"),
            "risk": os.getenv("RISK_MANAGER_ARN")
        }
        
        if all(arns.values()):
            return arns
        
        # Load from JSON deployment files
        base_dir = Path(__file__).parent.parent
        agent_dirs = {
            "financial": "financial_analyst",
            "portfolio": "portfolio_architect", 
            "risk": "risk_manager"
        }
        
        for agent_key, agent_dir in agent_dirs.items():
            if not arns[agent_key]:
                info_file = base_dir / agent_dir / "deployment_info.json"
                with open(info_file, 'r') as f:
                    arns[agent_key] = json.load(f)["agent_arn"]
        
        return arns
    
    def _load_memory_id(self):
        """Load Memory ID from environment or deployment file"""
        memory_id = os.getenv("FUND_MEMORY_ID")
        if memory_id:
            return memory_id
        
        memory_file = Path(__file__).parent / "agentcore_memory" / "deployment_info.json"
        with open(memory_file, 'r') as f:
            return json.load(f)["memory_id"]
    
    def call_agent_with_streaming(self, agent_type, data, writer):
        """Invoke agent with streaming response"""
        response = self.client.invoke_agent_runtime(
            agentRuntimeArn=self.arns[agent_type],
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": data})
        )
        
        final_result = None
        
        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    writer(event_data)

                    if event_data.get("type") == "streaming_complete":
                        final_result = event_data.get("result")
                
                except json.JSONDecodeError:
                    continue
        
        return final_result

    def save_to_memory(self, session_id, agent_type, user_input, agent_result):
        """Save conversation to memory - SUMMARY strategy automatically summarizes entire session"""
        if not self.memory_id or not agent_result:
            return
        
        try:
            input_text = json.dumps(user_input, ensure_ascii=False) if isinstance(user_input, dict) else str(user_input)
            
            self.memory_client.create_event(
                memory_id=self.memory_id,
                actor_id="fund_user",
                session_id=session_id,
                messages=[
                    (f"{agent_type} analysis request: {input_text}", "USER"),
                    (f"{agent_type} result: {agent_result}", "ASSISTANT")
                ]
            )
            
            print(f"💾 {agent_type} event saved successfully (Session: {session_id})")
            
        except Exception as e:
            print(f"❌ Memory save failed ({agent_type}): {e}")
    


agent_client = AgentClient()

def financial_node(state: FundManagementState):
    """Financial Analysis node"""
    writer = get_stream_writer()
    writer({"type": "node_start", "agent_name": "financial", "session_id": state["session_id"]})
    
    # Invoke Financial Analyst
    result = agent_client.call_agent_with_streaming("financial", state["user_input"], writer)
    
    writer({"type": "node_complete", "agent_name": "financial", "session_id": state["session_id"], "result": result})
    
    # Save to memory
    agent_client.save_to_memory(state["session_id"], "financial", state["user_input"], result)
    
    state["financial_analysis"] = result
    return state

def portfolio_node(state: FundManagementState):
    """Portfolio Architecture node"""
    writer = get_stream_writer()
    writer({"type": "node_start", "agent_name": "portfolio", "session_id": state["session_id"]})
    
    # Invoke Portfolio Architect
    result = agent_client.call_agent_with_streaming("portfolio", state["financial_analysis"], writer)
    
    writer({"type": "node_complete", "agent_name": "portfolio", "session_id": state["session_id"], "result": result})
    
    # Save to memory
    agent_client.save_to_memory(state["session_id"], "portfolio", state["financial_analysis"], result)
    
    state["portfolio_recommendation"] = result
    return state

def risk_node(state: FundManagementState):
    """Risk Management node"""
    writer = get_stream_writer()
    writer({"type": "node_start", "agent_name": "risk", "session_id": state["session_id"]})
    
    # Invoke Risk Manager
    result = agent_client.call_agent_with_streaming("risk", state["portfolio_recommendation"], writer)
    
    writer({"type": "node_complete", "agent_name": "risk", "session_id": state["session_id"], "result": result})
    
    # Save to memory
    agent_client.save_to_memory(state["session_id"], "risk", state["portfolio_recommendation"], result)
    
    state["risk_analysis"] = result
    return state



def create_graph():
    workflow = StateGraph(FundManagementState)
    
    workflow.add_node("financial", financial_node)
    workflow.add_node("portfolio", portfolio_node)
    workflow.add_node("risk", risk_node)
    
    workflow.set_entry_point("financial")
    workflow.add_edge("financial", "portfolio")
    workflow.add_edge("portfolio", "risk")
    workflow.add_edge("risk", END)
    
    return workflow.compile()

class FundManager:
    def __init__(self):
        self.graph = create_graph()
    
    async def run_consultation(self, user_input, session_id=None):
        """Execute fund management consultation"""
        # Use session ID from Streamlit, generate default if not provided
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        initial_state = {
            "user_input": user_input,
            "session_id": session_id,
            "financial_analysis": "",
            "portfolio_recommendation": "",
            "risk_analysis": ""
        }
        
        config = {"configurable": {"thread_id": session_id}}
        
        for chunk in self.graph.stream(initial_state, config=config, stream_mode="custom"):
            yield chunk

advisor = None

@app.entrypoint
async def fund_manager_entrypoint(payload):
    global advisor
    if advisor is None:
        advisor = FundManager()
    
    user_input = payload.get("input_data")
    session_id = payload.get("session_id")
    
    async for chunk in advisor.run_consultation(user_input, session_id):
        yield chunk

if __name__ == "__main__":
    app.run()