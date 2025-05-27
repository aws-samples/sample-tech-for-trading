output "clickhouse_endpoint" {
  description = "Endpoint for Clickhouse"
  value       = module.clickhouse.clickhouse_endpoint
}

output "clickhouse_port" {
  description = "Port for Clickhouse"
  value       = module.clickhouse.clickhouse_port
}

output "clickhouse_secret_arn" {
  description = "ARN of the secret containing Clickhouse credentials"
  value       = aws_secretsmanager_secret.clickhouse_credentials.arn
}

output "clickhouse_secret_name" {
  description = "Name of the secret containing Clickhouse credentials"
  value       = aws_secretsmanager_secret.clickhouse_credentials.name
}

output "clickhouse_username" {
  description = "Username for Clickhouse"
  value       = "default"
}

output "ssh_key_name" {
  description = "Name of the SSH key pair created for Clickhouse instance"
  value       = aws_key_pair.clickhouse_key.key_name
}

output "ssh_private_key_path" {
  description = "Path to the private key file for SSH access"
  value       = local_file.clickhouse_private_key.filename
  sensitive   = true
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for encrypting the secret"
  value       = aws_kms_key.clickhouse_secret_key.arn
}
