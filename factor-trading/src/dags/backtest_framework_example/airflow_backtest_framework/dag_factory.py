"""
DAG factory module for the Airflow Backtest Framework.
"""

import os
import json
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.batch import BatchOperator
from airflow.models import Variable

from airflow_backtest_framework.config import BacktestConfig, create_batch_config


class BacktestDAGFactory:
    """
    Factory for creating backtest DAGs.
    """
    
    @staticmethod
    def create_dag(
        config: BacktestConfig,
        dag_id: str,
        schedule: Optional[str] = None,
        default_args: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        before_backtest_callback: Optional[Callable] = None,
        after_backtest_callback: Optional[Callable] = None,
        retry_callback: Optional[Callable] = None
    ) -> DAG:
        """
        Create an Airflow DAG for backtest execution.
        
        Args:
            config: Backtest configuration
            dag_id: ID for the DAG
            schedule: Schedule interval for the DAG
            default_args: Default arguments for the DAG
            tags: Tags for the DAG
            description: Description for the DAG
            before_backtest_callback: Function to execute before backtests
            after_backtest_callback: Function to execute after backtests
            retry_callback: Callback function for retry logic
            
        Returns:
            DAG: Airflow DAG for backtest execution
        """
        # Validate configuration
        config.validate()
        
        # Set default arguments if not provided
        if default_args is None:
            default_args = {
                'owner': 'airflow',
                'depends_on_past': False,
                'email_on_failure': False,
                'email_on_retry': False,
                'retries': 3,
                'retry_delay': timedelta(minutes=5),
                'retry_exponential_backoff': True,
            }
            
        # Set default tags if not provided
        if tags is None:
            tags = ['backtest', 'trading']
            
        # Set default description if not provided
        if description is None:
            description = f'Backtest DAG for {config.strategy_class}'
            
        # Create DAG
        dag = DAG(
            dag_id,
            default_args=default_args,
            description=description,
            schedule_interval=schedule,
            start_date=datetime(2023, 1, 1),
            catchup=False,
            tags=tags,
        )
        
        # Generate parameter combinations
        combinations = config.generate_combinations()
        
        with dag:
            # Create before-backtest task if a callback is provided
            if before_backtest_callback:
                before_task = PythonOperator(
                    task_id='before_backtest',
                    python_callable=before_backtest_callback,
                )
                
            # Create backtest tasks
            # TODO: Configure these Airflow Variables with your AWS Batch resources
            batch_job_queue = config.batch_job_queue or Variable.get('batch_job_queue', 'YOUR_BATCH_JOB_QUEUE_NAME')
            batch_job_definition = config.batch_job_definition or Variable.get('batch_job_definition', 'YOUR_BATCH_JOB_DEFINITION_NAME')
            
            # Create batch tasks using expand for parallel execution
            # Generate a base job name with the current timestamp
            import time
            timestamp = int(time.time())
            
            backtest_tasks = BatchOperator.partial(
                task_id='backtest',
                job_name=f'backtest-{dag_id}-{timestamp}',  # Static job name with timestamp
                job_queue=batch_job_queue,
                job_definition=batch_job_definition,
                on_retry_callback=retry_callback if retry_callback else BacktestDAGFactory._default_retry_callback,
            ).expand(
                container_overrides=[create_batch_config(combo) for combo in combinations]
            )
            
            # Create after-backtest task if a callback is provided
            if after_backtest_callback:
                after_task = PythonOperator(
                    task_id='after_backtest',
                    python_callable=after_backtest_callback,
                )
                
            # Set task dependencies
            if before_backtest_callback and after_backtest_callback:
                before_task >> backtest_tasks >> after_task
            elif before_backtest_callback:
                before_task >> backtest_tasks
            elif after_backtest_callback:
                backtest_tasks >> after_task
                
        return dag
    
    @staticmethod
    def _default_retry_callback(context):
        """
        Default retry callback for batch tasks.
        
        Args:
            context: Airflow task context
            
        Returns:
            bool: True to retry, False otherwise
        """
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
        
    @staticmethod
    def create_multi_strategy_dag(
        configs: List[BacktestConfig],
        dag_id: str,
        schedule: Optional[str] = None,
        default_args: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        before_backtest_callback: Optional[Callable] = None,
        after_backtest_callback: Optional[Callable] = None,
        retry_callback: Optional[Callable] = None
    ) -> DAG:
        """
        Create an Airflow DAG for multiple strategy backtests.
        
        Args:
            configs: List of backtest configurations
            dag_id: ID for the DAG
            schedule: Schedule interval for the DAG
            default_args: Default arguments for the DAG
            tags: Tags for the DAG
            description: Description for the DAG
            before_backtest_callback: Function to execute before backtests
            after_backtest_callback: Function to execute after backtests
            retry_callback: Callback function for retry logic
            
        Returns:
            DAG: Airflow DAG for backtest execution
        """
        # Set default arguments if not provided
        if default_args is None:
            default_args = {
                'owner': 'airflow',
                'depends_on_past': False,
                'email_on_failure': False,
                'email_on_retry': False,
                'retries': 3,
                'retry_delay': timedelta(minutes=5),
                'retry_exponential_backoff': True,
            }
            
        # Set default tags if not provided
        if tags is None:
            tags = ['backtest', 'trading', 'multi-strategy']
            
        # Set default description if not provided
        if description is None:
            description = 'Multi-strategy backtest DAG'
            
        # Create DAG
        dag = DAG(
            dag_id,
            default_args=default_args,
            description=description,
            schedule_interval=schedule,
            start_date=datetime(2023, 1, 1),
            catchup=False,
            tags=tags,
        )
        
        with dag:
            # Create before-backtest task if a callback is provided
            if before_backtest_callback:
                before_task = PythonOperator(
                    task_id='before_backtest',
                    python_callable=before_backtest_callback,
                )
                
            # Create backtest tasks for each configuration
            backtest_tasks = []
            for i, config in enumerate(configs):
                # Validate configuration
                config.validate()
                
                # Generate parameter combinations
                combinations = config.generate_combinations()
                
                # Get batch job details
                # TODO: Configure these Airflow Variables with your AWS Batch resources
                batch_job_queue = config.batch_job_queue or Variable.get('batch_job_queue', 'YOUR_BATCH_JOB_QUEUE_NAME')
                batch_job_definition = config.batch_job_definition or Variable.get('batch_job_definition', 'YOUR_BATCH_JOB_DEFINITION_NAME')
                
                # Create batch tasks using expand for parallel execution
                # Generate a unique job name with timestamp
                import time
                timestamp = int(time.time())
                
                strategy_tasks = BatchOperator.partial(
                    task_id=f'backtest_strategy_{i}',
                    job_name=f'backtest-strategy-{i}-{timestamp}',  # Static job name with timestamp
                    job_queue=batch_job_queue,
                    job_definition=batch_job_definition,
                    on_retry_callback=retry_callback if retry_callback else BacktestDAGFactory._default_retry_callback,
                ).expand(
                    container_overrides=[create_batch_config(combo) for combo in combinations]
                )
                
                backtest_tasks.append(strategy_tasks)
                
            # Create after-backtest task if a callback is provided
            if after_backtest_callback:
                after_task = PythonOperator(
                    task_id='after_backtest',
                    python_callable=after_backtest_callback,
                )
                
            # Set task dependencies
            if before_backtest_callback:
                for task in backtest_tasks:
                    before_task >> task
                    
            if after_backtest_callback:
                for task in backtest_tasks:
                    task >> after_task
                    
        return dag