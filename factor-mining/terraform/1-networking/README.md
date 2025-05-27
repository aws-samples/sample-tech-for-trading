# Network Infrastructure Module

This module creates the network infrastructure required for the factor mining platform on AWS. It implements a high-availability architecture with a NAT gateway in each availability zone, ensuring that resources in other availability zones can still access the internet even if one availability zone fails.

## Architecture Components

- **VPC**: Creates a Virtual Private Cloud with DNS support
- **Subnets**:
  - One public subnet per availability zone (for NAT gateways, load balancers, etc.)
  - One private subnet per availability zone (for application servers, databases, etc.)
- **Gateways**:
  - Internet Gateway: Allows public subnets to access the internet
  - NAT Gateways: One per availability zone, allowing private subnets to access the internet
- **Route Tables**:
  - Public route table: Routes traffic to the internet gateway
  - Private route tables: One per availability zone, routing traffic to the corresponding NAT gateway
- **Security Group**: Default security group allowing all outbound traffic

## Usage

The module includes a `deploy.sh` script that simplifies deployment by automatically configuring the S3 backend using the bucket name from `../terraform_state_bucket.txt`.

1. Make the script executable (if not already):
   ```bash
   chmod +x deploy.sh
   ```

2. Run the deployment script:
   ```bash
   # View the execution plan (default)
   ./deploy.sh

   # Specify a different region (overrides terraform.tfvars)
   ./deploy.sh --region=us-west-2

   # Apply the changes
   ./deploy.sh --action=apply

   # View outputs
   ./deploy.sh --action=output

   # Destroy resources
   ./deploy.sh --action=destroy

   # Specify environment
   ./deploy.sh --environment=prod --action=apply
   ```

The script automatically:
- Reads the S3 bucket name from `../terraform_state_bucket.txt`
- Reads the AWS region from `terraform.tfvars` (if available)
- Configures Terraform to use this bucket for state storage
- Runs the specified action with the provided parameters

## Variables

| Variable Name | Description | Type | Default Value |
|------|-------------|------|---------|
| vpc_cidr | CIDR block for the VPC | string | "10.0.0.0/16" |
| region | AWS region | string | "us-east-1" |
| availability_zones | List of availability zones | list(string) | ["us-east-1a", "us-east-1b"] |
| project_name | Project name | string | "factor-mining" |
| environment | Environment name | string | "dev" |

## Outputs

| Output Name | Description | Example |
|------|-------------|------|
| vpc_id | ID of the VPC | vpc-0b429b8a7f45bb6c2 |
| private_subnet_ids | List of private subnet IDs | ["subnet-03e54a5f7dbd99d1f", "subnet-071e9043ea8d2fc5c"] |
| public_subnet_ids | List of public subnet IDs | ["subnet-0e7b1550eb74df381", "subnet-08cdfcae24fcca760"] |
| security_group_ids | Security group ID | sg-0fcf3e2a4d6d9a481 |
