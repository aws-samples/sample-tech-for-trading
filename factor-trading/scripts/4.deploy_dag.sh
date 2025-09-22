#!/bin/bash

# Deploy DAGs to MWAA Environment
# This script deploys the Airflow Backtest Framework DAGs to the MWAA environment
# It expects the MWAA environment to be created from the previous infrastructure deployment

set -e  # Exit on any error

# Configuration variables
AWS_REGION="us-east-1"
MWAA_ENVIRONMENT_NAME="TradingStrategiesMwaaEnvironment"
S3_BUCKET_NAME="xxx" # The one created in step 3.deploy_batch_mwaa.sh
DAG_SOURCE_DIR="src/dags/backtest_framework_example"
REQUIREMENTS_FILE="requirements.txt"
VERIFY_DEPLOYMENT="true"
CONFIGURE_VARIABLES="true"
DRY_RUN="false"

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

# Function to auto-detect MWAA environment
detect_mwaa_environment() {
    if [ -z "$MWAA_ENVIRONMENT_NAME" ]; then
        print_status "Auto-detecting MWAA environment..."
        
        # First, get all environments
        ALL_ENVIRONMENTS=$(aws mwaa list-environments --region $AWS_REGION --query 'Environments' --output text 2>/dev/null)
        
        if [ -z "$ALL_ENVIRONMENTS" ] || [ "$ALL_ENVIRONMENTS" = "None" ]; then
            print_error "No MWAA environments found in region $AWS_REGION"
            print_status "Please run scripts/3.deploy_batch_mwaa.sh first or provide --environment-name"
            exit 1
        fi
        
        # Look for trading-related environment names
        TRADING_ENV=""
        for env in $ALL_ENVIRONMENTS; do
            if [[ "$env" == *"trading"* ]] || [[ "$env" == *"factor"* ]] || [[ "$env" == *"backtest"* ]]; then
                TRADING_ENV="$env"
                break
            fi
        done
        
        if [ -n "$TRADING_ENV" ]; then
            MWAA_ENVIRONMENT_NAME="$TRADING_ENV"
            print_success "Auto-detected MWAA environment: $MWAA_ENVIRONMENT_NAME"
        else
            # Use the first available environment
            MWAA_ENVIRONMENT_NAME=$(echo $ALL_ENVIRONMENTS | awk '{print $1}')
            print_warning "No trading-related environment found, using: $MWAA_ENVIRONMENT_NAME"
        fi
    else
        print_status "Using provided MWAA environment: $MWAA_ENVIRONMENT_NAME"
    fi
}

# Function to get MWAA S3 bucket
get_mwaa_s3_bucket() {
    if [ -z "$S3_BUCKET_NAME" ]; then
        print_status "Getting MWAA S3 bucket from environment configuration..."
        
        S3_BUCKET_NAME=$(aws mwaa get-environment --name $MWAA_ENVIRONMENT_NAME --region $AWS_REGION --query 'Environment.SourceBucketArn' --output text | sed 's/arn:aws:s3::://')
        
        if [ -n "$S3_BUCKET_NAME" ] && [ "$S3_BUCKET_NAME" != "None" ]; then
            print_success "Found MWAA S3 bucket: $S3_BUCKET_NAME"
        else
            print_error "Could not determine MWAA S3 bucket"
            print_status "Please provide --s3-bucket parameter"
            exit 1
        fi
    else
        print_status "Using provided S3 bucket: $S3_BUCKET_NAME"
    fi
}

# Function to validate DAG source directory
validate_dag_source() {
    project_root=$(get_project_root)
    dag_source_path="$project_root/$DAG_SOURCE_DIR"
    
    if [ ! -d "$dag_source_path" ]; then
        print_error "DAG source directory not found at $dag_source_path"
        exit 1
    fi
    
    # Check for required files
    if [ ! -f "$dag_source_path/framework_backtest_simple_example_dag.py" ]; then
        print_error "Required DAG file not found: framework_backtest_simple_example_dag.py"
        exit 1
    fi
    
    if [ ! -f "$dag_source_path/framework_backtest_multi_example_dag.py" ]; then
        print_error "Required DAG file not found: framework_backtest_multi_example_dag.py"
        exit 1
    fi
    
    if [ ! -d "$dag_source_path/airflow_backtest_framework" ]; then
        print_error "Required framework directory not found: airflow_backtest_framework"
        exit 1
    fi
    
    print_success "DAG source validation passed"
}

# Function to upload requirements.txt
upload_requirements() {
    project_root=$(get_project_root)
    requirements_path="$project_root/$DAG_SOURCE_DIR/$REQUIREMENTS_FILE"
    
    if [ -f "$requirements_path" ]; then
        print_status "Uploading requirements.txt to S3..."
        
        if [ "$DRY_RUN" = "true" ]; then
            print_status "[DRY RUN] Would upload: $requirements_path -> s3://$S3_BUCKET_NAME/dags/requirements.txt"
        else
            aws s3 cp "$requirements_path" "s3://$S3_BUCKET_NAME/dags/requirements.txt" --region $AWS_REGION
            print_success "Requirements.txt uploaded successfully"
        fi
    else
        print_warning "Requirements.txt not found at $requirements_path"
        print_status "MWAA will use default Python packages"
    fi
}

# Function to upload DAGs
upload_dags() {
    project_root=$(get_project_root)
    dag_source_path="$project_root/$DAG_SOURCE_DIR"
    
    print_status "Uploading DAGs and framework to S3..."
    
    if [ "$DRY_RUN" = "true" ]; then
        print_status "[DRY RUN] Would upload DAG files:"
        find "$dag_source_path" -name "*.py" -type f | while read file; do
            relative_path=${file#$dag_source_path/}
            echo "  $relative_path -> s3://$S3_BUCKET_NAME/dags/$relative_path"
        done
        print_status "[DRY RUN] Would upload framework files (excluding README.md):"
        find "$dag_source_path/airflow_backtest_framework" -name "*.py" -type f | while read file; do
            relative_path=${file#$dag_source_path/}
            echo "  $relative_path -> s3://$S3_BUCKET_NAME/dags/$relative_path"
        done
        return
    fi
    
    # Upload individual DAG files
    print_status "Uploading DAG files..."
    aws s3 cp "$dag_source_path/framework_backtest_simple_example_dag.py" "s3://$S3_BUCKET_NAME/dags/" --region $AWS_REGION
    aws s3 cp "$dag_source_path/framework_backtest_multi_example_dag.py" "s3://$S3_BUCKET_NAME/dags/" --region $AWS_REGION
    
    # Upload the entire framework directory (excluding README.md)
    print_status "Uploading framework directory..."
    aws s3 cp "$dag_source_path/airflow_backtest_framework/" "s3://$S3_BUCKET_NAME/dags/airflow_backtest_framework/" --recursive --region $AWS_REGION --exclude "README.md"
    
    print_success "DAGs and framework uploaded successfully"
}

# Function to configure Airflow variables
configure_airflow_variables() {
    if [ "$CONFIGURE_VARIABLES" = "true" ]; then
        print_status "Configuring Airflow Variables..."
        print_warning "The following variables need to be configured manually in the Airflow UI:"
        echo ""
        echo "Required Variables (set these in MWAA Airflow UI under Admin > Variables):"
        echo "┌─────────────────────────────┬─────────────────────────────────────┐"
        echo "│ Variable Key                │ Example Value                       │"
        echo "├─────────────────────────────┼─────────────────────────────────────┤"
        echo "│ batch_job_queue             │ factor-trading-fargate-job-queue-00 │"
        echo "│ batch_job_definition        │ factor-trading-backtest             │"
        echo "│ trading_strategies_bucket   │ your-s3-results-bucket-name         │"
        echo "│ db_host                     │ your-database-host                  │"
        echo "│ db_port                     │ 9000                                │"
        echo "│ db_user                     │ your-database-username              │"
        echo "│ db_password                 │ your-database-password              │"
        echo "│ db_database                 │ your-database-name                  │"
        echo "└─────────────────────────────┴─────────────────────────────────────┘"
        echo ""
        print_status "Access your MWAA Airflow UI at:"
        
        # Get MWAA web server URL
        WEBSERVER_URL=$(aws mwaa get-environment --name $MWAA_ENVIRONMENT_NAME --region $AWS_REGION --query 'Environment.WebserverUrl' --output text)
        if [ -n "$WEBSERVER_URL" ] && [ "$WEBSERVER_URL" != "None" ]; then
            echo "  https://$WEBSERVER_URL"
        else
            echo "  (URL not available - check AWS Console)"
        fi
        echo ""
        print_status "See CONFIGURATION.md for detailed setup instructions"
    fi
}

# Function to verify deployment
verify_deployment() {
    if [ "$VERIFY_DEPLOYMENT" = "true" ]; then
        if [ "$DRY_RUN" = "true" ]; then
            print_status "Skipping deployment verification (dry run mode)"
            print_status "In actual deployment, this would verify:"
            echo "  - DAG files uploaded to S3"
            echo "  - Framework files uploaded to S3"
            echo "  - Requirements.txt uploaded to S3"
            echo "  - MWAA environment status"
            return
        fi
        
        print_status "Verifying deployment..."
        
        # Track verification results
        verification_failed=false
        
        # Check S3 bucket contents
        print_status "Checking uploaded files in S3..."
        
        # Check DAG files
        echo "DAG files:"
        dag_files=$(aws s3 ls "s3://$S3_BUCKET_NAME/dags/" --region $AWS_REGION --recursive | grep -E "\\.py$" | head -10)
        if [ -n "$dag_files" ]; then
            echo "$dag_files"
            print_success "DAG files found in S3"
        else
            print_error "No DAG files found in S3"
            verification_failed=true
        fi
        
        echo ""
        # Check Framework files
        echo "Framework files:"
        framework_files=$(aws s3 ls "s3://$S3_BUCKET_NAME/dags/airflow_backtest_framework/" --region $AWS_REGION --recursive | head -5)
        if [ -n "$framework_files" ]; then
            echo "$framework_files"
            print_success "Framework files found in S3"
        else
            print_error "No framework files found in S3"
            verification_failed=true
        fi
        
        echo ""
        # Check Requirements file (now in dags/ folder)
        echo "Requirements file:"
        if aws s3 ls "s3://$S3_BUCKET_NAME/dags/requirements.txt" --region $AWS_REGION >/dev/null 2>&1; then
            aws s3 ls "s3://$S3_BUCKET_NAME/dags/requirements.txt" --region $AWS_REGION
            print_success "Requirements.txt found in S3"
        else
            print_warning "requirements.txt not found in S3 (this is optional)"
        fi
        
        echo ""
        # Check MWAA environment status
        print_status "Checking MWAA environment status..."
        ENVIRONMENT_STATUS=$(aws mwaa get-environment --name $MWAA_ENVIRONMENT_NAME --region $AWS_REGION --query 'Environment.Status' --output text 2>/dev/null)
        
        if [ "$ENVIRONMENT_STATUS" = "AVAILABLE" ]; then
            print_success "MWAA environment is available and ready"
        elif [ -n "$ENVIRONMENT_STATUS" ]; then
            print_warning "MWAA environment status: $ENVIRONMENT_STATUS"
            print_status "Wait for environment to become AVAILABLE before using DAGs"
        else
            print_error "Could not determine MWAA environment status"
            verification_failed=true
        fi
        
        echo ""
        # Overall verification result
        if [ "$verification_failed" = "true" ]; then
            print_error "Deployment verification failed - some issues detected"
            print_status "Check the errors above and retry deployment if needed"
        else
            print_success "Deployment verification completed successfully"
        fi
        
        # Display next steps
        print_status "Next Steps:"
        echo "  1. Configure Airflow Variables (see output above)"
        echo "  2. Access MWAA Airflow UI to verify DAGs are loaded"
        echo "  3. Check DAG import errors if any"
        echo "  4. Test run the example DAGs:"
        echo "     - framework_backtest_simple_example"
        echo "     - framework_backtest_multi_example"
        echo "  5. Monitor execution in Airflow UI and AWS Batch console"
    fi
}

# Function to display usage
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deploy Airflow Backtest Framework DAGs to MWAA environment"
    echo ""
    echo "Options:"
    echo "  --environment-name NAME     MWAA environment name (auto-detected if not provided)"
    echo "  --s3-bucket BUCKET         S3 bucket for MWAA (auto-detected if not provided)"
    echo "  --region REGION            AWS region (default: $AWS_REGION)"
    echo "  --dag-source-dir DIR       DAG source directory (default: $DAG_SOURCE_DIR)"
    echo "  --no-verify                Skip deployment verification"
    echo "  --no-variables             Skip Airflow variables configuration guide"
    echo "  --dry-run                  Show what would be uploaded without actually doing it"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Basic deployment (auto-detect MWAA environment)"
    echo "  $0"
    echo ""
    echo "  # Deployment with specific MWAA environment"
    echo "  $0 --environment-name my-mwaa-environment"
    echo ""
    echo "  # Dry run to see what would be uploaded"
    echo "  $0 --dry-run"
    echo ""
    echo "  # Deploy without configuration guide"
    echo "  $0 --no-variables"
    echo ""
    echo "Prerequisites:"
    echo "  - AWS CLI configured with appropriate permissions"
    echo "  - MWAA environment deployed (run scripts/3.deploy_batch_mwaa.sh first)"
    echo "  - DAG source files in $DAG_SOURCE_DIR"
    echo ""
    echo "Files Deployed:"
    echo "  - framework_backtest_simple_example_dag.py"
    echo "  - framework_backtest_multi_example_dag.py"
    echo "  - airflow_backtest_framework/ (entire directory)"
    echo "  - requirements.txt (if present)"
    echo "  - CONFIGURATION.md (if present)"
}

# Main execution
main() {
    echo "=========================================="
    echo "    MWAA DAG Deployment Script"
    echo "=========================================="
    echo ""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment-name)
                MWAA_ENVIRONMENT_NAME="$2"
                shift 2
                ;;
            --s3-bucket)
                S3_BUCKET_NAME="$2"
                shift 2
                ;;
            --region)
                AWS_REGION="$2"
                shift 2
                ;;
            --dag-source-dir)
                DAG_SOURCE_DIR="$2"
                shift 2
                ;;
            --no-verify)
                VERIFY_DEPLOYMENT="false"
                shift
                ;;
            --no-variables)
                CONFIGURE_VARIABLES="false"
                shift
                ;;
            --dry-run)
                DRY_RUN="true"
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
    echo "  DAG Source Directory: $DAG_SOURCE_DIR"
    echo "  Verify Deployment: $VERIFY_DEPLOYMENT"
    echo "  Configure Variables: $CONFIGURE_VARIABLES"
    echo "  Dry Run: $DRY_RUN"
    if [ -n "$MWAA_ENVIRONMENT_NAME" ]; then
        echo "  MWAA Environment: $MWAA_ENVIRONMENT_NAME"
    fi
    if [ -n "$S3_BUCKET_NAME" ]; then
        echo "  S3 Bucket: $S3_BUCKET_NAME"
    fi
    echo ""
    
    # Execute deployment steps
    check_prerequisites
    detect_mwaa_environment
    get_mwaa_s3_bucket
    validate_dag_source
    upload_requirements
    upload_dags
    configure_airflow_variables
    verify_deployment
    
    print_success "DAG deployment completed successfully!"
    echo ""
    print_status "Your Airflow Backtest Framework DAGs are now deployed to MWAA."
    print_status "Configure the required Airflow Variables before running the DAGs."
}

# Run main function
main "$@"