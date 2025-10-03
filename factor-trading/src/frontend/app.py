"""
Factor Trading Frontend - Main Application
Combined backtest management and results visualization.
"""

import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Factor Trading Frontend",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application entry point."""
    st.title("📊 Factor Trading Frontend")
    st.markdown("""
    Welcome to the Factor Trading Frontend! This application provides a complete workflow for:
    
    1. **🚀 Backtest Management** - Create, deploy, and monitor trading strategy backtests
    2. **📈 Results Visualization** - Analyze and compare backtest results
    
    Use the sidebar to navigate between pages.
    """)
    
    st.info("👈 Select a page from the sidebar to get started!")
    
    # Quick navigation
    st.subheader("Quick Navigation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🚀 Backtest Management
        - Create backtest configurations
        - Deploy DAGs to AWS MWAA
        - Trigger backtest execution
        - Monitor progress in real-time
        """)
    
    with col2:
        st.markdown("""
        ### 📈 Results Visualization
        - View backtest performance metrics
        - Compare different strategies
        - Analyze trade details
        - Explore factor effectiveness
        """)

if __name__ == "__main__":
    main()