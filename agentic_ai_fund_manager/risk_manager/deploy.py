"""
deploy.py

Risk Manager Deployment Script
AgentCore Runtime deployment for Risk Manager
"""

import sys
import time
import json
from pathlib import Path
from bedrock_agentcore_starter_toolkit import Runtime

# Add common configuration and shared module paths
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))
sys.path.insert(0, str(root_path / "shared"))

from config import Config as GlobalConfig
from runtime_utils import create_agentcore_runtime_role

class Config:
    """Risk Manager deployment configuration"""
    REGION = GlobalConfig.REGION
    AGENT_NAME = GlobalConfig.RISK_MANAGER_NAME

def load_gateway_info():
    """Load Gateway deployment information"""
    info_file = Path(__file__).parent / "gateway" / "gateway_deployment_info.json"
    if not info_file.exists():
        print("❌ Gateway deployment information not found.")
        print("💡 Please run the following commands first:")
        print("   cd lambda_layer && python deploy_lambda_layer.py")
        print("   cd ../lambda && python deploy_lambda.py") 
        print("   cd ../gateway && python deploy_gateway.py")
        raise FileNotFoundError("Please deploy Gateway first.")
    
    with open(info_file) as f:
        return json.load(f)

def deploy_risk_manager(gateway_info):
    """Deploy Risk Manager Runtime"""
    print("🎯 Deploying Risk Manager...")
    
    # Create IAM role
    iam_role = create_agentcore_runtime_role(Config.AGENT_NAME, Config.REGION)
    iam_role_name = iam_role['Role']['RoleName']
    
    # Configure Runtime
    current_dir = Path(__file__).parent
    runtime = Runtime()
    runtime.configure(
        entrypoint=str(current_dir / "risk_manager.py"),
        execution_role=iam_role['Role']['Arn'],
        auto_create_ecr=True,
        requirements_file=str(current_dir / "requirements.txt"),
        region=Config.REGION,
        agent_name=Config.AGENT_NAME
    )
    
    # Set environment variables
    env_vars = {
        "MCP_CLIENT_ID": gateway_info['client_id'],
        "MCP_CLIENT_SECRET": gateway_info['client_secret'],
        "MCP_GATEWAY_URL": gateway_info['gateway_url'],
        "MCP_USER_POOL_ID": gateway_info['user_pool_id'],
        "MCP_TARGET_ID": gateway_info.get('target_id', 'target-risk-manager'),
        "AWS_REGION": Config.REGION
    }
    
    # Execute deployment
    launch_result = runtime.launch(auto_update_on_conflict=True, env_vars=env_vars)
    
    # Wait for deployment completion
    for i in range(30):  # Maximum 15 minutes wait
        try:
            status = runtime.status().endpoint['status']
            print(f"📊 Status: {status} ({i*30} seconds elapsed)")
            if status in ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']:
                break
        except Exception as e:
            print(f"⚠️ Status check error: {e}")
        time.sleep(30)
    
    if status != 'READY':
        raise Exception(f"Deployment failed: {status}")
    
    # Extract ECR repository name
    ecr_repo_name = None
    if hasattr(launch_result, 'ecr_uri') and launch_result.ecr_uri:
        ecr_repo_name = launch_result.ecr_uri.split('/')[-1].split(':')[0]
    
    return {
        "agent_arn": launch_result.agent_arn,
        "agent_id": launch_result.agent_id,
        "region": Config.REGION,
        "iam_role_name": iam_role_name,
        "ecr_repo_name": ecr_repo_name
    }

def save_deployment_info(gateway_info, agent_info):
    """Save deployment information"""
    deployment_info = {
        "agent_name": Config.AGENT_NAME,
        "agent_arn": agent_info["agent_arn"],
        "agent_id": agent_info["agent_id"],
        "region": Config.REGION,
        "iam_role_name": agent_info["iam_role_name"],
        "ecr_repo_name": agent_info.get("ecr_repo_name"),
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    info_file = Path(__file__).parent / "deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    return str(info_file)

def main():
    try:
        print("🚀 Risk Manager Runtime Deployment")
        
        # Load Gateway information (required)
        gateway_info = load_gateway_info()
        print("✅ Gateway information loading complete")
        
        # Deploy Risk Manager
        agent_info = deploy_risk_manager(gateway_info)
        
        # Save deployment information
        info_file = save_deployment_info(gateway_info, agent_info)
        
        print(f"\n🎉 Deployment Complete!")
        print(f"📄 Deployment Info: {info_file}")
        print(f"🔗 Risk Manager ARN: {agent_info['agent_arn']}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Deployment Failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())