resource "aws_ecr_repository" "repository" {
  name                 = var.repository_name
  force_delete = true
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = var.kms_key
  }

  tags = var.tags
}

resource "aws_ecr_lifecycle_policy" "policy" {
  count      = var.enable_lifecycle_policy ? 1 : 0
  repository = aws_ecr_repository.repository.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last ${var.max_image_count} images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = var.max_image_count
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
