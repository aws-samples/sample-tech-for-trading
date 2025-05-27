provider "aws" {
  region = var.aws_region
}

# Get availability zones for the selected region
data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  # Use the first 2 availability zones by default
  availability_zones = length(var.availability_zones) > 0 ? var.availability_zones : slice(data.aws_availability_zones.available.names, 0, 2)
}

module "networking" {
  source = "../modules/networking"

  vpc_cidr            = var.vpc_cidr
  availability_zones  = local.availability_zones
  project_name        = var.project_name
  environment         = var.environment
}
