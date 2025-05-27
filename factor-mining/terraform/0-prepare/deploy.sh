#!/bin/bash

# Extract region and bucket name from terraform.tfvars
AWS_REGION=$(grep aws_region terraform.tfvars | cut -d'"' -f2)
BUCKET_NAME=$(grep terraform_state_bucket_name terraform.tfvars | cut -d'"' -f2)

echo "Using AWS Region: $AWS_REGION"
echo "Using Bucket Name: $BUCKET_NAME"
echo $BUCKET_NAME > ../terraform_state_bucket.txt

# Check if bucket exists
echo "Checking if bucket exists..."
if aws s3api head-bucket --bucket $BUCKET_NAME 2>/dev/null; then
    echo "Bucket $BUCKET_NAME already exists and you have access to it."
else
    echo "Creating bucket $BUCKET_NAME in region $AWS_REGION..."
    
    # Create bucket with different commands based on region
    if [ "$AWS_REGION" = "us-east-1" ]; then
        # For us-east-1, don't specify the LocationConstraint
        aws s3api create-bucket \
            --bucket ${BUCKET_NAME} \
            --region ${AWS_REGION} \
            --object-ownership BucketOwnerEnforced
    else
        # For other regions, specify the LocationConstraint
        aws s3api create-bucket \
            --bucket ${BUCKET_NAME} \
            --region ${AWS_REGION} \
            --create-bucket-configuration LocationConstraint=${AWS_REGION} \
            --object-ownership BucketOwnerEnforced
    fi
    
    if [ $? -eq 0 ]; then
        echo "Successfully created bucket $BUCKET_NAME"
    else
        echo "Failed to create bucket $BUCKET_NAME"
        exit 1
    fi
fi

# Initialize Terraform with backend configuration and reconfigure flag
echo "Initializing Terraform..."
terraform init -reconfigure \
    -backend-config="bucket=${BUCKET_NAME}" \
    -backend-config="key=terraform/0-prepare/terraform.tfstate" \
    -backend-config="region=${AWS_REGION}"

# Run Terraform plan and apply
echo "Running Terraform plan..."
terraform plan

echo "Running Terraform apply..."
terraform apply
