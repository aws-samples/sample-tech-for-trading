import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime, date
from database import ClickHouseConnection
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Factor Trading Backtest Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .best-backtest {
        background-color: #e8f5e8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def convert_uuids_to_strings(df):
    """Convert UUID columns to strings to avoid JSON serialization issues"""
    if df.empty:
        return df
    
    # Convert UUID columns to strings
    uuid_columns = ['backtest_id', 'strategy_id', 'order_id', 'trade_id']
    for col in uuid_columns:
        if col in df.columns:
            df[col] = df[col].astype(str)
    
    return df

def load_data():
    """Load data from ClickHouse with debug info"""
    db = ClickHouseConnection()
    if not db.connect():
        st.error("Failed to connect to database")
        return None, None, None
    
    backtests = db.get_backtests()
    # st.success(f"Loaded {len(backtests)} backtests from database")
    
    strategies = db.get_strategy_definitions()
    # st.success(f"Loaded {len(strategies)} strategies from database")
    
    factors = db.get_available_factors()
    # st.success(f"Loaded {len(factors)} factors from database")
    
    # Convert UUIDs to strings
    backtests = convert_uuids_to_strings(backtests)
    strategies = convert_uuids_to_strings(strategies)
    
    db.close()
    return backtests, strategies, factors

def format_strategy_parameters(params_str):
    """Format strategy parameters for display"""
    try:
        params = json.loads(params_str) if isinstance(params_str, str) else params_str
        return "\n".join([f"{k}: {v}" for k, v in params.items()])
    except:
        return str(params_str)

def create_performance_chart(df):
    """Create performance comparison chart"""
    if df.empty:
        return go.Figure()
    
    # Ensure numeric columns are properly typed
    numeric_columns = ['annual_return', 'sharpe_ratio', 'win_rate', 'profit_factor', 'max_drawdown', 'total_return']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Annual Return vs Sharpe Ratio', 'Win Rate vs Profit Factor',
                       'Max Drawdown Distribution', 'Total Return Distribution'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Annual Return vs Sharpe Ratio
    fig.add_trace(
        go.Scatter(x=df['annual_return'], y=df['sharpe_ratio'],
                  mode='markers', name='Backtests',
                  text=df['backtest_id'],
                  hovertemplate='Annual Return: %{x:.2%}<br>Sharpe Ratio: %{y:.2f}<br>ID: %{text}'),
        row=1, col=1
    )
    
    # Win Rate vs Profit Factor
    fig.add_trace(
        go.Scatter(x=df['win_rate'], y=df['profit_factor'],
                  mode='markers', name='Backtests',
                  text=df['backtest_id'],
                  hovertemplate='Win Rate: %{x:.2%}<br>Profit Factor: %{y:.2f}<br>ID: %{text}'),
        row=1, col=2
    )
    
    # Max Drawdown Distribution
    fig.add_trace(
        go.Histogram(x=df['max_drawdown'], name='Max Drawdown'),
        row=2, col=1
    )
    
    # Total Return Distribution
    fig.add_trace(
        go.Histogram(x=df['total_return'], name='Total Return'),
        row=2, col=2
    )
    
    fig.update_layout(height=600, showlegend=False)
    return fig

def display_best_backtests():
    """Display best performing backtests"""
    st.header("🏆 Best Performing Backtests")
    
    metrics = ['annual_return', 'sharpe_ratio', 'win_rate', 'max_drawdown', 'profit_factor']
    metric_names = ['Annual Return', 'Sharpe Ratio', 'Win Rate', 'Max Drawdown', 'Profit Factor']
    
    cols = st.columns(len(metrics))
    
    db = ClickHouseConnection()
    if not db.connect():
        st.error("Failed to connect to database")
        return
    
    for i, (metric, name) in enumerate(zip(metrics, metric_names)):
        with cols[i]:
            st.subheader(name)
            best_df = db.get_best_backtests(metric, limit=3)
            best_df = convert_uuids_to_strings(best_df)
            
            if not best_df.empty:
                for idx, row in best_df.iterrows():
                    with st.container():
                        # Handle factors display safely
                        factors_display = "N/A"
                        if row['factors'] and str(row['factors']) != 'nan':
                            try:
                                factors_list = eval(str(row['factors'])) if isinstance(row['factors'], str) else row['factors']
                                if isinstance(factors_list, list):
                                    factors_display = ', '.join(factors_list)
                                else:
                                    factors_display = str(factors_list)
                            except:
                                factors_display = str(row['factors'])
                        
                        st.markdown(f"""
                        <div class="best-backtest">
                            <strong>Rank {idx + 1}</strong><br>
                            <strong>{name}:</strong> {row[metric]:.4f}<br>
                            <strong>Strategy:</strong> {str(row['strategy_id'])[:8]}...<br>
                            <strong>Period:</strong> {row['start_date']} to {row['end_date']}<br>
                            <strong>Factors:</strong> {factors_display}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(f"View Details", key=f"{metric}_{idx}"):
                            st.session_state.selected_backtest = str(row['backtest_id'])
                            st.rerun()
    
    db.close()

def display_backtest_details(backtest_id):
    """Display detailed information for a specific backtest"""
    st.header(f"📊 Backtest Details: {backtest_id}")
    
    db = ClickHouseConnection()
    if not db.connect():
        st.error("Failed to connect to database")
        return
    
    # Get backtest info
    backtest_info = db.get_backtests()
    backtest_info = convert_uuids_to_strings(backtest_info)
    backtest_info = backtest_info[backtest_info['backtest_id'] == backtest_id]
    
    if backtest_info.empty:
        st.error("Backtest not found")
        return
    
    info = backtest_info.iloc[0]
    
    # Display basic info
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Return", f"{float(info['total_return']):.2%}")
        st.metric("Annual Return", f"{float(info['annual_return']):.2%}")
    
    with col2:
        st.metric("Sharpe Ratio", f"{float(info['sharpe_ratio']):.2f}")
        st.metric("Max Drawdown", f"{float(info['max_drawdown']):.2f}%")
    
    with col3:
        st.metric("Win Rate", f"{float(info['win_rate']):.2%}")
        st.metric("Profit Factor", f"{float(info['profit_factor']):.2f}")
    
    with col4:
        st.metric("Number of Trades", f"{int(info['num_trades'])}")
        st.metric("Final Capital", f"${float(info['final_capital']):,.2f}")
    
    # Strategy Parameters
    st.subheader("Strategy Parameters")
    params_formatted = format_strategy_parameters(info['strategy_parameters'])
    st.text(params_formatted)
    
    # Factors
    st.subheader("Factors Used")
    try:
        factors = eval(str(info['factors'])) if info['factors'] and str(info['factors']) != 'nan' else []
        if isinstance(factors, list):
            st.write(", ".join(factors))
        else:
            st.write(str(factors))
    except:
        st.write(str(info['factors']))
    
    # Orders and Trades
    tab1, tab2 = st.tabs(["📋 Orders", "💰 Trades"])
    
    with tab1:
        st.subheader("Orders")
        orders = db.get_backtest_orders(backtest_id)
        orders = convert_uuids_to_strings(orders)
        
        if not orders.empty:
            st.dataframe(orders, use_container_width=True)
            
            # Orders summary
            col1, col2 = st.columns(2)
            with col1:
                order_summary = orders['order_type'].value_counts()
                fig = px.pie(values=order_summary.values, names=order_summary.index, 
                           title="Order Types Distribution")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                status_summary = orders['execution_status'].value_counts()
                fig = px.pie(values=status_summary.values, names=status_summary.index,
                           title="Execution Status Distribution")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No orders found for this backtest")
    
    with tab2:
        st.subheader("Trades")
        trades = db.get_backtest_trades(backtest_id)
        trades = convert_uuids_to_strings(trades)
        
        if not trades.empty:
            st.dataframe(trades, use_container_width=True)
            
            # Trades analysis
            col1, col2 = st.columns(2)
            
            with col1:
                # PnL distribution
                fig = px.histogram(trades, x='pnl', title="PnL Distribution", 
                                 nbins=20, color_discrete_sequence=['#1f77b4'])
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Exit reasons
                exit_reasons = trades['exit_reason'].value_counts()
                fig = px.pie(values=exit_reasons.values, names=exit_reasons.index,
                           title="Exit Reasons Distribution")
                st.plotly_chart(fig, use_container_width=True)
            
            # Duration analysis
            fig = px.histogram(trades, x='duration_days', title="Trade Duration Distribution",
                             nbins=20, color_discrete_sequence=['#2ca02c'])
            st.plotly_chart(fig, use_container_width=True)
            
            # Symbol performance
            symbol_pnl = trades.groupby('symbol')['pnl'].sum().sort_values(ascending=False)
            fig = px.bar(x=symbol_pnl.index[:20], y=symbol_pnl.values[:20],
                        title="Top 20 Symbols by PnL")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trades found for this backtest")
    
    db.close()

def main():
    st.title("📈 Factor Trading Backtest Dashboard")
    st.markdown("Analyze and compare your trading strategy backtests")
    
    # Load data
    with st.spinner("Loading data from ClickHouse..."):
        backtests, strategies, factors = load_data()
    
    if backtests is None:
        st.error("Failed to load data. Please check your ClickHouse connection.")
        return
    
    if backtests.empty:
        st.warning("No backtest data found.")
        return
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Strategy filter
    strategy_options = ['All'] + (strategies['strategy_name'].tolist() if not strategies.empty else [])
    selected_strategy = st.sidebar.selectbox("Strategy", strategy_options)
    
    # Date filters
    min_date = pd.to_datetime(backtests['start_date']).min().date()
    max_date = pd.to_datetime(backtests['end_date']).max().date()
    
    start_date_filter = st.sidebar.date_input("Start Date From", min_date)
    end_date_filter = st.sidebar.date_input("End Date To", max_date)
    
    # Factors filter
    if factors:
        selected_factors = st.sidebar.multiselect("Factors", factors)
    else:
        selected_factors = []
    
    # Apply filters
    filtered_backtests = backtests.copy()
    
    if selected_strategy != 'All':
        # Filter by strategy (you might need to join with strategy_definitions table)
        pass  # Implement strategy filtering logic
    
    if start_date_filter:
        filtered_backtests = filtered_backtests[
            pd.to_datetime(filtered_backtests['start_date']).dt.date >= start_date_filter
        ]
    
    if end_date_filter:
        filtered_backtests = filtered_backtests[
            pd.to_datetime(filtered_backtests['end_date']).dt.date <= end_date_filter
        ]
    
    # Main content
    if 'selected_backtest' in st.session_state:
        if st.button("← Back to Overview"):
            del st.session_state.selected_backtest
            st.rerun()
        display_backtest_details(st.session_state.selected_backtest)
    else:
        # Overview
        st.header("📊 Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Backtests", len(filtered_backtests))
        
        with col2:
            avg_return = filtered_backtests['annual_return'].mean()
            st.metric("Avg Annual Return", f"{avg_return:.2%}")
        
        with col3:
            avg_sharpe = filtered_backtests['sharpe_ratio'].mean()
            st.metric("Avg Sharpe Ratio", f"{avg_sharpe:.2f}")
        
        with col4:
            avg_drawdown = filtered_backtests['max_drawdown'].mean()
            st.metric("Avg Max Drawdown", f"{avg_drawdown:.2f}%")
        
        # Performance charts
        st.header("📈 Performance Analysis")
        if len(filtered_backtests) > 0:
            fig = create_performance_chart(filtered_backtests)
            st.plotly_chart(fig, use_container_width=True)
        
        # Best backtests
        display_best_backtests()
        
        # All backtests table
        st.header("📋 All Backtests")
        
        # Select columns to display
        display_columns = [
            'backtest_id', 'start_date', 'end_date', 'annual_return', 
            'sharpe_ratio', 'max_drawdown', 'win_rate', 'profit_factor',
            'num_trades', 'factors', 'created_at'
        ]
        
        display_df = filtered_backtests[display_columns].copy()
        
        # Format columns
        display_df['annual_return'] = display_df['annual_return'].apply(lambda x: f"{float(x):.2%}")
        display_df['max_drawdown'] = display_df['max_drawdown'].apply(lambda x: f"{float(x):.2f}%")
        display_df['win_rate'] = display_df['win_rate'].apply(lambda x: f"{float(x):.2%}")
        display_df['sharpe_ratio'] = display_df['sharpe_ratio'].apply(lambda x: f"{float(x):.2f}")
        display_df['profit_factor'] = display_df['profit_factor'].apply(lambda x: f"{float(x):.2f}")
        
        # Add selection
        selected_indices = st.dataframe(
            display_df,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        if selected_indices and len(selected_indices['selection']['rows']) > 0:
            selected_idx = selected_indices['selection']['rows'][0]
            selected_backtest_id = str(filtered_backtests.iloc[selected_idx]['backtest_id'])
            
            if st.button("View Selected Backtest Details"):
                st.session_state.selected_backtest = selected_backtest_id
                st.rerun()

if __name__ == "__main__":
    main()
