# Streamlit Module

This module creates a complete infrastructure for deploying Streamlit applications on AWS using ECS Fargate.

## Features

- ECR repository for the Docker image
- ECS Fargate cluster and service
- Application Load Balancer
- IAM roles with appropriate permissions
- Security groups and networking configuration

## Usage

```hcl
module "streamlit_app" {
  source = "../modules/streamlit"

  app_name        = "factor-mining-visualization"
  aws_region      = "us-east-1"
  vpc_id          = "vpc-12345678"
  subnet_ids      = ["subnet-12345678", "subnet-87654321"]
  
  task_cpu        = "1024"
  task_memory     = "2048"
  
  clickhouse_host     = "44.222.122.134"
  clickhouse_port     = 9000
  clickhouse_user     = "default"
  clickhouse_password = "clickhouse@aws"
  clickhouse_database = "factor_modeling_db"
  
  state_machine_arn = "arn:aws:states:us-east-1:123456789012:stateMachine:factor-modeling-workflow"
  
  tags = {
    Environment = "production"
    Project     = "factor-mining"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| app_name | Name of the Streamlit application | string | n/a | yes |
| aws_region | AWS region to deploy resources | string | n/a | yes |
| vpc_id | ID of the VPC | string | n/a | yes |
| subnet_ids | List of subnet IDs for the ECS service | list(string) | n/a | yes |
| container_port | Port exposed by the Streamlit container | number | 8501 | no |
| task_cpu | CPU units for the ECS task | string | "1024" | no |
| task_memory | Memory for the ECS task | string | "2048" | no |
| service_desired_count | Desired count of ECS tasks | number | 1 | no |
| clickhouse_host | Clickhouse host address | string | n/a | yes |
| clickhouse_port | Clickhouse port | number | 9000 | no |
| clickhouse_user | Clickhouse username | string | "default" | no |
| clickhouse_password | Clickhouse password | string | n/a | yes |
| clickhouse_database | Clickhouse database name | string | n/a | yes |
| state_machine_arn | ARN of the Step Function state machine | string | n/a | yes |
| tags | A map of tags to assign to resources | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| ecr_repository_url | URL of the ECR repository |
| ecs_cluster_name | Name of the ECS cluster |
| ecs_service_name | Name of the ECS service |
| load_balancer_dns | DNS name of the load balancer |
| application_url | URL to access the application |

## Dependencies

This module uses the following sub-modules:
- `../ecr`
- `../iam`
- `../alb`
- `../ecs-fargate`
