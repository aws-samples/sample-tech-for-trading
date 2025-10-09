"""
Backtest Frontend - Main Streamlit Application
A Streamlit application for backtest management.
"""

import streamlit as st
import os
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv
from aws_utils import AWSUtils
from dag_generator import DAGGenerator
from error_handler import ErrorHandler

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Backtest Frontend",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def add_persistent_message(backtest_id: str, message_type: str, message: str):
    """Add a persistent message that stays on the page."""
    if backtest_id not in st.session_state.persistent_messages:
        st.session_state.persistent_messages[backtest_id] = []
    
    st.session_state.persistent_messages[backtest_id].append({
        'type': message_type,  # 'success', 'error', 'warning', 'info'
        'message': message,
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })

def show_persistent_messages(backtest_id: str):
    """Display all persistent messages for a backtest."""
    if backtest_id in st.session_state.persistent_messages:
        for msg in st.session_state.persistent_messages[backtest_id]:
            if msg['type'] == 'success':
                st.success(f"✅ {msg['message']} ({msg['timestamp']})")
            elif msg['type'] == 'error':
                st.error(f"❌ {msg['message']} ({msg['timestamp']})")
            elif msg['type'] == 'warning':
                st.warning(f"⚠️ {msg['message']} ({msg['timestamp']})")
            elif msg['type'] == 'info':
                st.info(f"ℹ️ {msg['message']} ({msg['timestamp']})")

def initialize_session_state():
    """Initialize session state variables."""
    if 'aws_utils' not in st.session_state:
        st.session_state.aws_utils = AWSUtils()
    
    if 'dag_generator' not in st.session_state:
        st.session_state.dag_generator = DAGGenerator()
    
    if 'backtest_configs' not in st.session_state:
        st.session_state.backtest_configs = {}
    
    if 'current_config' not in st.session_state:
        st.session_state.current_config = {}
    
    if 'deployed_dags' not in st.session_state:
        st.session_state.deployed_dags = {}
    
    if 'connection_status' not in st.session_state:
        st.session_state.connection_status = {}
    
    if 'generated_dags' not in st.session_state:
        st.session_state.generated_dags = {}
    
    if 'running_dags' not in st.session_state:
        st.session_state.running_dags = {}
    
    if 'workflow_progress' not in st.session_state:
        st.session_state.workflow_progress = {
            'create': False,
            'deploy': False, 
            'trigger': False,
            'monitor': False
        }
    
    if 'persistent_messages' not in st.session_state:
        st.session_state.persistent_messages = {}
    
    # Clean up any stale progress indicators on app restart
    keys_to_remove = [key for key in st.session_state.keys() 
                      if key.startswith(('deploying_', 'triggering_', 'checking_'))]
    for key in keys_to_remove:
        del st.session_state[key]

def main():
    """Main application entry point."""
    st.title("📊 Backtest Management Workflow")
    st.markdown("Streamlined backtest management with AWS MWAA integration")
    
    # Initialize session state
    initialize_session_state()
    
    # Sidebar configuration and connection testing
    show_configuration_status()
    
    # Main workflow sections
    show_workflow_progress_bar()
    show_single_page_workflow()

def show_configuration_status():
    """Show configuration status and connection testing in sidebar."""
    with st.sidebar:
        st.subheader("Configuration Status")
        
        # Validate configuration
        missing_config = st.session_state.aws_utils.validate_configuration()
        
        if missing_config:
            st.error("⚠️ Configuration Issues:")
            for key, message in missing_config.items():
                st.write(f"• {message}")
            st.info("Please check your .env file configuration")
        else:
            st.success("✅ Configuration looks good")
            
            # Test connections button
            if st.button("Test AWS Connections", key="test_connections"):
                with st.spinner("Testing connections..."):
                    results = st.session_state.aws_utils.test_connections()
                    st.session_state.connection_status = results
                    
                    for service, status in results.items():
                        if status:
                            st.success(f"✅ {service.upper()}: Connected")
                        else:
                            st.error(f"❌ {service.upper()}: Failed")
        
        # Show last connection test results
        if st.session_state.connection_status:
            st.subheader("Last Connection Test")
            for service, status in st.session_state.connection_status.items():
                icon = "✅" if status else "❌"
                st.write(f"{icon} {service.upper()}")
        


def show_workflow_progress_bar():
    """Show workflow progress indicator."""
    st.subheader("🔄 Workflow Progress")
    
    progress = st.session_state.workflow_progress
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        icon = "✅" if progress['create'] else "⭕"
        st.write(f"{icon} **1. Create**")
    
    with col2:
        icon = "✅" if progress['deploy'] else "⭕"
        st.write(f"{icon} **2. Deploy**")
    
    with col3:
        icon = "✅" if progress['trigger'] else "⭕"
        st.write(f"{icon} **3. Trigger**")
    
    with col4:
        icon = "✅" if progress['monitor'] else "⭕"
        st.write(f"{icon} **4. Monitor**")
    
    st.divider()

def show_single_page_workflow():
    """Display the single-page workflow with expandable sections."""
    
    # Step 1: Create Configuration
    with st.expander("1️⃣ Create Backtest Configuration", expanded=True):
        show_create_section()
    
    # Step 2: Deploy DAG (enabled after create)
    create_completed = bool(st.session_state.backtest_configs)
    with st.expander("2️⃣ Deploy DAG to MWAA", expanded=create_completed and not st.session_state.workflow_progress['deploy']):
        if create_completed:
            show_deploy_section()
        else:
            st.info("💡 Complete step 1 to enable deployment")
    
    # Step 3: Trigger Backtest (enabled after deploy)
    deploy_completed = bool(st.session_state.deployed_dags)
    with st.expander("3️⃣ Trigger Backtest Execution", expanded=deploy_completed and not st.session_state.workflow_progress['trigger']):
        if deploy_completed:
            show_trigger_section()
        else:
            st.info("💡 Complete step 2 to enable triggering")
    
    # Step 4: Monitor Progress (enabled after trigger)
    trigger_completed = bool(st.session_state.running_dags)
    with st.expander("4️⃣ Monitor Backtest Progress", expanded=trigger_completed):
        if trigger_completed:
            show_monitor_section()
        else:
            st.info("💡 Complete step 3 to enable monitoring")
    


def show_create_section():
    """Display the create backtest configuration section."""
    st.markdown("### 📋 Configuration Form")
    
    # Check if connections are working
    if not st.session_state.connection_status:
        st.warning("⚠️ Please test AWS connections first using the sidebar.")
        return
    
    if not all(st.session_state.connection_status.values()):
        st.error("❌ Some AWS connections failed. Please check your configuration.")
        return
    
    with st.form("create_backtest_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            backtest_name = st.text_input(
                "Backtest Name",
                value=st.session_state.current_config.get('name', ''),
                placeholder="e.g., LongShort_Q1_2024",
                help="Human-readable name for this backtest"
            )
            
            strategy_class = st.selectbox(
                "Strategy Class",
                options=[
                    "LongShortEquityStrategy",
                    "MeanReversionStrategy", 
                    "MomentumStrategy"
                ],
                help="Strategy class to use for backtesting"
            )
            
            start_date = st.date_input(
                "Start Date",
                value=datetime(2022, 1, 1).date(),
                help="Backtest start date"
            )
        
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime(2024, 12, 31).date(),
                help="Backtest end date"
            )
            
            initial_capital = st.number_input(
                "Initial Capital ($)",
                value=1000000.0,
                min_value=1000.0,
                step=10000.0,
                format="%.0f",
                help="Starting capital for the backtest"
            )
            
            factors_input = st.text_input(
                "Factors (comma-separated)",
                value="NewsSentiment",
                placeholder="NewsSentiment, DebtToEquity, PriceToEarnings",
                help="Factors to use in the strategy"
            )
        
        # Parse factors
        factors = [f.strip() for f in factors_input.split(',') if f.strip()]
        
        # Additional configuration options
        st.subheader("🎯 Trading Universe")
        
        universe_input = st.text_input(
            "Universe (comma-separated symbols)",
            value="",
            placeholder="AAPL, MSFT, GOOGL (leave empty for default universe)",
            help="Specific securities to trade. Leave empty to use default universe from strategy."
        )
        
        # Parse universe
        universe = [s.strip().upper() for s in universe_input.split(',') if s.strip()] if universe_input.strip() else []
        
        # Strategy parameters
        st.subheader("⚙️ Strategy Parameters")
        
        param_grid = {}
        if strategy_class == "LongShortEquityStrategy":
            col1, col2 = st.columns(2)
            with col1:
                param_grid['rebalance_period'] = st.text_input(
                    "Rebalance Period (days)", 
                    value="7,14,21",
                    help="Days between portfolio rebalancing"
                )
                param_grid['take_profit_pct'] = st.text_input(
                    "Take Profit %", 
                    value="0.1,0.15,0.2",
                    help="Take profit percentage (e.g., 0.1 = 10%)"
                )
            with col2:
                param_grid['stop_loss_pct'] = st.text_input(
                    "Stop Loss %", 
                    value="0.05,0.08,0.1",
                    help="Stop loss percentage (e.g., 0.05 = 5%)"
                )
                param_grid['cooldown_period'] = st.text_input(
                    "Cooldown Period (days)", 
                    value="7,14,21",
                    help="Days to wait before re-entering a position"
                )
        elif strategy_class == "MeanReversionStrategy":
            col1, col2 = st.columns(2)
            with col1:
                param_grid['lookback_period'] = st.text_input(
                    "Lookback Period", 
                    value="20,30,40",
                    help="Number of periods to look back for mean calculation"
                )
                param_grid['entry_threshold'] = st.text_input(
                    "Entry Threshold", 
                    value="2.0,2.5,3.0",
                    help="Standard deviations from mean to trigger entry"
                )
            with col2:
                param_grid['stop_loss_pct'] = st.text_input(
                    "Stop Loss %", 
                    value="0.05,0.08,0.1",
                    help="Stop loss percentage"
                )
                param_grid['cooldown_period'] = st.text_input(
                    "Cooldown Period (days)", 
                    value="5,10,15",
                    help="Days to wait before re-entering"
                )
        else:  # MomentumStrategy
            col1, col2 = st.columns(2)
            with col1:
                param_grid['momentum_period'] = st.text_input(
                    "Momentum Period", 
                    value="10,20,30",
                    help="Period for momentum calculation"
                )
                param_grid['signal_threshold'] = st.text_input(
                    "Signal Threshold", 
                    value="0.05,0.1,0.15",
                    help="Minimum signal strength to trigger trade"
                )
            with col2:
                param_grid['stop_loss_pct'] = st.text_input(
                    "Stop Loss %", 
                    value="0.05,0.08,0.1",
                    help="Stop loss percentage"
                )
                param_grid['cooldown_period'] = st.text_input(
                    "Cooldown Period (days)", 
                    value="3,7,14",
                    help="Days to wait before re-entering"
                )
        
        # Comprehensive validation using ErrorHandler
        config_for_validation = {
            'name': backtest_name.strip() if backtest_name else '',
            'strategy_class': strategy_class,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'initial_capital': initial_capital,
            'factors': factors,
            'universe': universe,
            'param_grid': param_grid
        }
        
        # Submit button (validate only on submit)
        submitted = st.form_submit_button(
            "🚀 Create Backtest Configuration",
            type="primary"
        )
        
        # Only validate when form is submitted
        if submitted:
            validation_result = ErrorHandler.validate_config(config_for_validation)
            

            
            # Show validation results
            if not validation_result['valid']:
                st.error("❌ Configuration Errors:")
                for error_info in validation_result['errors']:
                    st.error(f"• {error_info['message']}")
                    if error_info.get('suggestions'):
                        for suggestion in error_info['suggestions'][:2]:  # Show first 2 suggestions
                            st.write(f"  💡 {suggestion}")
                validation_errors = validation_result['errors']
            else:
                total_jobs = validation_result['total_combinations']
                st.success(f"✅ Configuration valid - Will create {total_jobs:,} backtest jobs")
                
                # Show warnings if any
                if validation_result.get('warnings'):
                    for warning in validation_result['warnings']:
                        st.warning(f"⚠️ {warning['message']}")
                
                validation_errors = []
        else:
            validation_errors = []
        
        if submitted and not validation_errors:
            # Create configuration
            config = config_for_validation.copy()
            config.update({
                'created_at': datetime.now().isoformat(),
                'total_jobs': total_jobs
            })
            
            # Generate unique backtest ID
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            clean_strategy = strategy_class.lower().replace('strategy', '')
            backtest_id = f"backtest_{clean_strategy}_{timestamp}"
            
            # Save to session state
            st.session_state.backtest_configs[backtest_id] = config
            st.session_state.current_config = config
            st.session_state.workflow_progress['create'] = True
            
            # Add persistent success messages
            add_persistent_message(backtest_id, 'success', 'Configuration created successfully!')
            add_persistent_message(backtest_id, 'info', f'Backtest ID: {backtest_id}')
            
            # Auto-generate DAG
            with st.spinner("🔧 Generating DAG..."):
                dag_result = st.session_state.dag_generator.generate_dag(config)
                if dag_result['success']:
                    st.session_state.generated_dags[backtest_id] = dag_result
                    add_persistent_message(backtest_id, 'success', 'DAG generated successfully!')
                else:
                    add_persistent_message(backtest_id, 'error', f'DAG generation failed: {dag_result["error"]}')
            
            st.rerun()

def deploy_dag_to_mwaa(backtest_id: str, dag_info: Dict[str, Any]) -> Dict[str, Any]:
    """Deploy DAG to MWAA with detailed persistent logging."""
    dag_content = dag_info['dag_content']
    dag_filename = dag_info['filename']
    dag_id = dag_info['dag_id']
    
    # Initialize deployment log in session state
    if 'deployment_logs' not in st.session_state:
        st.session_state.deployment_logs = {}
    
    deployment_log = []
    
    try:
        # Step 1: Upload to S3
        deployment_log.append("📤 **Step 1: Uploading DAG to S3...**")
        deployment_log.append(f"   - DAG ID: `{dag_id}`")
        deployment_log.append(f"   - Filename: `{dag_filename}`")
        deployment_log.append(f"   - Content size: {len(dag_content)} characters")
        deployment_log.append(f"   - Target bucket: `{st.session_state.aws_utils.s3_dags_bucket}`")
        
        upload_result = st.session_state.aws_utils.upload_dag_to_s3(dag_content, dag_filename)
        
        if not upload_result['success']:
            deployment_log.append(f"❌ **S3 upload failed:** {upload_result['error']}")
            deployment_log.append("   - **Troubleshooting:**")
            deployment_log.append("     • Check S3 bucket permissions")
            deployment_log.append("     • Verify AWS credentials and profile")
            deployment_log.append("     • Ensure bucket exists and is accessible")
            deployment_log.append("     • Check network connectivity")
            
            st.session_state.deployment_logs[backtest_id] = deployment_log
            
            # Add persistent error message
            add_persistent_message(backtest_id, 'error', f'Deployment failed: {upload_result["error"]}')
            
            return {'success': False, 'error': upload_result['error']}
        
        deployment_log.append(f"✅ **S3 upload successful**")
        deployment_log.append(f"   - S3 Path: `{upload_result['s3_path']}`")
        deployment_log.append(f"   - Upload completed at: {datetime.now().strftime('%H:%M:%S')}")
        
        # Step 2: Wait for MWAA detection (required for streamlined workflow)
        deployment_log.append("⏳ **Step 2: Waiting for MWAA detection...**")
        
        import time
        max_attempts = 30  # 5 minutes total
        
        for attempt in range(max_attempts):
            check_result = st.session_state.aws_utils.check_dag_in_airflow(dag_id)
            
            if check_result['success'] and check_result['found']:
                deployment_log.append(f"✅ **DAG detected by MWAA!** (attempt {attempt + 1})")
                
                # Step 3: Unpause the DAG automatically
                if check_result.get('is_paused', True):
                    deployment_log.append("🔓 **Step 3: Unpausing DAG...**")
                    unpause_result = st.session_state.aws_utils.unpause_dag(dag_id)
                    
                    if unpause_result['success']:
                        deployment_log.append("✅ **DAG unpaused successfully**")
                    else:
                        deployment_log.append(f"❌ **Failed to unpause DAG:** {unpause_result['error']}")
                else:
                    deployment_log.append("✅ **Step 3: DAG already active**")
                
                # Mark as deployed and ready
                st.session_state.deployed_dags[backtest_id] = {
                    'success': True,
                    'dag_id': dag_id,
                    's3_path': upload_result['s3_path'],
                    'deployed_at': datetime.now().isoformat(),
                    'ready_to_trigger': True
                }
                st.session_state.workflow_progress['deploy'] = True
                
                deployment_log.append("🎉 **Deployment completed successfully!**")
                
                st.session_state.deployment_logs[backtest_id] = deployment_log
                
                # Add persistent success message
                add_persistent_message(backtest_id, 'success', 'Deployment completed - DAG ready to trigger!')
                
                return {
                    'success': True,
                    'dag_id': dag_id,
                    's3_path': upload_result['s3_path']
                }
            
            # Still waiting for detection
            if attempt < max_attempts - 1:  # Don't sleep on last attempt
                time.sleep(10)
        
        # Timeout - DAG not detected
        deployment_log.append("❌ **Timeout: DAG not detected by MWAA**")
        deployment_log.append("   - **Possible issues:**")
        deployment_log.append("     • DAG has parsing errors")
        deployment_log.append("     • MWAA is experiencing delays")
        deployment_log.append("     • Network connectivity issues")
        deployment_log.append("   - **Action:** Check Airflow UI for import errors")
        
        st.session_state.deployment_logs[backtest_id] = deployment_log
        
        # Add persistent error message
        add_persistent_message(backtest_id, 'error', 'Deployment timeout - DAG not detected by MWAA')
        
        return {
            'success': False,
            'error': 'Timeout waiting for MWAA to detect the DAG'
        }
        
    except Exception as e:
        deployment_log.append(f"❌ **Deployment failed with exception:** {str(e)}")
        deployment_log.append("   - **Error details:**")
        deployment_log.append(f"     • Exception type: {type(e).__name__}")
        deployment_log.append(f"     • Error message: {str(e)}")
        deployment_log.append("   - **Troubleshooting:**")
        deployment_log.append("     • Check AWS credentials and permissions")
        deployment_log.append("     • Verify network connectivity")
        deployment_log.append("     • Check application logs for more details")
        
        st.session_state.deployment_logs[backtest_id] = deployment_log
        return {'success': False, 'error': str(e)}

def show_deploy_section():
    """Display the deploy DAG section."""
    st.markdown("### 🚀 Deploy to MWAA")
    
    if not st.session_state.generated_dags:
        st.info("No generated DAGs available for deployment")
        return
    
    for backtest_id, dag_info in st.session_state.generated_dags.items():
        if not dag_info['success']:
            continue
            
        config = st.session_state.backtest_configs[backtest_id]
        
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**{config['name']}** ({dag_info['dag_id']})")
                st.write(f"Strategy: {config['strategy_class']}, Jobs: {config['total_jobs']:,}")
                
                # Show persistent messages for this backtest
                show_persistent_messages(backtest_id)
            
            with col2:
                if backtest_id not in st.session_state.deployed_dags:
                    # Check if deployment is in progress
                    deployment_in_progress = st.session_state.get(f'deploying_{backtest_id}', False)
                    
                    if deployment_in_progress:
                        st.button("🔄 Deploying...", key=f"deploy_{backtest_id}", disabled=True)
                    else:
                        if st.button(f"🚀 Deploy", key=f"deploy_{backtest_id}"):
                            # Set deployment in progress
                            st.session_state[f'deploying_{backtest_id}'] = True
                            
                            with st.spinner("Deploying DAG to MWAA..."):
                                deploy_result = deploy_dag_to_mwaa(backtest_id, dag_info)
                            
                            # Clear deployment in progress
                            st.session_state[f'deploying_{backtest_id}'] = False
                            
                            # Rerun to update UI
                            st.rerun()
                else:
                    deploy_info = st.session_state.deployed_dags[backtest_id]
                    if deploy_info['success']:
                        st.success("✅ Deployed")
                        

                        
                        # Check detection button
                        checking_in_progress = st.session_state.get(f'checking_{backtest_id}', False)
                        
                        if checking_in_progress:
                            st.button("🔄 Checking...", key=f"check_{backtest_id}", disabled=True)
                        else:
                            if st.button(f"🔍 Check Detection", key=f"check_{backtest_id}"):
                                # Set checking in progress
                                st.session_state[f'checking_{backtest_id}'] = True
                                
                                with st.spinner("Checking DAG detection..."):
                                    check_result = st.session_state.aws_utils.check_dag_in_airflow(dag_info['dag_id'])
                                    if check_result['success'] and check_result['found']:
                                        st.success("✅ DAG detected by MWAA!")
                                        st.info(f"Status: {'Paused' if check_result.get('is_paused') else 'Active'}")
                                    else:
                                        st.warning("⏳ DAG not detected yet. Wait a bit longer.")
                                
                                # Clear checking in progress
                                st.session_state[f'checking_{backtest_id}'] = False
                    else:
                        st.error("❌ Failed")
                        


def trigger_dag_run(backtest_id: str, dag_id: str) -> Dict[str, Any]:
    """Trigger a DAG run with detailed persistent logging."""
    # Initialize trigger log in session state
    if 'trigger_logs' not in st.session_state:
        st.session_state.trigger_logs = {}
    
    trigger_log = []
    
    try:
        # Step 1: Check if already running
        trigger_log.append("🔍 **Step 1: Checking existing runs...**")
        trigger_log.append(f"   - DAG ID: `{dag_id}`")
        
        if backtest_id in st.session_state.running_dags:
            existing_run = st.session_state.running_dags[backtest_id]
            if existing_run.get('state') in ['running', 'queued']:
                trigger_log.append("⚠️ **Backtest already running**")
                trigger_log.append(f"   - Existing run ID: `{existing_run.get('dag_run_id', 'unknown')}`")
                trigger_log.append(f"   - Current state: `{existing_run.get('state', 'unknown')}`")
                trigger_log.append("   - **Action:** Cannot start new run while existing run is active")
                
                st.session_state.trigger_logs[backtest_id] = trigger_log
                
                # Add persistent warning message
                add_persistent_message(backtest_id, 'warning', 'Backtest already running!')
                
                return {'success': False, 'error': 'DAG already running'}
        
        trigger_log.append("✅ **No existing runs found - proceeding**")
        
        # Step 2: Check DAG status
        trigger_log.append("🔍 **Step 2: Checking DAG status in MWAA...**")
        trigger_log.append("   - Querying Airflow API...")
        
        dag_check = st.session_state.aws_utils.check_dag_in_airflow(dag_id)
        
        if not dag_check['success']:
            trigger_log.append(f"❌ **API Error:** {dag_check['error']}")
            trigger_log.append("   - **Troubleshooting:**")
            trigger_log.append("     • Check network connectivity")
            trigger_log.append("     • Verify MWAA environment is running")
            trigger_log.append("     • Check AWS credentials")
            
            st.session_state.trigger_logs[backtest_id] = trigger_log
            return {'success': False, 'error': dag_check['error']}
        
        if not dag_check['found']:
            trigger_log.append("❌ **DAG not found in Airflow**")
            trigger_log.append("   - **Possible causes:**")
            trigger_log.append("     • DAG not yet detected by MWAA (wait 2-5 minutes)")
            trigger_log.append("     • DAG has parsing errors")
            trigger_log.append("     • DAG file not properly uploaded to S3")
            trigger_log.append("   - **Action:** Wait and retry, or check Airflow UI")
            
            st.session_state.trigger_logs[backtest_id] = trigger_log
            
            # Add persistent error message
            add_persistent_message(backtest_id, 'error', 'DAG not found in Airflow!')
            
            return {'success': False, 'error': 'DAG not found'}
        
        trigger_log.append("✅ **DAG found in Airflow**")
        trigger_log.append(f"   - Status: {'Paused' if dag_check.get('is_paused') else 'Active'}")
        trigger_log.append(f"   - Last parsed: {dag_check.get('dag_info', {}).get('last_parsed_time', 'Unknown')}")
        
        # Step 3: Unpause if needed
        if dag_check.get('is_paused', True):
            trigger_log.append("🔓 **Step 3: Unpausing DAG...**")
            trigger_log.append("   - DAG is currently paused")
            trigger_log.append("   - Sending unpause request...")
            
            unpause_result = st.session_state.aws_utils.unpause_dag(dag_id)
            if not unpause_result['success']:
                trigger_log.append(f"❌ **Failed to unpause DAG:** {unpause_result['error']}")
                trigger_log.append("   - **Troubleshooting:**")
                trigger_log.append("     • Check DAG permissions")
                trigger_log.append("     • Verify API connectivity")
                trigger_log.append("     • Try manually unpausing in Airflow UI")
                
                st.session_state.trigger_logs[backtest_id] = trigger_log
                return unpause_result
            
            trigger_log.append("✅ **DAG unpaused successfully**")
        else:
            trigger_log.append("✅ **Step 3: DAG already active (not paused)**")
        
        # Step 4: Trigger the DAG
        trigger_log.append("▶️ **Step 4: Triggering DAG run...**")
        config = st.session_state.backtest_configs.get(backtest_id, {})
        trigger_log.append(f"   - Configuration: {len(config)} parameters")
        trigger_log.append(f"   - Strategy: {config.get('strategy_class', 'Unknown')}")
        trigger_log.append(f"   - Expected jobs: {config.get('total_jobs', 'Unknown')}")
        trigger_log.append("   - Sending trigger request...")
        
        result = st.session_state.aws_utils.trigger_dag_run(dag_id, config)
        
        if result['success']:
            trigger_log.append("🎉 **DAG triggered successfully!**")
            trigger_log.append(f"   - DAG Run ID: `{result['dag_run_id']}`")
            trigger_log.append(f"   - Execution Date: `{result.get('execution_date', 'Unknown')}`")
            trigger_log.append(f"   - Initial State: `{result.get('state', 'Unknown')}`")
            trigger_log.append(f"   - Triggered at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            trigger_log.append("   - **Status:** Ready for monitoring")
            
            # Store running DAG info
            st.session_state.running_dags[backtest_id] = {
                'dag_id': dag_id,
                'dag_run_id': result['dag_run_id'],
                'execution_date': result['execution_date'],
                'state': result['state'],
                'triggered_at': result['triggered_at'],
                'config': config
            }
            st.session_state.workflow_progress['trigger'] = True
            
            st.session_state.trigger_logs[backtest_id] = trigger_log
            
            # Add persistent success message
            add_persistent_message(backtest_id, 'success', f'DAG triggered successfully! Run ID: {result["dag_run_id"]}')
            
            return result
        else:
            trigger_log.append(f"❌ **Failed to trigger DAG:** {result['error']}")
            trigger_log.append("   - **Error details:**")
            trigger_log.append(f"     • Error type: {result.get('error_type', 'Unknown')}")
            trigger_log.append("   - **Troubleshooting:**")
            trigger_log.append("     • Check DAG configuration")
            trigger_log.append("     • Verify DAG is not paused")
            trigger_log.append("     • Check Airflow UI for more details")
            
            st.session_state.trigger_logs[backtest_id] = trigger_log
            return result
            
    except Exception as e:
        trigger_log.append(f"❌ **Trigger failed with exception:** {str(e)}")
        trigger_log.append("   - **Error details:**")
        trigger_log.append(f"     • Exception type: {type(e).__name__}")
        trigger_log.append(f"     • Error message: {str(e)}")
        trigger_log.append("   - **Troubleshooting:**")
        trigger_log.append("     • Check network connectivity")
        trigger_log.append("     • Verify AWS credentials")
        trigger_log.append("     • Check application logs")
        
        st.session_state.trigger_logs[backtest_id] = trigger_log
        return {'success': False, 'error': str(e)}

def show_trigger_section():
    """Display the trigger backtest section."""
    st.markdown("### ▶️ Trigger Execution")
    
    if not st.session_state.deployed_dags:
        st.info("No deployed DAGs available for triggering")
        return
    
    for backtest_id, deploy_info in st.session_state.deployed_dags.items():
        if deploy_info['success']:
            config = st.session_state.backtest_configs[backtest_id]
            dag_id = deploy_info['dag_id']
            
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**{config['name']}** ({dag_id})")
                    st.write(f"Jobs: {config['total_jobs']:,}")
                
                with col2:
                    if backtest_id not in st.session_state.running_dags:
                        # Check if triggering is in progress
                        triggering_in_progress = st.session_state.get(f'triggering_{backtest_id}', False)
                        
                        if triggering_in_progress:
                            st.button("⏳ Triggering...", key=f"trigger_{backtest_id}", disabled=True)
                        else:
                            if st.button(f"▶️ Trigger", key=f"trigger_{backtest_id}"):
                                # Set triggering in progress
                                st.session_state[f'triggering_{backtest_id}'] = True
                                
                                with st.spinner("Triggering DAG run..."):
                                    trigger_result = trigger_dag_run(backtest_id, dag_id)
                                
                                # Clear triggering in progress
                                st.session_state[f'triggering_{backtest_id}'] = False
                                
                                # Rerun to update UI
                                st.rerun()
                    else:
                        run_info = st.session_state.running_dags[backtest_id]
                        state = run_info.get('state', 'unknown')
                        if state in ['running', 'queued']:
                            st.info("🏃 Running")
                        elif state == 'success':
                            st.success("✅ Complete")
                        elif state == 'failed':
                            st.error("❌ Failed")
                        else:
                            st.info(f"📊 {state.title()}")
                


def show_monitor_section():
    """Display the monitor backtest section with real-time monitoring."""
    st.markdown("### 📊 Monitor Progress")
    
    if not st.session_state.running_dags:
        st.info("No running backtests to monitor")
        return
    
    st.session_state.workflow_progress['monitor'] = True
    
    # Auto-refresh controls
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("🔄 **Real-time Monitoring** (updates every 10 seconds)")
    with col2:
        refreshing_in_progress = st.session_state.get('refreshing_monitor', False)
        
        if refreshing_in_progress:
            st.button("⏳ Refreshing...", key="refresh_monitor", disabled=True)
        else:
            if st.button("🔄 Refresh Now", key="refresh_monitor"):
                # Set refreshing in progress
                st.session_state['refreshing_monitor'] = True
                
                with st.spinner("Refreshing monitoring data..."):
                    # Small delay to show the spinner
                    import time
                    time.sleep(0.5)
                
                # Clear refreshing in progress
                st.session_state['refreshing_monitor'] = False
                
                st.rerun()
    
    for backtest_id, run_info in st.session_state.running_dags.items():
        config = st.session_state.backtest_configs[backtest_id]
        dag_id = run_info['dag_id']
        dag_run_id = run_info['dag_run_id']
        
        with st.container():
            st.write(f"**{config['name']}** - {dag_run_id}")
            
            # Get current status from Airflow
            with st.spinner("Fetching status..."):
                status_result = st.session_state.aws_utils.get_dag_run_status(dag_id, dag_run_id)
            
            if status_result['success']:
                dag_run = status_result['dag_run']
                tasks = status_result['tasks']
                current_state = dag_run.get('state', 'unknown')
                
                # Update stored state
                st.session_state.running_dags[backtest_id]['state'] = current_state
                
                # Display metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Status", current_state.title())
                with col2:
                    if tasks:
                        st.metric("Total Jobs", f"{len(tasks):,}")
                    else:
                        st.metric("Total Jobs", f"{config.get('total_jobs', 0):,}")
                with col3:
                    if tasks:
                        completed_tasks = len([t for t in tasks if t.get('state') == 'success'])
                        st.metric("Completed", f"{completed_tasks}/{len(tasks)}")
                    else:
                        st.metric("Completed", "Loading...")
                with col4:
                    start_date = dag_run.get('start_date')
                    if start_date:
                        from datetime import datetime
                        start_time = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        duration = datetime.now() - start_time.replace(tzinfo=None)
                        total_minutes = int(duration.total_seconds() // 60)
                        
                        # Format duration nicely
                        if total_minutes < 60:
                            st.metric("Duration", f"{total_minutes}m")
                        else:
                            hours = total_minutes // 60
                            minutes = total_minutes % 60
                            st.metric("Duration", f"{hours}h {minutes}m")
                    else:
                        st.metric("Duration", "N/A")
                
                # Progress bar
                if tasks:
                    completed = len([t for t in tasks if t.get('state') == 'success'])
                    failed = len([t for t in tasks if t.get('state') == 'failed'])
                    running = len([t for t in tasks if t.get('state') == 'running'])
                    total = len(tasks)
                    
                    if total > 0:
                        progress = completed / total
                        st.progress(progress)
                        
                        if failed > 0:
                            st.error(f"❌ {failed} tasks failed")
                        if running > 0:
                            st.info(f"🏃 {running} tasks running")
                        if completed == total:
                            st.success("✅ All tasks completed!")
                
                # Task details in expander
                if tasks:
                    with st.expander(f"Task Details ({len(tasks)} tasks)", expanded=False):
                        for task in tasks[:10]:  # Show first 10 tasks
                            task_state = task.get('state', 'unknown')
                            task_id = task.get('task_id', 'unknown')
                            
                            if task_state == 'success':
                                st.success(f"✅ {task_id}")
                            elif task_state == 'failed':
                                st.error(f"❌ {task_id}")
                            elif task_state == 'running':
                                st.info(f"🏃 {task_id}")
                            else:
                                st.write(f"⭕ {task_id} - {task_state}")
                        
                        if len(tasks) > 10:
                            st.write(f"... and {len(tasks) - 10} more tasks")
                
                # Final status handling
                if current_state in ['success', 'failed']:
                    if current_state == 'success':
                        st.success("🎉 Backtest completed successfully!")
                    else:
                        st.error("❌ Backtest failed")
                    
                    # Option to remove from monitoring
                    reviewing_in_progress = st.session_state.get(f'reviewing_{backtest_id}', False)
                    
                    if reviewing_in_progress:
                        st.button("⏳ Processing...", key=f"review_{backtest_id}", disabled=True)
                    else:
                        if st.button(f"✅ Mark as Reviewed", key=f"review_{backtest_id}"):
                            # Set reviewing in progress
                            st.session_state[f'reviewing_{backtest_id}'] = True
                            
                            with st.spinner("Marking as reviewed..."):
                                # Small delay to show the spinner
                                import time
                                time.sleep(0.3)
                                del st.session_state.running_dags[backtest_id]
                            
                            # Clear reviewing in progress
                            st.session_state[f'reviewing_{backtest_id}'] = False
                            
                            st.rerun()
            
            else:
                st.error(f"❌ Failed to get status: {status_result['error']}")
            
            st.divider()
    
    # Auto-refresh every 10 seconds for running DAGs
    if any(run_info.get('state') in ['running', 'queued', None] for run_info in st.session_state.running_dags.values()):
        import time
        time.sleep(10)
        st.rerun()

if __name__ == "__main__":
    main()