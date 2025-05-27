#!/bin/bash

# destroyAll.sh - Script to destroy all Terraform infrastructure in reverse order
# This ensures dependencies are properly handled during destruction

set -e  # Exit immediately if a command exits with a non-zero status

echo "Starting infrastructure destruction in reverse order..."

# Define color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to destroy a module
destroy_module() {
  local module=$1
  echo -e "${YELLOW}Destroying module: $module${NC}"
  
  cd "$module"
  
  # Initialize Terraform if needed
  terraform init
  
  # Destroy with auto-approve
  if terraform destroy -auto-approve; then
    echo -e "${GREEN}Successfully destroyed $module${NC}"
  else
    echo -e "${RED}Failed to destroy $module${NC}"
    exit 1
  fi
  
  cd ..
}

# Destroy modules in reverse order
destroy_module "9-visualization"
destroy_module "8-factor-mining"
destroy_module "7-financial-report"
destroy_module "6-sec-filing"
destroy_module "5-web-search"
destroy_module "4-market-data"
destroy_module "3-jump-host"
destroy_module "2-clickhouse"
destroy_module "1-networking"
destroy_module "0-prepare"

echo -e "${GREEN}All infrastructure has been destroyed successfully!${NC}"
