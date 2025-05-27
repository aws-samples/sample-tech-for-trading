# Application Load Balancer (ALB) Module

This module creates an AWS Application Load Balancer with target group and listeners.

## Usage

```hcl
module "alb" {
  source = "../modules/alb"

  name               = "my-app-alb"
  internal           = false
  security_group_ids = [aws_security_group.alb_sg.id]
  subnet_ids         = ["subnet-12345678", "subnet-87654321"]
  vpc_id             = "vpc-12345678"
  
  target_port     = 8080
  target_protocol = "HTTP"
  target_type     = "ip"
  
  health_check_path = "/health"
  
  # Optional HTTPS configuration
  enable_https    = true
  certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/abcd1234-ef56-gh78-ij90-klmnopqrstuv"
  
  tags = {
    Environment = "production"
    Project     = "factor-mining"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| name | Name of the ALB | string | n/a | yes |
| internal | Whether the ALB is internal | bool | false | no |
| security_group_ids | List of security group IDs for the ALB | list(string) | n/a | yes |
| subnet_ids | List of subnet IDs for the ALB | list(string) | n/a | yes |
| vpc_id | ID of the VPC | string | n/a | yes |
| enable_deletion_protection | Whether to enable deletion protection for the ALB | bool | false | no |
| idle_timeout | The time in seconds that the connection is allowed to be idle | number | 60 | no |
| enable_access_logs | Whether to enable access logs | bool | false | no |
| access_logs_bucket | S3 bucket for access logs | string | null | no |
| access_logs_prefix | S3 bucket prefix for access logs | string | null | no |
| target_port | Port for the target group | number | n/a | yes |
| target_protocol | Protocol for the target group | string | "HTTP" | no |
| target_type | Type of target for the target group | string | "ip" | no |
| health_check_interval | Interval between health checks | number | 30 | no |
| health_check_path | Path for health checks | string | "/" | no |
| health_check_port | Port for health checks | string | "traffic-port" | no |
| health_check_healthy_threshold | Number of consecutive successful health checks required for a healthy target | number | 3 | no |
| health_check_unhealthy_threshold | Number of consecutive failed health checks required for an unhealthy target | number | 3 | no |
| health_check_timeout | Timeout for health checks | number | 5 | no |
| health_check_protocol | Protocol for health checks | string | "HTTP" | no |
| health_check_matcher | HTTP codes to use when checking for a successful response from a target | string | "200" | no |
| deregistration_delay | Time to wait before deregistering a target | number | 300 | no |
| listener_port | Port for the listener | number | 80 | no |
| listener_protocol | Protocol for the listener | string | "HTTP" | no |
| enable_https | Whether to enable HTTPS | bool | false | no |
| ssl_policy | SSL policy for HTTPS listener | string | "ELBSecurityPolicy-2016-08" | no |
| certificate_arn | ARN of the SSL certificate for HTTPS | string | null | no |
| tags | A map of tags to assign to resources | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| alb_id | ID of the ALB |
| alb_arn | ARN of the ALB |
| alb_dns_name | DNS name of the ALB |
| alb_zone_id | Zone ID of the ALB |
| target_group_arn | ARN of the target group |
| target_group_name | Name of the target group |
| http_listener_arn | ARN of the HTTP listener |
| https_listener_arn | ARN of the HTTPS listener |
