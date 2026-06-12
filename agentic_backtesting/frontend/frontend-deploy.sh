#!/bin/bash
# Quick frontend code update - rebuilds and redeploys to existing ECS service
set -e

echo "🚀 Frontend Code Update"
echo "======================="

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.us-east-2.amazonaws.com/agentcore-backtest-ecr"
STACK_NAME="agentcore-backtest-v2"

echo "📦 Building..."
npm run build

echo "🐳 Building Docker image..."
docker buildx build --platform linux/amd64 -t agentcore-backtest-ecr . --load

echo "📤 Pushing to ECR..."
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin "$ECR_URI" > /dev/null 2>&1
docker tag agentcore-backtest-ecr:latest "$ECR_URI:latest"
docker push "$ECR_URI:latest"

echo "🔄 Redeploying ECS..."
CLUSTER=$(aws ecs list-clusters --region us-east-2 --query "clusterArns[?contains(@,'$STACK_NAME')]" --output text)
SERVICE=$(aws ecs list-services --cluster "$CLUSTER" --region us-east-2 --query 'serviceArns[0]' --output text)
aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" --force-new-deployment --region us-east-2 > /dev/null

echo ""
echo "✅ Done! New version will be live in ~2 minutes"
