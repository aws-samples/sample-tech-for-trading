"""
app.py

Fund Manager Streamlit App
AI Fund Manager Web Interface
"""

import streamlit as st
import os
import json
import boto3
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
from pathlib import Path
from bedrock_agentcore.memory import MemoryClient

st.set_page_config(
    page_title="🤖 Agentic AI Fund Manager",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("🤖 Agentic AI Fund Manager")

# Session management initialization - automatically generated on page load
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Sidebar menu
menu = st.sidebar.selectbox(
    "Select Menu",
    ["🤖 New Fund Management", "📚 Management History (Long-term Memory)"]
)

# Display session information in sidebar
st.sidebar.divider()
st.sidebar.success(f"**Current Session**: {st.session_state.current_session_id}")
st.sidebar.caption("Automatically generated on page load")

# Session reset button
if st.sidebar.button("🔄 Start New Session"):
    st.session_state.current_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    st.rerun()

# Load deployment information (environment variables first, then local JSON files)
def load_deployment_info():
    """Load deployment information from environment variables or local JSON files"""
    # Try environment variables first (Docker container environment)
    agent_arn = os.getenv("BWB_FUND_MANAGER_ARN")
    memory_id = os.getenv("BWB_MEMORY_ID") 
    region = os.getenv("BWB_AWS_REGION")
    
    if agent_arn and memory_id and region:
        # Docker environment: set static folder path
        return agent_arn, memory_id, region, "static"
    
    # If no environment variables, load from local JSON files (local development environment)
    try:
        with open(Path(__file__).parent / "deployment_info.json") as f:
            deployment_info = json.load(f)
        agent_arn = deployment_info["agent_arn"]
        region = deployment_info["region"]
        
        with open(Path(__file__).parent / "agentcore_memory" / "deployment_info.json") as f:
            memory_info = json.load(f)
        memory_id = memory_info["memory_id"]
        
        # Local environment: set static folder path
        return agent_arn, memory_id, region, "../static"
        
    except Exception as e:
        st.error(f"Deployment information not found. Please set environment variables (FUND_MANAGER_ARN, MEMORY_ID, AWS_REGION) or run deploy.py first. Error: {e}")
        st.stop()

AGENT_ARN, MEMORY_ID, REGION, STATIC_PATH = load_deployment_info()

agentcore_client = boto3.client('bedrock-agentcore', region_name=REGION)
memory_client = MemoryClient(region_name=REGION)

def display_calculator_result(container, tool_input, result_text):
    """Display Calculator tool results"""
    container.markdown("**Return Rate Calculated by Calculator Tool**")
    container.code(f"Input: {tool_input}\n\n{result_text}", language="text")

def display_etf_analysis_result(container, etf_data):
    """Display individual ETF analysis results"""
    try:
        container.markdown(f"**📊 {etf_data['ticker']} Analysis Results (Monte Carlo Simulation)**")
        
        col1, col2, col3, col4 = container.columns(4)
        
        with col1:
            st.metric("Expected Return", f"{etf_data['expected_annual_return']}%")
        with col2:
            st.metric("Loss Probability", f"{etf_data['loss_probability']}%")
        with col3:
            st.metric("Volatility", f"{etf_data['volatility']}%")
        with col4:
            st.metric("Historical Return", f"{etf_data['historical_annual_return']}%")
        
        if 'return_distribution' in etf_data:
            distribution = etf_data['return_distribution']
            ranges = list(distribution.keys())
            counts = list(distribution.values())
            
            fig = go.Figure(data=[go.Bar(
                x=ranges,
                y=counts,
                text=[f"{count} times<br>({count/5:.1f}%)" for count in counts],
                textposition='auto',
                marker_color='lightblue',
                name=etf_data['ticker']
            )])
            
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

def display_correlation_analysis(container, correlation_data):
    """Display correlation analysis results"""
    try:
        container.markdown("**🔗 ETF Correlation Matrix**")
        
        correlation_matrix = correlation_data.get('correlation_matrix', {})
        
        if correlation_matrix:
            df = pd.DataFrame(correlation_matrix)
            
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
            
            container.markdown("**Correlation Interpretation**")
            container.info("""
            - **0.7 and above**: High correlation (limited diversification effect)
            - **0.3~0.7**: Medium correlation (moderate diversification effect)
            - **Below 0.3**: Low correlation (good diversification effect)
            """)
        
    except Exception as e:
        container.error(f"Correlation analysis display error: {e}")

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

def display_financial_analysis(container, analysis_content):
    """Display financial analysis results"""
    data = json.loads(analysis_content)
    
    container.markdown("**Overall Assessment**")
    container.info(data.get("summary", ""))

    col1, col2 = container.columns(2)
    
    with col1:
        st.metric("**Risk Profile**", data.get("risk_profile", "N/A"))
        st.markdown("**Risk Profile Analysis**")
        st.write(data.get("risk_profile_reason", ""))
    
    with col2:
        st.metric("**Required Return**", f"{data.get('required_annual_return_rate', 'N/A')}%")
        
        # Display recommended fund investment sectors as tags
        st.markdown("**🎯 Recommended Fund Investment Sectors**")
        sectors = data.get("key_sectors", [])
        tag_html = ""
        for sector in sectors:
            tag_html += f'<span style="background-color: #e1f5fe; color: #01579b; padding: 4px 8px; margin: 2px; border-radius: 12px; font-size: 12px; display: inline-block;">{sector}</span> '
        st.markdown(tag_html, unsafe_allow_html=True)

def display_portfolio_result(container, portfolio_content):
    """Display portfolio design results"""
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
        container.error(f"Portfolio display error: {str(e)}")

def display_risk_analysis_result(container, analysis_content):
    """Display risk analysis results"""
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

def invoke_fund_manager(input_data, session_id):
    """Invoke Fund Manager - Pass session ID"""
    try:
        # Include session ID in payload
        payload_data = {
            "input_data": input_data,
            "session_id": session_id
        }
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps(payload_data)
        )
        
        progress_container = st.container()
        results_container = st.container()
        
        current_agent = None
        agent_containers = {}
        agent_thinking_containers = {}
        current_thinking = {}
        current_text_placeholders = {}
        tool_id_to_name = {}
        tool_id_to_input = {}
        
        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    event_type = event_data.get("type")
                    
                    if event_type == "text_chunk":
                        chunk_data = event_data.get("data", "")
                        if current_agent and current_agent in current_thinking:
                            current_thinking[current_agent] += chunk_data
                            if current_thinking[current_agent].strip() and current_agent in current_text_placeholders:
                                # Display in chat format inside expander
                                with current_text_placeholders[current_agent].chat_message("assistant"):
                                    st.markdown(current_thinking[current_agent])
                    
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
                        
                        if tool_content and len(tool_content) > 0 and current_agent in agent_thinking_containers:
                            result_text = tool_content[0].get("text", "{}")
                            container = agent_thinking_containers[current_agent]
                            
                            if current_agent == "financial" and actual_tool_name == "calculator":
                                display_calculator_result(container, tool_input, result_text)
                            elif current_agent == "portfolio":
                                try:
                                    body = json.loads(result_text)
                                    if actual_tool_name == "analyze_etf_performance":
                                        display_etf_analysis_result(container, body)
                                    elif actual_tool_name == "calculate_correlation":
                                        display_correlation_analysis(container, body)
                                except:
                                    pass
                            elif current_agent == "risk":
                                try:
                                    parsed_result = json.loads(result_text)
                                    if "statusCode" in parsed_result and "body" in parsed_result:
                                        body = parsed_result["body"]
                                        if isinstance(body, str):
                                            body = json.loads(body)
                                    else:
                                        body = parsed_result
                                    
                                    if actual_tool_name == "get_product_news":
                                        display_news_data(container, body)
                                    elif actual_tool_name == "get_market_data":
                                        display_market_data(container, body)
                                    elif actual_tool_name == "get_geopolitical_indicators":
                                        display_geopolitical_data(container, body)
                                except:
                                    pass
                        
                        if current_agent:
                            current_thinking[current_agent] = ""
                            if tool_use_id in tool_id_to_name:
                                del tool_id_to_name[tool_use_id]
                            if tool_use_id in tool_id_to_input:
                                del tool_id_to_input[tool_use_id]
                            if current_agent in current_text_placeholders:
                                current_text_placeholders[current_agent] = agent_thinking_containers[current_agent].empty()
                    
                    elif event_type == "node_start":
                        agent_name = event_data.get("agent_name")
                        current_agent = agent_name
                        
                        agent_display_names = {
                            "financial": "Financial Analyst",
                            "portfolio": "Portfolio Architect", 
                            "risk": "Risk Manager"
                        }
                        
                        agent_containers[agent_name] = results_container.container()
                        
                        # Wrap reasoning process in expander
                        thinking_expander = agent_containers[agent_name].expander(f"🧠 {agent_display_names.get(agent_name, agent_name)} Reasoning", expanded=True)
                        agent_thinking_containers[agent_name] = thinking_expander.container()
                        
                        current_thinking[agent_name] = ""
                        current_text_placeholders[agent_name] = agent_thinking_containers[agent_name].empty()
                        
                    elif event_type == "node_complete":
                        agent_name = event_data.get("agent_name")
                        result = event_data.get("result")
                        
                        if agent_name in agent_containers and result:
                            container = agent_containers[agent_name]
                            
                            # Display final results outside expander (main area)
                            if agent_name == "financial":
                                container.subheader("📌 Financial Analysis Results")
                                display_financial_analysis(container, result)
                                container.divider()
                                
                            elif agent_name == "portfolio":
                                container.subheader("📌 Portfolio Design Results")
                                display_portfolio_result(container, result)
                                container.divider()
                                
                            elif agent_name == "risk":
                                container.subheader("📌 Risk Analysis and Scenario Planning")
                                display_risk_analysis_result(container, result)
                                container.divider()
                        


                    elif event_type == "error":
                        return {"status": "error", "error": event_data.get("error", "Unknown error")}
                        
                except json.JSONDecodeError:
                    continue
        
        # Display analysis completion message at the bottom of results_container
        with results_container:
            st.success("🎉 All Agent Analysis Complete!")
            st.info("💾 This fund management content is automatically summarized and stored in AgentCore Memory. You can check it in the 📚 Management History menu on the left.")

        return {"status": "success"}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def load_current_session_summary():
    """Load current session's Long-term Memory summary"""
    try:
        # Query current session's SUMMARY strategy results
        current_session = st.session_state.current_session_id
        session_namespace = f"fund/session/{current_session}"
        
        response = memory_client.retrieve_memories(
            memory_id=MEMORY_ID,
            namespace=session_namespace,
            query="fund management summary"
        )
        
        if response and len(response) > 0:
            # Return the latest summary
            latest_record = response[0]
            
            # Extract content
            content = latest_record.get('content', {})
            content_text = content.get('text', str(content)) if isinstance(content, dict) else str(content)
            
            # Extract timestamp
            timestamp = latest_record.get('createdAt', latest_record.get('created_at', 'Unknown'))
            timestamp_str = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
            
            return {
                'session_id': current_session,
                'timestamp': timestamp_str,
                'content': content_text,
                'found': True
            }
        else:
            return {
                'session_id': current_session,
                'found': False
            }
        
    except Exception as e:
        st.error(f"Current session Memory query failed: {e}")
        return {
            'session_id': st.session_state.current_session_id,
            'found': False,
            'error': str(e)
        }

# UI configuration by menu
if menu == "🤖 New Fund Management":
    with st.expander("🏗️ Fund Manager Architecture", expanded=True):
        st.image(os.path.join(STATIC_PATH, "fund_manager.png"))


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
        # Use existing session (already created on page load)
        
        age_number = int(age.split('-')[0]) + 2
        
        experience_mapping = {
            "0-1 years": 1, "1-3 years": 2, "3-5 years": 4, 
            "5-10 years": 7, "10-20 years": 15, "20+ years": 25
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
            result = invoke_fund_manager(
                input_data, 
                st.session_state.current_session_id
            )
            
            if result['status'] == 'error':
                st.error(f"❌ Analysis error: {result.get('error', 'Unknown error')}")

elif menu == "📚 Management History (Long-term Memory)":
    st.markdown("### 📚 Current Session Fund Management Summary")
    st.info(f"You can check the automatic summary of current session **{st.session_state.current_session_id}** using AgentCore SUMMARY strategy.")
    
    if st.button("🔄 Refresh Summary", width='stretch'):
        st.rerun()
    
    with st.spinner("Loading current session's Long-term Memory..."):
        summary_data = load_current_session_summary()
    
    if not summary_data['found']:
        if 'error' in summary_data:
            st.error(f"Error occurred while querying summary: {summary_data['error']}")
        else:
            st.warning("Fund management summary for the current session has not been generated yet.")
            st.markdown("""
            **Summary Generation Conditions:**
            - Fund management consultation must be completed (all 3 agents executed)
            - AgentCore SUMMARY strategy automatically generates summaries
            - Summary generation may take a few minutes
            """)
    else:
        # Format time display for better readability
        timestamp = summary_data['timestamp']
        try:
            if isinstance(timestamp, str) and 'T' in timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_display = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_display = str(timestamp)
        except:
            time_display = str(timestamp)
        
        content = summary_data['content']
        
        # Simple processing of XML-format summary
        if isinstance(content, str):
            st.markdown("## 📋 Fund Management Consultation Summary")
            
            # Extract and display topics from XML
            import re
            topics = re.findall(r'<topic name="([^"]+)">\s*(.*?)\s*</topic>', content, re.DOTALL)
            
            if topics:
                for topic_name, topic_content in topics:
                    st.subheader(f"📌 {topic_name}")
                    # HTML entity decoding
                    clean_content = topic_content.replace('&quot;', '"').replace('&#39;', "'")
                    st.write(clean_content.strip())
                    st.divider()
            else:
                # Display original content if XML parsing fails
                st.text(content)
        else:
            # General text processing
            st.markdown("## 📋 Fund Management Consultation Summary")
            st.write(content)
