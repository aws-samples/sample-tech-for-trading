# ECR Repository Module

This module creates an Amazon Elastic Container Registry (ECR) repository with optional lifecycle policy.

## Usage

```hcl
module "ecr" {
  source = "../modules/ecr"

  repository_name      = "my-app-repository"
  image_tag_mutability = "MUTABLE"
  scan_on_push         = true
  
  # Optional lifecycle policy
  enable_lifecycle_policy = true
  max_image_count         = 30
  
  tags = {
    Environment = "production"
    Project     = "factor-mining"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| repository_name | Name of the ECR repository | string | n/a | yes |
| image_tag_mutability | The tag mutability setting for the repository (MUTABLE or IMMUTABLE) | string | "MUTABLE" | no |
| scan_on_push | Indicates whether images are scanned after being pushed to the repository | bool | true | no |
| encryption_type | The encryption type to use for the repository (AES256 or KMS) | string | "AES256" | no |
| kms_key | The ARN of the KMS key to use when encryption_type is KMS | string | null | no |
| enable_lifecycle_policy | Whether to enable lifecycle policy for the repository | bool | true | no |
| max_image_count | Maximum number of images to keep in the repository | number | 30 | no |
| tags | A map of tags to assign to the repository | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| repository_url | The URL of the repository |
| repository_arn | The ARN of the repository |
| repository_name | The name of the repository |
| repository_registry_id | The registry ID where the repository was created |
