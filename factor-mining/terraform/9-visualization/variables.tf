variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "clickhouse_host" {
  description = "Clickhouse host address"
  type        = string
}

variable "clickhouse_port" {
  description = "Clickhouse port"
  type        = number
  default     = 9000
}

variable "clickhouse_database" {
  description = "Clickhouse database name"
  type        = string
  default     = "factor_modeling_db"
}

variable "task_cpu" {
  description = "CPU units for the ECS task"
  type        = string
  default     = "1024"
}

variable "task_memory" {
  description = "Memory for the ECS task"
  type        = string
  default     = "2048"
}

variable "service_desired_count" {
  description = "Desired count of ECS tasks"
  type        = number
  default     = 1
}
