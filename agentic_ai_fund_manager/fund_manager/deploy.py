"""
deploy.py

Fund Manager Deployment Script
AgentCore Runtime deployment for Fund Manager
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
    """Fund Manager deployment configuration"""
    REGION = GlobalConfig.REGION
    AGENT_NAME = GlobalConfig.FUND_MANAGER_NAME

def load_agent_arns():
    """Load deployment information of other agents"""
    print("📋 Loading other agent deployment information...")
    
    base_path = Path(__file__).parent.parent
    agent_arns = {}
    
    # Required agent list
    required_agents = [
        ("financial_analyst", "Financial Analyst"),
        ("portfolio_architect", "Portfolio Architect"), 
        ("risk_manager", "Risk Manager")
    ]
    
    missing_agents = []
    for agent_dir, agent_name in required_agents:
        info_file = base_path / agent_dir / "deployment_info.json"
        
        if not info_file.exists():
            missing_agents.append(agent_name)
        else:
            with open(info_file, 'r') as f:
                deployment_info = json.load(f)
                agent_arns[agent_dir] = deployment_info["agent_arn"]
                print(f"✅ {agent_name}: {deployment_info['agent_arn']}")
    
    if missing_agents:
        raise FileNotFoundError(
            f"The following agents must be deployed first: {', '.join(missing_agents)}\n"
            "Run 'python deploy.py' in each agent folder."
        )
    
    return agent_arns

def load_memory_info():
    """Load AgentCore Memory deployment information"""
    print("🧠 Loading AgentCore Memory deployment information...")
    
    info_file = Path(__file__).parent / "agentcore_memory" / "deployment_info.json"
    
    if not info_file.exists():
        raise FileNotFoundError(
            "AgentCore Memory must be deployed first.\n"
            "Run the following command: cd agentcore_memory && python deploy_agentcore_memory.py"
        )
    
    with open(info_file, 'r') as f:
        memory_info = json.load(f)
        memory_id = memory_info["memory_id"]
        print(f"✅ Memory ID: {memory_id}")
        return memory_id

def create_iam_role_with_agent_permissions():
    """Create IAM role for Fund Manager (including permissions to call other agents)"""
    print("🔐 Creating Fund Manager IAM role...")
    
    # Create basic AgentCore Runtime role
    iam_role = create_agentcore_runtime_role(Config.AGENT_NAME, Config.REGION)
    iam_role_name = iam_role['Role']['RoleName']
    
    # Add permissions to call other agents
    _add_agent_call_permissions(iam_role_name)
    
    return iam_role['Role']['Arn'], iam_role_name

def _add_agent_call_permissions(role_name):
    """Add permissions to call other agents to IAM role"""
    print("🔐 Adding permissions to call other agents...")
    
    import boto3
    iam_client = boto3.client('iam')
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    
    additional_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:InvokeAgentRuntime",
                    "bedrock-agentcore:GetAgentRuntime"
                ],
                "Resource": [
                    f"arn:aws:bedrock-agentcore:{Config.REGION}:{account_id}:runtime/financial_analyst-*",
                    f"arn:aws:bedrock-agentcore:{Config.REGION}:{account_id}:runtime/portfolio_architect-*",
                    f"arn:aws:bedrock-agentcore:{Config.REGION}:{account_id}:runtime/risk_manager-*"
                ]
            }
        ]
    }
    
    try:
        iam_client.put_role_policy(
            PolicyDocument=json.dumps(additional_policy),
            PolicyName="FundManagerAgentCallsPolicy",
            RoleName=role_name
        )
        print("✅ Agent call permissions added successfully")
    except Exception as e:
        print(f"⚠️ Additional permission setup error: {e}")

def deploy_fund_manager(agent_arns, memory_id):
    """Deploy Fund Manager Runtime"""
    print("🎯 Deploying Fund Manager...")
    
    # Create IAM role (with permissions)
    role_arn, iam_role_name = create_iam_role_with_agent_permissions()
    
    # Configure Runtime
    current_dir = Path(__file__).parent
    runtime = Runtime()
    runtime.configure(
        entrypoint=str(current_dir / "fund_manager.py"),
        execution_role=role_arn,
        auto_create_ecr=True,
        requirements_file=str(current_dir / "requirements.txt"),
        region=Config.REGION,
        agent_name=Config.AGENT_NAME
    )
    
    # Set environment variables
    env_vars = {
        "FINANCIAL_ANALYST_ARN": agent_arns["financial_analyst"],
        "PORTFOLIO_ARCHITECT_ARN": agent_arns["portfolio_architect"],
        "RISK_MANAGER_ARN": agent_arns["risk_manager"],
        "FUND_MEMORY_ID": memory_id,
        "AWS_REGION": Config.REGION
    }
    
    # Execute deployment
    launch_result = runtime.launch(auto_update_on_conflict=True, env_vars=env_vars)
    
    # Wait for deployment completion
    for i in range(30):  # Wait up to 15 minutes
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

def save_deployment_info(agent_info, agent_arns):
    """Save deployment information"""
    deployment_info = {
        "agent_name": Config.AGENT_NAME,
        "agent_arn": agent_info["agent_arn"],
        "agent_id": agent_info["agent_id"],
        "region": Config.REGION,
        "iam_role_name": agent_info["iam_role_name"],
        "ecr_repo_name": agent_info.get("ecr_repo_name"),
        "dependent_agents": agent_arns,
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    info_file = Path(__file__).parent / "deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    return str(info_file)

def main():
    try:
        print("🚀 Fund Manager Runtime Deployment")
        
        # Load other agent ARNs
        agent_arns = load_agent_arns()
        
        # Load AgentCore Memory information
        memory_id = load_memory_info()
        
        # Deploy Fund Manager
        agent_info = deploy_fund_manager(agent_arns, memory_id)
        
        # Save deployment information
        info_file = save_deployment_info(agent_info, agent_arns)
        
        print(f"\n🎉 Deployment Complete!")
        print(f"📄 Deployment Info: {info_file}")
        print(f"🔗 Fund Manager ARN: {agent_info['agent_arn']}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Deployment Failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())