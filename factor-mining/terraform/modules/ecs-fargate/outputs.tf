output "cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.cluster.id
}

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.cluster.name
}

output "cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.cluster.arn
}

output "service_id" {
  description = "ID of the ECS service"
  value       = aws_ecs_service.service.id
}

output "service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.service.name
}

output "task_definition_arn" {
  description = "ARN of the task definition"
  value       = aws_ecs_task_definition.task.arn
}

output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.logs.name
}
