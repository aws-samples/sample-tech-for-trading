# Jump Host for ClickHouse Access

This module deploys an EC2 instance that serves as a jump host to access the ClickHouse database deployed in a private subnet.

## Features

- EC2 instance running Amazon Linux 2023 in a public subnet
- IAM role with Session Manager access
- SSH key pair for direct SSH access
- Pre-installed ClickHouse client and database utilities
- Security group configuration for secure access

## Prerequisites

- The networking module (1-networking) must be deployed first
- The ClickHouse module (2-clickhouse) must be deployed
- AWS CLI configured with appropriate permissions

## Deployment

1. Make sure you have the S3 bucket name in the `terraform_state_bucket.txt` file at the root of the project
2. Update `terraform.tfvars` with your desired configuration
3. Run the deployment script:

```bash
./deploy.sh
```

## Accessing the Jump Host

### Using SSH

```bash
ssh -i $(terraform output -raw ssh_key_path) ec2-user@$(terraform output -raw jump_host_public_ip)
```

## Connecting to ClickHouse from the Jump Host

Once connected to the jump host, you can access the ClickHouse instance using (passwrod is in secrets manager):

```bash
clickhouse client --host <clickhouse_private_ip> --port 9000 --user default --password
```

You can retrieve the ClickHouse private IP and credentials from the AWS Secrets Manager.
