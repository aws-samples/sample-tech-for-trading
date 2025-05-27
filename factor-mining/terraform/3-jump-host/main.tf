provider "aws" {
  region = var.aws_region
}

# Generate random ID for resources
resource "random_id" "jump_host" {
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
    region = var.aws_region
  }
}

# Get clickhouse outputs from remote state
data "terraform_remote_state" "clickhouse" {
  backend = "s3"
  config = {
    bucket = local.bucket_name
    key    = "terraform/2-clickhouse/terraform.tfstate"
    region = var.aws_region
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Generate a new RSA key pair for SSH access
resource "tls_private_key" "jump_host_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Create AWS key pair using the generated public key
resource "aws_key_pair" "jump_host_key" {
  key_name   = "${var.project_name}-${var.environment}-jump-host-keypair-${random_id.jump_host.hex}"
  public_key = tls_private_key.jump_host_key.public_key_openssh

  tags = {
    Name        = "${var.project_name}-${var.environment}-jump-host-key"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# Save private key locally with restricted permissions
resource "local_file" "jump_host_private_key" {
  content         = tls_private_key.jump_host_key.private_key_pem
  filename        = "${path.module}/${var.project_name}-${var.environment}-jump-host-key.pem"
  file_permission = "0600"
}

# Create IAM role for EC2 instance with Session Manager access
resource "aws_iam_role" "jump_host_role" {
  name = "${var.project_name}-${var.environment}-jump-host-role-${random_id.jump_host.hex}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          Service = "ec2.amazonaws.com"
        },
        Effect = "Allow",
        Sid    = ""
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-jump-host-role"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# Attach AmazonSSMManagedInstanceCore policy to the role for Session Manager access
resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.jump_host_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Create instance profile for the EC2 instance
resource "aws_iam_instance_profile" "jump_host_profile" {
  name = "${var.project_name}-${var.environment}-jump-host-profile-${random_id.jump_host.hex}"
  role = aws_iam_role.jump_host_role.name
}

# Get the latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Create the jump host EC2 instance
resource "aws_instance" "jump_host" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.jump_host_key.key_name
  subnet_id              = data.terraform_remote_state.networking.outputs.public_subnet_ids[0]
  vpc_security_group_ids = [data.terraform_remote_state.networking.outputs.security_group_ids]
  iam_instance_profile   = aws_iam_instance_profile.jump_host_profile.name

  root_block_device {
    volume_size = var.volume_size
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = <<-EOF
    #!/bin/bash
    dnf update -y
    dnf install -y mysql postgresql telnet nc
    
    # Install ClickHouse client
    curl https://clickhouse.com/ | sh
    
    # Add useful utilities
    dnf install -y htop tmux vim git
  EOF

  tags = {
    Name        = "${var.project_name}-${var.environment}-jump-host"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}
