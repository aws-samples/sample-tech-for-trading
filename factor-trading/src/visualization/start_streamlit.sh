#!/bin/bash

# Set environment variables
export CLICKHOUSE_HOST=${CLICKHOUSE_HOST:-44.222.122.134}
export CLICKHOUSE_PORT=${CLICKHOUSE_PORT:-8123}
export CLICKHOUSE_USER=${CLICKHOUSE_USER:-default}
export CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD:-'clickhouse@aws'}
export CLICKHOUSE_DATABASE=${CLICKHOUSE_DATABASE:-factor_model_tick_data_database}

# Start Streamlit
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
