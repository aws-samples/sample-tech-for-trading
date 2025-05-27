locals {
  app_name = var.app_name
}

# Create ECR Repository
module "ecr" {
  source = "../ecr"

  repository_name      = local.app_name
  image_tag_mutability = "MUTABLE"
  scan_on_push         = true
  
  enable_lifecycle_policy = true
  max_image_count         = 30
  
  tags = var.tags
}

# Create IAM roles
module "ecs_execution_role" {
  source = "../iam"

  role_name        = "${local.app_name}-ecs-execution-role"
  role_description = "Execution role for ${local.app_name} ECS tasks"
  
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
  
  create_policy = true
  policy_name   = "${local.app_name}-execution-policy"
  policy_description = "Allow access to ECR"
  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:ecr:${var.aws_region}:*:repository/${local.app_name}"
      }
    ]
  })
  
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
  ]
  
  tags = var.tags
}

module "ecs_task_role" {
  source = "../iam"

  role_name        = "${local.app_name}-ecs-task-role"
  role_description = "Task role for ${local.app_name} ECS tasks"
  
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
  
  create_policy = true
  policy_name   = "${local.app_name}-task-policy"
  policy_description = "Allow access to Step Functions and ECR"
  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
            "Effect": "Allow",
            "Action": [
                "states:ListExecutions",
                "states:DescribeExecution",
                "states:GetExecutionHistory"
            ],
            "Resource": "${var.state_machine_arn}:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "states:ListExecutions",
                "states:DescribeExecution",
                "states:GetExecutionHistory"
            ],
            "Resource": "arn:aws:states:${var.aws_region}:*:stateMachine:*"
        },
      {
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:ecr:${var.aws_region}:*:repository/${local.app_name}"
      }
    ]
  })
  
  tags = var.tags
}

# Create ALB security group
resource "aws_security_group" "alb_sg" {
  name        = "${local.app_name}-alb-sg"
  description = "Security group for ${local.app_name} ALB"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["15.0.0.0/8"]
    description = "Only allow traffic from 15.0.0.0/8"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow egress all"
  }

  tags = merge(
    var.tags,
    {
      Name = "${local.app_name}-alb-sg"
    }
  )
}

# Create task security group
resource "aws_security_group" "task_sg" {
  name        = "${local.app_name}-task-sg"
  description = "Security group for ${local.app_name} ECS tasks"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
    description = "Allow traffic from ALB security group"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow egress all"
  }

  tags = merge(
    var.tags,
    {
      Name = "${local.app_name}-task-sg"
    }
  )
}

# Create ALB
module "alb" {
  source = "../alb"

  name               = "${local.app_name}-alb"
  internal           = false
  security_group_ids = [aws_security_group.alb_sg.id]  # Use ALB security group
  subnet_ids         = var.subnet_ids
  vpc_id             = var.vpc_id
  
  target_port     = var.container_port
  target_protocol = "HTTP"
  target_type     = "ip"
  
  health_check_path = "/"
  
  tags = var.tags
}

# Create ECS Fargate service
module "ecs_fargate" {
  source = "../ecs-fargate"

  aws_region       = var.aws_region
  cluster_name     = "${local.app_name}-cluster"
  service_name     = local.app_name
  container_name   = local.app_name
  container_image  = "${module.ecr.repository_url}:latest"
  container_port   = var.container_port
  
  task_cpu         = var.task_cpu
  task_memory      = var.task_memory
  
  execution_role_arn = module.ecs_execution_role.role_arn
  task_role_arn      = module.ecs_task_role.role_arn
  
  subnet_ids         = var.subnet_ids
  security_group_ids = [aws_security_group.task_sg.id]  # Use task security group
  assign_public_ip   = true
  
  target_group_arn   = module.alb.target_group_arn
  
  environment_variables = [
    {
      name  = "CLICKHOUSE_HOST"
      value = var.clickhouse_host
    },
    {
      name  = "CLICKHOUSE_PORT"
      value = tostring(var.clickhouse_port)
    },
    {
      name  = "CLICKHOUSE_USER"
      value = var.clickhouse_user
    },
    {
      name  = "CLICKHOUSE_PASSWORD"
      value = var.clickhouse_password
    },
    {
      name  = "CLICKHOUSE_DATABASE"
      value = var.clickhouse_database
    },
    {
      name  = "AWS_REGION"
      value = var.aws_region
    },
    {
      name  = "STATE_MACHINE_ARN"
      value = var.state_machine_arn
    }
  ]
  
  desired_count = var.service_desired_count
  
  tags = var.tags
}
