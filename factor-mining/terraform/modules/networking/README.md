# Networking Infrastructure Module

This reusable Terraform module creates a highly available AWS network infrastructure, including VPC, subnets, route tables, gateways, and security groups.

## Architecture Features

- **High Availability Design**: Resources deployed across multiple availability zones for improved fault tolerance
- **Public/Private Network Isolation**: Strict separation of public and private subnets for enhanced security
- **Per-AZ NAT Gateways**: Independent NAT gateway for each availability zone, ensuring AZ isolation
- **Standardized Tagging**: All resources use a consistent tagging system for management and cost allocation

## Created Resources

| Resource Type | Count | Description |
|---------|-----|------|
| VPC | 1 | Main network container |
| Public Subnets | 1 per AZ | For internet-facing resources (e.g., load balancers) |
| Private Subnets | 1 per AZ | For internal resources (e.g., application servers, databases) |
| Internet Gateway | 1 | Allows VPC to communicate with the internet |
| NAT Gateways | 1 per AZ | Allows resources in private subnets to access the internet |
| Elastic IPs | 1 per NAT Gateway | Provides static public IPs for NAT gateways |
| Public Route Table | 1 | Routes traffic for public subnets |
| Private Route Tables | 1 per AZ | Routes traffic from private subnets to corresponding NAT gateways |
| Security Group | 1 | Default security group allowing all outbound traffic |

## Subnet Tagging System

All subnets are tagged with a `SubnetType` tag:
- `public`: Public subnets
- `private`: Private subnets

This allows other modules to easily identify subnet types, for example:
```hcl
resource "aws_instance" "web" {
  for_each = {
    for id, tags in module.networking.subnet_tags_by_id :
    id => tags if tags["SubnetType"] == "private"
  }
  
  subnet_id = each.key
  # Other configuration...
}
```

## Usage Example

```hcl
module "networking" {
  source = "../modules/networking"

  vpc_cidr           = "10.0.0.0/16"
  availability_zones = ["us-east-1a", "us-east-1b"]
  project_name       = "factor-mining"
  environment        = "dev"
}

# Access VPC ID
output "vpc_id" {
  value = module.networking.vpc_id
}

# Access private subnet IDs list
output "private_subnet_ids" {
  value = module.networking.private_subnet_ids
}

# Access public subnet IDs list
output "public_subnet_ids" {
  value = module.networking.public_subnet_ids
}

# Access security group ID
output "security_group_id" {
  value = module.networking.security_group_ids
}
```

## Input Variables

| Variable Name | Description | Type | Default Value |
|------|-------------|------|---------|
| vpc_cidr | CIDR block for the VPC | string | "10.0.0.0/16" |
| availability_zones | List of availability zones | list(string) | ["us-east-1a", "us-east-1b"] |
| project_name | Project name for resource naming | string | "factor-mining" |
| environment | Environment name (e.g., dev, prod) | string | "dev" |

## Output Values

| Output Name | Description | Type |
|------|-------------|------|
| vpc_id | ID of the VPC | string |
| private_subnet_ids | List of private subnet IDs | list(string) |
| public_subnet_ids | List of public subnet IDs | list(string) |
| security_group_ids | Default security group ID | string |

## Considerations

1. **Cost Considerations**: Each NAT gateway incurs hourly charges and data processing fees. If cost reduction is needed, the code can be modified to use only one NAT gateway, but this will reduce availability.

2. **Security Group Configuration**: The default security group only allows outbound traffic with no inbound rules configured. Appropriate inbound rules should be added in the higher-level configuration using this module as needed.

3. **Scalability**: To add more availability zones, simply add more zones to the `availability_zones` variable, and the module will automatically create corresponding resources for each zone.
