# Factor Mining Infrastructure Preparation

This module sets up the necessary AWS infrastructure for the Factor Mining project, including S3 buckets, Lambda layers, and code signing configurations.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform installed (version >= 1.0.0)
- Python 3.12 (for Lambda layer compatibility)

## Configuration

1. Create or modify `terraform.tfvars` with your specific settings:

```hcl
# AWS region where resources will be created
aws_region = "us-west-2"  # Change this to your desired region

# S3 bucket for Lambda artifacts (must be globally unique)
lambda_artifacts_bucket_name = "factor-mining-lambda-artifacts-<unique-identifier>"

# S3 bucket for Terraform state (must be globally unique)
terraform_state_bucket_name = "factor-mining-terraform-state-<unique-identifier>"

# code_signing_profile_name
code_signing_profile_name = "signer=unique-name"

# Other configurations
enable_code_signing = true
clickhouse_layer_zip_path = "./clickhouse-driver-layer.zip"
pypdf_layer_zip_path = "./PyPDF-layer.zip"
yfinance_layer_zip_path = "./yfinance-layer.zip"
```

Replace `<unique-identifier>` with something unique to you, such as:
- Your AWS account ID (or part of it)
- Your username
- A random string
- Region name
- Timestamp

Example bucket names:
```hcl
lambda_artifacts_bucket_name = "factor-mining-lambda-artifacts-usw2-jane123"
terraform_state_bucket_name = "factor-mining-terraform-state-usw2-jane123"
```

## Deployment

1. Make the deployment script executable:
```bash
chmod +x deploy.sh
```

2. Run the deployment script:
```bash
./deploy.sh
```

The script will:
- Check if the S3 buckets exist and create them if needed
- Initialize Terraform with the correct backend configuration
- Plan and apply the Terraform configuration

## What Gets Created

The deployment creates:
- S3 bucket for Lambda artifacts with:
  - Versioning enabled
  - Server-side encryption
  - Public access blocked
- Lambda code signing profile
- Lambda code signing configuration
- Lambda layers:
  - Clickhouse driver Lambda layer
  - PyPDF Lambda layer
  - yfinance Lambda layer

Note: Ensure you have necessary permissions in your AWS account to create and manage these resources.
