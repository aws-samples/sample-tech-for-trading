# ECS Fargate Module

This module creates an Amazon ECS cluster with Fargate launch type, including task definition, service, and CloudWatch logs.

## Usage

```hcl
module "ecs_fargate" {
  source = "../modules/ecs-fargate"

  aws_region       = "us-east-1"
  cluster_name     = "my-app-cluster"
  service_name     = "my-app"
  container_name   = "my-app-container"
  container_image  = "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:latest"
  container_port   = 8080
  
  task_cpu         = "1024"
  task_memory      = "2048"
  
  execution_role_arn = aws_iam_role.ecs_execution_role.arn
  task_role_arn      = aws_iam_role.ecs_task_role.arn
  
  subnet_ids         = ["subnet-12345678", "subnet-87654321"]
  security_group_ids = [aws_security_group.ecs_sg.id]
  assign_public_ip   = true
  
  target_group_arn   = aws_lb_target_group.app.arn
  
  environment_variables = [
    {
      name  = "ENV"
      value = "production"
    },
    {
      name  = "LOG_LEVEL"
      value = "info"
    }
  ]
  
  tags = {
    Environment = "production"
    Project     = "factor-mining"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| aws_region | AWS region to deploy resources | string | n/a | yes |
| cluster_name | Name of the ECS cluster | string | n/a | yes |
| service_name | Name of the ECS service | string | n/a | yes |
| container_name | Name of the container | string | n/a | yes |
| container_image | Docker image for the container | string | n/a | yes |
| container_port | Port exposed by the container | number | n/a | yes |
| task_cpu | CPU units for the ECS task | string | "256" | no |
| task_memory | Memory for the ECS task | string | "512" | no |
| execution_role_arn | ARN of the IAM role for ECS task execution | string | n/a | yes |
| task_role_arn | ARN of the IAM role for the ECS task | string | n/a | yes |
| subnet_ids | List of subnet IDs for the ECS service | list(string) | n/a | yes |
| security_group_ids | List of security group IDs for the ECS service | list(string) | n/a | yes |
| assign_public_ip | Whether to assign a public IP to the task | bool | false | no |
| target_group_arn | ARN of the target group for the load balancer | string | null | no |
| desired_count | Desired count of ECS tasks | number | 1 | no |
| environment_variables | Environment variables for the container | list(object) | [] | no |
| enable_container_insights | Whether to enable CloudWatch Container Insights | bool | true | no |
| log_retention_days | Number of days to retain logs | number | 30 | no |
| health_check_grace_period_seconds | Grace period for health checks | number | 60 | no |
| enable_circuit_breaker | Whether to enable deployment circuit breaker | bool | true | no |
| enable_circuit_breaker_rollback | Whether to enable rollback on deployment failure | bool | true | no |
| tags | A map of tags to assign to resources | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| cluster_id | ID of the ECS cluster |
| cluster_name | Name of the ECS cluster |
| cluster_arn | ARN of the ECS cluster |
| service_id | ID of the ECS service |
| service_name | Name of the ECS service |
| task_definition_arn | ARN of the task definition |
| log_group_name | Name of the CloudWatch log group |
