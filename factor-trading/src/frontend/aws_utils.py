"""
AWS Utilities for Backtest Frontend
Minimal AWS SDK operations for MWAA integration.
"""

import boto3
import requests
import os
import json
from typing import Dict, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError
import logging

logger = logging.getLogger(__name__)

class AWSUtils:
    """Minimal AWS utilities for backtest frontend."""
    
    def __init__(self):
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.aws_profile = os.getenv('AWS_PROFILE')  # Optional AWS profile
        self.mwaa_environment_name = os.getenv('MWAA_ENVIRONMENT_NAME')
        self.s3_dags_bucket = os.getenv('S3_DAGS_BUCKET')
        self.airflow_webserver_url = os.getenv('AIRFLOW_WEBSERVER_URL')
        
        # Initialize clients lazily
        self._s3_client = None
        self._mwaa_client = None
        self._airflow_session = None
    
    def validate_configuration(self) -> Dict[str, str]:
        """Validate required environment variables and AWS profile."""
        missing = {}
        
        if not self.aws_region:
            missing['AWS_REGION'] = 'AWS region is required'
        if not self.mwaa_environment_name:
            missing['MWAA_ENVIRONMENT_NAME'] = 'MWAA environment name is required'
        if not self.s3_dags_bucket:
            missing['S3_DAGS_BUCKET'] = 'S3 DAGs bucket is required'
        if not self.airflow_webserver_url:
            missing['AIRFLOW_WEBSERVER_URL'] = 'Airflow webserver URL is required'
        
        # Validate AWS profile if specified
        if self.aws_profile:
            try:
                session = boto3.Session(profile_name=self.aws_profile)
                # Try to get credentials to validate profile exists
                credentials = session.get_credentials()
                if not credentials:
                    missing['AWS_PROFILE'] = f'AWS profile "{self.aws_profile}" not found or has no credentials'
            except Exception as e:
                missing['AWS_PROFILE'] = f'AWS profile "{self.aws_profile}" error: {str(e)}'
        
        return missing
    
    def get_s3_client(self) -> boto3.client:
        """Get S3 client with lazy initialization using AWS profile."""
        if self._s3_client is None:
            if self.aws_profile:
                # Use specific AWS profile
                session = boto3.Session(profile_name=self.aws_profile)
                self._s3_client = session.client('s3', region_name=self.aws_region)
            else:
                # Use default credentials (IAM role, default profile, or environment variables)
                self._s3_client = boto3.client('s3', region_name=self.aws_region)
        return self._s3_client
    
    def get_mwaa_client(self) -> boto3.client:
        """Get MWAA client with lazy initialization using AWS profile."""
        if self._mwaa_client is None:
            if self.aws_profile:
                # Use specific AWS profile
                session = boto3.Session(profile_name=self.aws_profile)
                self._mwaa_client = session.client('mwaa', region_name=self.aws_region)
            else:
                # Use default credentials (IAM role, default profile, or environment variables)
                self._mwaa_client = boto3.client('mwaa', region_name=self.aws_region)
        return self._mwaa_client
    
    def get_airflow_session(self) -> requests.Session:
        """Get Airflow API session with MWAA web token authentication."""
        try:
            # Get MWAA web token
            mwaa_client = self.get_mwaa_client()
            response = mwaa_client.create_web_login_token(Name=self.mwaa_environment_name)
            
            hostname = response['WebServerHostname']
            token = response['WebToken']
            
            # Exchange for session cookie
            login_response = requests.post(
                f"https://{hostname}/aws_mwaa/login",
                data={"token": token},
                timeout=10
            )
            
            if login_response.status_code != 200:
                raise Exception(f"Failed to get session cookie: HTTP {login_response.status_code}")
            
            # Create session with cookie
            session = requests.Session()
            session.cookies.set("session", login_response.cookies["session"])
            session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to get Airflow session: {e}")
            raise Exception(f"MWAA authentication failed: {e}")
    
    def test_connections(self) -> Dict[str, bool]:
        """Test connections to AWS services."""
        results = {}
        
        # Test S3 connection
        try:
            s3_client = self.get_s3_client()
            s3_client.head_bucket(Bucket=self.s3_dags_bucket)
            results['s3'] = True
        except Exception as e:
            logger.error(f"S3 connection failed: {e}")
            results['s3'] = False
        
        # Test MWAA connection
        try:
            mwaa_client = self.get_mwaa_client()
            response = mwaa_client.get_environment(Name=self.mwaa_environment_name)
            results['mwaa'] = response['Environment']['Status'] == 'AVAILABLE'
        except Exception as e:
            logger.error(f"MWAA connection failed: {e}")
            results['mwaa'] = False
        
        # Test Airflow API connection via MWAA web session
        try:
            session = self.get_airflow_session()
            response = session.get(f"{self.airflow_webserver_url}/api/v1/health", timeout=10)
            results['airflow'] = response.status_code == 200
        except Exception as e:
            logger.error(f"Airflow API connection failed: {e}")
            results['airflow'] = False
        
        return results
    
    def upload_dag_to_s3(self, dag_content: str, dag_filename: str) -> Dict[str, Any]:
        """Upload DAG file to S3 bucket."""
        try:
            s3_client = self.get_s3_client()
            s3_key = f"dags/{dag_filename}"
            
            s3_client.put_object(
                Bucket=self.s3_dags_bucket,
                Key=s3_key,
                Body=dag_content.encode('utf-8'),
                ContentType='text/x-python'
            )
            
            return {
                'success': True,
                's3_path': f"s3://{self.s3_dags_bucket}/{s3_key}",
                's3_key': s3_key
            }
            
        except Exception as e:
            logger.error(f"Failed to upload DAG to S3: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_dag_in_airflow(self, dag_id: str) -> Dict[str, Any]:
        """Check if DAG is available in Airflow using MWAA web session."""
        try:
            session = self.get_airflow_session()
            url = f"{self.airflow_webserver_url}/api/v1/dags/{dag_id}"
            
            response = session.get(url, timeout=10)
            
            if response.status_code == 200:
                dag_info = response.json()
                return {
                    'success': True,
                    'found': True,
                    'is_paused': dag_info.get('is_paused', True),
                    'dag_info': dag_info
                }
            elif response.status_code == 404:
                return {
                    'success': True,
                    'found': False,
                    'message': 'DAG not found in Airflow yet'
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text[:200]}"
                }
                
        except Exception as e:
            logger.error(f"Failed to check DAG in Airflow: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def trigger_dag_run(self, dag_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a DAG run via MWAA web session."""
        try:
            session = self.get_airflow_session()
            
            # Create unique run ID
            from datetime import datetime
            run_id = f"manual__{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            payload = {
                'dag_run_id': run_id,
                'conf': config or {}
            }
            
            url = f"{self.airflow_webserver_url}/api/v1/dags/{dag_id}/dagRuns"
            response = session.post(url, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                run_info = response.json()
                return {
                    'success': True,
                    'dag_run_id': run_info.get('dag_run_id', run_id),
                    'execution_date': run_info.get('execution_date'),
                    'state': run_info.get('state', 'queued'),
                    'triggered_at': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'error_type': 'api_error'
                }
                
        except Exception as e:
            logger.error(f"Failed to trigger DAG run: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'connection_error'
            }
    
    def get_dag_run_status(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        """Get DAG run status and task details via MWAA web session."""
        try:
            session = self.get_airflow_session()
            
            # Get DAG run info
            run_url = f"{self.airflow_webserver_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"
            run_response = session.get(run_url, timeout=30)
            
            if run_response.status_code != 200:
                return {
                    'success': False,
                    'error': f"Failed to get DAG run info: HTTP {run_response.status_code}"
                }
            
            run_info = run_response.json()
            
            # Get task instances
            tasks_url = f"{self.airflow_webserver_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances"
            tasks_response = session.get(tasks_url, timeout=30)
            
            tasks_info = []
            if tasks_response.status_code == 200:
                tasks_info = tasks_response.json().get('task_instances', [])
            
            return {
                'success': True,
                'dag_run': run_info,
                'tasks': tasks_info,
                'state': run_info.get('state'),
                'start_date': run_info.get('start_date'),
                'end_date': run_info.get('end_date')
            }
            
        except Exception as e:
            logger.error(f"Failed to get DAG run status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def unpause_dag(self, dag_id: str) -> Dict[str, Any]:
        """Unpause a DAG in Airflow via MWAA web session."""
        try:
            session = self.get_airflow_session()
            url = f"{self.airflow_webserver_url}/api/v1/dags/{dag_id}"
            
            payload = {'is_paused': False}
            response = session.patch(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Failed to unpause DAG: {e}")
            return {
                'success': False,
                'error': str(e)
            }