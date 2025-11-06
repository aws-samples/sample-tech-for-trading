#!/bin/bash

# Deploy Lambda function as container image with PyIceberg
set -e

# Configuration
FUNCTION_NAME="market-data-mcp"
REGION="us-east-1"
AWS_PROFILE="factor"
ACCOUNT_ID=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account --output text)
ECR_REPO_NAME="market-data-mcp"
IMAGE_TAG="latest"

echo "🚀 Deploying Lambda Container with PyIceberg"
echo "============================================"
echo "📦 Function: $FUNCTION_NAME"
echo "🌍 Region: $REGION"
echo "🔧 Profile: $AWS_PROFILE"
echo "📋 Account: $ACCOUNT_ID"
echo ""

# Step 1: Create ECR repository if it doesn't exist
echo "📦 Setting up ECR repository..."
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --profile $AWS_PROFILE --region $REGION >/dev/null 2>&1 || {
    echo "Creating ECR repository: $ECR_REPO_NAME"
    aws ecr create-repository --repository-name $ECR_REPO_NAME --profile $AWS_PROFILE --region $REGION
}

# Step 2: Get ECR login token
echo "🔐 Logging into ECR..."
aws ecr get-login-password --profile $AWS_PROFILE --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Step 3: Build Docker image
echo "🔨 Building Docker image..."
docker build -t $ECR_REPO_NAME:$IMAGE_TAG .

# Step 4: Tag and push image
echo "📤 Pushing image to ECR..."
docker tag $ECR_REPO_NAME:$IMAGE_TAG $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG

# Step 5: Update or create Lambda function
echo "⚡ Updating Lambda function..."
IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG"

# Check if function exists
if aws lambda get-function --function-name $FUNCTION_NAME --profile $AWS_PROFILE --region $REGION >/dev/null 2>&1; then
    echo "📝 Updating existing function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --image-uri $IMAGE_URI \
        --profile $AWS_PROFILE \
        --region $REGION
else
    echo "🆕 Creating new function..."
    # Get or create execution role
    ROLE_NAME="market-data-lambda-container-role"
    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --profile $AWS_PROFILE --query 'Role.Arn' --output text 2>/dev/null || {
        echo "Creating IAM role: $ROLE_NAME"
        aws iam create-role \
            --role-name $ROLE_NAME \
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
            --profile $AWS_PROFILE \
            --query 'Role.Arn' \
            --output text
        
        # Attach policies
        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
            --profile $AWS_PROFILE
        
        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/AmazonS3TablesFullAccess \
            --profile $AWS_PROFILE
        
        echo "arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"
    })
    
    # Wait for role to be ready
    sleep 10
    
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --code ImageUri=$IMAGE_URI \
        --role $ROLE_ARN \
        --package-type Image \
        --timeout 30 \
        --memory-size 512 \
        --profile $AWS_PROFILE \
        --region $REGION
fi

echo ""
echo "🎉 Lambda container deployment completed!"
echo "📦 Function: $FUNCTION_NAME"
echo "🖼️  Image: $IMAGE_URI"
echo ""
echo "🧪 Test with:"
echo "aws lambda invoke --function-name $FUNCTION_NAME --payload '{\"symbol\":\"AMZN\"}' response.json --profile $AWS_PROFILE --region $REGION"
