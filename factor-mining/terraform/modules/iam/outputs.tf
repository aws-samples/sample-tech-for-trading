output "role_id" {
  description = "ID of the IAM role"
  value       = aws_iam_role.role.id
}

output "role_name" {
  description = "Name of the IAM role"
  value       = aws_iam_role.role.name
}

output "role_arn" {
  description = "ARN of the IAM role"
  value       = aws_iam_role.role.arn
}

output "policy_id" {
  description = "ID of the IAM policy"
  value       = var.create_policy ? aws_iam_policy.policy[0].id : null
}

output "policy_name" {
  description = "Name of the IAM policy"
  value       = var.create_policy ? aws_iam_policy.policy[0].name : null
}

output "policy_arn" {
  description = "ARN of the IAM policy"
  value       = var.create_policy ? aws_iam_policy.policy[0].arn : null
}
