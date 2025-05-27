output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = module.ecr.repository_url
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.ecs_fargate.cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = module.ecs_fargate.service_name
}

output "load_balancer_dns" {
  description = "DNS name of the load balancer"
  value       = module.alb.alb_dns_name
}

output "application_url" {
  description = "URL to access the application"
  value       = "http://${module.alb.alb_dns_name}"
}
