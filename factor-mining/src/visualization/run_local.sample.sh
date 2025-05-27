#!/bin/bash

# Set environment variables
export CLICKHOUSE_HOST=
export CLICKHOUSE_PORT=9000
export CLICKHOUSE_USER=
export CLICKHOUSE_SECRET_ARN=arn:aws:secretsmanager:us-east-1:11111:secret:xxxx
export CLICKHOUSE_DATABASE=factor_modeling
export AWS_REGION=us-east-1
export STATE_MACHINE_ARN=arn:aws:states:us-east-1:11111:stateMachine:xxx

# Set AWS profile
export AWS_PROFILE=default

# Run the Streamlit application
streamlit run app.py
