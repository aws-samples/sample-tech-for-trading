#!/bin/bash

# Exit on error
set -e

# Read AWS region from terraform.tfvars
AWS_REGION=$(grep aws_region terraform.tfvars | cut -d'=' -f2 | tr -d ' "')
if [ -z "$AWS_REGION" ]; then
    echo "Error: aws_region not found in terraform.tfvars"
    exit 1
fi

# Read S3 bucket name from terraform state bucket file
S3_BUCKET=$(cat ../terraform_state_bucket.txt | tr -d '[:space:]')
if [ -z "$S3_BUCKET" ]; then
    echo "Error: S3 bucket name not found in ../terraform_state_bucket.txt"
    exit 1
fi

# Initialize Terraform with S3 backend
terraform init -reconfigure \
    -backend-config="bucket=$S3_BUCKET" \
    -backend-config="key=terraform/9-visualization/terraform.tfstate" \
    -backend-config="region=$AWS_REGION"

# Apply Terraform configuration
terraform apply -auto-approve

# Get ECR repository URL
ECR_REPO=$(terraform output -raw ecr_repository_url)
echo "ECR Repository: $ECR_REPO"

# Navigate to the application directory
cd ../../src/visualization

# Build Docker image for AMD64 platform
echo "Building Docker image for AMD64 platform..."
docker buildx create --use --name builder || true
docker buildx use builder
docker buildx build --platform linux/amd64 -t factor-mining-visualization:latest .

# Log in to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO

# Tag and push the image
echo "Tagging and pushing image to ECR..."
docker buildx build --platform linux/amd64 -t $ECR_REPO:latest --push .

# Force new deployment of the ECS service
echo "Updating ECS service..."
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
SERVICE_NAME=$(terraform output -raw ecs_service_name)
aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force-new-deployment --region $AWS_REGION

echo "Deployment completed!"
echo "Application URL: $(terraform output -raw application_url)"
echo "It may take a few minutes for the new container to start and the health checks to pass."
