output "step_function_arn" {
  description = "ARN of the Step Function state machine"
  value       = aws_sfn_state_machine.factor_modeling_workflow.arn
}

output "step_function_name" {
  description = "Name of the Step Function state machine"
  value       = aws_sfn_state_machine.factor_modeling_workflow.name
}

output "lambda_role_arn" {
  description = "ARN of the Lambda IAM role"
  value       = aws_iam_role.lambda_role.arn
}

output "step_function_role_arn" {
  description = "ARN of the Step Function IAM role"
  value       = aws_iam_role.step_function_role.arn
}
