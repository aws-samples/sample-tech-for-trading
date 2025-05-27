provider "aws" {
  region  = var.aws_region
}

provider "random" {}

# Generate random suffix for resource names
resource "random_id" "suffix" {
  byte_length = 4
}

# Define local values
locals {
  name_suffix = random_id.suffix.hex
}

# Reference the networking state
data "terraform_remote_state" "networking" {
  backend = "s3"
  config = {
    bucket = trimspace(file("${path.module}/../terraform_state_bucket.txt"))
    key    = "terraform/1-networking/terraform.tfstate"
    region = var.aws_region
  }
}

# Reference the shared layers and signing profile from the 0-prepare module
data "terraform_remote_state" "shared_layers" {
  backend = "s3"
  config = {
    bucket = trimspace(file("${path.module}/../terraform_state_bucket.txt"))
    key    = "terraform/0-prepare/terraform.tfstate"
    region = var.aws_region
  }
}

# Reference the Clickhouse secrets from 2-clickhouse
data "terraform_remote_state" "clickhouse" {
  backend = "s3"
  config = {
    bucket = trimspace(file("${path.module}/../terraform_state_bucket.txt"))
    key    = "terraform/2-clickhouse/terraform.tfstate"
    region = var.aws_region
  }
}

# S3 bucket for storing SEC data
resource "aws_s3_bucket" "sec_data_bucket" {
  bucket = "djia-tickers-sec-${random_id.suffix.hex}"
  force_destroy = true
}

# S3 bucket-level Public Access Block configuration
resource "aws_s3_bucket_public_access_block" "sec_data_bucket" {
  bucket = aws_s3_bucket.sec_data_bucket.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "sec_data_bucket" {
  bucket = aws_s3_bucket.sec_data_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "sec_data_bucket" {
  bucket = aws_s3_bucket.sec_data_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# IAM role for sec_data_lambda
resource "aws_iam_role" "sec_data_lambda_role" {
  name = "sec_data_lambda_role_${random_id.suffix.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for sec_data_lambda to write to S3 and CloudWatch Logs
resource "aws_iam_policy" "sec_data_lambda_policy" {
  name        = "sec_data_lambda_policy_${random_id.suffix.hex}"
  description = "Policy for SEC data Lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          aws_s3_bucket.sec_data_bucket.arn,
          "${aws_s3_bucket.sec_data_bucket.arn}/*"
        ]
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ],
        Effect   = "Allow",
        Resource = "*"
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "sec_data_lambda_policy_attachment" {
  role       = aws_iam_role.sec_data_lambda_role.name
  policy_arn = aws_iam_policy.sec_data_lambda_policy.arn
}

# IAM role for extract_sec_lambda
resource "aws_iam_role" "extract_sec_lambda_role" {
  name = "extract_sec_lambda_role_${random_id.suffix.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for extract_sec_lambda to read from S3, access CloudWatch Logs, and access Secrets Manager
resource "aws_iam_policy" "extract_sec_lambda_policy" {
  name        = "extract_sec_lambda_policy_${random_id.suffix.hex}"
  description = "Policy for SEC data extraction Lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          aws_s3_bucket.sec_data_bucket.arn,
          "${aws_s3_bucket.sec_data_bucket.arn}/*"
        ]
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ],
        Effect   = "Allow",
        Resource = "*"
      },
      {
        Action = [
          "secretsmanager:GetSecretValue"
        ],
        Effect   = "Allow",
        Resource = [data.terraform_remote_state.clickhouse.outputs.clickhouse_secret_arn]
      },
      {
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ],
        Effect   = "Allow",
        Resource = [data.terraform_remote_state.clickhouse.outputs.kms_key_arn]
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "extract_sec_lambda_policy_attachment" {
  role       = aws_iam_role.extract_sec_lambda_role.name
  policy_arn = aws_iam_policy.extract_sec_lambda_policy.arn
}

# Create Lambda deployment package for sec_data_lambda
data "archive_file" "sec_data_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../../src/sec-filing/sec_data_lambda.py"
  output_path = "${path.module}/sec_data_lambda.zip"
}

# Create Lambda deployment package for extract_sec_lambda
data "archive_file" "extract_sec_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../../src/sec-filing/extract_sec_lambda.py"
  output_path = "${path.module}/extract_sec_lambda.zip"
}

# Upload unsigned Lambda code to S3
resource "aws_s3_object" "sec_data_lambda_unsigned" {
  bucket = data.terraform_remote_state.shared_layers.outputs.lambda_artifacts_bucket_name
  key    = "unsigned/sec_data_lambda-${random_id.suffix.hex}.zip"
  source = data.archive_file.sec_data_lambda_zip.output_path
  etag   = filemd5(data.archive_file.sec_data_lambda_zip.output_path)
}

# Upload unsigned Lambda code to S3
resource "aws_s3_object" "extract_sec_lambda_unsigned" {
  bucket = data.terraform_remote_state.shared_layers.outputs.lambda_artifacts_bucket_name
  key    = "unsigned/extract_sec_lambda-${random_id.suffix.hex}.zip"
  source = data.archive_file.extract_sec_lambda_zip.output_path
  etag   = filemd5(data.archive_file.extract_sec_lambda_zip.output_path)
}

# Sign the sec_data_lambda code
resource "aws_signer_signing_job" "sec_data_lambda_signing" {
  profile_name = data.terraform_remote_state.shared_layers.outputs.lambda_signing_profile_name

  source {
    s3 {
      bucket  = data.terraform_remote_state.shared_layers.outputs.lambda_artifacts_bucket_name
      key     = aws_s3_object.sec_data_lambda_unsigned.key
      version = aws_s3_object.sec_data_lambda_unsigned.version_id
    }
  }

  destination {
    s3 {
      bucket = data.terraform_remote_state.shared_layers.outputs.lambda_artifacts_bucket_name
      prefix = "signed/sec_data_lambda-${random_id.suffix.hex}"
    }
  }

  ignore_signing_job_failure = false
}

# Sign the extract_sec_lambda code
resource "aws_signer_signing_job" "extract_sec_lambda_signing" {
  profile_name = data.terraform_remote_state.shared_layers.outputs.lambda_signing_profile_name

  source {
    s3 {
      bucket  = data.terraform_remote_state.shared_layers.outputs.lambda_artifacts_bucket_name
      key     = aws_s3_object.extract_sec_lambda_unsigned.key
      version = aws_s3_object.extract_sec_lambda_unsigned.version_id
    }
  }

  destination {
    s3 {
      bucket = data.terraform_remote_state.shared_layers.outputs.lambda_artifacts_bucket_name
      prefix = "signed/extract_sec_lambda-${random_id.suffix.hex}"
    }
  }

  ignore_signing_job_failure = false
}

# Lambda function for SEC data collection
resource "aws_lambda_function" "sec_data_lambda" {
  function_name    = "sec_data_lambda-${random_id.suffix.hex}"
  role             = aws_iam_role.sec_data_lambda_role.arn
  handler          = "sec_data_lambda.lambda_handler"
  runtime          = "python3.12"
  timeout          = 600
  memory_size      = 256
  
  # Use the signed artifact
  s3_bucket        = data.terraform_remote_state.shared_layers.outputs.lambda_artifacts_bucket_name
  s3_key           = aws_signer_signing_job.sec_data_lambda_signing.signed_object[0].s3[0].key
  source_code_hash = data.archive_file.sec_data_lambda_zip.output_base64sha256
  
  # VPC configuration
  vpc_config {
    subnet_ids         = data.terraform_remote_state.networking.outputs.private_subnet_ids
    security_group_ids = [data.terraform_remote_state.networking.outputs.security_group_ids]
  }

  # Lambda code signing
  code_signing_config_arn = data.terraform_remote_state.shared_layers.outputs.lambda_code_signing_config_arn

  environment {
    variables = {
      DJIA_TICKERS = join(",", var.tickers)
      CIK_MAPPING  = jsonencode(var.cik_mapping)
      EMAIL        = var.email
      BUCKET_NAME  = aws_s3_bucket.sec_data_bucket.id
    }
  }

  depends_on = [aws_signer_signing_job.sec_data_lambda_signing]
}

# Lambda function for SEC data extraction
resource "aws_lambda_function" "extract_sec_lambda" {
  function_name    = "extract_sec_lambda-${random_id.suffix.hex}"
  role             = aws_iam_role.extract_sec_lambda_role.arn
  handler          = "extract_sec_lambda.lambda_handler"
  runtime          = "python3.12"
  timeout          = 600
  memory_size      = 512
  
  # Use the signed artifact
  s3_bucket        = data.terraform_remote_state.shared_layers.outputs.lambda_artifacts_bucket_name
  s3_key           = aws_signer_signing_job.extract_sec_lambda_signing.signed_object[0].s3[0].key
  source_code_hash = data.archive_file.extract_sec_lambda_zip.output_base64sha256
  
  # Use the ClickHouse layer
  layers = [data.terraform_remote_state.shared_layers.outputs.clickhouse_layer_arn]
  
  # VPC configuration
  vpc_config {
    subnet_ids         = data.terraform_remote_state.networking.outputs.private_subnet_ids
    security_group_ids = [data.terraform_remote_state.networking.outputs.security_group_ids]
  }

  # Lambda code signing
  code_signing_config_arn = data.terraform_remote_state.shared_layers.outputs.lambda_code_signing_config_arn

  environment {
    variables = {
      CLICKHOUSE_SECRET_ARN = data.terraform_remote_state.clickhouse.outputs.clickhouse_secret_arn
      CLICKHOUSE_HOST = data.terraform_remote_state.clickhouse.outputs.clickhouse_endpoint
      CLICKHOUSE_USER = data.terraform_remote_state.clickhouse.outputs.clickhouse_username
      CLICKHOUSE_DATABASE = var.clickhouse_db_name
      PYTHONPATH            = "/opt/python"
    }
  }

  depends_on = [aws_signer_signing_job.extract_sec_lambda_signing]
}
