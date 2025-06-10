import streamlit as st
import json
import os
import financial_analyst_lib as flib

# Config
FINANCIAL_ANALYST_ID = ""
FINANCIAL_ANALYST_REFLECTION_ID = ""

# Functions
def display_financial_analysis(trace_container, input_content):
    """Display financial analysis results"""
    data = json.loads(input_content, strict=False)
    sub_col1, sub_col2 = trace_container.columns(2)
    
    with sub_col1:
        st.metric("**Risk Profile**", data["risk_profile"])
        st.markdown("**Risk Profile Analysis**")
        st.info(data["risk_profile_reason"])
    
    with sub_col2:
        st.metric("**Required Return Rate**", f"{data['required_annual_return_rate']}%")
        st.markdown("**Return Rate Analysis**")
        st.info(data["return_rate_reason"])

def display_reflection_result(trace_container, input_content):
    """Display reflection analysis results"""
    if input_content.strip().lower() == "yes":
        trace_container.success("Financial Analysis Review Successful")
    else:
        trace_container.error("Financial Analysis Review Failed")
        trace_container.markdown(input_content[3:])

# Page setup
st.set_page_config(page_title="Financial Analyst")

st.title("🤖 Financial Analyst")

with st.expander("Architecture", expanded=True):
    st.image(os.path.join("../../dataset/images/financial_analyst.png"))

# Input form
st.markdown("**Enter Investor Information**")
col1, col2, col3 = st.columns(3)

with col1:
    total_investable_amount = st.number_input(
        "💰 Total Investable Amount (in USD)",
        min_value=0,
        max_value=10000000,
        value=50000,
        step=1000,
        format="%d"
    )
    st.caption("Example: 50000 = $50,000")

with col2:
    age_options = [f"{i}-{i+4} years" for i in range(20, 101, 5)]
    age = st.selectbox(
        "Age",
        options=age_options,
        index=3
    )

with col3:
    experience_categories = ["0-1 year", "1-3 years", "3-5 years", "5-10 years", "10-20 years", "20+ years"]
    stock_investment_experience_years = st.selectbox(
        "Stock Investment Experience",
        options=experience_categories,
        index=3
    )

target_amount = st.number_input(
    "💰 Target Amount After 1 Year (in USD)",
    min_value=0,
    max_value=10000000,
    value=70000,
    step=1000,
    format="%d"
)
st.caption("Example: 70000 = $70,000")

submitted = st.button("Start Analysis", use_container_width=True)

if submitted:
    input_data = {
        "total_investable_amount": total_investable_amount,
        "age": age,
        "stock_investment_experience_years": stock_investment_experience_years,
        "target_amount": target_amount,
    }
    
    st.divider()
    placeholder = st.container()
    
    with st.spinner("AI is processing..."):
        # Financial Analysis
        placeholder.markdown("🤖 **Financial Analyst**")
        placeholder.subheader("📌 Financial Analysis")
        
        response = flib.get_prompt_management_response(
            FINANCIAL_ANALYST_ID,
            "user_input",
            json.dumps(input_data)
        )
        content = response['output']['message']['content'][0]['text']
        display_financial_analysis(placeholder, content)
        
        # Reflection Analysis
        placeholder.subheader("")
        placeholder.subheader("📌 Financial Analysis Review (Reflection)")
        
        reflection_response = flib.get_prompt_management_response(
            FINANCIAL_ANALYST_REFLECTION_ID,
            "finance_result",
            content
        )
        reflection_content = reflection_response['output']['message']['content'][0]['text']
        display_reflection_result(placeholder, reflection_content)