# Backtest Frontend

A Streamlit application for backtest management with AWS MWAA integration.

## Overview

This application provides an interface for creating, deploying, triggering, and monitoring backtest DAGs in AWS MWAA. It focuses on simplicity and user experience while maintaining full integration with the existing airflow_backtest_framework.

## Features

### ✅ Core Features

1. **Single-Page Workflow**
   - Streamlined interface with sequential workflow sections
   - Visual progress indicators showing completion status
   - Expandable sections that enable automatically as you progress
   - Clear visual flow from Create → Deploy → Trigger → Monitor

2. **Configuration Management**
   - Form with dynamic parameter fields
   - Real-time validation with error messages
   - Support for multiple strategy types
   - Flexible parameter grid input (single values, lists, ranges)

3. **DAG Deployment**
   - Integration with AWS MWAA environment
   - S3 deployment with progress indication
   - Unpause the DAG before triggering (By default after deployment the DAG is paused)
   - Deployment verification and status tracking

4. **Execution & Monitoring**
   - One-click DAG triggering
   - Real-time status monitoring
   - Progress tracking and completion summaries

5. **Connection Testing**
   - AWS service connection validation
   - Real-time connection status monitoring
   - Configuration verification

## Architecture

### Frontend Application Structure

```
src/backtest_frontend/
├── app.py                 # Main Streamlit application (single-page workflow)
├── dag_generator.py       # DAG generation engine with Airflow Variables integration
├── aws_utils.py          # AWS service utilities (MWAA, S3, Batch operations)
├── error_handler.py      # Configuration validation and error handling
├── requirements.txt       # Python dependencies
├── .env.example          # Environment configuration template
├── start_streamlit.sh    # Application startup script
└── README.md            # Documentation
```

### Framework Integration

```
src/dags/backtest_framework_example/
├── framework_backtest_simple_example_dag.py    # Working example DAG
└── airflow_backtest_framework/
    ├── config.py         # Backtest configuration classes
    └── dag_factory.py    # DAG factory for framework integration
```

### Component Responsibilities

#### **Frontend Layer**
- **`app.py`**: Main Streamlit interface with single-page workflow
- **`dag_generator.py`**: Generates Airflow DAGs compatible with existing framework
- **`aws_utils.py`**: Handles AWS service interactions (MWAA API, S3 uploads, Batch monitoring)
- **`error_handler.py`**: Validates configurations and provides user-friendly error messages

#### **Integration Layer**
- **`airflow_backtest_framework/`**: Existing framework components for DAG creation
- **`framework_backtest_simple_example_dag.py`**: Reference implementation showing working patterns

### Data Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit     │    │   DAG Generator  │    │   AWS MWAA      │
│   Frontend      │───▶│   (dag_generator │───▶│   Environment   │
│   (app.py)      │    │    .py)          │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         │                        │                       ▼
         │                        │              ┌─────────────────┐
         │                        │              │   Backtest      │
         │                        │              │   Execution     │
         │                        │              │                 │
         │                        │              └─────────────────┘
         │                        │                       │
         ▼                        ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AWS Utils     │    │   S3 DAG         │    │   Results       │
│   (aws_utils.py)│    │   Storage        │    │   Storage       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Key Integration Points

1. **Airflow Variables Integration**: DAG generator reads configuration from Airflow Variables (`batch_job_queue`, `batch_job_definition`, `db_host`, etc.)

2. **Environment Variable Passing**: Generated DAGs use `container_overrides` with environment variables for proper parameter passing

3. **Framework Compatibility**: Generated DAGs follow the same patterns as the working example DAG

4. **AWS Service Integration**: Seamless integration with MWAA, S3, and Batch services through `aws_utils.py`

## QuickStart

### 1. AWS Profile Setup

First, configure your AWS profile with the necessary credentials:

```bash
# Configure a new AWS profile
aws configure --profile your-profile-name

# Or use the default profile
aws configure
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=your-profile-name  # Optional: omit to use default profile
MWAA_ENVIRONMENT_NAME=TradingStrategiesMwaaEnvironment
S3_DAGS_BUCKET=your-mwaa-dags-bucket

# Airflow Configuration (MWAA)
AIRFLOW_WEBSERVER_URL=https://your-mwaa-webserver-url
```

**Note**: Make sure your profile has the necessary permissions for MWAA, S3, and Batch services.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Application

```bash
./start_streamlit.sh
# Or directly:
streamlit run app.py --server.port 8502
```

## Parameter Grid Input Format

The application supports flexible parameter input:

- **Single value**: `7`
- **Multiple values**: `7,14,21,28`
- **Range notation**: `7:91:5` (min:max:steps)

### Available Parameters by Strategy

#### **LongShortEquityStrategy**
- `rebalance_period`: `7,14,21,28,35` (days between rebalancing)
- `take_profit_pct`: `0.1,0.15,0.2` (take profit percentage)
- `stop_loss_pct`: `0.05,0.08,0.1` (stop loss percentage)
- `cooldown_period`: `7,14,21` (days before re-entering position)

#### **MeanReversionStrategy**
- `lookback_period`: `20,30,40` (periods for mean calculation)
- `entry_threshold`: `2.0,2.5,3.0` (standard deviations from mean)
- `stop_loss_pct`: `0.05,0.08,0.1` (stop loss percentage)
- `cooldown_period`: `5,10,15` (days before re-entering)

#### **MomentumStrategy**
- `momentum_period`: `10,20,30` (momentum calculation period)
- `signal_threshold`: `0.05,0.1,0.15` (minimum signal strength)
- `stop_loss_pct`: `0.05,0.08,0.1` (stop loss percentage)
- `cooldown_period`: `3,7,14` (days before re-entering)

### Additional Configuration
- **Universe**: Comma-separated list of symbols (e.g., `AAPL,MSFT,GOOGL`)
- **Factors**: Comma-separated list of factors (e.g., `NewsSentiment,DebtToEquity`)

## Integration with Existing Framework

The application integrates with existing infrastructure:

- **DAG Generation**: Compatible with existing backtest framework
- **Deployment**: Uses AWS MWAA best practices
- **Monitoring**: Real-time status tracking via Airflow API
- **Authentication**: AWS IAM-based authentication

## Security

- **Credentials**: Supports IAM roles and AWS profiles
- **Validation**: All user inputs validated before processing
- **Error Handling**: Sensitive information not exposed in error messages

## Troubleshooting

### Common Issues

1. **Connection Failures**
   - Check AWS credentials and permissions
   - Verify MWAA environment name and region
   - Test network connectivity using sidebar

2. **Configuration Errors**
   - Review validation messages in the form
   - Check parameter format and ranges
   - Ensure all required fields are filled

3. **Deployment Issues**
   - Verify S3 bucket permissions
   - Check MWAA environment status
   - Review AWS region configuration

### Debug Features

- Connection testing in sidebar
- Real-time validation feedback
- Clear error messages with guidance
- Connection status monitoring and validation

