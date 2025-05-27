# Factor Mining Visualization Infrastructure

This directory contains Terraform configuration for deploying the Factor Mining Visualization application to AWS.

## Architecture

The application is deployed as a containerized Streamlit application running on AWS Fargate with the following components:

- Amazon ECR repository for storing the Docker image
- ECS Cluster and Service for running the application
- Application Load Balancer for routing traffic
- IAM roles and policies for accessing AWS resources
- CloudWatch Log Group for logging
- Integration with existing VPC from networking module
- Secrets management through AWS Secrets Manager
- Remote state management using S3 backend

## Prerequisites

- AWS credentials configured
- Terraform 1.0+
- Docker installed locally
- Existing VPC (deployed through ../1-networking)
- Existing ClickHouse setup (deployed through ../2-clickhouse)
- S3 bucket for Terraform state (name stored in ../terraform_state_bucket.txt)

## Deployment Steps

1. Create the terraform.tfvars file with your desired values
2. Run the deployment script:

```bash
# Navigate to the terraform directory
cd terraform/9-visualization

# Run the deployment script
./deploy.sh
```

The script will:
- Configure S3 backend for Terraform state
- Apply the Terraform configuration
- Build and push the Docker image to ECR
- Deploy the application to ECS Fargate
- Output the URL to access the application

