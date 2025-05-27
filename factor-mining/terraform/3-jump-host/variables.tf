variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type for jump host"
  type        = string
  default     = "t3.micro"
}

variable "volume_size" {
  description = "EBS volume size in GB"
  type        = number
  default     = 40
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
