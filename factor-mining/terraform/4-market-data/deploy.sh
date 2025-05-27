#!/bin/bash

# Exit on error
set -e

# Read and trim the S3 bucket name from the file
S3_BUCKET=$(cat ../terraform_state_bucket.txt | tr -d '[:space:]')

# Read AWS region from terraform.tfvars
AWS_REGION=$(grep aws_region terraform.tfvars | cut -d'=' -f2 | tr -d ' "')

echo "Using S3 bucket: ${S3_BUCKET}"
echo "Using AWS region: ${AWS_REGION}"

# Initialize Terraform with S3 backend
echo "Initializing Terraform..."
terraform init -reconfigure \
  -backend=true \
  -backend-config="bucket=${S3_BUCKET}" \
  -backend-config="key=terraform/4-market-data/terraform.tfstate" \
  -backend-config="region=${AWS_REGION}"

# Plan the changes
echo "Applying Terraform plan..."
terraform plan

echo "Applying Terraform apply..."
terraform apply