#!/bin/bash

# Test Docker Build Script
# This script tests the Docker build locally before pushing to ECR

set -e

# Configuration
IMAGE_NAME="factor-trading-backtest"
IMAGE_TAG="test"
DOCKERFILE_PATH="docker/Dockerfile"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get project root directory
get_project_root() {
    cd "$(dirname "${BASH_SOURCE[0]}")/.."
    pwd
}

main() {
    print_status "Testing Docker build locally..."
    
    project_root=$(get_project_root)
    cd "$project_root"
    
    # Check if Dockerfile exists
    if [ ! -f "$DOCKERFILE_PATH" ]; then
        print_error "Dockerfile not found at $DOCKERFILE_PATH"
        exit 1
    fi
    
    # Build the image
    print_status "Building Docker image: $IMAGE_NAME:$IMAGE_TAG"
    docker build -f "$DOCKERFILE_PATH"  --platform linux/amd64  -t "$IMAGE_NAME:$IMAGE_TAG" .
    
    if [ $? -eq 0 ]; then
        print_success "Docker image built successfully"
    else
        print_error "Docker image build failed"
        exit 1
    fi
    
    # Test the image
    print_status "Testing the Docker image..."
    docker run --rm "$IMAGE_NAME:$IMAGE_TAG" python -c "
import sys
sys.path.append('/app/src')
from trading_strategies_model.backtesting.backtest_engine import BacktestEngine
print('✅ BacktestEngine import successful')
from trading_strategies_model.strategies.long_short_equity import LongShortEquityStrategy
print('✅ LongShortEquityStrategy import successful')
print('✅ Docker image test completed successfully')
"
    
    if [ $? -eq 0 ]; then
        print_success "Docker image test passed"
    else
        print_error "Docker image test failed"
        exit 1
    fi
    
    # Display image info
    print_status "Image built successfully:"
    echo "  Name: $IMAGE_NAME:$IMAGE_TAG"
    echo "  Size: $(docker images --format "table {{.Size}}" $IMAGE_NAME:$IMAGE_TAG | tail -n 1)"
    
    print_success "Local Docker build test completed successfully!"
    print_status "You can now run: ./scripts/2.build_and_push_ecr.sh to push to ECR"
}

main "$@"
