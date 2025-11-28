#!/bin/bash

# Setup S3 Tables and migrate data from ClickHouse
set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load environment variables
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
else
    echo "❌ Environment file not found: $ENV_FILE"
    exit 1
fi

# Function to update environment file
update_env_var() {
    local key="$1"
    local value="$2"
    if grep -q "^${key}=" "$ENV_FILE"; then
        sed -i.bak "s|^${key}=.*|${key}=\"${value}\"|" "$ENV_FILE"
    else
        echo "${key}=\"${value}\"" >> "$ENV_FILE"
    fi
    rm -f "${ENV_FILE}.bak"
}

echo "🚀 Setting up S3 Tables and populating with CSV data..."
echo "🌍 Region: $AWS_REGION"

# Generate unique bucket name if not set
if [ -z "$S3_TABLES_BUCKET" ]; then
    TIMESTAMP=$(date +%s)
    S3_TABLES_BUCKET="market-data-$TIMESTAMP"
    echo "📦 Generated bucket name: $S3_TABLES_BUCKET"
    update_env_var "S3_TABLES_BUCKET" "$S3_TABLES_BUCKET"
fi

echo "📦 S3 Tables Bucket: $S3_TABLES_BUCKET"
echo "📊 Namespace: $S3_TABLES_NAMESPACE"
echo "📋 Table: $S3_TABLES_TABLE"

# Check if Python population script exists
POPULATION_SCRIPT="$PROJECT_DIR/data/populate_s3_table.py"
if [ ! -f "$POPULATION_SCRIPT" ]; then
    echo "❌ Population script not found: $POPULATION_SCRIPT"
    exit 1
fi

# Install population dependencies
echo "📦 Installing population dependencies..."
cd "$PROJECT_DIR"

# Check if virtual environment should be used
if command -v python3 >/dev/null 2>&1; then
    echo "🐍 Installing PyIceberg and dependencies..."
    pip3 install -r requirements.txt
else
    echo "❌ Python 3 not found. Please install Python 3 and pip3"
    exit 1
fi

# Run the population script
echo "🔄 Populating S3 Tables from CSV data..."
cd "$PROJECT_DIR/data"
python3 populate_s3_table.py

echo "✅ S3 Tables setup and data population completed!"
echo "📦 Bucket: $S3_TABLES_BUCKET"
echo "📊 Namespace: $S3_TABLES_NAMESPACE"
echo "📋 Table: $S3_TABLES_TABLE"
echo "💾 Environment updated: $ENV_FILE"
