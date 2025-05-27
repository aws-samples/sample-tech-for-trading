variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type for Clickhouse"
  type        = string
  default     = "r6i.2xlarge"
}

variable "volume_size" {
  description = "EBS volume size in GB"
  type        = number
  default     = 100
}

variable "clickhouse_version" {
  description = "Clickhouse version"
  type        = string
  default     = "22.3.13.80"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "factor-mining"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}
