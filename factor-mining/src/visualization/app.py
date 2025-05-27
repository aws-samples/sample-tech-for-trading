import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import boto3
import os
import datetime
from clickhouse_driver import Client
import json
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Set page configuration
st.set_page_config(
    page_title="Factor Mining Dashboard",
    page_icon="📊",
    layout="wide"
)

# Clickhouse connection parameters
CLICKHOUSE_HOST = os.environ.get('CLICKHOUSE_HOST', '127.0.0.1')
CLICKHOUSE_PORT = int(os.environ.get('CLICKHOUSE_PORT', '9000'))
CLICKHOUSE_USER = os.environ.get('CLICKHOUSE_USER', 'default')
CLICKHOUSE_SECRET_ARN = os.environ.get('CLICKHOUSE_SECRET_ARN', '')
CLICKHOUSE_DATABASE = os.environ.get('CLICKHOUSE_DATABASE', 'factor-modelling')

# AWS Step Functions parameters
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN', 'arn:aws:states:us-east-1:600627331406:stateMachine:factor-modeling-workflow')


def get_secret(secret_name):
    """Retrieve secret from AWS Secrets Manager"""
    client = boto3.client(
        service_name='secretsmanager'
    )
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        logger.error(f"Secret retrieval error: {str(e)}")
        logger.error(traceback.format_exc())
        raise


# Function to connect to Clickhouse
@st.cache_resource
def get_clickhouse_client():
    secret = get_secret(CLICKHOUSE_SECRET_ARN)
    return Client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        user=CLICKHOUSE_USER,
        password=secret.get('password', ''),
        database=CLICKHOUSE_DATABASE
    )

# Function to fetch factor data from Clickhouse
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_factor_data():
    client = get_clickhouse_client()
    query = """
    SELECT 
        factor_name,
        factor_type,
        test_date,
        start_date,
        end_date,
        abs(avg_beta) AS avg_beta,
        abs(avg_tstat) AS avg_tstat,
        avg_rsquared,
        update_time
    FROM (
        SELECT 
            factor_name,
            factor_type,
            test_date,
            start_date,
            end_date,
            avg_beta,
            avg_tstat,
            avg_rsquared,
            update_time,
            ROW_NUMBER() OVER (
                PARTITION BY factor_name, start_date, end_date 
                ORDER BY avg_rsquared DESC
            ) AS rn
        FROM factor_summary
    ) t
    WHERE rn = 1
    ORDER BY test_date DESC, factor_name
    """
    result = client.execute(query)
    df = pd.DataFrame(
        result,
        columns=[
            'factor_name', 'factor_type', 'test_date', 'start_date', 'end_date',
            'avg_beta', 'avg_tstat', 'avg_rsquared', 'update_time'
        ]
    )
    
    # Map Clickhouse factor names to Step Function Input Arg names
    factor_name_mapping = {
        'PEG': 'PEG',
        'RSI14': 'RSI14',
        'RSI28': 'RSI28',
        'SMB': 'SMB',
        'HML': 'HML',
        'Rm_Rf': 'MARKET',
        'PB': 'PB',
        'TradingVolume': 'VOLUME',
        'ROC20': 'ROC',
        'CurrentRatio': 'CR',
        'CashRatio': 'CASH',
        'InventoryTurnover': 'IT',
        'GrossProfitMargin': 'GPM',
        'DebtToEquity': 'DE',
        'InterestCoverage': 'IC',
        'RevenueGrowth': 'RG',
        'BoardAge': 'BA',
        'ExecCompToRevenue': 'EC',
        'EnvRating': 'ER',
        'AvgSentiment14': 'SENT',
        'NEWSENT': 'NEWSENT'
    }
    
    # Add a column for Step Function Input Arg name
    df['input_arg_name'] = df['factor_name'].apply(lambda x: factor_name_mapping.get(x, x))
    
    return df

# Function to fetch Step Function executions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_step_function_executions():
    try:
        session = boto3.Session()
        sfn_client = session.client('stepfunctions')
        
        response = sfn_client.list_executions(
            stateMachineArn=STATE_MACHINE_ARN,
            maxResults=100,
            statusFilter='SUCCEEDED'
        )
        
        executions = []
        for execution in response['executions']:
            # Get execution details to extract thread_no, parallel_m, and factor
            exec_details = sfn_client.describe_execution(
                executionArn=execution['executionArn']
            )
            
            # Parse input to get thread_no, parallel_m, and factor
            try:
                input_data = json.loads(exec_details.get('input', '{}'))
                thread_no = input_data.get('thread_no', 'Unknown')
                parallel_m = input_data.get('parallel_m', 'Unknown')
                factor = input_data.get('factor', 'Unknown')
            except:
                thread_no = 'Unknown'
                parallel_m = 'Unknown'
                factor = 'Unknown'
            
            executions.append({
                'executionArn': execution['executionArn'],
                'name': execution['name'],
                'startDate': execution['startDate'],
                'stopDate': execution['stopDate'],
                'status': execution['status'],
                'thread_no': thread_no,
                'parallel_m': parallel_m,
                'factor': factor,
                'duration': (execution['stopDate'] - execution['startDate']).total_seconds() / 60  # Duration in minutes
            })
        
        # Try to get more executions if there's a next token
        while 'nextToken' in response and len(executions) < 500:  # Limit to 500 executions to avoid performance issues
            response = sfn_client.list_executions(
                stateMachineArn=STATE_MACHINE_ARN,
                maxResults=100,
                statusFilter='SUCCEEDED',
                nextToken=response['nextToken']
            )
            
            for execution in response['executions']:
                # Get execution details to extract thread_no, parallel_m, and factor
                exec_details = sfn_client.describe_execution(
                    executionArn=execution['executionArn']
                )

                try:
                    input_data = json.loads(exec_details.get('input', '{}'))

                    # Parse input to get thread_no, parallel_m, and factor
                    if not all(key in input_data and input_data[key] is not None for key in
                               ['thread_no', 'parallel_m', 'factor']):
                        continue  # Skip this execution if any required key is missing or None

                    thread_no = input_data.get('thread_no', 'Unknown')
                    parallel_m = input_data.get('parallel_m', 'Unknown')
                    factor = input_data.get('factor', 'Unknown')
                except:
                    thread_no = 'Unknown'
                    parallel_m = 'Unknown'
                    factor = 'Unknown'
                
                executions.append({
                    'executionArn': execution['executionArn'],
                    'name': execution['name'],
                    'startDate': execution['startDate'],
                    'stopDate': execution['stopDate'],
                    'status': execution['status'],
                    'thread_no': thread_no,
                    'parallel_m': parallel_m,
                    'factor': factor,
                    'duration': (execution['stopDate'] - execution['startDate']).total_seconds() / 60  # Duration in minutes
                })
        
        return pd.DataFrame(executions)
    except Exception as e:
        st.error(f"Error fetching Step Function executions: {str(e)}")
        return pd.DataFrame()

# Main app
def main():
    st.title("Factor Mining Dashboard")
    
    # Add a description explaining the mapping
    with st.expander("About Factor Names"):
        st.markdown("""
        ### Factor Name Mapping
        
        This dashboard displays Step Function Input Arg names instead of the Clickhouse factor names.
        Below is the mapping between them:
        
        | Step Function Input Arg | Factor Name in Clickhouse DB | Factor Type |
        |-------------------------|------------------------------|-------------|
        | PEG | PEG | Fundamental |
        | RSI14 | RSI14 | Technical |
        | RSI28 | RSI28 | Technical |
        | SMB | SMB | Fama-French |
        | HML | HML | Fama-French |
        | MARKET | Rm_Rf | Fama-French |
        | PB | PB | Valuation |
        | VOLUME | TradingVolume | Liquidity |
        | ROC | ROC20 | Technical |
        | CR | CurrentRatio | Financial Health |
        | CASH | CashRatio | Financial Health |
        | IT | InventoryTurnover | Operational |
        | GPM | GrossProfitMargin | Operational |
        | DE | DebtToEquity | Financial Risk |
        | IC | InterestCoverage | Financial Risk |
        | RG | RevenueGrowth | Growth |
        | BA | BoardAge | Governance |
        | EC | ExecCompToRevenue | ESG Governance |
        | ER | EnvRating | ESG Environmental |
        | SENT | AvgSentiment14 | Sentiment |
        | NEWSENT | NEWSENT | Sentiment |
        """)
    
    # Sidebar for filters
    st.sidebar.header("Filters")
    
    # Load data
    try:
        factor_data = get_factor_data()
        
        if factor_data.empty:
            st.warning("No factor data available.")
            return
            
        # Get unique values for filters
        unique_factor_types = sorted(factor_data['factor_type'].unique())
        unique_input_args = sorted([str(x) for x in factor_data['input_arg_name'].unique()])
        unique_start_dates = sorted(factor_data['start_date'].unique())
        unique_end_dates = sorted(factor_data['end_date'].unique())
        unique_test_dates = sorted(factor_data['test_date'].unique(), reverse=True)
        
        # Add filters in the specified order
        selected_factor_types = st.sidebar.multiselect(
            "Factor Type",
            options=unique_factor_types,
            default=[]
        )
        
        # Filter input args based on selected factor types
        filtered_input_args = unique_input_args
        if selected_factor_types:
            filtered_input_args = factor_data[factor_data['factor_type'].isin(selected_factor_types)]['input_arg_name'].unique()
            
        selected_input_args = st.sidebar.multiselect(
            "Factor Name (Step Function Input Arg)",
            options=sorted(filtered_input_args),
            default=[]
        )
        
        selected_start_dates = st.sidebar.multiselect(
            "Start Date",
            options=unique_start_dates,
            default=[]
        )
        
        selected_end_dates = st.sidebar.multiselect(
            "End Date",
            options=unique_end_dates,
            default=[]
        )
        
        selected_test_dates = st.sidebar.multiselect(
            "Test Date",
            options=unique_test_dates,
            default=[unique_test_dates[0]] if unique_test_dates else []
        )
        
        # Apply filters to data
        filtered_data = factor_data.copy()
        
        if selected_factor_types:
            filtered_data = filtered_data[filtered_data['factor_type'].isin(selected_factor_types)]
            
        if selected_input_args:
            filtered_data = filtered_data[filtered_data['input_arg_name'].isin(selected_input_args)]
            
        if selected_start_dates:
            filtered_data = filtered_data[filtered_data['start_date'].isin(selected_start_dates)]
            
        if selected_end_dates:
            filtered_data = filtered_data[filtered_data['end_date'].isin(selected_end_dates)]
            
        if selected_test_dates:
            filtered_data = filtered_data[filtered_data['test_date'].isin(selected_test_dates)]
        
        # Display factor summary
        st.header("Factor Performance Summary")
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["Factor Summary", "Performance Metrics", "Step Function Performance", "Architecture"])
        
        with tab1:
            # Display factor summary with Step Function Input Arg names
            display_df = filtered_data[['input_arg_name', 'factor_type', 'test_date', 'start_date', 'end_date', 
                                        'avg_beta', 'avg_tstat', 'avg_rsquared', 'update_time']]
            
            # Rename columns for display
            display_df = display_df.rename(columns={
                'input_arg_name': 'Factor Name (Input Arg)',
                'factor_type': 'Factor Type',
                'test_date': 'Test Date',
                'start_date': 'Start Date',
                'end_date': 'End Date',
                'avg_beta': 'Avg Beta',
                'avg_tstat': 'Avg T-Stat',
                'avg_rsquared': 'Avg R-Squared',
                'update_time': 'Update Time'
            })
            
            st.dataframe(
                display_df.sort_values(by=['Test Date', 'Factor Name (Input Arg)'], ascending=[False, True]),
                use_container_width=True,
                hide_index=True
            )
        
        with tab2:
            if not filtered_data.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    # T-stat distribution
                    fig_tstat = px.box(
                        filtered_data, 
                        x='factor_type', 
                        y='avg_tstat',
                        color='factor_type',
                        title='T-Statistic Distribution by Factor Type',
                        hover_data=['input_arg_name', 'test_date']
                    )
                    st.plotly_chart(fig_tstat, use_container_width=True)
                
                with col2:
                    # R-squared distribution
                    fig_rsq = px.box(
                        filtered_data, 
                        x='factor_type', 
                        y='avg_rsquared',
                        color='factor_type',
                        title='R-Squared Distribution by Factor Type',
                        hover_data=['input_arg_name', 'test_date']
                    )
                    st.plotly_chart(fig_rsq, use_container_width=True)
                
                # Beta vs T-stat scatter plot
                plot_data = filtered_data.dropna(subset=['avg_rsquared'])
                fig_scatter = px.scatter(
                    plot_data,
                    x='avg_beta',
                    y='avg_tstat',
                    color='factor_type',
                    size='avg_rsquared',
                    hover_name='input_arg_name',
                    title='Beta vs T-Statistic (size represents R-squared)',
                    labels={
                        'avg_beta': 'Average Beta',
                        'avg_tstat': 'Average T-Statistic',
                        'factor_type': 'Factor Type'
                    }
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("Please select filters to view performance metrics.")
        
        with tab3:
            st.subheader("Step Function Performance Analysis")
            
            try:
                # Get Step Function executions
                executions_df = get_step_function_executions()
                
                if not executions_df.empty:
                    # Join with factor data based on timestamps
                    # Convert update_time to datetime if it's not already
                    if not pd.api.types.is_datetime64_any_dtype(factor_data['update_time']):
                        factor_data['update_time'] = pd.to_datetime(factor_data['update_time'])
                    
                    # Group factor data by update_time to get counts
                    factor_updates = factor_data.groupby('update_time').size().reset_index(name='factor_count')
                    
                    # Convert thread_no and parallel_m to numeric if possible
                    for col in ['thread_no', 'parallel_m']:
                        if col in executions_df.columns:
                            executions_df[col] = pd.to_numeric(executions_df[col], errors='ignore')
                    
                    # Filter executions based on selected input args
                    if selected_input_args:
                        executions_df = executions_df[executions_df['factor'].isin(selected_input_args)]
                        if executions_df.empty:
                            st.info(f"No Step Function executions found for the selected factors: {', '.join(selected_input_args)}")
                            return
                    
                    # Create tabs for different performance views
                    perf_tab1, perf_tab2, perf_tab3, perf_tab4 = st.tabs([
                        "Thread No Impact", 
                        "Parallel M Impact", 
                        "Combined Analysis",
                        "Factor-Specific Analysis"
                    ])
                    
                    # Display a message showing which factors are being displayed
                    if selected_input_args:
                        st.info(f"Showing Step Function performance for factors: {', '.join(selected_input_args)}")
                    
                    with perf_tab1:
                        if 'thread_no' in executions_df.columns and not all(executions_df['thread_no'] == 'Unknown'):
                            # Plot thread_no vs Duration
                            fig_thread = px.scatter(
                                executions_df,
                                x='thread_no',
                                y='duration',
                                title='Step Function Duration vs Thread No (ParallelBatchProcessing Concurrency)',
                                labels={
                                    'thread_no': 'Thread No',
                                    'duration': 'Duration (minutes)'
                                },
                                hover_data=['name', 'startDate', 'stopDate', 'parallel_m', 'factor']
                            )
                            
                            # Add trendline
                            fig_thread.update_traces(marker=dict(size=10))
                            fig_thread.update_layout(
                                xaxis_title="Thread No (ParallelBatchProcessing Concurrency)",
                                yaxis_title="Duration (minutes)"
                            )
                            
                            st.plotly_chart(fig_thread, use_container_width=True)
                        else:
                            st.info("Thread No information not available in Step Function executions.")
                    
                    with perf_tab2:
                        if 'parallel_m' in executions_df.columns and not all(executions_df['parallel_m'] == 'Unknown'):
                            # Plot parallel_m vs Duration
                            fig_parallel = px.scatter(
                                executions_df,
                                x='parallel_m',
                                y='duration',
                                title='Step Function Duration vs Parallel M (PerTickerBatchProcessing Concurrency)',
                                labels={
                                    'parallel_m': 'Parallel M',
                                    'duration': 'Duration (minutes)'
                                },
                                hover_data=['name', 'startDate', 'stopDate', 'thread_no', 'factor']
                            )
                            
                            # Add trendline
                            fig_parallel.update_traces(marker=dict(size=10))
                            fig_parallel.update_layout(
                                xaxis_title="Parallel M (PerTickerBatchProcessing Concurrency)",
                                yaxis_title="Duration (minutes)"
                            )
                            
                            st.plotly_chart(fig_parallel, use_container_width=True)
                        else:
                            st.info("Parallel M information not available in Step Function executions.")
                    
                    with perf_tab3:
                        if ('thread_no' in executions_df.columns and 'parallel_m' in executions_df.columns and 
                            not all(executions_df['thread_no'] == 'Unknown') and not all(executions_df['parallel_m'] == 'Unknown')):
                            
                            # Create a 3D scatter plot
                            fig_3d = px.scatter_3d(
                                executions_df,
                                x='thread_no',
                                y='parallel_m',
                                z='duration',
                                color='duration',
                                title='Step Function Duration vs Thread No and Parallel M',
                                labels={
                                    'thread_no': 'Thread No',
                                    'parallel_m': 'Parallel M',
                                    'duration': 'Duration (minutes)'
                                },
                                hover_data=['name', 'startDate', 'stopDate', 'factor']
                            )
                            
                            fig_3d.update_layout(
                                scene=dict(
                                    xaxis_title='Thread No',
                                    yaxis_title='Parallel M',
                                    zaxis_title='Duration (minutes)'
                                )
                            )
                            
                            st.plotly_chart(fig_3d, use_container_width=True)
                            
                            # Create a heatmap for thread_no vs parallel_m with duration as color
                            if len(executions_df['thread_no'].unique()) > 1 and len(executions_df['parallel_m'].unique()) > 1:
                                # Create pivot table for heatmap
                                pivot_data = executions_df.pivot_table(
                                    values='duration', 
                                    index='thread_no', 
                                    columns='parallel_m', 
                                    aggfunc='mean'
                                )
                                
                                fig_heatmap = px.imshow(
                                    pivot_data,
                                    labels=dict(x="Parallel M", y="Thread No", color="Duration (minutes)"),
                                    title="Average Duration by Thread No and Parallel M Combinations"
                                )
                                
                                st.plotly_chart(fig_heatmap, use_container_width=True)
                        else:
                            st.info("Thread No or Parallel M information not available for combined analysis.")
                    
                    with perf_tab4:
                        if 'factor' in executions_df.columns and not all(executions_df['factor'] == 'Unknown'):
                            # Map Step Function factor input args to Clickhouse factor names
                            factor_arg_to_name = {
                                'PEG': 'PEG',
                                'RSI14': 'RSI14',
                                'RSI28': 'RSI28',
                                'SMB': 'SMB',
                                'HML': 'HML',
                                'MARKET': 'Rm_Rf',
                                'PB': 'PB',
                                'VOLUME': 'TradingVolume',
                                'ROC': 'ROC20',
                                'CR': 'CurrentRatio',
                                'CASH': 'CashRatio',
                                'IT': 'InventoryTurnover',
                                'GPM': 'GrossProfitMargin',
                                'DE': 'DebtToEquity',
                                'IC': 'InterestCoverage',
                                'RG': 'RevenueGrowth',
                                'BA': 'BoardAge',
                                'EC': 'ExecCompToRevenue',
                                'ER': 'EnvRating',
                                'SENT': 'AvgSentiment14',
                                'NEWSENT': 'NEWSENT'
                            }
                            
                            # We're already filtering by selected_input_args at the beginning of tab3
                            factor_executions = executions_df
                            
                            if not factor_executions.empty:
                                # Group by factor and calculate average duration
                                factor_performance = factor_executions.groupby('factor')['duration'].mean().reset_index()
                                factor_performance = factor_performance.sort_values('duration')
                                
                                # Plot factor vs average duration
                                fig_factor_duration = px.bar(
                                    factor_performance,
                                    x='factor',
                                    y='duration',
                                    title='Average Step Function Duration by Factor',
                                    labels={
                                        'factor': 'Factor (Input Arg)',
                                        'duration': 'Average Duration (minutes)'
                                    }
                                )
                                
                                st.plotly_chart(fig_factor_duration, use_container_width=True)
                                
                                # Create scatter plots for each factor showing thread_no and parallel_m impact
                                st.subheader("Concurrency Impact by Factor")
                                
                                # Select a specific factor for detailed analysis
                                factors_with_data = factor_executions['factor'].unique()
                                if len(factors_with_data) > 0:
                                    selected_factor_for_analysis = st.selectbox(
                                        "Select a factor for detailed analysis",
                                        options=factors_with_data
                                    )
                                    
                                    factor_specific_data = factor_executions[factor_executions['factor'] == selected_factor_for_analysis]
                                    
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        # Thread No impact for specific factor
                                        fig_factor_thread = px.scatter(
                                            factor_specific_data,
                                            x='thread_no',
                                            y='duration',
                                            title=f'Thread No Impact for {selected_factor_for_analysis}',
                                            labels={
                                                'thread_no': 'Thread No',
                                                'duration': 'Duration (minutes)'
                                            },
                                            trendline='ols'
                                        )
                                        st.plotly_chart(fig_factor_thread, use_container_width=True)
                                    
                                    with col2:
                                        # Parallel M impact for specific factor
                                        fig_factor_parallel = px.scatter(
                                            factor_specific_data,
                                            x='parallel_m',
                                            y='duration',
                                            title=f'Parallel M Impact for {selected_factor_for_analysis}',
                                            labels={
                                                'parallel_m': 'Parallel M',
                                                'duration': 'Duration (minutes)'
                                            },
                                            trendline='ols'
                                        )
                                        st.plotly_chart(fig_factor_parallel, use_container_width=True)
                                    
                                    # 3D plot for specific factor
                                    fig_factor_3d = px.scatter_3d(
                                        factor_specific_data,
                                        x='thread_no',
                                        y='parallel_m',
                                        z='duration',
                                        color='duration',
                                        title=f'Combined Concurrency Impact for {selected_factor_for_analysis}',
                                        labels={
                                            'thread_no': 'Thread No',
                                            'parallel_m': 'Parallel M',
                                            'duration': 'Duration (minutes)'
                                        }
                                    )
                                    
                                    st.plotly_chart(fig_factor_3d, use_container_width=True)
                            else:
                                st.info("No execution data available for the selected factors.")
                        else:
                            st.info("Factor information not available in Step Function executions.")
                    
                    # Show execution details
                    st.subheader("Step Function Execution Details")
                    
                    # Create a display dataframe with input arg names
                    exec_display_df = executions_df[['name', 'startDate', 'stopDate', 'duration', 'thread_no', 'parallel_m', 'factor', 'status']].copy()
                    exec_display_df = exec_display_df.rename(columns={
                        'name': 'Execution Name',
                        'startDate': 'Start Date',
                        'stopDate': 'Stop Date',
                        'duration': 'Duration (min)',
                        'thread_no': 'Thread No',
                        'parallel_m': 'Parallel M',
                        'factor': 'Factor (Input Arg)',
                        'status': 'Status'
                    })
                    
                    st.dataframe(
                        exec_display_df,
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Correlation with factor updates
                    if not factor_updates.empty:
                        st.subheader("Factor Updates Analysis")
                        st.write("This section analyzes the relationship between Step Function executions and factor updates.")
                        
                        # Convert execution dates to datetime for comparison
                        executions_df['date_only'] = executions_df['stopDate'].dt.date
                        
                        # Convert factor update times to date only for comparison
                        if isinstance(factor_updates['update_time'].iloc[0], pd.Timestamp):
                            factor_updates['date_only'] = factor_updates['update_time'].dt.date
                        else:
                            factor_updates['date_only'] = pd.to_datetime(factor_updates['update_time']).dt.date
                        
                        # Group by date and count executions
                        exec_by_date = executions_df.groupby('date_only').size().reset_index(name='execution_count')
                        
                        # Group factor updates by date and sum counts
                        factor_by_date = factor_updates.groupby('date_only')['factor_count'].sum().reset_index()
                        
                        # Merge the two dataframes
                        merged_data = pd.merge(exec_by_date, factor_by_date, on='date_only', how='outer').fillna(0)
                        merged_data.columns = ['Date', 'Executions', 'Factor Updates']
                        
                        # Create a bar chart
                        fig_correlation = px.bar(
                            merged_data,
                            x='Date',
                            y=['Executions', 'Factor Updates'],
                            barmode='group',
                            title='Step Function Executions vs Factor Updates by Date'
                        )
                        
                        st.plotly_chart(fig_correlation, use_container_width=True)
                else:
                    st.info("No Step Function execution data available.")
            except Exception as e:
                st.error(f"Error analyzing Step Function performance: {str(e)}")
                st.info("Make sure you have the correct AWS permissions and profile configured.")

        # Architecture tab
        with tab4:
            st.subheader("Factor Mining Architecture")

            # Display the architecture image from S3
            st.image("https://d35e4qkdhhuz52.cloudfront.net/architecture/factor-mining-architecture.png",
                    caption="Factor Mining Platform Architecture",
                    use_column_width=True)

            # Add explanation about the architecture
            st.markdown("""
            ## How Factor Mining Works
            
            The Factor Mining Platform uses a combination of AWS services to collect, process, and analyze financial data to discover 
            and validate investment factors. The architecture is designed for scalability, reliability, and performance.
            
            ### Key Components:
            
            1. **Data Collection**: Lambda functions collect market data, SEC filings, and web search results
            2. **Data Storage**: Clickhouse database for time-series data and S3 buckets for raw data
            3. **Processing**: AWS Step Functions and AWS Batch for parallel factor mining
            4. **Visualization**: Streamlit application (this dashboard) for visualizing results
            
            ### Technology Stack:
            
            - **AWS Step Functions**: Orchestrates the factor mining workflow
            - **AWS Batch**: Runs compute-intensive factor calculations
            - **Amazon S3**: Stores raw and processed data
            - **Amazon Clickhouse**: High-performance time-series database
            - **AWS Lambda**: Serverless data collection and processing
            - **Amazon Bedrock**: Provides GenAI capabilities for sentiment analysis
            """)

            # Display the GenAI code snippet
            st.subheader("GenAI in Factor Mining")
            st.markdown("""
            The platform leverages Amazon Bedrock's Nova Pro model for sentiment analysis of financial news and reports.
            Below is the code snippet showing how we use Amazon Bedrock for sentiment analysis:
            """)

            st.code("""
    # Prepare prompt for sentiment analysis
    prompt = f\"\"\"
    Analyze the sentiment of the following text about a company's stock and financial performance.
    Rate the sentiment on a scale from -1 to 1, where:
    - -1 represents extremely negative sentiment
    - 0 represents neutral sentiment
    - 1 represents extremely positive sentiment
    
    Only respond with a single number between -1 and 1, with up to two decimal places. No need explanation.
    
    Text to analyze:
    {text}
    \"\"\"
    
    # Call Amazon Nova Pro model through Bedrock using converse API
    messages = [
        {"role": "user", "content": [{"text": prompt}]},
    ]
    
    response = bedrock_runtime.converse(
        modelId="us.amazon.nova-pro-v1:0",
        messages=messages
    )
    
    # Parse response
    sentiment_text = response['output']['message']['content'][0]['text'].strip()
    sentiment_score = float(sentiment_text)
            """, language="python")

            st.markdown("""
            ### Benefits of GenAI in Factor Mining
            
            - **Sentiment Analysis**: Extracts sentiment from financial news, reports, and social media
            - **Pattern Recognition**: Identifies patterns in market data that traditional methods might miss
            - **Natural Language Processing**: Processes unstructured text data from various sources
            - **Automated Research**: Accelerates the research process by automating data analysis
            
            The sentiment scores generated by this process are used as inputs to factor models, allowing us to incorporate market sentiment into our investment strategies.
            """)

    except Exception as e:
        trace_str = traceback.format_exc()
        st.error(f"Error loading data: {str(e)}")
        st.error(f"Trace: {trace_str}")
        st.info("Check your Clickhouse connection parameters and ensure the database is accessible.")


if __name__ == "__main__":
    main()
