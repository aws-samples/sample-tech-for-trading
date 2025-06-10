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
        st.metric("**위험 성향**", data["risk_profile"])
        st.markdown("**위험 성향 분석**")
        st.info(data["risk_profile_reason"])
    
    with sub_col2:
        st.metric("**필요 수익률**", f"{data['required_annual_return_rate']}%")
        st.markdown("**수익률 분석**")
        st.info(data["return_rate_reason"])

def display_reflection_result(trace_container, input_content):
    """Display reflection analysis results"""
    if input_content.strip().lower() == "yes":
        trace_container.success("재무분석 검토 성공")
    else:
        trace_container.error("재무분석 검토 실패")
        trace_container.markdown(input_content[3:])

# Page setup
st.set_page_config(page_title="Financial Analyst")

st.title("🤖 Financial Analyst")

with st.expander("아키텍처", expanded=True):
    st.image(os.path.join("../../dataset/images/financial_analyst.png"))

# Input form
st.markdown("**투자자 정보 입력**")
col1, col2, col3 = st.columns(3)

with col1:
    total_investable_amount = st.number_input(
        "💰 투자 가능 금액 (억원 단위)",
        min_value=0.0,
        max_value=1000.0,
        value=1.5,
        step=0.1,
        format="%.1f"
    )
    st.caption("예: 1.5 = 1억 5천만원")

with col2:
    age_options = [f"{i}-{i+4}세" for i in range(20, 101, 5)]
    age = st.selectbox(
        "나이",
        options=age_options,
        index=3
    )

with col3:
    experience_categories = ["0-1년", "1-3년", "3-5년", "5-10년", "10-20년", "20년 이상"]
    stock_investment_experience_years = st.selectbox(
        "주식 투자 경험",
        options=experience_categories,
        index=3
    )

target_amount = st.number_input(
    "💰1년 후 목표 금액 (억원 단위)",
    min_value=0.0,
    max_value=1000.0,
    value=2.0,
    step=0.1,
    format="%.1f"
)
st.caption("예: 2.0 = 2억원")

submitted = st.button("분석 시작", use_container_width=True)

if submitted:
    input_data = {
        "total_investable_amount": int(total_investable_amount * 100000000),
        "age": age,
        "stock_investment_experience_years": stock_investment_experience_years,
        "target_amount": int(target_amount * 100000000),
    }
    
    st.divider()
    placeholder = st.container()
    
    with st.spinner("AI is processing..."):
        # Financial Analysis
        placeholder.markdown("🤖 **Financial Analyst**")
        placeholder.subheader("📌 재무 분석")
        
        response = flib.get_prompt_management_response(
            FINANCIAL_ANALYST_ID,
            "user_input",
            json.dumps(input_data)
        )
        content = response['output']['message']['content'][0]['text']
        display_financial_analysis(placeholder, content)
        
        # Reflection Analysis
        placeholder.subheader("")
        placeholder.subheader("📌 재무 분석 검토 (Reflection)")
        
        reflection_response = flib.get_prompt_management_response(
            FINANCIAL_ANALYST_REFLECTION_ID,
            "finance_result",
            content
        )
        reflection_content = reflection_response['output']['message']['content'][0]['text']
        display_reflection_result(placeholder, reflection_content)