provider "aws" {
  region = var.aws_region
}

# Read the terraform state bucket name from file
data "local_file" "terraform_state_bucket" {
  filename = "${path.module}/../terraform_state_bucket.txt"
}

locals {
  terraform_state_bucket = trimspace(data.local_file.terraform_state_bucket.content)
  s3_bucket_name         = "${var.s3_bucket_prefix}-${random_string.bucket_suffix.result}"
}

# Get networking information from remote state
data "terraform_remote_state" "networking" {
  backend = "s3"
  config = {
    bucket  = local.terraform_state_bucket
    key     = "terraform/1-networking/terraform.tfstate"
    region  = var.aws_region
  }
}

# Get lambda signing profile from prepare module
data "terraform_remote_state" "prepare" {
  backend = "s3"
  config = {
    bucket  = local.terraform_state_bucket
    key     = "terraform/0-prepare/terraform.tfstate"
    region  = var.aws_region
  }
}

# Random string for S3 bucket name uniqueness
resource "random_string" "bucket_suffix" {
  length  = 4
  special = false
  upper   = false
}

# Random ID for resource uniqueness
resource "random_id" "resource_suffix" {
  byte_length = 4
}

# S3 bucket for storing news data
resource "aws_s3_bucket" "news_bucket" {
  bucket = local.s3_bucket_name
  
  # Prevent errors when deleting non-empty buckets
  lifecycle {
    prevent_destroy = false
    ignore_changes = [force_destroy]
  }
}

# Use a local to reference the bucket ID
locals {
  bucket_id = aws_s3_bucket.news_bucket.id
}

# S3 bucket lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "news_bucket_lifecycle" {
  bucket = local.bucket_id

  # Rule for incomplete multipart uploads
  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 5
    }
  }

  # Standard lifecycle rule for objects
  rule {
    id     = "standard-objects-lifecycle"
    status = "Enabled"

    # Optional: Set expiration for objects if needed
    expiration {
      days = 365 # Example: expire objects after 1 year
    }

    # Optional: Transition objects to different storage classes
    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
  }
}

resource "aws_s3_bucket_ownership_controls" "news_bucket" {
  bucket = local.bucket_id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "news_bucket" {
  depends_on = [aws_s3_bucket_ownership_controls.news_bucket]
  bucket     = local.bucket_id
  acl        = "private"
}

# Store Tavily API key in Secrets Manager
resource "aws_secretsmanager_secret" "tavily_api_key" {
  name        = "TAVILY_API_KEY_${random_string.bucket_suffix.result}"
  description = "API Key for Tavily web search service"
  
  # Handle the case where the secret is scheduled for deletion
  recovery_window_in_days = 0  # Immediately delete without recovery window
  force_overwrite_replica_secret = true
}

# Use a local to reference the secret ID
locals {
  secret_id = aws_secretsmanager_secret.tavily_api_key.id
}

resource "aws_secretsmanager_secret_version" "tavily_api_key" {
  secret_id     = local.secret_id
  secret_string = var.tavily_api_key != "" ? var.tavily_api_key : "dummy-api-key-for-testing"
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "stock_news_lambda_role_${random_id.resource_suffix.hex}"

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

# Use a local to reference the role ARN
locals {
  role_arn = aws_iam_role.lambda_role.arn
}

# IAM policy for Lambda to write to S3, access Secrets Manager, and CloudWatch Logs
resource "aws_iam_policy" "lambda_policy" {
  name        = "stock_news_lambda_policy_${random_id.resource_suffix.hex}"
  description = "Policy for stock news Lambda function"

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
          "arn:aws:s3:::${local.bucket_id}",
          "arn:aws:s3:::${local.bucket_id}/*"
        ]
      },
      {
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Effect   = "Allow"
        Resource = [
          aws_secretsmanager_secret.tavily_api_key.arn
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
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# Create Lambda deployment package
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/web-search"
  output_path = "${path.module}/lambda_function.zip"
}

# Upload unsigned Lambda code to S3
resource "aws_s3_object" "lambda_code_unsigned" {
  bucket = data.terraform_remote_state.prepare.outputs.lambda_artifacts_bucket_name
  key    = "unsigned/stock_news_fetcher-${random_id.resource_suffix.hex}.zip"
  source = data.archive_file.lambda_zip.output_path
  etag   = filemd5(data.archive_file.lambda_zip.output_path)
}

# Sign the Lambda code
resource "aws_signer_signing_job" "lambda_code_signing" {
  profile_name = data.terraform_remote_state.prepare.outputs.lambda_signing_profile_name

  source {
    s3 {
      bucket  = data.terraform_remote_state.prepare.outputs.lambda_artifacts_bucket_name
      key     = aws_s3_object.lambda_code_unsigned.key
      version = aws_s3_object.lambda_code_unsigned.version_id
    }
  }

  destination {
    s3 {
      bucket = data.terraform_remote_state.prepare.outputs.lambda_artifacts_bucket_name
      prefix = "signed/stock_news_fetcher-${random_id.resource_suffix.hex}"
    }
  }

  ignore_signing_job_failure = false
}

# Lambda function
resource "aws_lambda_function" "stock_news_lambda" {
  function_name    = "stock_news_fetcher-${random_id.resource_suffix.hex}"
  
  # Use the signed artifact
  s3_bucket        = data.terraform_remote_state.prepare.outputs.lambda_artifacts_bucket_name
  s3_key           = aws_signer_signing_job.lambda_code_signing.signed_object[0].s3[0].key
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  role            = local.role_arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.12"
  timeout         = 60
  memory_size     = 256
  
  # Lambda code signing
  code_signing_config_arn = data.terraform_remote_state.prepare.outputs.lambda_code_signing_config_arn

  environment {
    variables = {
      S3_BUCKET           = local.bucket_id
      TAVILY_API_KEY_NAME = aws_secretsmanager_secret.tavily_api_key.name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_policy_attachment,
    aws_signer_signing_job.lambda_code_signing
  ]
}

# EventBridge rule to trigger Lambda daily
resource "aws_cloudwatch_event_rule" "daily_trigger" {
  name                = "daily-stock-news-trigger-${random_id.resource_suffix.hex}"
  description         = "Triggers stock news Lambda function daily"
  schedule_expression = "cron(0 0 * * ? *)" # Run at midnight UTC every day
}

# Single EventBridge target that passes ticker as input
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_trigger.name
  target_id = "stock_news_lambda"
  arn       = aws_lambda_function.stock_news_lambda.arn
  
  input = jsonencode({
    tickers = var.tickers
    date    = "$${aws:CurrentDate}"  # This will be resolved at runtime to the current date
  })
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stock_news_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_trigger.arn
}

# Outputs
output "s3_bucket_name" {
  value = local.bucket_id
}

output "lambda_function_name" {
  value = aws_lambda_function.stock_news_lambda.function_name
}

output "eventbridge_rule_name" {
  value = aws_cloudwatch_event_rule.daily_trigger.name
}
