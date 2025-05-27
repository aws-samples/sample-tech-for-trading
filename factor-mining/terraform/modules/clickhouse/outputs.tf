output "clickhouse_endpoint" {
  description = "Endpoint for Clickhouse"
  value       = aws_instance.clickhouse.private_dns
}

output "clickhouse_public_endpoint" {
  description = "Public endpoint for Clickhouse"
  value       = aws_instance.clickhouse.public_dns
}

output "clickhouse_port" {
  description = "Port for Clickhouse HTTP interface"
  value       = 8123
}

output "clickhouse_native_port" {
  description = "Port for Clickhouse native interface"
  value       = 9000
}

output "clickhouse_instance_id" {
  description = "ID of the Clickhouse EC2 instance"
  value       = aws_instance.clickhouse.id
}

output "instance_role_arn" {
  description = "ARN of the IAM role attached to the ClickHouse instance"
  value       = aws_iam_role.clickhouse_role.arn
}
