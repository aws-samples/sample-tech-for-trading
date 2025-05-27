#!/bin/bash

# Read the S3 bucket name from the terraform_state_bucket.txt file
BUCKET_NAME=$(cat ../terraform_state_bucket.txt)
if [ -z "$BUCKET_NAME" ]; then
    echo "Error: Could not read bucket name from ../terraform_state_bucket.txt"
    exit 1
fi

# Read region from terraform.tfvars if it exists
if [ -f "terraform.tfvars" ]; then
    AWS_REGION=$(grep -E "^aws_region|^region" terraform.tfvars | cut -d'"' -f2 | tr -d ' ')
    if [ -z "$AWS_REGION" ]; then
        AWS_REGION="us-east-1"  # Default if not found in tfvars
    fi
else
    AWS_REGION="us-east-1"  # Default if tfvars doesn't exist
fi

# Default action and environment
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
    -backend-config="key=terraform/1-networking/terraform.tfstate" \
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
terraform apply

