variable "app_name" {
  description = "Name of the Streamlit application"
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the ECS service"
  type        = list(string)
}

variable "container_port" {
  description = "Port exposed by the Streamlit container"
  type        = number
  default     = 8501
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

variable "clickhouse_host" {
  description = "Clickhouse host address"
  type        = string
}

variable "clickhouse_port" {
  description = "Clickhouse port"
  type        = number
  default     = 9000
}

variable "clickhouse_user" {
  description = "Clickhouse username"
  type        = string
  default     = "default"
}

variable "clickhouse_password" {
  description = "Clickhouse password"
  type        = string
  sensitive   = true
}

variable "clickhouse_database" {
  description = "Clickhouse database name"
  type        = string
}

variable "state_machine_arn" {
  description = "ARN of the Step Function state machine"
  type        = string
}

variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}
