"""
deploy_lambda.py

Lambda Function Deployment Script
Risk Manager Lambda Function Deployment
"""

import boto3
import zipfile
import json
import os
import time
import sys
from pathlib import Path

# Add common configuration path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))
from config import Config as GlobalConfig

class Config:
    """Lambda deployment configuration"""
    REGION = GlobalConfig.REGION
    FUNCTION_NAME = GlobalConfig.LAMBDA_FUNCTION_NAME

def create_lambda_package():
    """Package Lambda function"""
    current_dir = Path(__file__).parent
    zip_filename = 'lambda_function.zip'
    zip_path = current_dir / zip_filename
    lambda_file = current_dir / 'lambda_function.py'
    
    if not lambda_file.exists():
        raise FileNotFoundError(f"Lambda function file not found: {lambda_file}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(lambda_file, 'lambda_function.py')
    
    return str(zip_path)

def setup_iam_role():
    """Set up IAM role"""
    print("🔐 Setting up IAM role...")
    iam = boto3.client('iam')
    role_name = f'{Config.FUNCTION_NAME}-role'
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Risk Manager Lambda execution role'
        )
        role_arn = response['Role']['Arn']
        
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        time.sleep(10)  # Wait for IAM propagation
        return role_arn
        
    except iam.exceptions.EntityAlreadyExistsException:
        response = iam.get_role(RoleName=role_name)
        return response['Role']['Arn']

def load_layer_info():
    """Load Layer deployment information"""
    layer_dir = Path(__file__).parent.parent / "lambda_layer"
    info_file = layer_dir / "layer_deployment_info.json"
    
    if not info_file.exists():
        return None
    
    with open(info_file, 'r') as f:
        layer_info = json.load(f)
    
    return layer_info.get('layer_version_arn')

def create_lambda_function(role_arn, layer_arn, zip_content):
    """Create Lambda function"""
    print("🔧 Creating Lambda function...")
    lambda_client = boto3.client('lambda', region_name=Config.REGION)
    
    # Delete existing function
    if _check_function_exists(lambda_client, Config.FUNCTION_NAME):
        lambda_client.delete_function(FunctionName=Config.FUNCTION_NAME)
        time.sleep(5)
    
    response = lambda_client.create_function(
        FunctionName=Config.FUNCTION_NAME,
        Runtime="python3.12",
        Role=role_arn,
        Handler='lambda_function.lambda_handler',
        Code={'ZipFile': zip_content},
        Description='Risk Manager - News and market data analysis',
        Timeout=30,
        MemorySize=256,
        Layers=[layer_arn]
    )
    
    # Wait for function activation
    _wait_for_function_active(lambda_client, Config.FUNCTION_NAME)
    
    return {
        'function_arn': response['FunctionArn'],
        'function_name': response['FunctionName']
    }

def _check_function_exists(lambda_client, function_name):
    """Check if Lambda function exists"""
    try:
        lambda_client.get_function(FunctionName=function_name)
        return True
    except lambda_client.exceptions.ResourceNotFoundException:
        return False

def _wait_for_function_active(lambda_client, function_name, max_attempts=15):
    """Wait for Lambda function to become active"""
    for attempt in range(max_attempts):
        try:
            response = lambda_client.get_function(FunctionName=function_name)
            state = response['Configuration']['State']
            
            if state == 'Active':
                return
            elif state == 'Failed':
                reason = response['Configuration'].get('StateReason', 'Unknown error')
                raise Exception(f"Lambda function activation failed: {reason}")
            
            time.sleep(2)
            
        except Exception as e:
            if attempt == max_attempts - 1:
                raise Exception(f"Lambda function status check failed: {str(e)}")
            time.sleep(2)
    
    raise Exception("Lambda function activation timeout")

def save_deployment_info(result):
    """Save deployment information"""
    info_file = Path(__file__).parent / "lambda_deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(result, f, indent=2)
    return str(info_file)

def main():
    try:
        print("🚀 Risk Manager Lambda Deployment")
        
        # Check Layer information
        layer_arn = load_layer_info()
        if not layer_arn:
            raise RuntimeError(
                "Layer not found. Please deploy Layer first:\n"
                "cd ../lambda_layer && python deploy_lambda_layer.py"
            )
        
        # Create Lambda package
        zip_filename = create_lambda_package()
        
        # Set up IAM role
        role_arn = setup_iam_role()
        
        # Load ZIP file
        with open(zip_filename, 'rb') as zip_file:
            zip_content = zip_file.read()
        
        # Create Lambda function
        lambda_result = create_lambda_function(role_arn, layer_arn, zip_content)
        
        # Clean up temporary files
        if os.path.exists(zip_filename):
            os.remove(zip_filename)
        
        # Configure deployment result
        result = {
            'function_name': lambda_result['function_name'],
            'function_arn': lambda_result['function_arn'],
            'region': Config.REGION,
            'deployed_at': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save deployment information
        info_file = save_deployment_info(result)
        
        print(f"\n🎉 Lambda Function Deployment Complete!")
        print(f"🔗 Function ARN: {result['function_arn']}")
        print(f"📄 Deployment Info: {info_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ Lambda Deployment Failed: {e}")
        raise

if __name__ == "__main__":
    main()