#!/bin/bash

# Exit on error
set -e

# Read the S3 bucket name from the terraform_state_bucket.txt file
BUCKET_NAME=$(cat ../terraform_state_bucket.txt | tr -d '\n')
if [ -z "$BUCKET_NAME" ]; then
    echo "Error: Could not read bucket name from ../terraform_state_bucket.txt"
    exit 1
fi

# Read region from terraform.tfvars if it exists
if [ -f "terraform.tfvars" ]; then
    AWS_REGION=$(grep -E "aws_region" terraform.tfvars | cut -d'"' -f2 | tr -d ' ')
    if [ -z "$AWS_REGION" ]; then
        echo "Error: Could not find region in terraform.tfvars"
        exit 1
    fi
else
    echo "Error: terraform.tfvars file not found"
    exit 1
fi

echo "Using AWS Region: $AWS_REGION"
echo "Using Bucket Name: $BUCKET_NAME"


# Initialize Terraform with backend configuration
echo "Initializing Terraform with S3 backend..."
terraform init -reconfigure \
    -backend-config="bucket=${BUCKET_NAME}" \
    -backend-config="key=terraform/2-clickhouse/terraform.tfstate" \
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
