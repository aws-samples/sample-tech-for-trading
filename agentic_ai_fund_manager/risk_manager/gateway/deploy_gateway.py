"""
deploy_gateway.py

Risk Manager Gateway Deployment Script
Mediates MCP communication between Lambda functions and AI agents.
"""

import boto3
import time
import json
import copy
import sys
from pathlib import Path
from target_config import TARGET_CONFIGURATION

# Add common configuration and shared module paths
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))
sys.path.insert(0, str(root_path / "shared"))

from config import Config as GlobalConfig
from cognito_utils import get_or_create_user_pool, get_or_create_resource_server, get_or_create_m2m_client
from gateway_utils import create_agentcore_gateway_role, create_gateway, create_gateway_target

class Config:
    """Gateway deployment configuration"""
    REGION = GlobalConfig.REGION
    GATEWAY_NAME = GlobalConfig.GATEWAY_NAME
    TARGET_NAME = GlobalConfig.TARGET_NAME

def load_lambda_info():
    """Load Lambda deployment information"""
    info_file = Path(__file__).parent.parent / "lambda" / "lambda_deployment_info.json"
    
    if not info_file.exists():
        raise FileNotFoundError("Lambda deployment information not found. Please deploy Lambda first.")
    
    with open(info_file, 'r') as f:
        lambda_info = json.load(f)
    
    lambda_arn = lambda_info.get('function_arn')
    if not lambda_arn:
        raise KeyError("Lambda ARN not found.")
    
    return lambda_arn

def cleanup_existing_gateway():
    """Clean up existing Gateway"""
    try:
        print("🔍 Checking existing Gateway...")
        gateway_client = boto3.client('bedrock-agentcore-control', region_name=Config.REGION)
        gateways = gateway_client.list_gateways().get('items', [])

        for gw in gateways:
            if gw['name'] == Config.GATEWAY_NAME:
                gateway_id = gw['gatewayId']
                print(f"🗑️ Deleting existing Gateway: {gateway_id}")
                
                # Delete targets first
                targets = gateway_client.list_gateway_targets(gatewayIdentifier=gateway_id).get('items', [])
                for target in targets:
                    gateway_client.delete_gateway_target(
                        gatewayIdentifier=gateway_id,
                        targetId=target['targetId']
                    )
                
                time.sleep(3)
                gateway_client.delete_gateway(gatewayIdentifier=gateway_id)
                time.sleep(3)
                break
                
    except Exception as e:
        print(f"⚠️ Error during Gateway cleanup (ignoring and proceeding): {str(e)}")
        pass

def setup_cognito_auth():
    """Set up Cognito authentication"""
    print("🔐 Setting up Cognito authentication...")
    cognito = boto3.client('cognito-idp', region_name=Config.REGION)
    
    # Create/get User Pool
    user_pool_id = get_or_create_user_pool(cognito, f"{Config.GATEWAY_NAME}-pool", Config.REGION)
    
    # Create/get Resource Server
    resource_server_id = f"{Config.GATEWAY_NAME}-server"
    scopes = [
        {"ScopeName": "gateway:read", "ScopeDescription": "Gateway read access"},
        {"ScopeName": "gateway:write", "ScopeDescription": "Gateway write access"}
    ]
    get_or_create_resource_server(cognito, user_pool_id, resource_server_id, 
                                 f"{Config.GATEWAY_NAME} Resource Server", scopes)
    
    # Create/get M2M Client
    client_id, client_secret = get_or_create_m2m_client(
        cognito, user_pool_id, f"{Config.GATEWAY_NAME}-client", 
        resource_server_id, ["gateway:read", "gateway:write"]
    )
    
    discovery_url = f'https://cognito-idp.{Config.REGION}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration'
    
    return {
        'user_pool_id': user_pool_id,
        'client_id': client_id,
        'client_secret': client_secret,
        'discovery_url': discovery_url
    }

def create_gateway_runtime(role_arn, auth_components, lambda_arn):
    """Create Gateway Runtime"""
    print("🔧 Configuring Gateway Runtime...")
    
    # Create Gateway
    gateway = create_gateway(Config.GATEWAY_NAME, role_arn, auth_components, Config.REGION)
    
    # Create Gateway Target (expose Lambda function as MCP tool)
    target_config = copy.deepcopy(TARGET_CONFIGURATION)
    target_config['mcp']['lambda']['lambdaArn'] = lambda_arn
    target = create_gateway_target(gateway['gatewayId'], Config.TARGET_NAME, target_config, Config.REGION)
    
    return {
        'gateway_id': gateway['gatewayId'],
        'gateway_url': gateway['gatewayUrl'],
        'target_id': target['targetId']
    }

def save_deployment_info(result):
    """Save deployment information"""
    info_file = Path(__file__).parent / "gateway_deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(result, f, indent=2)
    return str(info_file)

def main():
    try:
        print("🚀 Risk Manager Gateway Deployment")
        
        # Load Lambda ARN
        lambda_arn = load_lambda_info()
        
        # Clean up existing Gateway
        cleanup_existing_gateway()
        
        # Create IAM role
        iam_role = create_agentcore_gateway_role(Config.GATEWAY_NAME, Config.REGION)
        iam_role_name = iam_role['Role']['RoleName']
        time.sleep(10)  # Wait for IAM propagation
        
        # Set up Cognito authentication
        auth_components = setup_cognito_auth()
        
        # Create Gateway Runtime
        runtime_result = create_gateway_runtime(iam_role['Role']['Arn'], auth_components, lambda_arn)
        
        # Configure deployment result
        result = {
            'lambda_arn': lambda_arn,
            'gateway_id': runtime_result['gateway_id'],
            'gateway_url': runtime_result['gateway_url'],
            'target_id': runtime_result['target_id'],
            'user_pool_id': auth_components['user_pool_id'],
            'client_id': auth_components['client_id'],
            'client_secret': auth_components['client_secret'],
            'region': Config.REGION,
            'iam_role_name': iam_role_name,
            'deployed_at': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save deployment information
        info_file = save_deployment_info(result)
        
        print(f"\n🎉 Gateway Deployment Complete!")
        print(f"🌐 Gateway URL: {result['gateway_url']}")
        print(f"📄 Deployment Info: {info_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ Gateway Deployment Failed: {e}")
        raise

if __name__ == "__main__":
    main()