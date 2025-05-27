#!/bin/bash

# Read the S3 bucket name from the terraform_state_bucket.txt file
BUCKET_NAME=$(cat ../terraform_state_bucket.txt | tr -d '[:space:]')
if [ -z "$BUCKET_NAME" ]; then
    echo "Error: Could not read bucket name from ../terraform_state_bucket.txt"
    exit 1
fi

# Read region from terraform.tfvars if it exists
if [ -f "terraform.tfvars" ]; then
    AWS_REGION=$(grep -E "^aws_region" terraform.tfvars | cut -d'"' -f2 | tr -d ' ')
    if [ -z "$AWS_REGION" ]; then
        AWS_REGION="us-east-1"  # Default if not found in tfvars
    fi
else
    AWS_REGION="us-east-1"  # Default if tfvars doesn't exist
fi

# Default environment
ENVIRONMENT="dev"

echo "Using AWS Region: $AWS_REGION"
echo "Using Bucket Name: $BUCKET_NAME"
echo "Environment: $ENVIRONMENT"

# Verify terraform.tf exists with backend configuration
if [ ! -f "terraform.tf" ] || ! grep -q "backend \"s3\"" terraform.tf; then
    echo "Error: terraform.tf file is missing or doesn't contain S3 backend configuration"
    exit 1
fi

# Initialize Terraform with backend configuration
echo "Initializing Terraform with S3 backend..."
terraform init -reconfigure \
    -backend-config="bucket=${BUCKET_NAME}" \
    -backend-config="key=terraform/8-factor-mining/terraform.tfstate" \
    -backend-config="region=${AWS_REGION}"

# Check if initialization was successful
if [ $? -ne 0 ]; then
    echo "Terraform initialization failed. Exiting."
    exit 1
fi

# Run Terraform plan and apply
echo "Running Terraform plan..."
terraform plan

echo "Running Terraform apply..."
terraform apply --auto-approve

# Get ECR repository URL
ECR_REPO=$(terraform output -raw ecr_repository_url)
echo "ECR Repository: $ECR_REPO"

# Navigate to the application directory
cd ../../src/factor-modeling-model

# Build Docker image for AMD64 platform
echo "Building Docker image for AMD64 platform..."
docker buildx create --use --name builder || true
docker buildx use builder
docker buildx build --platform linux/amd64 -t factor-mining-model:latest .

# Log in to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO

# Tag and push the image
echo "Tagging and pushing image to ECR..."
docker buildx build --platform linux/amd64 -t $ECR_REPO:latest --push .

echo "Deployment completed successfully!"
echo ""
echo "To submit a batch job, run:"
echo "aws batch submit-job --job-name factor-modeling-job-\$(date +%s) --job-queue factor-modeling-queue --job-definition factor-modeling-job --parameters batch_no=0,factor=ALL,tickers=ALL,start_date=2020-01-01,end_date=2025-03-31"
echo ""
echo "To submit specific batch jobs (0, 1, 2, or 3), run:"
echo "aws batch submit-job --job-name factor-modeling-job-\$(date +%s) --job-queue factor-modeling-queue --job-definition factor-modeling-job --parameters batch_no=1,factor=ALL,tickers=ALL,start_date=2020-01-01,end_date=2025-03-31"
echo ""
echo "To run a specific factor, use:"
echo "aws batch submit-job --job-name factor-modeling-job-\$(date +%s) --job-queue factor-modeling-queue --job-definition factor-modeling-job --parameters batch_no=0,factor=PEG,tickers=ALL,start_date=2020-01-01,end_date=2025-03-31"