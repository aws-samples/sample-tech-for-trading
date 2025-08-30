# Airflow Backtest Framework

The module for orchestrating trading strategy backtests using Apache Airflow and AWS Batch.

## Overview

The Airflow Backtest Framework provides a standardized way to define, configure, execute, and analyze backtests at scale, leveraging the existing trading strategies model and backtest engine. The framework abstracts away the complexities of Airflow DAG creation, allowing users to focus on strategy development and analysis.

This framework is designed to work with your existing AWS Batch infrastructure and focuses solely on the Airflow/MWAA component of the backtest orchestration.

## Framework Structure

```
airflow_backtest_framework/
├── __init__.py          # Package initialization
├── config.py            # Configuration management
└── dag_factory.py       # DAG creation utilities
```

## Key Components

### 1. BacktestConfig (config.py)

The `BacktestConfig` class is the core of the framework, responsible for:

- Defining backtest parameters (strategy, date range, factors, etc.)
- Validating configuration values
- Generating parameter combinations for grid search
- Converting configurations to formats suitable for AWS Batch

```python
config = BacktestConfig(
    strategy_class='LongShortEquityStrategy',
    start_date='2022-01-01',
    end_date='2022-12-31',
    initial_capital=1000000.0,
    factors=['DebtToEquity'],
    param_grid={
        'take_profit_pct': [5.0, 10.0, 15.0],
        'stop_loss_pct': [3.0, 5.0, 8.0],
    }
)
```

### Parameter Configuration Examples

Let's look at practical examples of how to configure your backtests for different scenarios:

#### Single Backtest Configuration
When you want to run a single backtest with specific parameters, simply provide direct parameter values without a `param_grid`:

```python
config = BacktestConfig(
    strategy_class='LongShortEquityStrategy',
    start_date='2022-01-01',
    end_date='2022-12-31',
    initial_capital=1000000.0,
    factors=['DebtToEquity'],
    take_profit_pct=10.0,
    stop_loss_pct=5.0,
    rebalance_period=1
)
# Result: 1 backtest with the specified parameter values
```

#### Parameter Optimization (Grid Search)
When you want to find the optimal parameter values, use `param_grid` to specify multiple values to test:

```python
config = BacktestConfig(
    strategy_class='LongShortEquityStrategy',
    start_date='2022-01-01',
    end_date='2022-12-31',
    initial_capital=1000000.0,
    factors=['DebtToEquity'],
    # These direct parameters are overridden by param_grid
    take_profit_pct=10.0,        # IGNORED
    stop_loss_pct=5.0,           # IGNORED
    rebalance_period=1,          # USED (not in param_grid)
    
    param_grid={
        'take_profit_pct': [5.0, 10.0, 15.0],    # Tests 3 values
        'stop_loss_pct': [3.0, 5.0, 8.0],        # Tests 3 values
        # rebalance_period uses direct value (1) for all combinations
    }
)
# Result: 9 backtests (3 × 3) with all combinations, each using rebalance_period=1
```

#### Mixed Parameter Strategy
You can combine fixed baseline parameters with selective optimization:

```python
config = BacktestConfig(
    strategy_class='LongShortEquityStrategy',
    start_date='2022-01-01',
    end_date='2022-12-31',
    initial_capital=1000000.0,
    factors=['DebtToEquity'],
    # Baseline parameters
    take_profit_pct=10.0,        # Will be overridden
    stop_loss_pct=5.0,           # Will be used as-is
    rebalance_period=1,          # Will be overridden
    cooldown_period=5,           # Will be used as-is
    
    # Only optimize specific parameters
    param_grid={
        'take_profit_pct': [5.0, 10.0, 15.0],
        'rebalance_period': [1, 7, 30],  # Daily, weekly, monthly
    }
)
# Result: 9 backtests (3 × 3), all using stop_loss_pct=5.0 and cooldown_period=5
```

### Configuration Best Practices

**For Parameter Optimization**: When running parameter sweeps, consider setting your most likely optimal values as direct parameters, then use `param_grid` to test variations around those values. This makes your configuration self-documenting.

**For Production Backtests**: Use direct parameters only when you have established optimal parameter values and want to run production backtests with consistent settings.

**For Experimentation**: Use `param_grid` extensively to explore the parameter space, but be mindful that the number of combinations grows exponentially (3 parameters with 3 values each = 27 backtests).

### 2. BacktestDAGFactory (dag_factory.py)

The `BacktestDAGFactory` class provides utilities for creating Airflow DAGs:

- Creating DAGs from backtest configurations
- Supporting single-strategy and multi-strategy backtests
- Handling task dependencies and parallel execution
- Managing error handling and retries
- Supporting custom callback functions for pre/post backtest logic

```python
dag = BacktestDAGFactory.create_dag(
    config=config,
    dag_id='my_backtest_dag',
    tags=['backtest', 'trading'],
    description='My backtest DAG',
    before_backtest_callback=my_setup_function,
    after_backtest_callback=my_analysis_function
)
```

#### Callback Functions

The framework supports optional callback functions that allow you to customize the DAG behavior:

**`before_backtest_callback`**: A function executed before backtests start
- **Purpose**: Setup tasks, validation, infrastructure checks
- **Signature**: `def my_callback(**context) -> Any`
- **Context**: Receives full Airflow task context
- **Common use cases**: 
  - Check AWS Batch queue status
  - Validate data availability
  - Setup temporary resources
  - Send start notifications

**`after_backtest_callback`**: A function executed after all backtests complete
- **Purpose**: Analysis, reporting, cleanup tasks
- **Signature**: `def my_callback(**context) -> Any`
- **Context**: Receives full Airflow task context
- **Common use cases**:
  - Generate performance reports
  - Analyze results and find best parameters
  - Send completion notifications
  - Cleanup temporary resources
  - Store results to external systems

**Example callback implementations:**

```python
import boto3
import logging
from airflow.exceptions import AirflowException

def check_batch_queue_status(**context):
    """Check if AWS Batch queue is available before starting backtests."""
    queue_name = Variable.get('batch_job_queue', 'trading-strategies-job-queue')
    batch_client = boto3.client('batch')
    
    response = batch_client.describe_job_queues(jobQueues=[queue_name])
    if not response['jobQueues'] or response['jobQueues'][0]['state'] != 'ENABLED':
        raise AirflowException(f"Batch queue '{queue_name}' is not available")
    
    logging.info(f"Batch queue '{queue_name}' is ready")

def generate_backtest_report(**context):
    """Generate a report of backtest execution results."""
    # Get task instances from the DAG run
    task_instances = context['dag_run'].get_task_instances()
    backtest_tasks = [ti for ti in task_instances if 'backtest' in ti.task_id]
    
    # Calculate metrics
    total_tasks = len(backtest_tasks)
    successful_tasks = len([ti for ti in backtest_tasks if ti.state == 'success'])
    
    report = {
        'total_backtests': total_tasks,
        'successful_backtests': successful_tasks,
        'success_rate': (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0
    }
    
    # Store in XCom for downstream use
    context['task_instance'].xcom_push(key='backtest_report', value=report)
    logging.info(f"Backtest Report: {report}")
    
    return report
```

These callbacks are completely optional and user-defined. The framework provides the structure, but you implement the specific logic that fits your needs.

## Integration with AWS Batch

The framework integrates with AWS Batch through the following mechanisms:

1. **Parameter Passing**: Converts configuration parameters to environment variables that the batch job can read.

2. **Job Execution**: Uses Airflow's BatchOperator to submit jobs to AWS Batch.

3. **Parallel Execution**: Leverages Airflow's task expansion to run multiple parameter combinations in parallel.

4. **Error Handling**: Provides custom retry logic for common failure scenarios.

## Setting Up in MWAA

To use this framework with Amazon MWAA:

1. **Upload the Framework Code**:
   ```bash
   aws s3 cp airflow_backtest_framework s3://your-mwaa-bucket/dags/airflow_backtest_framework --recursive
   ```

2. **Upload the Example DAGs**:
   ```bash
   aws s3 cp framework_backtest_simple_example_dag.py s3://your-mwaa-bucket/dags/
   aws s3 cp framework_backtest_multi_example_dag.py s3://your-mwaa-bucket/dags/
   ```

3. **Configure Airflow Variables**:
   - `batch_job_queue`: Your AWS Batch job queue
   - `batch_job_definition`: Your AWS Batch job definition
   - `trading_strategies_bucket`: Your S3 bucket for storing results
   - Database configuration variables (if needed)

## Configuration Guide

### Understanding BacktestConfig Parameters

The `BacktestConfig` class accepts various parameters that control how your backtests are executed. These parameters fall into several categories:

#### Required Parameters
Every backtest configuration must specify:
- `strategy_class`: The name of the trading strategy class to use
- `start_date` and `end_date`: The date range for the backtest (in 'YYYY-MM-DD' format)

#### Core Backtest Parameters
These parameters define the fundamental aspects of your backtest:
- `initial_capital`: Starting capital for the backtest (defaults to 1,000,000)
- `factors`: List of factor names to use in the strategy (e.g., ['DebtToEquity', 'PriceToEarnings'])
- `universe`: List of securities to include in the backtest (optional)

#### Strategy Parameters
These parameters control the behavior of your trading strategy:
- `rebalance_period`: Number of days between portfolio rebalances
- `take_profit_pct`: Percentage gain at which to take profits
- `stop_loss_pct`: Percentage loss at which to stop losses
- `cooldown_period`: Number of days to wait after a stop-loss or take-profit event

#### Infrastructure Parameters
These parameters specify the AWS resources to use:
- `batch_job_queue`: AWS Batch job queue name (can also be set via Airflow variables)
- `batch_job_definition`: AWS Batch job definition name (can also be set via Airflow variables)
- `s3_bucket`: S3 bucket for storing backtest results
- `db_config`: Database configuration dictionary for data access

#### Parameter Grid for Optimization
The `param_grid` parameter is special - it allows you to specify multiple values for any parameter to run parameter sweeps. When you include a parameter in `param_grid`, it will override any direct parameter value you've set.

### How Parameter Override Works

The framework uses a simple but powerful override system. When you specify both direct parameters and a `param_grid`, the system follows these rules:

1. **Direct parameters only**: If you don't provide a `param_grid`, all direct parameters are used exactly as specified for a single backtest.

2. **Parameter grid override**: Any parameter that appears in `param_grid` will completely override the corresponding direct parameter. The framework generates all possible combinations of the `param_grid` values.

3. **Mixed usage**: Parameters not included in `param_grid` will use their direct parameter values across all generated combinations.

This design allows you to set "baseline" values as direct parameters and then selectively optimize specific parameters using `param_grid`, making your configuration both readable and flexible.

## Troubleshooting

### Common Issues

1. **Module Not Found Error**:
   - Make sure the framework code is in the correct location
   - Check that imports use the correct path

2. **AWS Batch Job Failures**:
   - Check the CloudWatch logs for the batch job
   - Verify that environment variables are being passed correctly

3. **Database Connection Issues**:
   - Verify database credentials in Airflow variables
   - Check network connectivity between AWS Batch and the database

## Next Steps

1. **Custom Result Analysis**: Implement custom result analysis functions to compare backtest results.

2. **Additional Strategy Parameters**: Extend the framework to support more strategy parameters.

3. **Visualization**: Add visualization capabilities for backtest results.

4. **Notification**: Implement notification mechanisms for completed backtests.