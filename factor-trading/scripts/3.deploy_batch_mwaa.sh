#!/bin/bash

# Deploy AWS Infrastructure for Factor Trading
# This script deploys AWS Batch and MWAA infrastructure using CDK
# It expects the ECR image URI from the previous build step

set -e  # Exit on any error

# Configuration variables
AWS_REGION="us-east-1"
CDK_DIR="cdk"
CONTAINER_IMAGE_URI=""
EXISTING_VPC_ID=""
BOOTSTRAP_REQUIRED="false"
VERIFY_DEPLOYMENT="true"

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

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists aws; then
        print_error "AWS CLI is not installed or not in PATH"
        exit 1
    fi
    
    if ! command_exists cdk; then
        print_error "AWS CDK is not installed or not in PATH"
        print_status "Install CDK with: npm install -g aws-cdk"
        exit 1
    fi
    
    if ! command_exists python3; then
        print_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
    
    # Verify AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS credentials not configured or invalid"
        print_status "Configure AWS credentials with: aws configure"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to get ECR image URI from previous build
get_ecr_image_uri() {
    if [ -z "$CONTAINER_IMAGE_URI" ]; then
        print_status "Attempting to auto-detect ECR image URI..."
        
        # Get AWS account ID
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        REPO_NAME="backtest1"
        
        # Check if ECR repository exists and get the latest image
        if aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION >/dev/null 2>&1; then
            # Get the latest image URI
            CONTAINER_IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest"
            
            # Verify the image exists
            if aws ecr describe-images --repository-name $REPO_NAME --image-ids imageTag=latest --region $AWS_REGION >/dev/null 2>&1; then
                print_success "Auto-detected ECR image URI: $CONTAINER_IMAGE_URI"
            else
                print_error "ECR repository exists but 'latest' tag not found"
                print_status "Please run scripts/2.build_and_push_ecr.sh first"
                exit 1
            fi
        else
            print_error "ECR repository '$REPO_NAME' not found"
            print_status "Please run scripts/2.build_and_push_ecr.sh first"
            exit 1
        fi
    else
        print_status "Using provided ECR image URI: $CONTAINER_IMAGE_URI"
    fi
}

# Function to prepare CDK environment
prepare_cdk_environment() {
    print_status "Preparing CDK environment..."
    
    project_root=$(get_project_root)
    cdk_path="$project_root/$CDK_DIR"
    
    if [ ! -d "$cdk_path" ]; then
        print_error "CDK directory not found at $cdk_path"
        exit 1
    fi
    
    cd "$cdk_path"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install CDK dependencies
    print_status "Installing CDK dependencies..."
    pip install -r requirements.txt
    
    print_success "CDK environment prepared"
}

# Function to bootstrap CDK
bootstrap_cdk() {
    if [ "$BOOTSTRAP_REQUIRED" = "true" ]; then
        print_status "Bootstrapping CDK environment..."
        
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        
        print_status "Bootstrapping AWS environment: aws://$AWS_ACCOUNT_ID/$AWS_REGION"
        cdk bootstrap "aws://$AWS_ACCOUNT_ID/$AWS_REGION"
        
        if [ $? -eq 0 ]; then
            print_success "CDK bootstrap completed successfully"
        else
            print_error "CDK bootstrap failed"
            exit 1
        fi
    else
        print_status "Skipping CDK bootstrap (use --bootstrap to force)"
    fi
}

# Function to deploy infrastructure
deploy_infrastructure() {
    print_status "Deploying AWS infrastructure..."
    print_status "CDK will execute app.py which defines TradingStrategiesStack"

    # Validate that container image URI is available
    if [ -z "$CONTAINER_IMAGE_URI" ]; then
        print_error "Container image URI is required for deployment"
        print_status "Please run scripts/2.build_and_push_ecr.sh first or provide --image-uri"
        exit 1
    fi
    
    # Prepare CDK deploy command - specifically deploy TradingStrategiesStack
    # Note: The stack name "TradingStrategiesStack" is defined in app.py
    deploy_cmd="cdk deploy TradingStrategiesStack --require-approval never"
    
    # Add container image URI as context (used by app.py)
    deploy_cmd="$deploy_cmd -c container_image_uri=$CONTAINER_IMAGE_URI"
    
    # Add existing VPC ID if provided (used by app.py)
    if [ -n "$EXISTING_VPC_ID" ]; then
        print_status "Using existing VPC: $EXISTING_VPC_ID"
        deploy_cmd="$deploy_cmd -c existing_vpc_id=$EXISTING_VPC_ID"
    else
        print_status "Creating new VPC"
    fi
    
    print_status "CDK Process:"
    echo "  1. CDK reads cdk.json -> 'app': 'python3 app.py'"
    echo "  2. CDK executes app.py with provided context parameters"
    echo "  3. app.py creates TradingStrategiesStack instance"
    echo "  4. CDK deploys the TradingStrategiesStack CloudFormation template"
    echo ""
    print_status "Executing: $deploy_cmd"
    print_status "Deploying stack: TradingStrategiesStack"
    
    # Execute deployment
    eval $deploy_cmd
    
    if [ $? -eq 0 ]; then
        print_success "TradingStrategiesStack deployment completed successfully"
    else
        print_error "TradingStrategiesStack deployment failed"
        print_status "Check the CDK output above for specific error details"
        exit 1
    fi
}

# Function to verify deployment
verify_deployment() {
    if [ "$VERIFY_DEPLOYMENT" = "true" ]; then
        print_status "Verifying deployment..."
        
        # Check AWS Batch resources
        print_status "Checking AWS Batch compute environments..."
        aws batch describe-compute-environments --region $AWS_REGION --query 'computeEnvironments[?starts_with(computeEnvironmentName, `factor-trading`)].{Name:computeEnvironmentName,State:state,Status:status}' --output table
        
        print_status "Checking AWS Batch job queues..."
        aws batch describe-job-queues --region $AWS_REGION --query 'jobQueues[?starts_with(jobQueueName, `factor-trading`)].{Name:jobQueueName,State:state,Status:status}' --output table
        
        print_status "Checking AWS Batch job definitions..."
        aws batch describe-job-definitions --region $AWS_REGION --status ACTIVE --query 'jobDefinitions[?starts_with(jobDefinitionName, `factor-trading`)].{Name:jobDefinitionName,Revision:revision,Status:status}' --output table
        
        # Check ECR repository
        print_status "Checking ECR repository..."
        REPO_NAME=$(echo $CONTAINER_IMAGE_URI | cut -d'/' -f2 | cut -d':' -f1)
        aws ecr describe-repositories --region $AWS_REGION --repository-names $REPO_NAME --query 'repositories[0].{Name:repositoryName,URI:repositoryUri,CreatedAt:createdAt}' --output table
        
        print_success "Deployment verification completed"
        
        # Display next steps
        print_status "Next Steps:"
        echo "  1. Your infrastructure is now deployed and ready"
        echo "  2. You can submit backtest jobs using AWS Batch"
        echo "  3. Available job queues:"
        echo "     - factor-trading-fargate-job-queue-00"
        echo "     - factor-trading-fargate-job-queue-01"
        echo "  4. Available job definitions:"
        echo "     - factor-trading-backtest"
        echo "     - factor-trading-strategy-execution"
        echo "  5. Container image URI: $CONTAINER_IMAGE_URI"
    fi
}

# Function to display usage
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deploy AWS infrastructure for Factor Trading using CDK"
    echo ""
    echo "Options:"
    echo "  --image-uri URI         ECR container image URI (auto-detected if not provided)"
    echo "  --existing-vpc VPC_ID   Use existing VPC instead of creating new one"
    echo "  --region REGION         AWS region (default: $AWS_REGION)"
    echo "  --bootstrap             Force CDK bootstrap"
    echo "  --no-verify             Skip deployment verification"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Basic deployment (auto-detect ECR image)"
    echo "  $0"
    echo ""
    echo "  # Deployment with specific ECR image"
    echo "  $0 --image-uri 123456789012.dkr.ecr.us-east-1.amazonaws.com/backtest1:latest"
    echo ""
    echo "  # Deployment with existing VPC"
    echo "  $0 --existing-vpc vpc-12345678"
    echo ""
    echo "  # Full deployment with bootstrap"
    echo "  $0 --bootstrap"
    echo ""
    echo "Prerequisites:"
    echo "  - AWS CLI configured with appropriate permissions"
    echo "  - AWS CDK installed (npm install -g aws-cdk)"
    echo "  - ECR image built and pushed (run scripts/2.build_and_push_ecr.sh first)"
    echo ""
    echo "CDK Context Parameters Passed:"
    echo "  - container_image_uri: ECR image URI for Batch jobs"
    echo "  - existing_vpc_id: VPC ID to use (optional)"
}

# Main execution
main() {
    echo "=========================================="
    echo "  AWS Infrastructure Deployment Script"
    echo "=========================================="
    echo ""
    
    # Parse command line arguments
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --image-uri)
                CONTAINER_IMAGE_URI="$2"
                shift 2
                ;;
            --existing-vpc)
                EXISTING_VPC_ID="$2"
                shift 2
                ;;
            --region)
                AWS_REGION="$2"
                shift 2
                ;;
            --bootstrap)
                BOOTSTRAP_REQUIRED="true"
                shift
                ;;
            --no-verify)
                VERIFY_DEPLOYMENT="false"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    print_status "Configuration:"
    echo "  AWS Region: $AWS_REGION"
    echo "  CDK Directory: $CDK_DIR"
    echo "  Bootstrap Required: $BOOTSTRAP_REQUIRED"
    echo "  Verify Deployment: $VERIFY_DEPLOYMENT"
    if [ -n "$EXISTING_VPC_ID" ]; then
        echo "  Existing VPC ID: $EXISTING_VPC_ID"
    fi
    echo ""
    
    # Execute deployment steps
    check_prerequisites
    get_ecr_image_uri
    prepare_cdk_environment
    bootstrap_cdk
    deploy_infrastructure
    verify_deployment
    
    print_success "Deployment completed successfully!"
    echo ""
    print_status "Your Factor Trading infrastructure is now ready to use."
}

# Run main function
main "$@"
