"""
Example DAG using the Airflow Backtest Framework.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable

from airflow_backtest_framework.config import BacktestConfig
from airflow_backtest_framework.dag_factory import BacktestDAGFactory

import boto3
import logging
from typing import Dict, Any
from airflow.exceptions import AirflowException


logger = logging.getLogger(__name__)


def check_batch_queue_status(**context) -> None:
    """
    AWS Batch queue status for demonstrating the before_backtest_fn parameter
    
    Args:
        **context: Airflow task context
        
    Raises:
        AirflowException: If batch queue is not available
    """
    try:
        # Get batch queue name from Variable or config
        queue_name = Variable.get('batch_job_queue', 'YOUR_BATCH_JOB_QUEUE_NAME')
        
        # Initialize Batch client
        batch_client = boto3.client('batch')
        
        # Check queue status
        response = batch_client.describe_job_queues(jobQueues=[queue_name])
        
        if not response['jobQueues']:
            raise AirflowException(f"Batch queue '{queue_name}' not found")
            
        queue = response['jobQueues'][0]
        state = queue['state']
        
        if state != 'ENABLED':
            raise AirflowException(f"Batch queue '{queue_name}' is not enabled (state: {state})")
            
        logger.info(f"Batch queue '{queue_name}' is available and enabled")
        
    except Exception as e:
        logger.error(f"Failed to check batch queue status: {str(e)}")
        raise AirflowException(f"Batch queue check failed: {str(e)}")


def generate_backtest_report(**context) -> Dict[str, Any]:
    """
    A simple backtest report generation for demostrating after_backtest_fn parameter.
    
    Args:
        **context: Airflow task context
        
    Returns:
        Dict[str, Any]: Report summary
    """
    try:
        # Get task instances from context
        task_instances = context['dag_run'].get_task_instances()
        
        # Filter for backtest tasks
        backtest_tasks = [ti for ti in task_instances if 'backtest' in ti.task_id and ti.task_id != 'after_backtest']
        
        # Calculate basic metrics
        total_tasks = len(backtest_tasks)
        successful_tasks = len([ti for ti in backtest_tasks if ti.state == 'success'])
        failed_tasks = len([ti for ti in backtest_tasks if ti.state == 'failed'])
        
        # Get execution times
        execution_times = []
        for ti in backtest_tasks:
            if ti.start_date and ti.end_date:
                duration = (ti.end_date - ti.start_date).total_seconds()
                execution_times.append(duration)
        
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Create report
        report = {
            'dag_id': context['dag'].dag_id,
            'run_id': context['dag_run'].run_id,
            'execution_date': context['execution_date'].isoformat(),
            'total_backtests': total_tasks,
            'successful_backtests': successful_tasks,
            'failed_backtests': failed_tasks,
            'success_rate': (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            'avg_execution_time_seconds': round(avg_execution_time, 2),
            'total_execution_time_seconds': round(sum(execution_times), 2)
        }
        
        # Log report
        logger.info(f"Backtest Report: {report}")
        
        # Store report in XCom for downstream tasks
        context['task_instance'].xcom_push(key='backtest_report', value=report)
        
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate backtest report: {str(e)}")
        # Don't fail the DAG for reporting issues
        return {'error': str(e)}


def intelligent_retry_callback(context):
    """Custom retry logic for factor trading failures"""
    exception = context.get('exception')
    print(f"Retry callback triggered. Exception: {exception}")
    
    # Handle ClickHouse connectivity issues
    if exception and ('ClickHouse' in str(exception) or 'Connection refused' in str(exception)):
        print("Database connectivity issue detected - retrying...")
        return True
    
    # Handle Batch spot interruptions  
    if exception and 'SpotFleetRequestTerminated' in str(exception):
        print("Spot interruption detected - retrying...")
        return True
    
    print("Retrying with exponential backoff...")
    return True


# Get configuration from Airflow variables
# TODO: Configure these Airflow Variables with your actual values
results_bucket = Variable.get('trading_strategies_bucket', 'YOUR_S3_RESULTS_BUCKET_NAME')

# Database configuration - in production, you might want to use Airflow connections or secrets
# TODO: Configure these Airflow Variables with your database connection details
db_config = {
    'db_host': Variable.get('db_host', 'YOUR_DATABASE_HOST'),
    'db_port': Variable.get('db_port', '9000'),
    'db_user': Variable.get('db_user', 'YOUR_DATABASE_USER'),
    'db_password': Variable.get('db_password', 'YOUR_DATABASE_PASSWORD'),
    'db_database': Variable.get('db_database', 'YOUR_DATABASE_NAME')
}

# Create backtest configuration
config = BacktestConfig(
    strategy_class='LongShortEquityStrategy',
    start_date='2022-01-01',
    end_date='2024-12-31',
    initial_capital=1000000.0,
    factors=['NewsSentiment'],
    param_grid={
        #'rebalance_period':[7, 14, 21, 28, 35, 42, 49, 56, 63, 70, 77, 84, 91],
        'rebalance_period':[7, 14, 21, 28, 35, 42, 49, 56, 63, 70, 77, 84, 91],
        'take_profit_pct': [0.1, 0.11, 0.12, 0.13,0.14, 0.15, 0.16, 0.17, 0.18],
        'stop_loss_pct': [ 0.05, 0.06, 0.07, 0.08, 0.09, 0.1],
        'cooldown_period': [7, 14, 21, 28, 35]
    },
    s3_bucket=results_bucket,
    db_config=db_config
    # batch_job_queue and batch_job_definition will be handled by the factory
    # using Airflow Variables with sensible defaults
)

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=1),
    'retry_exponential_backoff': True,
}

# Create DAG using the factory
dag = BacktestDAGFactory.create_dag(
    config=config,
    dag_id='framework_backtest_simple_example',
    default_args=default_args,
    tags=['example', 'framework', 'backtest'],
    description='Example DAG using the Airflow Backtest Framework',
    before_backtest_callback=check_batch_queue_status,
    after_backtest_callback=generate_backtest_report,
    retry_callback=intelligent_retry_callback
)