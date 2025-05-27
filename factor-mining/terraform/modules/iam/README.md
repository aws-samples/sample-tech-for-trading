# IAM Module

This module creates IAM roles and policies with optional policy attachments.

## Usage

### Basic Role with Managed Policies

```hcl
module "ecs_task_role" {
  source = "../modules/iam"

  role_name = "ecs-task-role"
  role_description = "Role for ECS tasks"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
    "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
  ]
  
  tags = {
    Environment = "production"
    Project     = "factor-mining"
  }
}
```

### Role with Custom Policy

```hcl
module "step_functions_role" {
  source = "../modules/iam"

  role_name = "step-functions-role"
  role_description = "Role for Step Functions"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
  
  create_policy = true
  policy_name = "step-functions-custom-policy"
  policy_description = "Custom policy for Step Functions"
  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "lambda:InvokeFunction",
          "batch:SubmitJob"
        ]
        Effect = "Allow"
        Resource = "*"
      }
    ]
  })
  
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
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
| role_name | Name of the IAM role | string | n/a | yes |
| role_description | Description of the IAM role | string | "" | no |
| assume_role_policy | Policy document for the assume role policy | string | n/a | yes |
| role_path | Path for the IAM role | string | "/" | no |
| max_session_duration | Maximum session duration in seconds | number | 3600 | no |
| create_policy | Whether to create a custom policy | bool | false | no |
| policy_name | Name of the IAM policy | string | "" | no |
| policy_description | Description of the IAM policy | string | "" | no |
| policy_document | Policy document for the IAM policy | string | "" | no |
| policy_path | Path for the IAM policy | string | "/" | no |
| managed_policy_arns | List of managed policy ARNs to attach to the role | list(string) | [] | no |
| tags | A map of tags to assign to resources | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| role_id | ID of the IAM role |
| role_name | Name of the IAM role |
| role_arn | ARN of the IAM role |
| policy_id | ID of the IAM policy |
| policy_name | Name of the IAM policy |
| policy_arn | ARN of the IAM policy |
