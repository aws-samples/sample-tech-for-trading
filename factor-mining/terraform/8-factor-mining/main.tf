provider "aws" {
  region = var.aws_region
}

provider "random" {}

resource "random_id" "suffix" {
  byte_length = 4
}

# Use remote state to get networking resources from 1-networking
data "terraform_remote_state" "networking" {
  backend = "s3"
  
  config = {
    bucket = trimspace(file("${path.module}/../terraform_state_bucket.txt"))
    key    = "terraform/1-networking/terraform.tfstate"
    region = var.aws_region
  }
}

# Use remote state to get Clickhouse resources from 2-clickhouse
data "terraform_remote_state" "clickhouse" {
  backend = "s3"
  
  config = {
    bucket = trimspace(file("${path.module}/../terraform_state_bucket.txt"))
    key    = "terraform/2-clickhouse/terraform.tfstate"
    region = var.aws_region
  }
}

# ECR Repository for storing our Docker image using the ECR module
module "ecr" {
  source = "../modules/ecr"

  repository_name      = "${var.resource_prefix}-${var.ecr_repository_name}"
  image_tag_mutability = "MUTABLE"
  scan_on_push         = true
  enable_lifecycle_policy = true
  max_image_count      = 30
  
  tags = {
    Name        = "${var.resource_prefix}-${var.ecr_repository_name}"
    Environment = var.environment
  }
}

# IAM Role for AWS Batch service
resource "aws_iam_role" "batch_service_role" {
  name = "${var.resource_prefix}-batch-service-role-${random_id.suffix.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "batch.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "batch_service_role_policy" {
  role       = aws_iam_role.batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

# Add additional policy for ECS cluster deletion
resource "aws_iam_policy" "batch_ecs_policy" {
  name        = "${var.resource_prefix}-batch-ecs-policy-${random_id.suffix.hex}"
  description = "Policy for AWS Batch to manage ECS clusters"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ecs:DeleteCluster",
          "ecs:DescribeClusters"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "batch_ecs_policy_attachment" {
  role       = aws_iam_role.batch_service_role.name
  policy_arn = aws_iam_policy.batch_ecs_policy.arn
}

# IAM Role for ECS instances
resource "aws_iam_role" "ecs_instance_role" {
  name = "${var.resource_prefix}-ecs-instance-role-${random_id.suffix.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_instance_role_policy" {
  role       = aws_iam_role.ecs_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "ecs_instance_profile" {
  name = "${var.resource_prefix}-ecs-instance-profile-${random_id.suffix.hex}"
  role = aws_iam_role.ecs_instance_role.name
}

# IAM Role for Batch job execution
resource "aws_iam_role" "batch_job_role" {
  name = "${var.resource_prefix}-batch-job-role-${random_id.suffix.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "batch_job_policy" {
  name        = "${var.resource_prefix}-batch-job-policy-${random_id.suffix.hex}"
  description = "Policy for batch job to access Secrets Manager and KMS"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Effect   = "Allow"
        Resource = [data.terraform_remote_state.clickhouse.outputs.clickhouse_secret_arn]
      },
      {
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Effect   = "Allow"
        Resource = [data.terraform_remote_state.clickhouse.outputs.kms_key_arn]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "batch_job_role_policy" {
  role       = aws_iam_role.batch_job_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "batch_job_secrets_policy" {
  role       = aws_iam_role.batch_job_role.name
  policy_arn = aws_iam_policy.batch_job_policy.arn
}

# AWS Batch Compute Environment
resource "aws_batch_compute_environment" "factor_modeling" {
  compute_environment_name = "${var.resource_prefix}-factor-modeling-env-${random_id.suffix.hex}"
  type                     = "MANAGED"
  state                    = "ENABLED"
  service_role             = aws_iam_role.batch_service_role.arn

  compute_resources {
    type                = "FARGATE"
    max_vcpus           = 16
    security_group_ids  = [data.terraform_remote_state.networking.outputs.security_group_ids]
    subnets             = data.terraform_remote_state.networking.outputs.private_subnet_ids
  }
}

# AWS Batch Job Queue
resource "aws_batch_job_queue" "factor_modeling" {
  name                 = "${var.resource_prefix}-factor-modeling-queue-${random_id.suffix.hex}"
  state                = "ENABLED"
  priority             = 1
  compute_environments = [aws_batch_compute_environment.factor_modeling.arn]
}

# AWS Batch Job Definition
resource "aws_batch_job_definition" "factor_modeling" {
  name                  = "${var.resource_prefix}-factor-modeling-job-${random_id.suffix.hex}"
  type                  = "container"
  platform_capabilities = ["FARGATE"]
  container_properties  = jsonencode({
    image = "${module.ecr.repository_url}:latest"
    fargatePlatformConfiguration = {
      platformVersion = "LATEST"
    }
    resourceRequirements = [
      {
        type  = "VCPU"
        value = "2"
      },
      {
        type  = "MEMORY"
        value = "4096"
      }
    ]
    executionRoleArn = aws_iam_role.batch_job_role.arn
    jobRoleArn = aws_iam_role.batch_job_role.arn
    command = ["python", "run_factor_analysis.py", "--batch-no", "Ref::batch_no", "--factor", "Ref::factor", "--tickers", "Ref::tickers", "--start-date", "Ref::start_date", "--end-date", "Ref::end_date"]
    networkConfiguration = {
      assignPublicIp = "ENABLED"
    }
    environment = [
      {
        name = "CLICKHOUSE_SECRET_ARN"
        value = data.terraform_remote_state.clickhouse.outputs.clickhouse_secret_arn
      }
    ]
  })

  parameters = {
    batch_no = "0"
    factor = "DE"
    tickers = "ALL"
    start_date = var.start_date
    end_date = var.end_date
  }
}

# Step Functions module for orchestrating the factor mining workflow
module "step_functions" {
  source = "../modules/step-functions"

  project_name = "${var.resource_prefix}-factor-mining-${random_id.suffix.hex}"
  environment = var.environment
  vpc_id = data.terraform_remote_state.networking.outputs.vpc_id
  subnet_ids = data.terraform_remote_state.networking.outputs.private_subnet_ids
  clickhouse_endpoint = data.terraform_remote_state.clickhouse.outputs.clickhouse_endpoint
  clickhouse_port = data.terraform_remote_state.clickhouse.outputs.clickhouse_port
  clickhouse_secret_arn = data.terraform_remote_state.clickhouse.outputs.clickhouse_secret_arn
  ecr_repository_url = module.ecr.repository_url
  batch_job_queue_arn = aws_batch_job_queue.factor_modeling.arn
  batch_job_definition_name = aws_batch_job_definition.factor_modeling.name
  tickers = var.tickers
  start_date = var.start_date
  end_date = var.end_date
  thread_no = var.thread_no
  parallel_m = var.parallel_m
  aws_region = var.aws_region
}
