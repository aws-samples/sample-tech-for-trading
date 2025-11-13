#!/bin/bash

# Deploy Market Data Lambda Function using Container Image
# This script can be used for both initial deployment and updates

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

# Container-specific configuration
TIMEOUT=60
MEMORY_SIZE=512
DESCRIPTION="Market Data Lambda Function for AgentCore MCP Gateway (Container)"
ECR_REPO_NAME="market-data-mcp"
IMAGE_TAG="latest"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG"

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

echo "🚀 Deploying Market Data Lambda Function (Container)..."
echo "📁 Project directory: $PROJECT_DIR"
echo "🌍 Region: $AWS_REGION"
echo "📋 Account: $ACCOUNT_ID"

# Step 1: Create ECR repository if it doesn't exist
echo "📦 Setting up ECR repository..."
if ! aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
    echo "Creating ECR repository: $ECR_REPO_NAME"
    aws ecr create-repository --repository-name "$ECR_REPO_NAME" --region "$AWS_REGION"
fi

# Step 2: Build and push Docker image
echo "🔨 Building and pushing Docker image..."
cd "$PROJECT_DIR"

# Login to ECR
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Build image (using legacy builder to avoid multi-platform issues)
DOCKER_BUILDKIT=0 docker build -t "$ECR_REPO_NAME:$IMAGE_TAG" .

# Tag and push
docker tag "$ECR_REPO_NAME:$IMAGE_TAG" "$IMAGE_URI"
docker push "$IMAGE_URI"

echo "✅ Docker image pushed to ECR"

# Step 3: Create or update Lambda function
echo "⚡ Managing Lambda function..."

# Check if function exists
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
    echo "📝 Function exists, updating code..."
    
    # Update function code
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --image-uri "$IMAGE_URI" \
        --region "$AWS_REGION"
    
    echo "⏳ Waiting for function update to complete..."
    aws lambda wait function-updated \
        --function-name "$FUNCTION_NAME" \
        --region "$AWS_REGION"
    
    echo "⚙️ Updating function configuration..."
    
    # Update configuration with S3 Tables environment variables
    if [ -n "$S3_TABLES_BUCKET" ]; then
        aws lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --timeout "$TIMEOUT" \
            --memory-size "$MEMORY_SIZE" \
            --description "$DESCRIPTION" \
            --environment "Variables={S3_TABLES_BUCKET=$S3_TABLES_BUCKET,S3_TABLES_NAMESPACE=$S3_TABLES_NAMESPACE,S3_TABLES_TABLE=$S3_TABLES_TABLE}" \
            --region "$AWS_REGION"
    else
        aws lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --timeout "$TIMEOUT" \
            --memory-size "$MEMORY_SIZE" \
            --description "$DESCRIPTION" \
            --region "$AWS_REGION"
    fi
    
    echo "✅ Lambda function updated successfully"
else
    echo "🆕 Function doesn't exist, creating new function..."
    
    # Get or create execution role
    ROLE_NAME="market-data-lambda-container-role"
    ROLE_ARN=""
    
    if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
        echo "📋 Using existing IAM role: $ROLE_NAME"
        ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
    else
        echo "🔐 Creating IAM role: $ROLE_NAME"
        
        # Create role
        aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document '{
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }
                ]
            }' \
            --description "Execution role for Market Data Lambda container function"
        
        # Attach policies
        aws iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        
        aws iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/AmazonS3TablesFullAccess"
        
        ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"
        
        echo "⏳ Waiting for role to be ready..."
        sleep 10
    fi
    
    # Create Lambda function with container image
    ENV_VARS=""
    if [ -n "$S3_TABLES_BUCKET" ]; then
        ENV_VARS="Variables={S3_TABLES_BUCKET=$S3_TABLES_BUCKET,S3_TABLES_NAMESPACE=$S3_TABLES_NAMESPACE,S3_TABLES_TABLE=$S3_TABLES_TABLE}"
    fi
    
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --code ImageUri="$IMAGE_URI" \
        --role "$ROLE_ARN" \
        --package-type Image \
        --timeout "$TIMEOUT" \
        --memory-size "$MEMORY_SIZE" \
        --description "$DESCRIPTION" \
        --region "$AWS_REGION" \
        ${ENV_VARS:+--environment "$ENV_VARS"}
    
    echo "✅ Lambda function created successfully"
fi

# Get function ARN and update environment
LAMBDA_FUNCTION_ARN=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" --query 'Configuration.FunctionArn' --output text)
echo "🔗 Function ARN: $LAMBDA_FUNCTION_ARN"

# Update environment file
update_env_var "LAMBDA_FUNCTION_ARN" "$LAMBDA_FUNCTION_ARN"
update_env_var "LAMBDA_DEPLOYED_AT" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
update_env_var "ECR_IMAGE_URI" "$IMAGE_URI"

# Store role ARN if we created/found one
if [ -n "$ROLE_ARN" ]; then
    update_env_var "LAMBDA_ROLE_ARN" "$ROLE_ARN"
fi

echo ""
echo "🎉 Lambda container deployment completed!"
echo "📝 Function Name: $FUNCTION_NAME"
echo "🔗 Function ARN: $LAMBDA_FUNCTION_ARN"
echo "🖼️  Image URI: $IMAGE_URI"
echo "💾 Environment updated: $ENV_FILE"
echo ""
echo "💡 Next steps:"
echo "   1. Run ./create_mcp_gateway.sh to create the MCP gateway"
echo "   2. Run ./setup_gateway_target.sh to connect the Lambda to the gateway"