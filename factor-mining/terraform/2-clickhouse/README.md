# Clickhouse Module

This module deploys a Clickhouse database on an EC2 instance.

## Features

- Deploys Clickhouse on an EC2 instance
- Automatically generates and securely stores SSH key pair
- Creates necessary security groups
- Sets up IAM roles and policies
- Configures Clickhouse with secure password
- Creates factor model database and tables
- Uses S3 backend for Terraform state management

## Prerequisites

- Base networking module must be deployed first
- S3 bucket for Terraform state must exist (specified in ../terraform_state_bucket.txt)
- DynamoDB table for state locking must exist (terraform-state-lock)


## SSH Access

An SSH key pair is automatically generated and the private key is saved locally as `[project_name]-[environment]-clickhouse-key.pem`. This file is set with 0600 permissions for security.

To connect to the instance:

```bash
ssh -i [project_name]-[environment]-clickhouse-key.pem ec2-user@[instance_ip]
```

## Deployment

1. Copy the example tfvars file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit the terraform.tfvars file with your desired values

3. Deploy using the deployment script:
   ```bash
   ./deploy.sh
   ```

The deploy script will:
- Read the S3 bucket name from ../terraform_state_bucket.txt
- Configure the S3 backend
- Initialize Terraform with the remote backend
- Plan and apply the changes
- Clean up temporary files

## Outputs

- `clickhouse_endpoint`: The endpoint for connecting to Clickhouse
- `clickhouse_port`: The port for connecting to Clickhouse
- `clickhouse_secret_arn`: ARN of the secret containing Clickhouse credentials
- `clickhouse_secret_name`: Name of the secret containing Clickhouse credentials
- `clickhouse_username`: Username for Clickhouse
- `ssh_key_name`: Name of the SSH key pair created for Clickhouse instance
- `ssh_private_key_path`: Path to the private key file for SSH access
