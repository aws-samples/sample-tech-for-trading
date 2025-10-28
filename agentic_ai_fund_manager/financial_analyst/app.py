"""
app.py

Financial Analyst Streamlit Application
AI Financial Analyst Web Interface
"""

import streamlit as st
import json
import os
import boto3
from pathlib import Path

st.set_page_config(page_title="Financial Analyst")
st.title("💰 Financial Analyst")

# Load deployment information
try:
    with open(Path(__file__).parent / "deployment_info.json") as f:
        deployment_info = json.load(f)
    AGENT_ARN = deployment_info["agent_arn"]
    REGION = deployment_info["region"]
except Exception:
    st.error("Deployment information not found. Please run deploy.py first.")
    st.stop()

agentcore_client = boto3.client('bedrock-agentcore', region_name=REGION)

def display_financial_analysis(trace_container, result):
    """Display financial analysis results"""
    trace_container.markdown("**Overall Assessment**")
    trace_container.info(result.get("summary", ""))

    col1, col2 = trace_container.columns(2)
    
    with col1:
        st.metric("**Risk Profile**", result.get("risk_profile", "N/A"))
        st.markdown("**Risk Profile Analysis**")
        st.write(result.get("risk_profile_reason", ""))
    
    with col2:
        st.metric("**Required Return**", f"{result.get('required_annual_return_rate', 'N/A')}%")
        
        # Display recommended investment sectors as tags
        st.markdown("**🎯 Recommended Investment Sectors**")
        sectors = result.get("key_sectors", [])
        tag_html = ""
        for sector in sectors:
            tag_html += f'<span style="background-color: #e8f5e8; color: #2e7d32; padding: 4px 8px; margin: 2px; border-radius: 12px; font-size: 12px; display: inline-block;">{sector}</span> '
        st.markdown(tag_html, unsafe_allow_html=True)

def display_calculator_result(trace_container, tool_input, result_text):
    """Display Calculator tool results"""
    trace_container.markdown("**Return Rate Calculated by Calculator Tool**")
    trace_container.code(f"Input: {tool_input}\n\n{result_text}", language="text")

def invoke_financial_advisor(input_data):
    """Invoke AgentCore Runtime"""
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": input_data})
        )

        placeholder = st.container()
        placeholder.markdown("🤖 **Financial Analyst**")

        current_thinking = ""
        current_text_placeholder = placeholder.empty()
        tool_id_to_name = {}
        tool_id_to_input = {}

        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    event_type = event_data.get("type")

                    if event_type == "text_chunk":
                        chunk_data = event_data.get("data", "")
                        current_thinking += chunk_data
                        if current_thinking.strip():
                            with current_text_placeholder.chat_message("assistant"):
                                st.markdown(current_thinking)
                    
                    elif event_type == "tool_use":
                        tool_name = event_data.get("tool_name", "")
                        tool_use_id = event_data.get("tool_use_id", "")
                        tool_input = event_data.get("tool_input", "")

                        actual_tool_name = tool_name.split("___")[-1] if "___" in tool_name else tool_name
                        tool_id_to_name[tool_use_id] = actual_tool_name
                        tool_id_to_input[tool_use_id] = tool_input
                    
                    elif event_type == "tool_result":
                        tool_use_id = event_data.get("tool_use_id", "")
                        actual_tool_name = tool_id_to_name.get(tool_use_id, "unknown")
                        tool_input = tool_id_to_input.get(tool_use_id, "unknown")
                        tool_content = event_data.get("content", [{}])
                        
                        if tool_content and len(tool_content) > 0:
                            result_text = tool_content[0].get("text", "{}")
                            
                            if actual_tool_name == "calculator":
                                display_calculator_result(placeholder, tool_input, result_text)
                        
                        current_thinking = ""
                        if tool_use_id in tool_id_to_name:
                            del tool_id_to_name[tool_use_id]
                        current_text_placeholder = placeholder.empty()
                    
                    elif event_type == "streaming_complete":
                        result_str = event_data.get("result", "")
                        result = json.loads(result_str)
                        
                        placeholder.divider()
                        placeholder.subheader("📌 Financial Analysis Results")
                        display_financial_analysis(placeholder, result)

                    elif event_type == "error":
                        return {"status": "error", "error": event_data.get("error", "Unknown error")}
                        
                except json.JSONDecodeError:
                    continue

        return {"status": "success"}

    except Exception as e:
        return {"status": "error", "error": str(e)}

# UI Configuration
with st.expander("🏗️ Financial Analyst Architecture", expanded=True):
    st.image("../static/financial_analyst.png")

# Input form
st.markdown("**Investor Information Input**")
col1, col2 = st.columns(2)

with col1:
    total_investable_amount = st.number_input(
        "💰 Available Investment Amount (in hundred millions)",
        min_value=0.0,
        max_value=1000.0,
        value=0.5,
        step=0.1,
        format="%.1f"
    )
    st.caption("e.g., 0.5 = 50 million")

with col2:
    target_amount = st.number_input(
        "🎯 Target Amount After 1 Year (in hundred millions)",
        min_value=0.0,
        max_value=1000.0,
        value=0.7,
        step=0.1,
        format="%.1f"
    )
    st.caption("e.g., 0.7 = 70 million")

col3, col4, col5 = st.columns(3)

with col3:
    age_options = [f"{i}-{i+4} years old" for i in range(20, 101, 5)]
    age = st.selectbox(
        "Age",
        options=age_options,
        index=3
    )

with col4:
    experience_categories = ["0-1 years", "1-3 years", "3-5 years", "5-10 years", "10-20 years", "20+ years"]
    stock_investment_experience_years = st.selectbox(
        "Stock Investment Experience",
        options=experience_categories,
        index=3
    )

with col5:
    investment_purpose = st.selectbox(
        "🎯 Investment Purpose",
        options=["Short-term Profit", "Retirement Planning", "Home Purchase Fund", "Education Fund", "Surplus Fund Management"],
        index=0
    )

preferred_sectors = st.multiselect(
    "📈 Investment Areas of Interest (Multiple Selection)",
    options=[
        "Dividend Stocks (Stable Dividends)",
        "Growth Stocks (Tech/Bio)",
        "Value Stocks (Undervalued Quality Stocks)", 
        "REITs (Real Estate Investment)",
        "Cryptocurrency (Digital Assets)",
        "Global Stocks (International Diversification)",
        "Bonds (Safe Assets)",
        "Commodities/Gold (Inflation Hedge)",
        "ESG/Green (Sustainable Investment)",
        "Infrastructure/Utilities (Essential Services)"
    ],
    default=["Growth Stocks (Tech/Bio)"]
)

submitted = st.button("Start Analysis", width='stretch')

if submitted:
    # Convert age range to number
    age_number = int(age.split('-')[0]) + 2
    
    # Convert experience years to number
    experience_mapping = {
        "0-1 years": 1,
        "1-3 years": 2,
        "3-5 years": 4,
        "5-10 years": 7,
        "10-20 years": 15,
        "20+ years": 25
    }
    experience_years = experience_mapping[stock_investment_experience_years]
    
    input_data = {
        "total_investable_amount": int(total_investable_amount * 100000000),
        "age": age_number,
        "stock_investment_experience_years": experience_years,
        "target_amount": int(target_amount * 100000000),
        "investment_purpose": investment_purpose,
        "preferred_sectors": preferred_sectors
    }
    
    st.divider()
    
    with st.spinner("AI Analysis in Progress..."):
        try:
            result = invoke_financial_advisor(input_data)
            
            if result['status'] == 'error':
                st.error(f"❌ An error occurred during analysis: {result.get('error', 'Unknown error')}")
                st.stop()
            
        except Exception as e:
            st.error(f"❌ An unexpected error occurred: {str(e)}")
            