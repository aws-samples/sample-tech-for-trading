output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = module.ecr.repository_url
}

output "batch_job_queue_arn" {
  description = "ARN of the AWS Batch job queue"
  value       = aws_batch_job_queue.factor_modeling.arn
}

output "batch_job_definition_arn" {
  description = "ARN of the AWS Batch job definition"
  value       = aws_batch_job_definition.factor_modeling.arn
}

output "batch_job_definition_name" {
  description = "Name of the AWS Batch job definition"
  value       = aws_batch_job_definition.factor_modeling.name
}

output "step_function_arn" {
  description = "ARN of the Step Function state machine"
  value       = module.step_functions.step_function_arn
}

output "step_function_name" {
  description = "Name of the Step Function state machine"
  value       = module.step_functions.step_function_name
}

output "vpc_id" {
  description = "ID of the VPC used"
  value       = data.terraform_remote_state.networking.outputs.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets used"
  value       = data.terraform_remote_state.networking.outputs.private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of the public subnets used"
  value       = data.terraform_remote_state.networking.outputs.public_subnet_ids
}
