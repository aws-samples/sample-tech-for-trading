#!/bin/bash
set -e

echo "===== Initializing Terraform ====="
# Read AWS region from terraform.tfvars
AWS_REGION=$(grep aws_region terraform.tfvars | cut -d'=' -f2 | tr -d ' "')
if [ -z "$AWS_REGION" ]; then
    echo "Error: Could not find aws_region in terraform.tfvars"
    exit 1
fi

# Read the bucket name from the terraform state bucket file
BUCKET_NAME=$(cat ../terraform_state_bucket.txt | tr -d '[:space:]')
if [ -z "$BUCKET_NAME" ]; then
    echo "Error: Could not find terraform state bucket name. Please run 0-prepare/deploy.sh first."
    exit 1
fi

# Initialize Terraform with the S3 backend
terraform init -reconfigure \
    -backend=true \
    -backend-config="bucket=${BUCKET_NAME}" \
    -backend-config="key=terraform/7-financial-report/terraform.tfstate" \
    -backend-config="region=${AWS_REGION}"

echo "===== Deploying Infrastructure ====="
terraform plan
terraform apply

echo "===== Deployment Complete ====="
