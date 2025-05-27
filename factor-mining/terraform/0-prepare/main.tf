provider "aws" {
  region = var.aws_region

  # Make it faster by skipping something
  skip_metadata_api_check     = true
  skip_region_validation      = true
  skip_credentials_validation = true
}

################################################################################
# Code Signing Configuration
################################################################################

resource "aws_signer_signing_profile" "lambda_signing_profile" {
  platform_id = "AWSLambda-SHA384-ECDSA"
  name        = replace("${var.code_signing_profile_name}", "-", "")
  tags        = var.tags

  signature_validity_period {
    value = 12
    type  = "MONTHS"
  }
}

resource "aws_lambda_code_signing_config" "lambda_code_signing" {
  allowed_publishers {
    signing_profile_version_arns = [aws_signer_signing_profile.lambda_signing_profile.version_arn]
  }

  policies {
    untrusted_artifact_on_deployment = "Enforce"
  }

  description = "Code signing configuration for Factor Mining Lambda functions"
}

################################################################################
# S3 Bucket for Lambda Artifacts
################################################################################

resource "aws_s3_bucket" "lambda_artifacts" {
  bucket        = var.lambda_artifacts_bucket_name
  force_destroy = true  # This allows Terraform to delete the bucket even when it contains objects
  tags          = var.tags
}

resource "aws_s3_bucket_versioning" "lambda_artifacts_versioning" {
  bucket = aws_s3_bucket.lambda_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lambda_artifacts_encryption" {
  bucket = aws_s3_bucket.lambda_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "lambda_artifacts_public_access_block" {
  bucket = aws_s3_bucket.lambda_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

################################################################################
# Clickhouse Driver Lambda Layer
################################################################################

# Upload unsigned layer to S3
resource "aws_s3_object" "clickhouse_layer_unsigned" {
  bucket = aws_s3_bucket.lambda_artifacts.id
  key    = "unsigned/clickhouse-driver-layer.zip"
  source = var.clickhouse_layer_zip_path
  etag   = filemd5(var.clickhouse_layer_zip_path)

  # Ensure S3 bucket is properly configured before uploading
  depends_on = [
    aws_s3_bucket_versioning.lambda_artifacts_versioning,
    aws_s3_bucket_server_side_encryption_configuration.lambda_artifacts_encryption,
    aws_s3_bucket_public_access_block.lambda_artifacts_public_access_block
  ]
}

# Sign the layer
resource "aws_signer_signing_job" "clickhouse_layer_signing" {
  profile_name = aws_signer_signing_profile.lambda_signing_profile.name

  source {
    s3 {
      bucket  = aws_s3_bucket.lambda_artifacts.id
      key     = aws_s3_object.clickhouse_layer_unsigned.key
      version = aws_s3_object.clickhouse_layer_unsigned.version_id
    }
  }

  destination {
    s3 {
      bucket = aws_s3_bucket.lambda_artifacts.id
      prefix = "signed/"
    }
  }

  ignore_signing_job_failure = false
}

# Create the Lambda layer using the signed artifact
resource "aws_lambda_layer_version" "clickhouse_layer" {
  layer_name          = "clickhouse-driver-layer"
  description         = "Layer containing Clickhouse driver and dependencies"
  compatible_runtimes = ["python3.12"]
  
  s3_bucket           = aws_s3_bucket.lambda_artifacts.id
  s3_key              = aws_signer_signing_job.clickhouse_layer_signing.signed_object[0].s3[0].key
  
  # Ensure the signing job completes before creating the layer
  depends_on = [aws_signer_signing_job.clickhouse_layer_signing]
}

################################################################################
# PyPDF Lambda Layer
################################################################################

# Upload unsigned layer to S3
resource "aws_s3_object" "pypdf_layer_unsigned" {
  bucket = aws_s3_bucket.lambda_artifacts.id
  key    = "unsigned/PyPDF-layer.zip"
  source = var.pypdf_layer_zip_path
  etag   = filemd5(var.pypdf_layer_zip_path)

  # Ensure S3 bucket is properly configured before uploading
  depends_on = [
    aws_s3_bucket_versioning.lambda_artifacts_versioning,
    aws_s3_bucket_server_side_encryption_configuration.lambda_artifacts_encryption,
    aws_s3_bucket_public_access_block.lambda_artifacts_public_access_block
  ]
}

# Sign the layer
resource "aws_signer_signing_job" "pypdf_layer_signing" {
  profile_name = aws_signer_signing_profile.lambda_signing_profile.name

  source {
    s3 {
      bucket  = aws_s3_bucket.lambda_artifacts.id
      key     = aws_s3_object.pypdf_layer_unsigned.key
      version = aws_s3_object.pypdf_layer_unsigned.version_id
    }
  }

  destination {
    s3 {
      bucket = aws_s3_bucket.lambda_artifacts.id
      prefix = "signed/"
    }
  }

  ignore_signing_job_failure = false
}

# Create the Lambda layer using the signed artifact
resource "aws_lambda_layer_version" "pypdf_layer" {
  layer_name          = "pypdf-layer"
  description         = "Layer containing PyPDF and dependencies"
  compatible_runtimes = ["python3.12"]
  
  s3_bucket           = aws_s3_bucket.lambda_artifacts.id
  s3_key              = aws_signer_signing_job.pypdf_layer_signing.signed_object[0].s3[0].key
  
  # Ensure the signing job completes before creating the layer
  depends_on = [aws_signer_signing_job.pypdf_layer_signing]
}

################################################################################
# yfinance Lambda Layer
################################################################################

# Upload unsigned layer to S3
resource "aws_s3_object" "yfinance_layer_unsigned" {
  bucket = aws_s3_bucket.lambda_artifacts.id
  key    = "unsigned/yfinance-layer.zip"
  source = var.yfinance_layer_zip_path
  etag   = filemd5(var.yfinance_layer_zip_path)

  # Ensure S3 bucket is properly configured before uploading
  depends_on = [
    aws_s3_bucket_versioning.lambda_artifacts_versioning,
    aws_s3_bucket_server_side_encryption_configuration.lambda_artifacts_encryption,
    aws_s3_bucket_public_access_block.lambda_artifacts_public_access_block
  ]
}

# Sign the layer
resource "aws_signer_signing_job" "yfinance_layer_signing" {
  profile_name = aws_signer_signing_profile.lambda_signing_profile.name

  source {
    s3 {
      bucket  = aws_s3_bucket.lambda_artifacts.id
      key     = aws_s3_object.yfinance_layer_unsigned.key
      version = aws_s3_object.yfinance_layer_unsigned.version_id
    }
  }

  destination {
    s3 {
      bucket = aws_s3_bucket.lambda_artifacts.id
      prefix = "signed/"
    }
  }

  ignore_signing_job_failure = false
}

# Create the Lambda layer using the signed artifact
resource "aws_lambda_layer_version" "yfinance_layer" {
  layer_name          = "yfinance-layer"
  description         = "Layer containing yfinance and dependencies"
  compatible_runtimes = ["python3.12"]
  
  s3_bucket           = aws_s3_bucket.lambda_artifacts.id
  s3_key              = aws_signer_signing_job.yfinance_layer_signing.signed_object[0].s3[0].key
  
  # Ensure the signing job completes before creating the layer
  depends_on = [aws_signer_signing_job.yfinance_layer_signing]
}

################################################################################
# Outputs
################################################################################

output "clickhouse_layer_arn" {
  value       = aws_lambda_layer_version.clickhouse_layer.arn
  description = "ARN of the Clickhouse driver Lambda layer"
}

output "pypdf_layer_arn" {
  value       = aws_lambda_layer_version.pypdf_layer.arn
  description = "ARN of the PyPDF Lambda layer"
}

output "yfinance_layer_arn" {
  value       = aws_lambda_layer_version.yfinance_layer.arn
  description = "ARN of the yfinance Lambda layer"
}

output "lambda_signing_profile_arn" {
  value       = aws_signer_signing_profile.lambda_signing_profile.arn
  description = "ARN of the Lambda signing profile"
}

output "lambda_signing_profile_name" {
  value       = aws_signer_signing_profile.lambda_signing_profile.name
  description = "Name of the Lambda signing profile"
}

output "lambda_signing_profile_version_arn" {
  value       = aws_signer_signing_profile.lambda_signing_profile.version_arn
  description = "Version ARN of the Lambda signing profile"
}

output "lambda_code_signing_config_arn" {
  value       = aws_lambda_code_signing_config.lambda_code_signing.arn
  description = "ARN of the Lambda code signing configuration"
}

output "lambda_artifacts_bucket_name" {
  value       = aws_s3_bucket.lambda_artifacts.id
  description = "Name of the S3 bucket for Lambda artifacts"
}
