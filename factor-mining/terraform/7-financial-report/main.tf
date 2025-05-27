provider "aws" {
  region = var.aws_region
}

provider "random" {}

resource "random_id" "suffix" {
  byte_length = 4
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

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../../src/financial-report-processor/financial_report_processor.py"
  output_path = "${path.module}/financial_report_processor.zip"
}

# Upload unsigned Lambda code to S3
resource "aws_s3_object" "lambda_code_unsigned" {
  bucket = data.terraform_remote_state.shared_layers.outputs.lambda_artifacts_bucket_name
  key    = "unsigned/financial_report_processor-${random_id.suffix.hex}.zip"
  source = data.archive_file.lambda_zip.output_path
  etag   = filemd5(data.archive_file.lambda_zip.output_path)
}

# Sign the Lambda code
resource "aws_signer_signing_job" "lambda_code_signing" {
  profile_name = data.terraform_remote_state.shared_layers.outputs.lambda_signing_profile_name

  source {
    s3 {
      bucket  = data.terraform_remote_state.shared_layers.outputs.lambda_artifacts_bucket_name
      key     = aws_s3_object.lambda_code_unsigned.key
      version = aws_s3_object.lambda_code_unsigned.version_id
    }
  }

  destination {
    s3 {
      bucket = data.terraform_remote_state.shared_layers.outputs.lambda_artifacts_bucket_name
      prefix = "signed/financial_report_processor-${random_id.suffix.hex}"
    }
  }

  ignore_signing_job_failure = false
}

resource "aws_lambda_function" "financial_report_processor" {
  function_name    = "financial_report_processor-${random_id.suffix.hex}"
  
  # Use the signed artifact
  s3_bucket        = data.terraform_remote_state.shared_layers.outputs.lambda_artifacts_bucket_name
  s3_key           = aws_signer_signing_job.lambda_code_signing.signed_object[0].s3[0].key
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  role            = aws_iam_role.lambda_role.arn
  handler         = "financial_report_processor.lambda_handler"
  runtime         = "python3.12"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size
  
  vpc_config {
    subnet_ids         = data.terraform_remote_state.networking.outputs.private_subnet_ids
    security_group_ids = [data.terraform_remote_state.networking.outputs.security_group_ids]
  }

  layers = [
    data.terraform_remote_state.shared_layers.outputs.clickhouse_layer_arn,
    data.terraform_remote_state.shared_layers.outputs.pypdf_layer_arn
  ]

  environment {
    variables = {
      CLICKHOUSE_SECRET_ARN = data.terraform_remote_state.clickhouse.outputs.clickhouse_secret_arn
      CLICKHOUSE_HOST       = data.terraform_remote_state.clickhouse.outputs.clickhouse_endpoint
      CLICKHOUSE_USER   =  data.terraform_remote_state.clickhouse.outputs.clickhouse_username
      CLICKHOUSE_DATABASE = var.clickhouse_db_name
      PYTHONPATH           = "/opt/python"
      BEDROCK_MODEL_ID     = var.bedrock_model_id
      FINANCIAL_REPORTS_BUCKET = var.financial_reports_bucket_name
    }
  }

  # Lambda code signing
  code_signing_config_arn = data.terraform_remote_state.shared_layers.outputs.lambda_code_signing_config_arn

  depends_on = [aws_signer_signing_job.lambda_code_signing]

  tags = var.tags
}

# IAM role for the Lambda function
resource "aws_iam_role" "lambda_role" {
  name = "financial_report_processor_role-${random_id.suffix.hex}"

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

  tags = var.tags
}

# IAM policy for the Lambda function
resource "aws_iam_policy" "lambda_policy" {
  name        = "financial_report_processor_policy-${var.aws_region}-${random_id.suffix.hex}"
  description = "Policy for financial report processor Lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
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
      },
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ],
        Effect = "Allow",
        Resource = [
          "arn:aws:s3:::${var.financial_reports_bucket_name}",
          "arn:aws:s3:::${var.financial_reports_bucket_name}/*"
        ]
      },
      {
        Action = [
          "bedrock:InvokeModel"
        ],
        Effect = "Allow",
        Resource = "*"
      }
    ]
  })
}

# Attach the IAM policy to the IAM role
resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# Create S3 bucket for financial reports
resource "aws_s3_bucket" "financial_reports" {
  bucket = var.financial_reports_bucket_name
  tags   = var.tags
}

resource "aws_s3_bucket_server_side_encryption_configuration" "financial_reports" {
  bucket = aws_s3_bucket.financial_reports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "financial_reports" {
  bucket = aws_s3_bucket.financial_reports.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Configure S3 event notification to trigger Lambda when files are uploaded
resource "aws_s3_bucket_notification" "financial_reports_notification" {
  bucket = aws_s3_bucket.financial_reports.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.financial_report_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = ""
    filter_suffix       = ""
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

# Add permission for S3 to invoke the Lambda function
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.financial_report_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.financial_reports.arn
}

# Create Lambda code signing configuration
resource "aws_lambda_code_signing_config" "financial_report_signing_config" {
  description = "Code signing configuration for financial report processor"
  
  allowed_publishers {
    signing_profile_version_arns = [data.terraform_remote_state.shared_layers.outputs.lambda_signing_profile_arn]
  }

  policies {
    untrusted_artifact_on_deployment = "Warn"
  }
}
