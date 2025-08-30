#!/bin/bash

# Build and Push Docker Image to ECR
# This script builds the trading strategies Docker image and pushes it to Amazon ECR

set -e  # Exit on any error

# Configuration variables - Auto-detect AWS Account ID
AWS_REGION="us-east-1"
REPO_NAME="backtest1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME"
IMAGE_TAG="latest"
DOCKERFILE_PATH="docker/Dockerfile"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command_exists aws; then
        print_error "AWS CLI is not installed or not in PATH"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to get script directory
get_script_dir() {
    cd "$(dirname "${BASH_SOURCE[0]}")"
    pwd
}

# Function to get project root directory
get_project_root() {
    script_dir=$(get_script_dir)
    cd "$script_dir/.."
    pwd
}

# Function to authenticate with ECR
authenticate_ecr() {
    print_status "Authenticating with Amazon ECR..."
    
    # Get ECR login token and authenticate Docker
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
    
    if [ $? -eq 0 ]; then
        print_success "ECR authentication successful"
    else
        print_error "ECR authentication failed"
        exit 1
    fi
}

# Function to create ECR repository if it doesn't exist
create_ecr_repo() {
    print_status "Checking if ECR repository exists..."
    
    # Check if repository exists
    if aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION >/dev/null 2>&1; then
        print_success "ECR repository '$REPO_NAME' already exists"
    else
        print_status "Creating ECR repository '$REPO_NAME'..."
        aws ecr create-repository --repository-name $REPO_NAME --region $AWS_REGION
        
        if [ $? -eq 0 ]; then
            print_success "ECR repository '$REPO_NAME' created successfully"
        else
            print_error "Failed to create ECR repository"
            exit 1
        fi
    fi
}

# Function to build Docker image
build_image() {
    print_status "Building Docker image..."
    
    project_root=$(get_project_root)
    cd "$project_root"
    
    # Check if Dockerfile exists
    if [ ! -f "$DOCKERFILE_PATH" ]; then
        print_error "Dockerfile not found at $DOCKERFILE_PATH"
        exit 1
    fi
    
    # Build the image
    docker build -f "$DOCKERFILE_PATH"  --platform linux/amd64 -t "$ECR_REPO:$IMAGE_TAG" .
    
    if [ $? -eq 0 ]; then
        print_success "Docker image built successfully"
    else
        print_error "Docker image build failed"
        exit 1
    fi
}

# Function to push image to ECR
push_image() {
    print_status "Pushing Docker image to ECR..."
    
    docker push "$ECR_REPO:$IMAGE_TAG"
    
    if [ $? -eq 0 ]; then
        print_success "Docker image pushed successfully to $ECR_REPO:$IMAGE_TAG"
    else
        print_error "Failed to push Docker image to ECR"
        exit 1
    fi
}

# Function to tag image with timestamp
tag_with_timestamp() {
    timestamp=$(date +%Y%m%d-%H%M%S)
    timestamp_tag="$ECR_REPO:$timestamp"
    
    print_status "Tagging image with timestamp: $timestamp"
    docker tag "$ECR_REPO:$IMAGE_TAG" "$timestamp_tag"
    docker push "$timestamp_tag"
    
    if [ $? -eq 0 ]; then
        print_success "Timestamp tagged image pushed: $timestamp_tag"
    else
        print_warning "Failed to push timestamp tagged image"
    fi
}

# Function to clean up local images (optional)
cleanup_local_images() {
    if [ "$CLEANUP_LOCAL" = "true" ]; then
        print_status "Cleaning up local Docker images..."
        docker rmi "$ECR_REPO:$IMAGE_TAG" 2>/dev/null || true
        print_success "Local cleanup completed"
    fi
}

# Function to display image information
display_image_info() {
    print_status "Image Information:"
    echo "  Repository: $ECR_REPO"
    echo "  Tag: $IMAGE_TAG"
    echo "  Full URI: $ECR_REPO:$IMAGE_TAG"
    echo ""
    print_status "You can now use this image URI in your AWS Batch job definitions"
}

# Main execution
main() {
    echo "=========================================="
    echo "  Docker Build and ECR Push Script"
    echo "=========================================="
    echo ""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --repo)
                ECR_REPO="$2"
                shift 2
                ;;
            --tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            --region)
                AWS_REGION="$2"
                shift 2
                ;;
            --cleanup)
                CLEANUP_LOCAL="true"
                shift
                ;;
            --timestamp)
                ADD_TIMESTAMP="true"
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --repo REPO_URI     ECR repository URI (default: $ECR_REPO)"
                echo "  --tag TAG           Image tag (default: $IMAGE_TAG)"
                echo "  --region REGION     AWS region (default: $AWS_REGION)"
                echo "  --cleanup           Remove local images after push"
                echo "  --timestamp         Also tag and push with timestamp"
                echo "  -h, --help          Show this help message"
                echo ""
                echo "Example:"
                echo "  $0 --repo 123456789012.dkr.ecr.us-west-2.amazonaws.com/my-repo --tag v1.0"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Extract account ID and repo name from ECR_REPO if not set
    if [[ $ECR_REPO =~ ^([0-9]+)\.dkr\.ecr\.([^.]+)\.amazonaws\.com/(.+)$ ]]; then
        AWS_ACCOUNT_ID="${BASH_REMATCH[1]}"
        AWS_REGION="${BASH_REMATCH[2]}"
        REPO_NAME="${BASH_REMATCH[3]}"
    fi
    
    print_status "Configuration:"
    echo "  ECR Repository: $ECR_REPO"
    echo "  Image Tag: $IMAGE_TAG"
    echo "  AWS Region: $AWS_REGION"
    echo "  AWS Account ID: $AWS_ACCOUNT_ID"
    echo "  Repository Name: $REPO_NAME"
    echo ""
    
    # Execute steps
    check_prerequisites
    authenticate_ecr
    create_ecr_repo
    build_image
    push_image
    
    if [ "$ADD_TIMESTAMP" = "true" ]; then
        tag_with_timestamp
    fi
    
    cleanup_local_images
    display_image_info
    
    print_success "Build and push completed successfully!"
}

# Run main function
main "$@"
