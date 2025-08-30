# Configuration Guide

This guide explains how to configure the Airflow Backtest Framework for your environment.

## Required Airflow Variables

Before using the framework, you need to set up the following Airflow Variables with your actual values:

### AWS Batch Configuration
```bash
# Set these in Airflow UI under Admin > Variables
batch_job_queue = "your-batch-job-queue-name"
batch_job_definition = "your-batch-job-definition-name"
```

### S3 Configuration
```bash
trading_strategies_bucket = "your-s3-results-bucket-name"
```

### Database Configuration
```bash
db_host = "your-database-host"
db_port = "9000"  # or your database port
db_user = "your-database-username"
db_password = "your-database-password"
db_database = "your-database-name"
```

## Setting Airflow Variables

### Via Airflow UI
1. Go to Admin > Variables in the Airflow web interface
2. Click "+" to add a new variable
3. Enter the key and value for each required variable

### Via CLI
```bash
airflow variables set batch_job_queue "your-batch-job-queue-name"
airflow variables set batch_job_definition "your-batch-job-definition-name"
airflow variables set trading_strategies_bucket "your-s3-results-bucket-name"
airflow variables set db_host "your-database-host"
airflow variables set db_port "9000"
airflow variables set db_user "your-database-username"
airflow variables set db_password "your-database-password"
airflow variables set db_database "your-database-name"
```

### Via Environment Variables
You can also set these as environment variables with the `AIRFLOW_VAR_` prefix:
```bash
export AIRFLOW_VAR_BATCH_JOB_QUEUE="your-batch-job-queue-name"
export AIRFLOW_VAR_BATCH_JOB_DEFINITION="your-batch-job-definition-name"
export AIRFLOW_VAR_TRADING_STRATEGIES_BUCKET="your-s3-results-bucket-name"
export AIRFLOW_VAR_DB_HOST="your-database-host"
export AIRFLOW_VAR_DB_PORT="9000"
export AIRFLOW_VAR_DB_USER="your-database-username"
export AIRFLOW_VAR_DB_PASSWORD="your-database-password"
export AIRFLOW_VAR_DB_DATABASE="your-database-name"
```

## AWS Batch Setup

The framework assumes you have:
1. An AWS Batch compute environment
2. A job queue
3. A job definition for your backtest container

Your job definition should:
- Use a container image with your backtest code
- Accept environment variables for configuration
- Write results to the specified S3 bucket

## Database Setup

The framework supports any database that your backtest code can connect to. The example uses ClickHouse, but you can adapt it for:
- PostgreSQL
- MySQL
- ClickHouse
- Any other database

## Security Best Practices

For production deployments:
1. Use Airflow Connections instead of Variables for sensitive data
2. Use AWS Secrets Manager or similar for database credentials
3. Enable encryption for S3 buckets
4. Use IAM roles with minimal required permissions

## Example Values

Here are example values to help you understand the format:

```bash
# AWS Batch
batch_job_queue = "trading-strategies-job-queue"
batch_job_definition = "backtest-job-definition"

# S3
trading_strategies_bucket = "my-company-backtest-results"

# Database (ClickHouse example)
db_host = "clickhouse.example.com"
db_port = "9000"
db_user = "backtest_user"
db_password = "secure_password_123"
db_database = "trading_data"
```

## Troubleshooting

### Common Issues

1. **"Variable does not exist" errors**: Make sure all required variables are set
2. **AWS permissions errors**: Ensure your Airflow execution role has permissions for Batch and S3
3. **Database connection errors**: Verify network connectivity and credentials
4. **Container failures**: Check your job definition and container logs in AWS Batch

### Validation

You can test your configuration by running the example DAGs:
- `framework_backtest_simple_example`
- `framework_backtest_multi_example`

Both DAGs include validation steps that will help identify configuration issues.