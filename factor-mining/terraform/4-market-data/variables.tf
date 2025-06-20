variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}


variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300
}

variable "clickhouse_db_name" {
  description = "clickhouse db name"
  type        = string
  default     = "factor_modeling_db"
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 512
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "Factor Mining"
    Environment = "Development"
    ManagedBy   = "Terraform"
    Component   = "Market Data"
  }
}
