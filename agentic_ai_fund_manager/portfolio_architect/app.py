"""
app.py

Portfolio Architect Streamlit App
AI Portfolio Designer Web Interface
"""

import streamlit as st
import json
import boto3
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Portfolio Architect")
st.title("🤖 Portfolio Architect")

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

def display_portfolio_result(container, portfolio_content):
    """Display final portfolio results"""
    try:
        data = json.loads(portfolio_content)
        if not data:
            container.error("Portfolio data not found.")
            return
        
        col1, col2 = container.columns(2)
        
        with col1:
            st.markdown("**Portfolio Allocation**")
            fig = go.Figure(data=[go.Pie(
                labels=list(data["portfolio_allocation"].keys()),
                values=list(data["portfolio_allocation"].values()),
                hole=.3,
                textinfo='label+percent'
            )])
            fig.update_layout(height=400)
            st.plotly_chart(fig)
        
        with col2:
            st.markdown("**Portfolio Composition Rationale**")
            st.info(data["reason"])
        
        # Display Portfolio Scores
        if "portfolio_scores" in data:
            container.markdown("**Portfolio Evaluation Scores**")
            scores = data["portfolio_scores"]
            
            col1, col2, col3 = container.columns(3)
            with col1:
                profitability = scores.get("profitability", {})
                st.metric("Profitability", f"{profitability.get('score', 'N/A')}/10")
                if profitability.get('reason'):
                    st.caption(profitability['reason'])
            
            with col2:
                risk_mgmt = scores.get("risk_management", {})
                st.metric("Risk Management", f"{risk_mgmt.get('score', 'N/A')}/10")
                if risk_mgmt.get('reason'):
                    st.caption(risk_mgmt['reason'])
            
            with col3:
                diversification = scores.get("diversification", {})
                st.metric("Diversification", f"{diversification.get('score', 'N/A')}/10")
                if diversification.get('reason'):
                    st.caption(diversification['reason'])
        

        
    except Exception as e:
        container.error(f"Portfolio display error: {e}")

def display_correlation_analysis(container, correlation_data):
    """Display correlation analysis results"""
    try:
        container.markdown("**🔗 ETF Correlation Matrix**")
        
        correlation_matrix = correlation_data.get('correlation_matrix', {})
        
        if correlation_matrix:
            # Convert correlation matrix to DataFrame
            df = pd.DataFrame(correlation_matrix)
            
            # Display as heatmap
            fig = px.imshow(
                df.values,
                x=df.columns,
                y=df.index,
                color_continuous_scale='RdBu_r',
                aspect="auto",
                text_auto=True,
                color_continuous_midpoint=0,
                zmin=-1,
                zmax=1
            )
            
            fig.update_layout(
                title="ETF Correlation Matrix",
                height=400,
                xaxis_title="ETF",
                yaxis_title="ETF"
            )
            
            fig.update_traces(texttemplate="%{z:.2f}", textfont_size=12)
            container.plotly_chart(fig, config={'displayModeBar': False})
            
            # Correlation interpretation
            container.markdown("**Correlation Interpretation**")
            container.info("""
            - **0.7 and above**: High correlation (limited diversification effect)
            - **0.3~0.7**: Medium correlation (moderate diversification effect)
            - **Below 0.3**: Low correlation (good diversification effect)
            """)
        
    except Exception as e:
        container.error(f"Correlation analysis display error: {e}")

def display_etf_analysis_result(container, etf_data):
    """Display individual ETF analysis results"""
    try:
        container.markdown(f"**📊 {etf_data['ticker']} Analysis Results (Monte Carlo Simulation)**")
        
        # Basic indicators
        col1, col2, col3, col4 = container.columns(4)
        
        with col1:
            st.metric(
                "Expected Return", 
                f"{etf_data['expected_annual_return']}%"
            )
        
        with col2:
            st.metric(
                "Loss Probability", 
                f"{etf_data['loss_probability']}%"
            )
        
        with col3:
            st.metric(
                "Volatility", 
                f"{etf_data['volatility']}%"
            )
        
        with col4:
            st.metric(
                "Historical Return", 
                f"{etf_data['historical_annual_return']}%"
            )
        
        # Return distribution chart
        if 'return_distribution' in etf_data:
            distribution = etf_data['return_distribution']
            ranges = list(distribution.keys())
            counts = list(distribution.values())
            
            fig = go.Figure(data=[
                go.Bar(
                    x=ranges,
                    y=counts,
                    text=[f"{count} times<br>({count/5:.1f}%)" for count in counts],
                    textposition='auto',
                    marker_color='lightblue',
                    name=etf_data['ticker']
                )
            ])
            
            fig.update_layout(
                title=f"Expected Return Distribution After 1 Year (1000 Simulations)",
                xaxis_title="Return Range",
                yaxis_title="Number of Scenarios",
                height=400,
                showlegend=False
            )
            
            container.plotly_chart(fig, config={'displayModeBar': False})
        
    except Exception as e:
        container.error(f"ETF analysis result display error: {e}")

def invoke_portfolio_architect(financial_analysis):
    """Invoke Portfolio Architect"""
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": financial_analysis})
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
                        try:
                            body = json.loads(result_text)
                        except:
                            body = result_text
                        
                        if actual_tool_name == "analyze_etf_performance":
                            display_etf_analysis_result(placeholder, body)
                        elif actual_tool_name == "calculate_correlation":
                            display_correlation_analysis(placeholder, body)
                    
                    current_thinking = ""
                    if tool_use_id in tool_id_to_name:
                        del tool_id_to_name[tool_use_id]
                    current_text_placeholder = placeholder.empty()
                
                elif event_type == "streaming_complete":
                    result_str = event_data.get("result", "")
                    
                    # Display final results
                    placeholder.divider()
                    placeholder.subheader("📌 Portfolio Design Results")
                    display_portfolio_result(placeholder, result_str)
                    
            except json.JSONDecodeError:
                continue
        
        return {"status": "success"}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

# UI Configuration
with st.expander("🏗️ Portfolio Architect Architecture", expanded=True):
    st.image("../static/portfolio_architect.png")

st.markdown("**Financial Analysis Results Input**")

risk_profile = st.text_input("Risk Profile", value="Aggressive")
risk_profile_reason = st.text_input("Risk Profile Reasoning", value="35 years old, aggressive investment preference")
required_return = st.number_input("Required Annual Return (%)", value=40.0)
key_sectors = st.multiselect(
    "Recommended Investment Areas", 
    options=[
        "Technology Stocks", "Healthcare", "Financial", 
        "Consumer", "Energy", "Real Estate", 
        "Utilities", "Industrial", "Materials", 
        "Cryptocurrency"
    ],
    default=["Technology Stocks", "Healthcare"]
)
summary = st.text_area("Overall Assessment", value="Aggressive investment strategy required for high target returns.")

if st.button("Start Analysis", width='stretch'):
    financial_analysis = {
        "risk_profile": risk_profile,
        "risk_profile_reason": risk_profile_reason,
        "required_annual_return_rate": required_return,
        "key_sectors": key_sectors,
        "summary": summary
    }
    
    st.divider()
    
    with st.spinner("AI Analysis in Progress..."):
        result = invoke_portfolio_architect(financial_analysis)
        
        if result['status'] == 'error':
            st.error(f"❌ Analysis error: {result.get('error', 'Unknown error')}")