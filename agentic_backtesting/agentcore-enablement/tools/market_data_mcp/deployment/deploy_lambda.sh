#!/bin/bash

# Deploy Market Data Lambda Function
# This script can be used for both initial deployment and updates

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAMBDA_DIR="$SCRIPT_DIR"

# Load environment variables
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
else
    echo "❌ Environment file not found: $ENV_FILE"
    exit 1
fi

# Lambda-specific configuration
RUNTIME="python3.11"
HANDLER="lambda_function.lambda_handler"
TIMEOUT=60
MEMORY_SIZE=512
DESCRIPTION="Market Data Lambda Function for AgentCore MCP Gateway"

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

echo "🚀 Deploying Market Data Lambda Function..."
echo "📁 Lambda directory: $LAMBDA_DIR"

# Create deployment package
echo "📦 Creating deployment package..."
cd "$LAMBDA_DIR"

# Create a temporary directory for the package
TEMP_DIR=$(mktemp -d)
echo "📂 Using temporary directory: $TEMP_DIR"

# Copy Lambda function code from parent directory
cp ../lambda_function.py "$TEMP_DIR/"
cp ../requirements.txt "$TEMP_DIR/"

# Install dependencies
echo "📦 Installing Python dependencies..."
cd "$TEMP_DIR"
pip install -r requirements.txt -t .

# Create zip package
zip -r lambda-deployment.zip .

echo "✅ Deployment package created"

# Check if function exists
echo "🔍 Checking if Lambda function exists..."
if aws lambda get-function --function-name "$FUNCTION_NAME" >/dev/null 2>&1; then
    echo "📝 Function exists, updating code..."
    
    # Update function code
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file fileb://lambda-deployment.zip
    
    echo "⚙️ Updating function configuration..."
    
    # Update with S3 Tables environment variables if available
    if [ -n "$S3_TABLES_BUCKET" ]; then
        aws lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --timeout "$TIMEOUT" \
            --memory-size "$MEMORY_SIZE" \
            --description "$DESCRIPTION" \
            --environment "Variables={S3_TABLES_BUCKET=$S3_TABLES_BUCKET,S3_TABLES_NAMESPACE=$S3_TABLES_NAMESPACE,S3_TABLES_TABLE=$S3_TABLES_TABLE}"
    else
        aws lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --timeout "$TIMEOUT" \
            --memory-size "$MEMORY_SIZE" \
            --description "$DESCRIPTION"
    fi
    
    echo "✅ Lambda function updated successfully"
else
    echo "🆕 Function doesn't exist, creating new function..."
    
    # Get or create execution role
    ROLE_NAME="market-data-lambda-role"
    ROLE_ARN=""
    
    if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
        echo "📋 Using existing IAM role: $ROLE_NAME"
        ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
    else
        echo "🔐 Creating IAM role: $ROLE_NAME"
        
        # Create trust policy
        cat > trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
        
        # Create role
        aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document file://trust-policy.json \
            --description "Execution role for Market Data Lambda function"
        
        # Attach basic execution policy
        aws iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        
        # Create S3 Tables and Athena policy
        cat > s3tables-athena-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3tables:GetTable",
                "s3tables:GetTableData"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "athena:StartQueryExecution",
                "athena:GetQueryExecution",
                "athena:GetQueryResults",
                "athena:StopQueryExecution"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::aws-athena-query-results-*",
                "arn:aws:s3:::aws-athena-query-results-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "glue:GetDatabase",
                "glue:GetTable",
                "glue:GetPartitions"
            ],
            "Resource": "*"
        }
    ]
}
EOF
        
        # Create and attach policy
        POLICY_ARN=$(aws iam create-policy \
            --policy-name "market-data-s3tables-athena-policy" \
            --policy-document file://s3tables-athena-policy.json \
            --query 'Policy.Arn' --output text 2>/dev/null || \
            aws iam list-policies --query "Policies[?PolicyName=='market-data-s3tables-athena-policy'].Arn" --output text)
        
        aws iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "$POLICY_ARN"
        
        rm -f s3tables-athena-policy.json
        
        ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
        
        echo "⏳ Waiting for role to be ready..."
        sleep 10
    fi
    
    # Create Lambda function with S3 Tables environment variables
    ENV_VARS=""
    if [ -n "$S3_TABLES_BUCKET" ]; then
        ENV_VARS="Variables={S3_TABLES_BUCKET=$S3_TABLES_BUCKET,S3_TABLES_NAMESPACE=$S3_TABLES_NAMESPACE,S3_TABLES_TABLE=$S3_TABLES_TABLE}"
    fi
    
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime "$RUNTIME" \
        --role "$ROLE_ARN" \
        --handler "$HANDLER" \
        --zip-file fileb://lambda-deployment.zip \
        --timeout "$TIMEOUT" \
        --memory-size "$MEMORY_SIZE" \
        --description "$DESCRIPTION" \
        ${ENV_VARS:+--environment "$ENV_VARS"}
    
    echo "✅ Lambda function created successfully"
fi

# Get function ARN and update environment
LAMBDA_FUNCTION_ARN=$(aws lambda get-function --function-name "$FUNCTION_NAME" --query 'Configuration.FunctionArn' --output text)
echo "🔗 Function ARN: $LAMBDA_FUNCTION_ARN"

# Update environment file
update_env_var "LAMBDA_FUNCTION_ARN" "$LAMBDA_FUNCTION_ARN"
update_env_var "LAMBDA_DEPLOYED_AT" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Store role ARN if we created/found one
if [ -n "$ROLE_ARN" ]; then
    update_env_var "LAMBDA_ROLE_ARN" "$ROLE_ARN"
fi



# Cleanup
cd "$LAMBDA_DIR"
rm -rf "$TEMP_DIR"

echo ""
echo "🎉 Lambda deployment completed!"
echo "📝 Function Name: $FUNCTION_NAME"
echo "🔗 Function ARN: $LAMBDA_FUNCTION_ARN"
echo "💾 Environment updated: $ENV_FILE"
echo ""
echo "💡 Next steps:"
echo "   1. Run ./create_mcp_gateway.sh to create the MCP gateway"
echo "   2. Run ./setup_gateway_target.sh to connect the Lambda to the gateway"