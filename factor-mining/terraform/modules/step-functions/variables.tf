variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "subnet_ids" {
  description = "IDs of the subnets"
  type        = list(string)
}

variable "clickhouse_endpoint" {
  description = "Endpoint for Clickhouse"
  type        = string
}

variable "clickhouse_port" {
  description = "Port for Clickhouse"
  type        = number
}

variable "clickhouse_secret_arn" {
  description = "ARN of the Secrets Manager secret containing Clickhouse credentials"
  type        = string
}

variable "batch_compute_type" {
  description = "AWS Batch compute type"
  type        = string
  default     = "FARGATE"
}

variable "batch_vcpus" {
  description = "vCPUs for batch jobs"
  type        = number
  default     = 4
}

variable "batch_memory" {
  description = "Memory for batch jobs in MB"
  type        = number
  default     = 16384
}

variable "tickers" {
  description = "List of tickers to analyze"
  type        = string
  default     = "AAPL,AMGN,AMZN,AXP,BA,CAT,CRM,CSCO,CVX,DIS,GS,HD,HON,IBM,JNJ,JPM,KO,MCD,MMM,MRK,MSFT,NKE,NVDA,PG,SHW,TRV,UNH,V,VZ,WMT"
}

variable "start_date" {
  description = "Start date for analysis"
  type        = string
  default     = "2020-01-01"
}

variable "end_date" {
  description = "End date for analysis"
  type        = string
  default     = "2023-01-01"
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

variable "ecr_repository_url" {
  description = "URL of the ECR repository containing the factor mining Docker image"
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "batch_job_queue_arn" {
  description = "ARN of the AWS Batch job queue"
  type        = string
}

variable "batch_job_definition_name" {
  description = "Name of the AWS Batch job definition"
  type        = string
  default     = "fm-factor-modeling-job"
}

variable "thread_no" {
  description = "Number of date range segments for parallel processing"
  type        = number
  default     = 5
}

variable "parallel_m" {
  description = "Number of ticker groups for parallel processing"
  type        = number
  default     = 6
}
