#!/bin/bash

# deployAll.sh - Script to deploy all Terraform infrastructure in order
# This ensures dependencies are properly handled during deployment

# Exit on error
set -e

# Define color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting deployment of all infrastructure components...${NC}"

# Navigate to root directory
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Function to deploy a module
deploy_module() {
  local module=$1
  echo -e "${YELLOW}Deploying module: $module${NC}"
  
  cd "$ROOT_DIR/$module"
  
  # Check if deploy.sh exists
  if [ -f "./deploy.sh" ]; then
    echo "yes" | ./deploy.sh
  else
    # If no deploy.sh, use terraform directly
    terraform init
    terraform apply -auto-approve
  fi
  
  echo -e "${GREEN}$module deployment completed.${NC}"
}

# Deploy modules in order
deploy_module "0-prepare"
deploy_module "1-networking"
deploy_module "2-clickhouse"
deploy_module "3-jump-host"
deploy_module "4-market-data"
deploy_module "5-web-search"
deploy_module "6-sec-filing"
deploy_module "7-financial-report"
deploy_module "8-factor-mining"
deploy_module "9-visualization"

echo -e "${GREEN}All deployments completed successfully!${NC}"
