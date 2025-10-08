#!/bin/bash

# Deploy Streamlit Frontend Dashboard
# Usage: ./5.deploy_frontend.sh [VPC_ID] [YOUR_IP]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying Factor Trading Frontend Dashboard ${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CDK_DIR="$PROJECT_ROOT/cdk"

# Check if VPC ID is provided
VPC_ID=${1:-$EXISTING_VPC_ID}
YOUR_IP=${2:-$YOUR_IP}

if [ -z "$VPC_ID" ]; then
    echo -e "${RED}❌ Error: VPC ID is required${NC}"
    echo "Usage: $0 <VPC_ID> [YOUR_IP]"
    echo "Or set EXISTING_VPC_ID environment variable"
    echo ""
    echo -e "${YELLOW}💡 The frontend stack requires an existing VPC with public subnets${NC}"
    echo -e "${YELLOW}   You can use the VPC created by the trading strategies stack${NC}"
    exit 1
fi

# Auto-detect IP if not provided
if [ -z "$YOUR_IP" ]; then
    echo -e "${YELLOW}🔍 Auto-detecting your IP address...${NC}"
    YOUR_IP=$(curl -s https://ipv4.icanhazip.com || echo "")
    if [ -z "$YOUR_IP" ]; then
        echo -e "${RED}❌ Could not auto-detect IP. Please provide it manually.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Detected IP: $YOUR_IP${NC}"
fi

# Navigate to CDK directory (merged location)
cd "$CDK_DIR"

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo -e "${RED}❌ AWS CDK is not installed. Please install it first:${NC}"
    echo "npm install -g aws-cdk"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Please run 'aws configure'${NC}"
    exit 1
fi

# Install CDK dependencies if needed
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Setting up CDK environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Bootstrap CDK if needed
echo -e "${YELLOW}🔧 Checking CDK bootstrap...${NC}"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")

# Check if bootstrap is needed
if ! aws cloudformation describe-stacks --stack-name CDKToolkit --region $REGION &> /dev/null; then
    echo -e "${YELLOW}🚀 Bootstrapping CDK...${NC}"
    cdk bootstrap aws://$ACCOUNT/$REGION
fi

# Deploy the frontend stack
echo -e "${GREEN}🚀 Deploying frontend stack ...${NC}"

# Deploy using CDK with frontend-only mode and capture outputs
echo -e "${BLUE}📋 Running CDK deploy with frontend mode...${NC}"
CDK_OUTPUT=$(cdk deploy FactorTradingFrontend \
    -c existing_vpc_id=$VPC_ID \
    -c your_ip=$YOUR_IP \
    -c deploy_mode=frontend \
    --require-approval never \
    --outputs-file cdk-outputs.json 2>&1)

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ CDK deployment failed!${NC}"
    echo "$CDK_OUTPUT"
    exit 1
fi

echo -e "${GREEN}✅ CDK deployment completed successfully!${NC}"

# Extract outputs from CDK
if [ -f "cdk-outputs.json" ]; then
    INSTANCE_ID=$(python3 -c "
import json
with open('cdk-outputs.json', 'r') as f:
    outputs = json.load(f)
    stack_outputs = outputs.get('FactorTradingFrontend', {})
    print(stack_outputs.get('InstanceId', ''))
")
    
    STREAMLIT_URL=$(python3 -c "
import json
with open('cdk-outputs.json', 'r') as f:
    outputs = json.load(f)
    stack_outputs = outputs.get('FactorTradingFrontend', {})
    print(stack_outputs.get('StreamlitURL', ''))
")
    
    SSH_COMMAND=$(python3 -c "
import json
with open('cdk-outputs.json', 'r') as f:
    outputs = json.load(f)
    stack_outputs = outputs.get('FactorTradingFrontend', {})
    print(stack_outputs.get('SSHCommand', ''))
")
else
    echo -e "${RED}❌ Could not find CDK outputs file${NC}"
    exit 1
fi

if [ -z "$INSTANCE_ID" ]; then
    echo -e "${RED}❌ Could not extract Instance ID from CDK outputs${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Extracted Instance ID: $INSTANCE_ID${NC}"
echo -e "${GREEN}✅ Streamlit URL will be: $STREAMLIT_URL${NC}"

# Wait for instance to be ready
echo -e "${YELLOW}⏳ Waiting for EC2 instance to be ready...${NC}"
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

# Wait a bit more for SSM agent to be ready
echo -e "${YELLOW}⏳ Waiting for SSM agent to be ready (30 seconds)...${NC}"
sleep 30

# Now copy the files using Python (embedded in the script)
echo -e "${BLUE}📁 Copying application files to instance...${NC}"

# Deactivate CDK venv and use project venv for file copying
deactivate

# Check if project has .venv or venv directory
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo -e "${YELLOW}   Using project .venv environment${NC}"
elif [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
    echo -e "${YELLOW}   Using project venv environment${NC}"
else
    echo -e "${YELLOW}   Using system Python (installing boto3 with --user)${NC}"
    python3 -m pip install --user boto3
fi

# Create a temporary Python script for file copying
cat > /tmp/copy_files_temp.py << 'EOF'
#!/usr/bin/env python3
import boto3
import base64
import time
import sys
import os

def copy_files_to_instance(instance_id, region='us-east-1'):
    ssm = boto3.client('ssm', region_name=region)
    
    # Get the project root directory (passed as argument)
    project_root = sys.argv[3] if len(sys.argv) > 3 else os.getcwd()
    
    # File paths
    app_path = os.path.join(project_root, 'src', 'frontend', 'app.py')
    db_path = os.path.join(project_root, 'src', 'frontend', 'database.py')
    req_path = os.path.join(project_root, 'src', 'frontend', 'requirements.txt')
    env_path = os.path.join(project_root, 'src', 'frontend', '.env')
    
    # Check if files exist
    for path in [app_path, db_path, req_path, env_path]:
        if not os.path.exists(path):
            print(f"❌ File not found: {path}")
            return False
    
    # Read the files
    with open(app_path, 'r') as f:
        app_content = f.read()
    
    with open(db_path, 'r') as f:
        database_content = f.read()
    
    with open(req_path, 'r') as f:
        requirements_content = f.read()
    
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    # Encode files in base64 to avoid shell escaping issues
    app_b64 = base64.b64encode(app_content.encode()).decode()
    db_b64 = base64.b64encode(database_content.encode()).decode()
    req_b64 = base64.b64encode(requirements_content.encode()).decode()
    env_b64 = base64.b64encode(env_content.encode()).decode()
    
    commands = [
        "cd /opt/streamlit-app",
        f"echo '{app_b64}' | base64 -d > app.py",
        f"echo '{db_b64}' | base64 -d > database.py", 
        f"echo '{req_b64}' | base64 -d > requirements.txt",
        f"echo '{env_b64}' | base64 -d > .env",
        "python3.11 -m pip install --user -r requirements.txt",
        "sudo systemctl restart streamlit"
    ]
    
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': commands}
        )
        
        command_id = response['Command']['CommandId']
        print(f"📤 Command sent with ID: {command_id}")
        
        # Wait for command to complete
        print("⏳ Waiting for file copy to complete...")
        for i in range(30):  # Wait up to 5 minutes
            time.sleep(10)
            result = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id
            )
            
            status = result['Status']
            print(f"   Status: {status}")
            
            if status in ['Success', 'Failed', 'Cancelled', 'TimedOut']:
                if status == 'Success':
                    print("✅ Files copied successfully!")
                    return True
                else:
                    print(f"❌ Command failed with status: {status}")
                    if 'StandardErrorContent' in result:
                        print(f"Error: {result['StandardErrorContent']}")
                    return False
        
        print("⏰ Command is still running...")
        return False
        
    except Exception as e:
        print(f"❌ Error copying files: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python copy_files_temp.py <instance_id> <region> [project_root]")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    region = sys.argv[2]
    
    success = copy_files_to_instance(instance_id, region)
    sys.exit(0 if success else 1)
EOF

# Run the file copying script
python3 /tmp/copy_files_temp.py $INSTANCE_ID $REGION "$PROJECT_ROOT"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ File copy completed successfully!${NC}"
    
    # Clean up temporary file
    rm -f /tmp/copy_files_temp.py
    
    echo ""
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    echo ""
    echo -e "${GREEN}📊 Your Streamlit dashboard is available at:${NC}"
    echo -e "${BLUE}   $STREAMLIT_URL${NC}"
    echo ""
    echo -e "${YELLOW}   Note: It may take a few minutes for the application to fully start${NC}"
    echo ""
    echo -e "${GREEN}🔑 To SSH into the instance:${NC}"
    echo -e "${YELLOW}   1. Download the private key from AWS EC2 Console -> Key Pairs -> streamlit-frontend-key${NC}"
    echo -e "${YELLOW}   2. Use: $SSH_COMMAND${NC}"
    echo ""
    echo -e "${GREEN}📝 To check the Streamlit service status:${NC}"
    echo -e "${YELLOW}   sudo systemctl status streamlit${NC}"
    echo ""
    echo -e "${GREEN}📋 To view Streamlit logs:${NC}"
    echo -e "${YELLOW}   sudo journalctl -u streamlit -f${NC}"
    echo ""
    echo -e "${GREEN}🔄 If the service isn't running, restart it:${NC}"
    echo -e "${YELLOW}   sudo systemctl restart streamlit${NC}"
    echo ""
    echo -e "${GREEN}Instance ID: $INSTANCE_ID${NC}"
    echo -e "${GREEN}Region: $REGION${NC}"
    echo ""
    echo -e "${BLUE}💡 Deployment Info:${NC}"
    echo -e "${YELLOW}   • Used cdk/app.py${NC}"
    echo -e "${YELLOW}   • Deployed only frontend stack (deploy_mode=frontend)${NC}"
    echo -e "${YELLOW}   • VPC ID: $VPC_ID${NC}"
    echo -e "${YELLOW}   • Your IP: $YOUR_IP${NC}"
    
else
    echo -e "${RED}❌ File copy failed!${NC}"
    echo ""
    echo -e "${YELLOW}You can manually copy files later using:${NC}"
    echo -e "${YELLOW}   python3 copy_files.py${NC}"
    echo -e "${YELLOW}   (Make sure to update the instance_id in copy_files.py to: $INSTANCE_ID)${NC}"
    echo ""
    echo -e "${GREEN}Streamlit URL: $STREAMLIT_URL${NC}"
    echo -e "${GREEN}SSH Command: $SSH_COMMAND${NC}"
    
    # Clean up temporary file
    rm -f /tmp/copy_files_temp.py
    exit 1
fi
