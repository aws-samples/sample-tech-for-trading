import risk_manager_lib as rlib
import json
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os
import uuid
import itertools

# Config
RISK_MANAGER_AGENT_ID = ""
RISK_MANAGER_AGENT_ALIAS_ID = ""

# Functions
def display_market_data(trace_container, trace):
    """Display market data"""
    data_text = trace.get('observation', {}).get('actionGroupInvocationOutput', {}).get('text')
    market_data = json.loads(data_text)
    
    trace_container.markdown("**Key Market Indicators**")
    for i in range(0, len(market_data), 3):
        cols = trace_container.columns(3)
        for j, (key, info) in enumerate(itertools.islice(market_data.items(), i, i + 3)):
            with cols[j]:
                st.metric(info['description'], f"{info['value']}")

def display_product_news(trace_container, trace):
    """Display news for investment products"""
    news_text = trace.get('observation', {}).get('actionGroupInvocationOutput', {}).get('text')
    news_data = json.loads(news_text)
    
    ticker = news_data["ticker"]
    trace_container.markdown(f"**Recent News for {ticker}**")
    news_df = pd.DataFrame(news_data["news"])
    trace_container.dataframe(
        news_df[['publish_date', 'title', 'summary']],
        hide_index=True,
        use_container_width=True
    )

def create_pie_chart(data, chart_title=""):
    """Create a pie chart for portfolio allocation"""
    fig = go.Figure(data=[go.Pie(
        labels=list(data.keys()),
        values=list(data.values()),
        hole=.3,
        textinfo='label+percent',
        marker=dict(colors=px.colors.qualitative.Set3)
    )])
    
    fig.update_layout(
        title=chart_title,
        showlegend=True,
        width=400,
        height=400
    )
    return fig

def display_risk_analysis(place_holder, input_content):
    """Display risk analysis results"""
    data = json.loads(input_content, strict=False)
    
    for i, scenario in enumerate(["scenario1", "scenario2"], 1):
        place_holder.subheader(f"Scenario {i}: {data[scenario]['name']}")
        place_holder.markdown(data[scenario]['description'])
        
        sub_col1, sub_col2 = place_holder.columns([1, 1])
        
        with sub_col1:
            fig = create_pie_chart(
                data[scenario]["allocation_management"],
                "Adjusted Portfolio Asset Allocation"
            )
            st.plotly_chart(fig)
        
        with sub_col2:
            st.markdown("**Adjustment Rationale and Strategy**")
            st.info(data[scenario]["reason"])

# Page setup
st.set_page_config(page_title="Risk Manager")

st.title("🤖 Risk Manager")

with st.expander("Architecture", expanded=True):
    st.image(os.path.join("../../dataset/images/risk_manager.png"))

# Input form
st.markdown("**Enter Portfolio Design (🤖 Portfolio Architect)**")

portfolio_design = st.text_area(
    "JSON format",
    height=200
)

submitted = st.button("Start Analysis", use_container_width=True)

if submitted and portfolio_design:
    st.divider()
    placeholder = st.container()
    
    with st.spinner("AI is processing..."):
        response = rlib.get_agent_response(
            RISK_MANAGER_AGENT_ID,
            RISK_MANAGER_AGENT_ALIAS_ID,
            str(uuid.uuid4()),
            portfolio_design
        )
        
        placeholder.subheader("Bedrock Reasoning")
        
        output_text = ""
        function_name = ""
        
        for event in response.get("completion"):
            if "chunk" in event:
                chunk = event["chunk"]
                output_text += chunk["bytes"].decode()
            
            if "trace" in event:
                each_trace = event["trace"]["trace"]
                
                if "orchestrationTrace" in each_trace:
                    trace = event["trace"]["trace"]["orchestrationTrace"]
                    
                    if "rationale" in trace:
                        with placeholder.chat_message("ai"):
                            st.markdown(trace['rationale']['text'])
                    
                    elif function_name != "":
                        if function_name == "get_market_data":
                            display_market_data(placeholder, trace)
                        elif function_name == "get_product_news":
                            display_product_news(placeholder, trace)

                        function_name = ""
                    
                    else:
                        function_name = trace.get('invocationInput', {}).get('actionGroupInvocationInput', {}).get(
                            'function', "")
        
        placeholder.divider()
        placeholder.markdown("🤖 **Risk Manager**")
        placeholder.subheader("📌 Risk Analysis")
        display_risk_analysis(placeholder, output_text)