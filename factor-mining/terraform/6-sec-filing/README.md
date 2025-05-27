# SEC Data Collection and Processing Module

This Terraform module deploys infrastructure for collecting and processing SEC financial data for DJIA stocks.

## Architecture

The module creates two Lambda functions:

1. **sec_data_lambda**: Collects company financial data from the SEC API and stores it in an S3 bucket
2. **extract_sec_lambda**: Processes the SEC data when new files are uploaded to S3 and stores the extracted data in ClickHouse

## Components

- **S3 Bucket**: Stores the raw SEC data files
- **Lambda Functions**: Two Lambda functions for data collection and processing
- **Lambda Layer**: Uses the ClickHouse driver layer from the 0-prepare module
- **EventBridge Rule**: Triggers the data collection Lambda function daily
- **S3 Event Notification**: Triggers the data processing Lambda function when new files are uploaded
- **VPC Integration**: Lambda functions run within the VPC created in the networking module
- **Lambda Code Signing**: Uses the signing profile from the 0-prepare module
- **Secrets Management**: Retrieves ClickHouse credentials from AWS Secrets Manager

## Prerequisites

- AWS account with appropriate permissions
- Terraform state bucket configured (referenced in ../terraform_state_bucket.txt)
- Completed deployment of:
  - 0-prepare module (for Lambda layers and signing profile)
  - 1-networking module (for VPC configuration)
  - 2-clickhouse module (for database credentials)

## Usage

1. Create the terraform.tfvars file with your desired values
2. Run the deployment script:

```bash
./deploy.sh
```

## Variables

| Name | Description | Type | Default |
|------|-------------|------|---------|
| tickers | List of stock ticker symbols | list(string) | DJIA 30 stocks |
| cik_mapping | Mapping of ticker symbols to CIK numbers | map(string) | DJIA 30 CIK mappings |
| email | Email for SEC API user agent | string | "your.email@example.com" |
| aws_region | AWS region | string | "us-east-1" |

## Outputs

| Name | Description |
|------|-------------|
| sec_data_bucket_name | Name of the S3 bucket storing SEC data |
| sec_data_lambda_function_name | Name of the Lambda function collecting SEC data |
| extract_sec_lambda_function_name | Name of the Lambda function extracting SEC data |
| sec_data_lambda_arn | ARN of the Lambda function collecting SEC data |
| extract_sec_lambda_arn | ARN of the Lambda function extracting SEC data |
