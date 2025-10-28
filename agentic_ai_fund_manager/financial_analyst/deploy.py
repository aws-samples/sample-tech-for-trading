"""
deploy.py

Financial Analyst Deployment Script
AgentCore Runtime deployment for Financial Analyst
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
    """Financial Analyst deployment configuration"""
    REGION = GlobalConfig.REGION
    AGENT_NAME = GlobalConfig.FINANCIAL_ANALYST_NAME

def deploy_financial_analyst():
    """Deploy Financial Analyst Runtime"""
    print("🎯 Deploying Financial Analyst...")
    
    # Create IAM role
    iam_role = create_agentcore_runtime_role(Config.AGENT_NAME, Config.REGION)
    iam_role_name = iam_role['Role']['RoleName']
    
    # Configure Runtime
    current_dir = Path(__file__).parent
    runtime = Runtime()
    runtime.configure(
        entrypoint=str(current_dir / "financial_analyst.py"),
        execution_role=iam_role['Role']['Arn'],
        auto_create_ecr=True,
        requirements_file=str(current_dir / "requirements.txt"),
        region=Config.REGION,
        agent_name=Config.AGENT_NAME
    )
    
    # Execute deployment
    launch_result = runtime.launch(auto_update_on_conflict=True)
    
    # Wait for deployment completion
    for i in range(30):
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

def save_deployment_info(agent_info):
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
        print("🚀 Financial Analyst Runtime Deployment")
        
        # Deploy Financial Analyst
        agent_info = deploy_financial_analyst()
        
        # Save deployment information
        info_file = save_deployment_info(agent_info)
        
        print(f"\n🎉 Deployment Complete!")
        print(f"📄 Deployment Info: {info_file}")
        print(f"🔗 Financial Analyst ARN: {agent_info['agent_arn']}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Deployment Failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())