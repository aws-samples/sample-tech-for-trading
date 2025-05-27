# Factor Mining Infrastructure

This module deploys the AWS infrastructure required for factor mining and analysis.

## Architecture

The module creates the following resources:
- ECR repository for Docker images (using the ECR module)
- AWS Batch compute environment using Fargate
- AWS Batch job queue and job definition
- IAM roles and policies for AWS Batch and ECS
- Step Functions for orchestrating the factor mining workflow

## Network Infrastructure

This module uses the VPC and subnets created by the `1-networking` module. It retrieves the networking resources using Terraform remote state from an S3 backend.

## Prerequisites

Before deploying this module, ensure that:
1. The `1-networking` module has been deployed
2. The `2-clickhouse` module has been deployed (for database credentials)

## Usage

1. Create the terraform.tfvars file with your desired values
2. Initialize and deploy using the provided script:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

2. After deployment, build and push the Docker image to the ECR repository:
   ```bash
   # Get the ECR repository URL
   ECR_REPO=$(terraform output -raw ecr_repository_url)
   
   # Authenticate Docker to ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REPO
   
   # Build the Docker image
   docker build -t $ECR_REPO:latest .
   
   # Push the image to ECR
   docker push $ECR_REPO:latest
   ```

3. Submit a batch job:
   ```bash
   ./batch_submit_jobs.sh
   ```

## Variables

| Name | Description | Default |
|------|-------------|---------|
| aws_region | AWS region to deploy resources | us-east-1 |
| resource_prefix | Prefix for resource names | fm |
| environment | Environment name | dev |
| ecr_repository_name | Name of the ECR repository | factor-modeling |
| tickers | List of tickers to analyze | AAPL,AMGN,AMZN,... |
| start_date | Start date for factor analysis | 2020-01-01 |
| end_date | End date for factor analysis | 2023-01-01 |
| thread_no | Number of date range segments for parallel processing | 5 |
| parallel_m | Number of ticker groups for parallel processing | 6 |

## Outputs

| Name | Description |
|------|-------------|
| ecr_repository_url | URL of the ECR repository |
| batch_job_queue_arn | ARN of the AWS Batch job queue |
| batch_job_definition_arn | ARN of the AWS Batch job definition |
| batch_job_definition_name | Name of the AWS Batch job definition |
| step_function_arn | ARN of the Step Function state machine |
| step_function_name | Name of the Step Function state machine |
| vpc_id | ID of the VPC used |
| private_subnet_ids | IDs of the private subnets used |
| public_subnet_ids | IDs of the public subnets used |

## Security

This module uses AWS Secrets Manager to securely store and retrieve ClickHouse credentials. The batch jobs access these credentials using the appropriate IAM permissions.
