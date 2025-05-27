provider "aws" {
  region = var.aws_region
}

# Read the S3 bucket name from file
data "local_file" "tf_state_bucket" {
  filename = "${path.module}/../terraform_state_bucket.txt"
}

locals {
  tf_state_bucket = trimspace(data.local_file.tf_state_bucket.content)
}

# Generate random suffix for unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}

# Get networking details from remote state
data "terraform_remote_state" "networking" {
  backend = "s3"
  config = {
    bucket = local.tf_state_bucket
    key    = "terraform/1-networking/terraform.tfstate"
    region = var.aws_region
  }
}

# Get ClickHouse layer from remote state
data "terraform_remote_state" "prepare" {
  backend = "s3"
  config = {
    bucket = local.tf_state_bucket
    key    = "terraform/0-prepare/terraform.tfstate"
    region = var.aws_region
  }
}

# Get ClickHouse secrets from remote state
data "terraform_remote_state" "clickhouse" {
  backend = "s3"
  config = {
    bucket = local.tf_state_bucket
    key    = "terraform/2-clickhouse/terraform.tfstate"
    region = var.aws_region
  }
}

locals {
  app_name = "factor-mining-visualization-${random_id.suffix.hex}"
}

# Security Group for ALB
resource "aws_security_group" "alb" {
  name        = "alb-${local.app_name}"
  description = "Security group for ALB"
  vpc_id      = data.terraform_remote_state.networking.outputs.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "alb-${local.app_name}"
  }
}

# Using the default security group from networking module for ECS Tasks
# Adding a rule to allow traffic from ALB to the ECS tasks
resource "aws_security_group_rule" "ecs_tasks_ingress" {
  security_group_id        = data.terraform_remote_state.networking.outputs.security_group_ids
  type                     = "ingress"
  from_port                = 8501
  to_port                  = 8501
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  description              = "Allow traffic from ALB to Streamlit app"
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${local.app_name}-cluster"
}

# ECS Task Role
resource "aws_iam_role" "ecs_task_role" {
  name = "ecs-task-role-${random_id.suffix.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecs-task-execution-role-${random_id.suffix.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# Task Execution Role Policy
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Secrets Access Policy
resource "aws_iam_policy" "secrets_access" {
  name = "secrets-access-${random_id.suffix.hex}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [data.terraform_remote_state.clickhouse.outputs.clickhouse_secret_arn]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = [data.terraform_remote_state.clickhouse.outputs.kms_key_arn]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "secrets_access" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.secrets_access.arn
}

# ALB
resource "aws_lb" "main" {
  name               = "alb-${random_id.suffix.hex}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = data.terraform_remote_state.networking.outputs.public_subnet_ids
}

# ALB Target Group
resource "aws_lb_target_group" "app" {
  name        = "tg-${random_id.suffix.hex}"
  port        = 8501
  protocol    = "HTTP"
  vpc_id      = data.terraform_remote_state.networking.outputs.vpc_id
  target_type = "ip"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 10
  }
}

# ALB Listener
resource "aws_lb_listener" "front_end" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# ECR Repository
resource "aws_ecr_repository" "app" {
  name = local.app_name
  force_delete = true
}

# ECS Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = local.app_name
  network_mode            = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                     = var.task_cpu
  memory                  = var.task_memory
  execution_role_arn      = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = local.app_name
      image = "${aws_ecr_repository.app.repository_url}:latest"
      portMappings = [
        {
          containerPort = 8501
          hostPort      = 8501
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "CLICKHOUSE_HOST"
          value = var.clickhouse_host
        },
        {
          name  = "CLICKHOUSE_PORT"
          value = tostring(var.clickhouse_port)
        },
        {
          name  = "CLICKHOUSE_DATABASE"
          value = var.clickhouse_database
        }
      ]
      secrets = [
        {
          name      = "CLICKHOUSE_SECRET_ARN"
          valueFrom = data.terraform_remote_state.clickhouse.outputs.clickhouse_secret_arn
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.app_name}"
  retention_in_days = 30
}

# ECS Service
resource "aws_ecs_service" "app" {
  name            = "${local.app_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.service_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.terraform_remote_state.networking.outputs.private_subnet_ids
    security_groups  = [data.terraform_remote_state.networking.outputs.security_group_ids]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = local.app_name
    container_port   = 8501
  }

  depends_on = [aws_lb_listener.front_end]
}
