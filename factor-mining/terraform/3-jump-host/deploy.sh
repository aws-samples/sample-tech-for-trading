#!/bin/bash
set -e

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Read the S3 bucket name from the file
BUCKET_NAME=$(cat "$SCRIPT_DIR/../terraform_state_bucket.txt" | tr -d '\n')

# Check if the bucket name is empty
if [ -z "$BUCKET_NAME" ]; then
  echo "Error: S3 bucket name is empty. Please make sure terraform_state_bucket.txt contains a valid bucket name."
  exit 1
fi


# Read AWS region from terraform.tfvars
AWS_REGION=$(grep aws_region terraform.tfvars | cut -d'=' -f2 | tr -d ' "')

echo "Using S3 bucket: ${BUCKET_NAME}"
echo "Using AWS region: ${AWS_REGION}"


# Initialize Terraform with the S3 backend
terraform init -reconfigure \
    -backend=true \
  -backend-config="bucket=${BUCKET_NAME}" \
  -backend-config="key=terraform/3-jump-host/terraform.tfstate" \
  -backend-config="region=${AWS_REGION}"

# Plan the changes
echo "Applying Terraform plan..."
terraform plan

echo "Applying Terraform apply..."
terraform apply

echo "Jump host deployment completed successfully!"
echo "You can connect to the jump host using Session Manager or SSH."
echo "Session Manager: aws ssm start-session --target \$(terraform output -raw jump_host_id)"
echo "SSH: \$(terraform output -raw ssh_command)"
