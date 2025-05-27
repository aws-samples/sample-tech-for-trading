# Market Data Processor

This module deploys a Lambda function that processes market data. The function is deployed in a VPC and uses multiple layers including Clickhouse driver, yfinance, and AWS SDK for Pandas.

## Components

- Lambda function with VPC configuration
- IAM roles and policies
- Integration with Clickhouse via Secrets Manager
- Multiple Lambda layers for dependencies
- Lambda code signing using profile from prepare module

## Prerequisites

- VPC and networking components deployed via ../1-networking
- Lambda layers and signing profile created in ../0-prepare
- Clickhouse secrets configured in ../2-clickhouse
- S3 bucket for Terraform state (defined in ../terraform_state_bucket.txt)

## Deployment

To deploy this module:

1. Ensure all prerequisites are met
2. Create the terraform.tfvars file with your desired values
3. Run the deployment script:
   ```bash
   ./deploy.sh
   ```

