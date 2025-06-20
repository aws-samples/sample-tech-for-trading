variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-west-2"
}

variable "financial_reports_bucket_name" {
  description = "Name of the S3 bucket to store financial reports"
  type        = string
}


variable "clickhouse_db_name" {
  description = "clickhouse db name"
  type        = string
  default     = "factor_modeling_db"
}


variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID"
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 512
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {
    Project = "Factor Mining Platform"
  }
}
