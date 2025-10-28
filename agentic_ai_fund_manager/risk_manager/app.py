"""
app.py

Risk Manager Streamlit App
AI Risk Manager Web Interface
"""

import streamlit as st
import json
import boto3
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Risk Manager")
st.title("⚠️ Risk Manager")

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

def parse_tool_result(result_text):
    """Extract actual data from tool execution results"""
    parsed_result = json.loads(result_text)
    
    # Handle statusCode and body structure
    if "statusCode" in parsed_result and "body" in parsed_result:
        body = parsed_result["body"]
        # Parse JSON again if body is a string
        if isinstance(body, str):
            return json.loads(body)
        return body
    
    # Return directly
    return parsed_result

def display_news_data(container, news_data):
    """Display ETF news data"""
    try:
        if isinstance(news_data, str):
            data = json.loads(news_data)
        else:
            data = news_data
        
        ticker = data.get('ticker', 'Unknown')
        news_list = data.get('news', [])
        
        if not news_list:
            container.warning(f"{ticker}: No news data available.")
            return
        
        container.markdown(f"**📰 {ticker} Latest News**")
        
        news_df = pd.DataFrame(news_list)
        if not news_df.empty and all(col in news_df.columns for col in ['publish_date', 'title', 'summary']):
            container.dataframe(
                news_df[['publish_date', 'title', 'summary']],
                hide_index=True,
                width="stretch"
            )
        else:
            for i, news_item in enumerate(news_list[:5], 1):
                with container.expander(f"{i}. {news_item.get('title', 'No Title')}"):
                    st.write(f"**Published:** {news_item.get('publish_date', 'Unknown')}")
                    st.write(f"**Summary:** {news_item.get('summary', 'No summary available')}")
                
    except Exception as e:
        container.error(f"News data display error: {str(e)}")

def display_market_data(container, market_data):
    """Display macroeconomic indicator data"""
    try:
        if isinstance(market_data, str):
            data = json.loads(market_data)
        else:
            data = market_data
        
        container.markdown("**📊 Key Macroeconomic Indicators**")
        
        indicators = {k: v for k, v in data.items() if not k.startswith('_')}
        
        indicator_items = list(indicators.items())
        for i in range(0, len(indicator_items), 3):
            cols = container.columns(3)
            for j, (key, info) in enumerate(indicator_items[i:i+3]):
                if j < len(cols):
                    with cols[j]:
                        if isinstance(info, dict) and 'value' in info:
                            description = info.get('description', key)
                            value = info['value']
                            st.metric(description, f"{value}")
                        else:
                            st.write(f"**{key}**: No data available")
                
    except Exception as e:
        container.error(f"Market data display error: {str(e)}")

def display_geopolitical_data(container, geopolitical_data):
    """Display geopolitical risk indicator data"""
    try:
        if isinstance(geopolitical_data, str):
            data = json.loads(geopolitical_data)
        else:
            data = geopolitical_data
        
        container.markdown("**🌍 Major Regional ETFs (Geopolitical Risk)**")
        
        indicators = {k: v for k, v in data.items() if not k.startswith('_')}
        
        indicator_items = list(indicators.items())
        for i in range(0, len(indicator_items), 3):
            cols = container.columns(3)
            for j, (key, info) in enumerate(indicator_items[i:i+3]):
                if j < len(cols):
                    with cols[j]:
                        if isinstance(info, dict) and 'value' in info:
                            description = info.get('description', key)
                            value = info['value']
                            st.metric(description, f"{value}")
                        else:
                            st.write(f"**{key}**: No data available")
                
    except Exception as e:
        container.error(f"Geopolitical data display error: {str(e)}")

def display_risk_analysis_result(container, analysis_content):
    """Display final risk analysis results"""
    try:
        data = json.loads(analysis_content)
        if not data:
            container.error("Risk analysis data not found.")
            return
        
        for i, scenario_key in enumerate(["scenario1", "scenario2"], 1):
            if scenario_key in data:
                scenario = data[scenario_key]
                
                container.subheader(f"Scenario {i}: {scenario.get('name', f'Scenario {i}')}")
                container.markdown(scenario.get('description', 'No description available'))
                
                # Display scenario probability (moved to top)
                probability_str = scenario.get('probability', '0%')
                try:
                    prob_value = int(probability_str.replace('%', ''))
                    container.markdown(f"**📊 Probability: {probability_str}**")
                    container.progress(prob_value / 100)
                except:
                    container.markdown(f"**📊 Probability: {probability_str}**")
                
                col1, col2 = container.columns(2)
                
                with col1:
                    st.markdown("**Adjusted Portfolio Allocation**")
                    allocation = scenario.get('allocation_management', {})
                    if allocation:
                        fig = go.Figure(data=[go.Pie(
                            labels=list(allocation.keys()),
                            values=list(allocation.values()),
                            hole=.3,
                            textinfo='label+percent'
                        )])
                        fig.update_layout(height=400, title=f"Scenario {i} Portfolio")
                        st.plotly_chart(fig, config={'displayModeBar': False})
                
                with col2:
                    st.markdown("**Adjustment Reasoning and Strategy**")
                    st.info(scenario.get('reason', 'No reasoning provided'))
        
    except Exception as e:
        container.error(f"Risk analysis display error: {str(e)}")
        container.text(str(analysis_content))

def invoke_risk_manager(portfolio_data):
    """Invoke Risk Manager"""
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": portfolio_data})
        )
        
        placeholder = st.container()
        placeholder.subheader("Reasoning")
        
        current_thinking = ""
        current_text_placeholder = placeholder.empty()
        tool_id_to_name = {}

        for line in response["response"].iter_lines(chunk_size=1):
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
                    actual_tool_name = tool_name.split("___")[-1] if "___" in tool_name else tool_name
                    tool_id_to_name[tool_use_id] = actual_tool_name
                
                elif event_type == "tool_result":
                    tool_use_id = event_data.get("tool_use_id", "")
                    actual_tool_name = tool_id_to_name.get(tool_use_id, "unknown")
                    
                    tool_content = event_data.get("content", [{}])
                    if tool_content and len(tool_content) > 0:
                        result_text = tool_content[0].get("text", "{}")
                        body = parse_tool_result(result_text)
                        
                        if actual_tool_name == "get_product_news":
                            display_news_data(placeholder, body)
                        elif actual_tool_name == "get_market_data":
                            display_market_data(placeholder, body)
                        elif actual_tool_name == "get_geopolitical_indicators":
                            display_geopolitical_data(placeholder, body)

                    current_thinking = ""
                    if tool_use_id in tool_id_to_name:
                        del tool_id_to_name[tool_use_id]
                    current_text_placeholder = placeholder.empty()
                
                elif event_type == "streaming_complete":
                    result_str = event_data.get("result", "")
                    
                    # Display final results
                    placeholder.divider()
                    placeholder.subheader("📌 Risk Analysis and Scenario Planning")
                    display_risk_analysis_result(placeholder, result_str)
                    
            except json.JSONDecodeError:
                continue
        
        return {"status": "success"}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

# UI Configuration
with st.expander("🏗️ Risk Manager Architecture", expanded=True):
    st.image("../static/risk_manager.png")
st.markdown("**Portfolio Configuration Input**")

# Portfolio allocation input
st.markdown("**Portfolio Allocation**")
col1, col2, col3 = st.columns(3)
with col1:
    ticker1 = st.text_input("ETF 1", value="QQQ")
    allocation1 = st.number_input("Allocation 1 (%)", min_value=0, max_value=100, value=60)
with col2:
    ticker2 = st.text_input("ETF 2", value="SPY")
    allocation2 = st.number_input("Allocation 2 (%)", min_value=0, max_value=100, value=30)
with col3:
    ticker3 = st.text_input("ETF 3", value="GLD")
    allocation3 = st.number_input("Allocation 3 (%)", min_value=0, max_value=100, value=10)

reason = st.text_area("Portfolio Composition Reasoning and Investment Strategy", value="Aggressive portfolio focused on high-growth technology stocks, designed to achieve high target returns for clients with aggressive risk tolerance", height=100)

# Portfolio Scores input
st.markdown("**Portfolio Evaluation Scores**")
col1, col2, col3 = st.columns(3)
with col1:
    profitability_score = st.number_input("Profitability (1-10)", min_value=1, max_value=10, value=8)
    profitability_reason = st.text_input("Profitability Assessment Reasoning", value="High probability of achieving target returns")
with col2:
    risk_score = st.number_input("Risk Management (1-10)", min_value=1, max_value=10, value=6)
    risk_reason = st.text_input("Risk Management Assessment Reasoning", value="Risk management needed due to high volatility")
with col3:
    diversification_score = st.number_input("Diversification (1-10)", min_value=1, max_value=10, value=7)
    diversification_reason = st.text_input("Diversification Assessment Reasoning", value="Some correlation exists but adequate diversification")

submitted = st.button("Start Risk Analysis", width='stretch')

if submitted:
    st.divider()
    
    with st.spinner("AI Analysis in Progress..."):
        portfolio_dict = {
            "portfolio_allocation": {
                ticker1: allocation1,
                ticker2: allocation2,
                ticker3: allocation3
            },
            "reason": reason,
            "portfolio_scores": {
                "profitability": {"score": profitability_score, "reason": profitability_reason},
                "risk_management": {"score": risk_score, "reason": risk_reason},
                "diversification": {"score": diversification_score, "reason": diversification_reason}
            }
        }
        
        result = invoke_risk_manager(portfolio_dict)
        
        if result['status'] == 'error':
            st.error(f"❌ Analysis error: {result.get('error', 'Unknown error')}")