output "jump_host_id" {
  description = "ID of the jump host EC2 instance"
  value       = aws_instance.jump_host.id
}

output "jump_host_public_ip" {
  description = "Public IP address of the jump host"
  value       = aws_instance.jump_host.public_ip
}

output "jump_host_private_ip" {
  description = "Private IP address of the jump host"
  value       = aws_instance.jump_host.private_ip
}

output "jump_host_role_arn" {
  description = "ARN of the IAM role attached to the jump host"
  value       = aws_iam_role.jump_host_role.arn
}

output "ssh_key_path" {
  description = "Path to the SSH private key file"
  value       = local_file.jump_host_private_key.filename
}

output "ssh_command" {
  description = "SSH command to connect to the jump host"
  value       = "ssh -i ${local_file.jump_host_private_key.filename} ec2-user@${aws_instance.jump_host.public_ip}"
}

output "session_manager_command" {
  description = "AWS Systems Manager Session Manager command to connect to the jump host"
  value       = "aws ssm start-session --target ${aws_instance.jump_host.id}"
}
