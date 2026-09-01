#!/bin/bash
# Master deployment - full deployment from scratch
set -e

echo "🚀 Full Deployment - Paper Backtest Frontend + Infrastructure"
echo "=============================================================="

if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | grep -v '^$' | xargs)
fi

if [ -z "$AGENTCORE_ARN" ]; then
    echo "❌ AGENTCORE_ARN not set in .env.local"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO_NAME="${ECR_REPO_NAME:-agentcore-paper-backtest-ecr}"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.us-east-2.amazonaws.com/${ECR_REPO_NAME}"

echo "✅ AWS Account: $AWS_ACCOUNT_ID"

# Step 1: Create ECR repository if needed
echo ""
echo "📦 Setting up ECR repository..."
if ! aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region us-east-2 &>/dev/null; then
    aws ecr create-repository --repository-name "$ECR_REPO_NAME" --region us-east-2 > /dev/null
    echo "✅ ECR repository created"
else
    echo "✅ ECR repository exists"
fi

# Step 2: Build and push Docker image
echo ""
echo "🐳 Building and pushing Docker image..."
docker buildx build --platform linux/amd64 -t "$ECR_REPO_NAME" . --load
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin "$ECR_URI" > /dev/null 2>&1
docker tag "$ECR_REPO_NAME:latest" "$ECR_URI:latest"
docker push "$ECR_URI:latest"
echo "✅ Image pushed: $ECR_URI:latest"

# Step 3: Deploy infrastructure
echo ""
echo "☁️  Deploying infrastructure..."
./infra-deploy.sh

echo ""
echo "✅ Full deployment complete!"
echo ""
echo "📝 Next steps:"
echo "   - For code updates only: ./frontend-deploy.sh"
echo "   - For infrastructure updates: ./infra-deploy.sh"
echo "   - For full redeployment: ./deploy.sh"
