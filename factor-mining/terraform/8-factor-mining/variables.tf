variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "resource_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "fm"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "factor_modeling"
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
