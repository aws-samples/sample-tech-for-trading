"""
DAG Generator for Backtest Frontend
Generates DAG files using the existing airflow_backtest_framework.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class DAGGenerator:
    """Generate DAG files using existing backtest framework patterns."""
    
    def __init__(self):
        # Add the project root to Python path to import framework
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
    
    def generate_dag(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a DAG file based on configuration."""
        try:
            # Generate DAG ID
            strategy_name = config['strategy_class'].lower().replace('strategy', '')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            dag_id = f"backtest_{strategy_name}_{timestamp}"
            
            # Generate DAG content
            dag_content = self._generate_dag_content(dag_id, config)
            
            # Validate Python syntax
            try:
                compile(dag_content, f"{dag_id}.py", 'exec')
            except SyntaxError as e:
                return {
                    'success': False,
                    'error': f"Generated DAG has syntax error: {e}",
                    'error_type': 'syntax_error'
                }
            
            return {
                'success': True,
                'dag_id': dag_id,
                'dag_content': dag_content,
                'filename': f"{dag_id}.py"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate DAG: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'generation_error'
            }
    
    def _generate_dag_content(self, dag_id: str, config: Dict[str, Any]) -> str:
        """Generate the actual DAG Python code."""
        
        # Parse parameter grid
        param_combinations = self._parse_parameter_grid(config['param_grid'])
        
        # Generate DAG content based on framework patterns
        dag_content = f'''"""
Generated Backtest DAG: {dag_id}
Strategy: {config['strategy_class']}
Generated at: {datetime.now().isoformat()}
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.batch import BatchOperator
import sys
import os

# Add project root to path
project_root = '/opt/airflow/dags/repo'
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# DAG configuration
default_args = {{
    'owner': 'backtest-frontend',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}}

# Create DAG
dag = DAG(
    '{dag_id}',
    default_args=default_args,
    description='Generated backtest DAG for {config["strategy_class"]}',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=['backtest', 'generated', '{config["strategy_class"].lower()}'],
)

# Get configuration from Airflow Variables (like the working example)
from airflow.models import Variable

BATCH_JOB_QUEUE = Variable.get("batch_job_queue")
BATCH_JOB_DEFINITION = Variable.get("batch_job_definition")

# Configuration from frontend
BACKTEST_CONFIG = {config}

# Parameter combinations
PARAM_COMBINATIONS = {param_combinations}

def create_backtest_tasks():
    """Create backtest tasks for each parameter combination."""
    tasks = []
    
    for i, params in enumerate(PARAM_COMBINATIONS):
        task_id = f"backtest_job_{{i+1:04d}}"
        
        # Create environment variables for the batch job (like the working DAG)
        env_vars = []
        env_vars.append({{'name': 'STRATEGY_CLASS', 'value': BACKTEST_CONFIG['strategy_class']}})
        env_vars.append({{'name': 'START_DATE', 'value': BACKTEST_CONFIG['start_date']}})
        env_vars.append({{'name': 'END_DATE', 'value': BACKTEST_CONFIG['end_date']}})
        env_vars.append({{'name': 'INITIAL_CAPITAL', 'value': str(BACKTEST_CONFIG['initial_capital'])}})
        env_vars.append({{'name': 'FACTORS', 'value': ','.join(BACKTEST_CONFIG['factors'])}})
        
        # Add universe if provided
        if BACKTEST_CONFIG.get('universe'):
            env_vars.append({{'name': 'UNIVERSE', 'value': ','.join(BACKTEST_CONFIG['universe'])}})
        
        # Add database configuration from Airflow Variables (like the working DAG)
        env_vars.append({{'name': 'DB_HOST', 'value': Variable.get('db_host', 'YOUR_DATABASE_HOST')}})
        env_vars.append({{'name': 'DB_PORT', 'value': Variable.get('db_port', '9000')}})
        env_vars.append({{'name': 'DB_USER', 'value': Variable.get('db_user', 'YOUR_DATABASE_USER')}})
        env_vars.append({{'name': 'DB_PASSWORD', 'value': Variable.get('db_password', 'YOUR_DATABASE_PASSWORD')}})
        env_vars.append({{'name': 'DB_DATABASE', 'value': Variable.get('db_database', 'YOUR_DATABASE_NAME')}})
        
        # Add S3 results bucket from Airflow Variables (like the working DAG)
        env_vars.append({{'name': 'RESULTS_BUCKET', 'value': Variable.get('trading_strategies_bucket', 'YOUR_S3_RESULTS_BUCKET_NAME')}})
        
        # Add parameter combination values as environment variables
        for k, v in params.items():
            if k == 'take_profit_pct':
                env_vars.append({{'name': 'TAKE_PROFIT', 'value': str(v)}})
            elif k == 'stop_loss_pct':
                env_vars.append({{'name': 'STOP_LOSS', 'value': str(v)}})
            else:
                env_vars.append({{'name': k.upper(), 'value': str(v)}})
        
        # Create Batch job for each parameter combination (using container_overrides like working DAG)
        batch_task = BatchOperator(
            task_id=task_id,
            job_name=f"{dag_id}_job_{{i+1}}",
            job_queue=BATCH_JOB_QUEUE,
            job_definition=BATCH_JOB_DEFINITION,
            container_overrides={{
                'environment': env_vars
            }},
            dag=dag,
        )
        
        tasks.append(batch_task)
    
    return tasks

# Create all backtest tasks
backtest_tasks = create_backtest_tasks()

# Set up task dependencies (can run in parallel)
# No dependencies needed - all tasks can run independently

# Summary task to collect results (optional)
def summarize_results(**context):
    """Summarize backtest results."""
    return "Backtest completed successfully"

summary_task = PythonOperator(
    task_id='summarize_results',
    python_callable=summarize_results,
    dag=dag,
)

# Set dependencies: all backtest tasks must complete before summary
for task in backtest_tasks:
    task >> summary_task
'''
        
        return dag_content
    
    def _parse_parameter_grid(self, param_grid: Dict[str, str]) -> List[Dict[str, Any]]:
        """Parse parameter grid into combinations."""
        import itertools
        
        parsed_params = {}
        
        for param_name, param_value in param_grid.items():
            if not param_value or not param_value.strip():
                continue
                
            param_str = param_value.strip()
            
            # Handle different input formats
            if ':' in param_str and param_str.count(':') == 2:
                # Range format: min:max:steps
                try:
                    parts = param_str.split(':')
                    min_val = float(parts[0])
                    max_val = float(parts[1])
                    steps = int(parts[2])
                    
                    if steps <= 1:
                        values = [min_val]
                    else:
                        step_size = (max_val - min_val) / (steps - 1)
                        values = [min_val + i * step_size for i in range(steps)]
                    
                    parsed_params[param_name] = values
                except (ValueError, IndexError):
                    # Fallback to treating as single value
                    parsed_params[param_name] = [param_str]
            
            elif ',' in param_str:
                # Comma-separated values
                values = []
                for val in param_str.split(','):
                    val = val.strip()
                    try:
                        # Try to convert to number
                        if '.' in val:
                            values.append(float(val))
                        else:
                            values.append(int(val))
                    except ValueError:
                        # Keep as string
                        values.append(val)
                
                parsed_params[param_name] = values
            
            else:
                # Single value
                try:
                    # Try to convert to number
                    if '.' in param_str:
                        parsed_params[param_name] = [float(param_str)]
                    else:
                        parsed_params[param_name] = [int(param_str)]
                except ValueError:
                    # Keep as string
                    parsed_params[param_name] = [param_str]
        
        # Generate all combinations
        if not parsed_params:
            return [{}]
        
        param_names = list(parsed_params.keys())
        param_values = list(parsed_params.values())
        
        combinations = []
        for combo in itertools.product(*param_values):
            combination = dict(zip(param_names, combo))
            combinations.append(combination)
        
        return combinations
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration before DAG generation."""
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ['name', 'strategy_class', 'start_date', 'end_date', 'initial_capital', 'factors']
        for field in required_fields:
            value = config.get(field)
            # Check for None, empty string, or whitespace-only string
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append({
                    'field': field,
                    'message': f"{field} is required",
                    'suggestions': [f"Please provide a value for {field}"]
                })
        
        # Date validation
        if config.get('start_date') and config.get('end_date'):
            try:
                start_date = datetime.strptime(config['start_date'], '%Y-%m-%d')
                end_date = datetime.strptime(config['end_date'], '%Y-%m-%d')
                
                if start_date >= end_date:
                    errors.append({
                        'field': 'date_range',
                        'message': "Start date must be before end date",
                        'suggestions': ["Check your date range"]
                    })
                
                # Check if date range is too large
                days_diff = (end_date - start_date).days
                if days_diff > 365 * 3:  # More than 3 years
                    warnings.append({
                        'field': 'date_range',
                        'message': f"Large date range ({days_diff} days) may result in long execution times"
                    })
                    
            except ValueError as e:
                errors.append({
                    'field': 'date_format',
                    'message': f"Invalid date format: {e}",
                    'suggestions': ["Use YYYY-MM-DD format"]
                })
        
        # Capital validation
        if config.get('initial_capital'):
            try:
                capital = float(config['initial_capital'])
                if capital <= 0:
                    errors.append({
                        'field': 'initial_capital',
                        'message': "Initial capital must be positive",
                        'suggestions': ["Enter a positive number"]
                    })
                elif capital < 10000:
                    warnings.append({
                        'field': 'initial_capital',
                        'message': "Small initial capital may not be realistic for backtesting"
                    })
            except (ValueError, TypeError):
                errors.append({
                    'field': 'initial_capital',
                    'message': "Initial capital must be a valid number",
                    'suggestions': ["Enter a numeric value"]
                })
        
        # Parameter grid validation and job count calculation
        total_combinations = 1
        if config.get('param_grid'):
            try:
                combinations = self._parse_parameter_grid(config['param_grid'])
                total_combinations = len(combinations)
                
                if total_combinations > 10000:
                    errors.append({
                        'field': 'param_grid',
                        'message': f"Too many parameter combinations ({total_combinations:,}). Maximum allowed is 10,000.",
                        'suggestions': ["Reduce the number of parameter values", "Use smaller ranges"]
                    })
                elif total_combinations > 1000:
                    warnings.append({
                        'field': 'param_grid',
                        'message': f"Large number of combinations ({total_combinations:,}) will be expensive to run"
                    })
                    
            except Exception as e:
                errors.append({
                    'field': 'param_grid',
                    'message': f"Error parsing parameter grid: {e}",
                    'suggestions': ["Check parameter format", "Use format: single_value, val1,val2,val3, or min:max:steps"]
                })
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'total_combinations': total_combinations
        }