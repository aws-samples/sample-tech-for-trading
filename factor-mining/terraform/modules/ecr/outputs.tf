output "repository_url" {
  description = "The URL of the repository"
  value       = aws_ecr_repository.repository.repository_url
}

output "repository_arn" {
  description = "The ARN of the repository"
  value       = aws_ecr_repository.repository.arn
}

output "repository_name" {
  description = "The name of the repository"
  value       = aws_ecr_repository.repository.name
}

output "repository_registry_id" {
  description = "The registry ID where the repository was created"
  value       = aws_ecr_repository.repository.registry_id
}
