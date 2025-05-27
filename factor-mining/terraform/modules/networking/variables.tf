variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a","us-east-1b"]
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
