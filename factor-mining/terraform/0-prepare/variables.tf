variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-west-2"
}

variable "clickhouse_layer_zip_path" {
  description = "Path to the pre-existing Clickhouse driver layer zip file"
  type        = string
  default     = "./clickhouse-driver-layer.zip"
}

variable "pypdf_layer_zip_path" {
  description = "Path to the pre-existing PyPDF layer zip file"
  type        = string
  default     = "./PyPDF-layer.zip"
}

variable "yfinance_layer_zip_path" {
  description = "Path to the pre-existing yfinance layer zip file"
  type        = string
  default     = "./yfinance-layer.zip"
}

variable "lambda_artifacts_bucket_name" {
  description = "Name of the S3 bucket to store Lambda artifacts"
  type        = string
  default     = "factor-mining-lambda-artifacts"
}


variable "code_signing_profile_name" {
  description = "Name of the code_signing_profile_name"
  type        = string
  default     = "factor-mining-lambda-signer"
}

variable "enable_code_signing" {
  description = "Enable code signing for Lambda functions and layers"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "Factor Mining"
    Environment = "Development"
    ManagedBy   = "Terraform"
    Component   = "Shared Layers"
  }
}
