provider "aws" {
  region = var.aws_region
}

# Generate random ID for KMS alias
resource "random_id" "clickhouse" {
  byte_length = 4
}

# Read bucket name from file and trim whitespace
locals {
  bucket_name = trimspace(file("${path.module}/../terraform_state_bucket.txt"))
}

# Get networking outputs from remote state
data "terraform_remote_state" "networking" {
  backend = "s3"
  config = {
    bucket = local.bucket_name
    key    = "terraform/1-networking/terraform.tfstate"
    region = var.aws_region  # Use the region variable from variables.tf
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Generate a random password for Clickhouse
resource "random_password" "clickhouse_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
  min_lower        = 1
  min_upper        = 1
  min_numeric      = 1
  min_special      = 1
}

# Create a KMS key for encrypting the secret
resource "aws_kms_key" "clickhouse_secret_key" {
  description             = "KMS key for ClickHouse credentials encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  
  # Add a policy that defines who can use and manage the key
  policy = jsonencode({
    Version = "2012-10-17",
    Id      = "key-policy-1",
    Statement = [
      {
        Sid    = "Enable IAM User Permissions",
        Effect = "Allow",
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        Action   = "kms:*",
        Resource = "*"
      },
      {
        Sid    = "Allow use of the key for Secrets Manager",
        Effect = "Allow",
        Principal = {
          Service = "secretsmanager.amazonaws.com"
        },
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ],
        Resource = "*"
      },
      {
        Sid    = "Allow EC2 instance to use the key",
        Effect = "Allow",
        Principal = {
          AWS = module.clickhouse.instance_role_arn
        },
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ],
        Resource = "*"
      }
    ]
  })
  
  tags = {
    Name        = "${var.project_name}-clickhouse-secret-key"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}


# Create an alias for the KMS key
resource "aws_kms_alias" "clickhouse_secret_key_alias" {
  name          = "alias/${var.project_name}-${var.environment}-clickhouse-secret-key-${random_id.clickhouse.hex}"
  target_key_id = aws_kms_key.clickhouse_secret_key.key_id
}

resource "aws_secretsmanager_secret" "clickhouse_credentials" {
  name_prefix = "${var.project_name}-${var.environment}-clickhouse-credentials-"
  description = "ClickHouse database credentials"
  kms_key_id  = aws_kms_key.clickhouse_secret_key.arn

  tags = {
    Name        = "${var.project_name}-clickhouse-credentials"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# Store generated password in the secret
resource "aws_secretsmanager_secret_version" "clickhouse_credentials" {
  secret_id = aws_secretsmanager_secret.clickhouse_credentials.id
  secret_string = jsonencode({
    username = "default"
    password = random_password.clickhouse_password.result
  })
}

# Generate a new RSA key pair for SSH access
resource "tls_private_key" "clickhouse_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Create AWS key pair using the generated public key
resource "aws_key_pair" "clickhouse_key" {
  key_name   = "${var.project_name}-${var.environment}-clickhouse-keypair-${random_id.clickhouse.hex}"
  public_key = tls_private_key.clickhouse_key.public_key_openssh

  tags = {
    Name        = "${var.project_name}-${var.environment}-clickhouse-key"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# Save private key locally with restricted permissions
resource "local_file" "clickhouse_private_key" {
  content         = tls_private_key.clickhouse_key.private_key_pem
  filename        = "${path.module}/${var.project_name}-${var.environment}-clickhouse-key.pem"
  file_permission = "0600"
}

module "clickhouse" {
  source = "../modules/clickhouse"

  vpc_id              = data.terraform_remote_state.networking.outputs.vpc_id
  subnet_ids          = data.terraform_remote_state.networking.outputs.private_subnet_ids
  security_group_ids  = [data.terraform_remote_state.networking.outputs.security_group_ids]
  instance_type       = var.instance_type
  volume_size         = var.volume_size
  clickhouse_version  = var.clickhouse_version
  project_name        = var.project_name
  environment         = var.environment
  key_name            = aws_key_pair.clickhouse_key.key_name
  clickhouse_password = random_password.clickhouse_password.result
  secret_arn          = aws_secretsmanager_secret.clickhouse_credentials.arn
  kms_key_arn         = aws_kms_key.clickhouse_secret_key.arn
}
