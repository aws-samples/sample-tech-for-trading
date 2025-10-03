# Factor Trading Frontend

A unified Streamlit application combining backtest management and results visualization for factor trading strategies.

## Overview

This application provides a complete workflow for factor trading strategy development and analysis:

1. **🚀 Backtest Management** - Create, deploy, and monitor trading strategy backtests using AWS MWAA
2. **📈 Results Visualization** - Analyze and compare backtest results from ClickHouse database

## Features

### 🚀 Backtest Management Page
- **Configuration Management**: Create backtest configurations with multiple strategy types
- **Parameter Grid Support**: Test multiple parameter combinations efficiently  
- **AWS MWAA Integration**: Deploy and trigger DAGs seamlessly
- **Real-time Monitoring**: Track backtest progress and completion
- **Progress Indicators**: Visual feedback during deployment and execution

### 📈 Results Visualization Page
- **Performance Analysis**: Compare backtests with interactive charts
- **Detailed Metrics**: View comprehensive performance statistics
- **Trade Analysis**: Examine individual trades and orders
- **Factor Effectiveness**: Analyze factor performance across strategies
- **Best Performers**: Identify top-performing configurations

## Architecture

```
src/frontend/
├── app.py                                    # Main entry point with navigation
├── pages/
│   ├── 1_Backtest_Management.py              # Backtest creation and management
│   └── 2_Results_Visualization.py            # Results analysis and visualization
├── aws_utils.py                              # AWS service utilities (MWAA, S3, Batch)
├── dag_generator.py                          # DAG generation engine
├── error_handler.py                          # Error handling and validation
├── database.py                               # ClickHouse database connection
├── requirements.txt                          # Combined dependencies
├── start_streamlit.sh                        # Startup script
└── README.md                                 # This file
```

## Quick Start

### 1. Environment Setup

Copy the environment configuration:
```bash
cp .env.example .env
```

Configure your settings in `.env`:
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=your-profile-name
MWAA_ENVIRONMENT_NAME=your-mwaa-environment
S3_DAGS_BUCKET=your-dags-bucket
AIRFLOW_WEBSERVER_URL=https://your-mwaa-webserver-url

# ClickHouse Configuration (for visualization)
CLICKHOUSE_HOST=your-clickhouse-host
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=your-username
CLICKHOUSE_PASSWORD=your-password
CLICKHOUSE_DATABASE=your-database
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start Application

```bash
./start_streamlit.sh
```

Or directly:
```bash
streamlit run app.py --server.port 8502
```

## Usage Workflow

### Step 1: Create Backtests (🚀 Backtest Management)
1. **Configure Strategy**: Select strategy type and parameters
2. **Set Parameter Grid**: Define parameter combinations to test
3. **Deploy to MWAA**: Upload DAG to AWS MWAA environment
4. **Trigger Execution**: Start backtest runs
5. **Monitor Progress**: Track completion in real-time

### Step 2: Analyze Results (📈 Results Visualization)
1. **View Overview**: See summary statistics across all backtests
2. **Compare Performance**: Use interactive charts to compare strategies
3. **Examine Details**: Drill down into specific backtest results
4. **Analyze Trades**: Review individual trade performance
5. **Identify Best Performers**: Find optimal parameter combinations

## Configuration

### AWS Services Required
- **AWS MWAA**: Managed Airflow for DAG execution
- **AWS S3**: DAG storage and results
- **AWS Batch**: Backtest job execution

### Database Requirements
- **ClickHouse**: For storing and querying backtest results

### Airflow Variables Required
Set these in your MWAA environment:
- `batch_job_queue`: AWS Batch job queue name
- `batch_job_definition`: AWS Batch job definition name
- `db_host`: ClickHouse database host
- `db_port`: ClickHouse database port
- `db_user`: ClickHouse username
- `db_password`: ClickHouse password
- `db_database`: ClickHouse database name
- `trading_strategies_bucket`: S3 bucket for results

## Navigation

The application uses Streamlit's multi-page functionality:
- **Main Page**: Overview and navigation
- **Backtest Management**: Create and manage backtests
- **Results Visualization**: Analyze backtest results

Pages are automatically discovered from the `pages/` directory and appear in the sidebar.

## Troubleshooting

### Connection Issues
- Use the "Test AWS Connections" button in the Backtest Management page
- Verify your AWS credentials and permissions
- Check MWAA environment status

### Database Issues
- Verify ClickHouse connection settings
- Ensure database contains backtest results
- Check network connectivity to database

### DAG Issues
- Check Airflow UI for DAG import errors
- Verify S3 bucket permissions
- Ensure Airflow Variables are set correctly

## Development

### Adding New Features
- **Backtest Management**: Modify `pages/1_Backtest_Management.py`
- **Visualization**: Modify `pages/2_Results_Visualization.py`
- **Shared Utilities**: Add to respective utility files

### Testing
```bash
# Test syntax
python -m py_compile app.py
python -m py_compile pages/*.py

# Test individual components
python -c "from aws_utils import AWSUtils; print('AWS utils OK')"
python -c "from database import ClickHouseConnection; print('Database OK')"
```

## Security

- AWS credentials managed through profiles or IAM roles
- Environment variables for sensitive configuration
- No hardcoded credentials in source code
- Secure database connections

## Performance

- Lazy loading of AWS clients
- Efficient database queries with pagination
- Streamlit caching for expensive operations
- Minimal data transfer between components