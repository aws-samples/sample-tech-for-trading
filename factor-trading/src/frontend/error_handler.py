"""
Error Handler for Backtest Frontend
Comprehensive error handling and user guidance.
"""

import os
import logging
import traceback
from typing import Dict, Any, List, Callable
from functools import wraps
import streamlit as st

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Comprehensive error handling for backtest frontend."""
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate backtest configuration with detailed error messages."""
        from dag_generator import DAGGenerator
        
        dag_generator = DAGGenerator()
        return dag_generator.validate_config(config)
    
    @staticmethod
    def handle_aws_error(error: Exception, operation: str) -> Dict[str, Any]:
        """Handle AWS-specific errors with user guidance."""
        error_str = str(error)
        error_type = type(error).__name__
        
        # Common AWS error patterns
        if 'NoCredentialsError' in error_type:
            return {
                'type': 'credentials',
                'message': 'AWS credentials not found',
                'suggestions': [
                    'Configure AWS profile: aws configure --profile your-profile-name',
                    'Set AWS_PROFILE in your .env file to match your profile',
                    'Use default profile: aws configure (and omit AWS_PROFILE)',
                    'Verify profile exists: aws configure list-profiles',
                    'Use IAM roles if running on EC2'
                ],
                'recovery_actions': ['test_connections']
            }
        
        elif 'AccessDenied' in error_str or 'Forbidden' in error_str:
            return {
                'type': 'permissions',
                'message': f'Access denied for {operation}',
                'suggestions': [
                    'Check IAM permissions for the required AWS services',
                    'Ensure your user/role has MWAA, S3, and Batch permissions',
                    'Verify the resource names in your configuration'
                ],
                'recovery_actions': ['check_config', 'test_connections']
            }
        
        elif 'BucketNotFound' in error_str or 'NoSuchBucket' in error_str:
            return {
                'type': 'resource_not_found',
                'message': 'S3 bucket not found',
                'suggestions': [
                    'Check the S3_DAGS_BUCKET setting in your .env file',
                    'Verify the bucket exists in the correct AWS region',
                    'Ensure the bucket name is correct'
                ],
                'recovery_actions': ['check_config']
            }
        
        elif 'EnvironmentNotFound' in error_str:
            return {
                'type': 'resource_not_found',
                'message': 'MWAA environment not found',
                'suggestions': [
                    'Check the MWAA_ENVIRONMENT_NAME setting',
                    'Verify the environment exists in the correct region',
                    'Ensure the environment is in AVAILABLE status'
                ],
                'recovery_actions': ['check_config']
            }
        
        elif 'ConnectionError' in error_type or 'timeout' in error_str.lower():
            return {
                'type': 'network',
                'message': f'Network error during {operation}',
                'suggestions': [
                    'Check your internet connection',
                    'Verify AWS service endpoints are accessible',
                    'Try again in a few moments'
                ],
                'recovery_actions': ['retry', 'test_connections']
            }
        
        else:
            return {
                'type': 'unknown',
                'message': f'AWS error during {operation}: {error_str}',
                'suggestions': [
                    'Check AWS service status',
                    'Verify your configuration',
                    'Try the operation again'
                ],
                'recovery_actions': ['retry', 'test_connections']
            }
    
    @staticmethod
    def handle_airflow_error(error: Exception, operation: str) -> Dict[str, Any]:
        """Handle Airflow API errors with specific guidance."""
        error_str = str(error)
        
        if '404' in error_str:
            return {
                'type': 'not_found',
                'message': 'DAG not found in Airflow',
                'suggestions': [
                    'Wait 2-5 minutes for MWAA to detect the DAG',
                    'Check if the DAG was deployed successfully',
                    'Verify the DAG file exists in the S3 bucket',
                    'Check the Airflow UI for import errors'
                ],
                'recovery_actions': ['wait', 'check_deployment', 'check_airflow_ui']
            }
        
        elif '401' in error_str or '403' in error_str:
            return {
                'type': 'authentication',
                'message': 'Authentication failed with Airflow API',
                'suggestions': [
                    'Check AIRFLOW_WEBSERVER_URL setting',
                    'Verify MWAA environment permissions',
                    'Ensure your AWS credentials have airflow:InvokeRestApi permission'
                ],
                'recovery_actions': ['check_config', 'test_connections']
            }
        
        elif '409' in error_str:
            return {
                'type': 'conflict',
                'message': 'DAG run already exists',
                'suggestions': [
                    'A run with this ID already exists',
                    'Wait for the current run to complete',
                    'Check the Monitor page for existing runs'
                ],
                'recovery_actions': ['check_monitor', 'wait']
            }
        
        elif 'timeout' in error_str.lower() or 'ConnectionError' in str(type(error)):
            return {
                'type': 'network',
                'message': 'Connection timeout to Airflow API',
                'suggestions': [
                    'Check your network connection',
                    'Verify AIRFLOW_WEBSERVER_URL is correct',
                    'Ensure MWAA environment is running'
                ],
                'recovery_actions': ['retry', 'test_connections']
            }
        
        else:
            return {
                'type': 'api_error',
                'message': f'Airflow API error: {error_str}',
                'suggestions': [
                    'Check the Airflow UI for more details',
                    'Verify the DAG is not paused',
                    'Try the operation again'
                ],
                'recovery_actions': ['retry', 'check_airflow_ui']
            }
    
    @staticmethod
    def display_error(error_info: Dict[str, Any], show_suggestions: bool = True):
        """Display error information in Streamlit with user guidance."""
        st.error(f"❌ {error_info['message']}")
        
        if show_suggestions and error_info.get('suggestions'):
            st.info("💡 **Troubleshooting suggestions:**")
            for suggestion in error_info['suggestions'][:3]:  # Show top 3 suggestions
                st.write(f"• {suggestion}")
        
        # Show recovery actions as buttons
        if error_info.get('recovery_actions'):
            st.write("**Recovery options:**")
            col1, col2, col3 = st.columns(3)
            
            actions = error_info['recovery_actions'][:3]  # Show up to 3 actions
            
            for i, action in enumerate(actions):
                with [col1, col2, col3][i]:
                    if action == 'retry':
                        st.button("🔄 Retry", key=f"retry_{hash(error_info['message'])}")
                    elif action == 'test_connections':
                        st.button("🔗 Test Connections", key=f"test_{hash(error_info['message'])}")
                    elif action == 'check_config':
                        st.button("⚙️ Check Config", key=f"config_{hash(error_info['message'])}")
    
    @staticmethod
    def with_error_handling(operation_name: str, show_success: bool = True):
        """Decorator for comprehensive error handling."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    result = func(*args, **kwargs)
                    
                    if show_success and isinstance(result, dict) and result.get('success'):
                        st.success(f"✅ {operation_name} completed successfully!")
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Error in {operation_name}: {e}")
                    logger.error(traceback.format_exc())
                    
                    # Determine error type and provide specific guidance
                    if 'boto' in str(type(e)).lower() or 'aws' in str(type(e)).lower():
                        error_info = ErrorHandler.handle_aws_error(e, operation_name)
                    elif 'requests' in str(type(e)).lower() or 'http' in str(e).lower():
                        error_info = ErrorHandler.handle_airflow_error(e, operation_name)
                    else:
                        error_info = {
                            'type': 'unknown',
                            'message': f'Error in {operation_name}: {str(e)}',
                            'suggestions': [
                                'Check the application logs for more details',
                                'Try the operation again',
                                'Verify your configuration'
                            ],
                            'recovery_actions': ['retry']
                        }
                    
                    ErrorHandler.display_error(error_info)
                    
                    return {
                        'success': False,
                        'error': str(e),
                        'error_info': error_info
                    }
            
            return wrapper
        return decorator
    

    
    @staticmethod
    def validate_environment():
        """Validate environment setup and provide guidance."""
        issues = []
        
        # Check required environment variables
        required_vars = [
            'AWS_REGION',
            'MWAA_ENVIRONMENT_NAME', 
            'S3_DAGS_BUCKET',
            'AIRFLOW_WEBSERVER_URL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            issues.append({
                'type': 'configuration',
                'message': f'Missing environment variables: {", ".join(missing_vars)}',
                'suggestions': [
                    'Create a .env file based on .env.example',
                    'Set the required environment variables',
                    'Check your configuration'
                ]
            })
        
        # Check Python dependencies
        try:
            import boto3
            import requests
            import streamlit
        except ImportError as e:
            issues.append({
                'type': 'dependencies',
                'message': f'Missing Python dependency: {e}',
                'suggestions': [
                    'Run: pip install -r requirements.txt',
                    'Check your Python environment'
                ]
            })
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }