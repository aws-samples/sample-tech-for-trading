#!/bin/bash

# Exit on error
set -e

# Read and trim the S3 bucket name from the file
S3_BUCKET=$(cat ../terraform_state_bucket.txt | tr -d '[:space:]')

# Read AWS region from terraform.tfvars
if [ -f "terraform.tfvars" ]; then
    AWS_REGION=$(grep aws_region terraform.tfvars | cut -d'=' -f2 | tr -d ' "')
    if [ -z "$AWS_REGION" ]; then
        AWS_REGION="us-east-1"  # Default if not found in tfvars
    fi
else
    AWS_REGION="us-east-1"  # Default if tfvars doesn't exist
fi

echo "Using S3 bucket: ${S3_BUCKET}"
echo "Using AWS region: ${AWS_REGION}"

# Initialize Terraform with S3 backend
echo "Initializing Terraform..."
terraform init -reconfigure \
  -backend=true \
  -backend-config="bucket=${S3_BUCKET}" \
  -backend-config="key=terraform/6-sec-filing/terraform.tfstate" \
  -backend-config="region=${AWS_REGION}"

# Plan the changes
echo "Planning Terraform changes..."
terraform plan

echo "Applying Terraform changes..."
terraform apply
