import investment_advisor_lib as ilib
import json
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import itertools
import re
import os


# Config
FLOW_ID = ""
FLOW_ALIAS_ID = ""

# Functions
def create_pie_chart(data, chart_title=""):
    """Create pie chart function"""
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


def display_financial_analysis(place_holder, input_content):
    """Display financial analysis results function"""
    data = json.loads(input_content, strict=False)
    sub_col1, sub_col2 = place_holder.columns(2)

    with sub_col1:
        st.metric("**위험 성향**", data["risk_profile"])
        st.markdown("**위험 성향 분석**")
        st.info(data["risk_profile_reason"])

    with sub_col2:
        st.metric("**필요 수익률**", f"{data['required_annual_return_rate']}%")
        st.markdown("**수익률 분석**")
        st.info(data["return_rate_reason"])


def get_product_chart_data(ticker):
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=100)

    etf = yf.Ticker(ticker)
    hist = etf.history(start=start_date, end=end_date)

    return hist


def display_portfolio_suggestion(place_holder, input_content):
    """Display portfolio suggestion results function"""
    data = json.loads(input_content, strict=False)
    sub_col1, sub_col2 = place_holder.columns([1, 1])

    with sub_col1:
        st.markdown("**포트폴리오**")
        # Display portfolio allocation with pie chart
        fig = create_pie_chart(
            data["portfolio_allocation"],
            "포트폴리오 자산 배분"
        )
        st.plotly_chart(fig)

    with sub_col2:
        st.markdown("**투자 전략**")
        st.info(data["strategy"])

    place_holder.markdown("**상세 근거**")
    place_holder.write(data["reason"])

    place_holder.markdown("\n\n")
    with place_holder.expander(f"**📈 분석에 사용된 데이터**"):
        for ticker, allocation in data["portfolio_allocation"].items():
            st.markdown(f"{ticker} 최근 100일 가격 동향")
            chart_data = get_product_chart_data(ticker)
            fig = go.Figure(data=[go.Candlestick(x=chart_data.index,
                                                 open=chart_data['Open'],
                                                 high=chart_data['High'],
                                                 low=chart_data['Low'],
                                                 close=chart_data['Close'])])
            fig.update_layout(xaxis_rangeslider_visible=False, height=300)
            st.plotly_chart(fig)


def get_market_data():
    market_info = {
        "us_dollar_index": {"ticker": "DX-Y.NYB", "description": "미국 달러 강세를 나타내는 지수"},
        "us_10y_treasury_yield": {"ticker": "^TNX", "description": "미국 10년 국채 수익률 (%)"},
        "us_2y_treasury_yield": {"ticker": "2YY=F", "description": "미국 2년 국채 수익률 (%)"},
        "vix_volatility_index": {"ticker": "^VIX", "description": "시장의 변동성을 나타내는 VIX 지수"},
        "crude_oil_price": {"ticker": "CL=F", "description": "WTI 원유 선물 가격 (USD/배럴)"}
    }

    data = {}
    for key, info in market_info.items():
        ticker = yf.Ticker(info["ticker"])
        market_price = ticker.info.get('regularMarketPreviousClose', 0)

        data[key] = {
            "description": info["description"],
            "value": round(market_price, 2)
        }

    return data


def get_product_news(ticker, top_n=5):
    stock = yf.Ticker(ticker)
    news = stock.news[:top_n]

    formatted_news = []
    for item in news:
        news_content = item.get("content", "")
        news_item = {
            "title": news_content.get("title", ""),
            "summary": news_content.get("summary", ""),
            "publish_date": news_content.get("pubDate", "")[:10]
        }
        formatted_news.append(news_item)

    result = {
        "ticker": ticker,
        "news": formatted_news,
    }

    return result


def display_risk_analysis(place_holder, input_content):
    """Display risk analysis results function"""
    data = json.loads(input_content, strict=False)

    for i, scenario in enumerate(["scenario1", "scenario2"], 1):
        if scenario in data:
            place_holder.subheader(f"시나리오 {i}: {data[scenario]['name']}")
            place_holder.info(data[scenario]['description'])

            sub_col1, sub_col2 = place_holder.columns([1, 1])
            with sub_col1:
                st.markdown("**조정된 포트폴리오**")
                # Display adjusted portfolio with pie chart
                fig = create_pie_chart(
                    data[scenario]['allocation_management'],
                    f"시나리오 {i} 자산 배분"
                )
                st.plotly_chart(fig)

            with sub_col2:
                st.markdown("**조정 근거**")
                st.write(data[scenario]['reason'])

    place_holder.markdown("\n\n")
    with place_holder.expander(f"**📈 분석에 사용된 데이터**"):
        market_data = get_market_data()

        for i in range(0, len(market_data), 3):
            cols = st.columns(3)
            for j, (key, info) in enumerate(itertools.islice(market_data.items(), i, i + 3)):
                with cols[j]:
                    st.metric(info['description'], f"{info['value']}")

        tickers = list(data["scenario1"]['allocation_management'].keys())
        for ticker in tickers:
            st.markdown(f"{ticker} 최근 뉴스")
            news_data = get_product_news(ticker)
            news_df = pd.DataFrame(news_data["news"])
            
            required_columns = ['publish_date', 'title', 'summary']
            for col in required_columns:
                if col not in news_df.columns:
                    news_df[col] = ''
                        
            columns_to_display = [col for col in required_columns if col in news_df.columns]
            
            if columns_to_display:
                st.dataframe(news_df[columns_to_display], hide_index=True)
            else:
                st.write("No news data available")

def display_report(place_holder, input_content):
    """Display report function"""
    styled_text = re.sub(
        r'\{([^}]+)\}',
        r'<span style="background-color: #ffd700; padding: 2px 6px; border-radius: 3px; font-weight: bold; color: #1e1e1e;">\1</span>',
        input_content
    )
    place_holder.markdown(styled_text, unsafe_allow_html=True)


def display_reflection(place_holder, input_content):
    """Display reflection function"""
    place_holder.error("재무분석 검토 실패")
    place_holder.markdown(input_content)


# Config
NODE_DISPLAY_FUNCTIONS = {
    "FinancialAnalyst": ("Financial Analyst", "재무 분석", display_financial_analysis),
    "PortfolioArchitect": ("Portfolio Architect", "포트폴리오 설계", display_portfolio_suggestion),
    "RiskManager": ("Risk Manager", "리스크 분석", display_risk_analysis),
    "ReportGenerator": ("Report Generator", "종합 보고서", display_report),
    "FinancialAnalystReflection": ("Financial Analyst Reflection", "재무 분석 검토", display_reflection),
}


# Page setup
st.set_page_config(page_title="Investment Advisor")

st.title("🤖 Investment Advisor")

with st.expander("아키텍처", expanded=True):
    st.image(os.path.join("../../dataset/images/investment_advisor.png"))

# Input form
st.markdown("**📊 투자자 정보**")
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
    age_options = [f"{i}-{i + 4}세" for i in range(20, 101, 5)]

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

st.markdown("**🎯 투자 목표**")

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

    # Output response
    placeholder = st.container()

    with st.spinner("AI가 분석 중입니다..."):
        response = ilib.get_flow_response(input_data, FLOW_ID, FLOW_ALIAS_ID)

        if response:
            placeholder.divider()

            # Dictionary to store results of each node
            node_results = {}

            # Process stream events
            for event in response.get('responseStream', []):
                if 'flowTraceEvent' in event:
                    trace = event['flowTraceEvent']['trace']

                    # Display information about the current node being processed
                    if 'nodeInputTrace' in trace:
                        node_name = trace['nodeInputTrace']['nodeName']
                        if node_name in NODE_DISPLAY_FUNCTIONS:
                            agent_name, title, display_func = NODE_DISPLAY_FUNCTIONS[node_name]

                            if agent_name != "Financial Analyst Reflection":
                                placeholder.markdown(f"🤖 **{agent_name}**")
                                placeholder.subheader(f"📌 {title}")

                    # Display node output results
                    if 'nodeOutputTrace' in trace:
                        node_name = trace['nodeOutputTrace']['nodeName']

                        if node_name in NODE_DISPLAY_FUNCTIONS:
                            agent_name, title, display_func = NODE_DISPLAY_FUNCTIONS[node_name]

                            try:
                                if agent_name != "Financial Analyst Reflection":
                                    content = trace['nodeOutputTrace']['fields'][0]['content']['document']
                                    display_func(placeholder, content)
                                    placeholder.subheader("")
                                else:
                                    content = trace['nodeOutputTrace']['fields'][0]['content']['document']
                                    if content != "yes":
                                        placeholder.markdown(f"🤖 **{agent_name}**")
                                        placeholder.subheader(f"📌 {title}")
                                        display_func(placeholder, content[3:])

                            except Exception as e:
                                st.error(f"Error processing {node_name}: {str(e)}")
                                st.json(trace['nodeOutputTrace'])