"""
cleanup.py

Portfolio Architect System Cleanup Script
Delete and clean up all AWS resources
"""

import json
import boto3
import time
import sys
from pathlib import Path

# Config classes no longer needed - use region information directly from deployment info

def load_deployment_info():
    """Load deployment information"""
    current_dir = Path(__file__).parent
    
    # Portfolio Architect information
    portfolio_info = None
    portfolio_file = current_dir / "deployment_info.json"
    if portfolio_file.exists():
        with open(portfolio_file) as f:
            portfolio_info = json.load(f)
    
    # MCP Server information
    mcp_info = None
    mcp_file = current_dir / "mcp_server" / "mcp_deployment_info.json"
    if mcp_file.exists():
        with open(mcp_file) as f:
            mcp_info = json.load(f)
    
    return portfolio_info, mcp_info

def delete_runtime(agent_arn, region):
    """Delete Runtime"""
    try:
        runtime_id = agent_arn.split('/')[-1]
        client = boto3.client('bedrock-agentcore-control', region_name=region)
        client.delete_agent_runtime(agentRuntimeId=runtime_id)
        print(f"✅ Runtime deleted: {runtime_id} (region: {region})")
        return True
    except Exception as e:
        print(f"⚠️ Runtime deletion failed: {e}")
        return False

def delete_ecr_repo(repo_name, region):
    """Delete ECR repository"""
    try:
        ecr = boto3.client('ecr', region_name=region)
        ecr.delete_repository(repositoryName=repo_name, force=True)
        print(f"✅ ECR deleted: {repo_name} (region: {region})")
        return True
    except Exception as e:
        print(f"⚠️ ECR deletion failed {repo_name}: {e}")
        return False

def delete_iam_role(role_name):
    """Delete IAM role"""
    try:
        iam = boto3.client('iam')
        
        # Delete inline policies
        policies = iam.list_role_policies(RoleName=role_name)
        for policy in policies['PolicyNames']:
            iam.delete_role_policy(RoleName=role_name, PolicyName=policy)
        
        # Detach managed policies
        attached_policies = iam.list_attached_role_policies(RoleName=role_name)
        for policy in attached_policies['AttachedPolicies']:
            iam.detach_role_policy(RoleName=role_name, PolicyArn=policy['PolicyArn'])
        
        # Delete role
        iam.delete_role(RoleName=role_name)
        print(f"✅ IAM role deleted: {role_name}")
        return True
    except Exception as e:
        print(f"⚠️ IAM role deletion failed {role_name}: {e}")
        return False



def delete_cognito_resources(user_pool_id, region):
    """Delete Cognito resources"""
    try:
        cognito = boto3.client('cognito-idp', region_name=region)
        
        # 1. Delete all clients first
        try:
            clients = cognito.list_user_pool_clients(UserPoolId=user_pool_id)
            for client in clients['UserPoolClients']:
                cognito.delete_user_pool_client(
                    UserPoolId=user_pool_id,
                    ClientId=client['ClientId']
                )
                print(f"✅ Cognito Client deleted: {client['ClientId']}")
        except Exception as e:
            print(f"⚠️ Client deletion failed: {e}")
        
        # 1.5. Delete resource servers
        try:
            # List and delete resource servers
            response = cognito.list_resource_servers(UserPoolId=user_pool_id, MaxResults=50)
            for resource_server in response.get('ResourceServers', []):
                cognito.delete_resource_server(
                    UserPoolId=user_pool_id,
                    Identifier=resource_server['Identifier']
                )
                print(f"✅ Resource Server deleted: {resource_server['Identifier']}")
        except Exception as e:
            print(f"⚠️ Resource server deletion failed: {e}")
        
        # 2. Delete domain if exists
        try:
            user_pool_details = cognito.describe_user_pool(UserPoolId=user_pool_id)
            domain = user_pool_details.get("UserPool", {}).get("Domain")
            
            if domain:
                cognito.delete_user_pool_domain(Domain=domain, UserPoolId=user_pool_id)
                print(f"✅ Cognito Domain deleted: {domain}")
                time.sleep(5)  # Wait for domain deletion
        except Exception as e:
            print(f"⚠️ Domain deletion failed (may not exist): {e}")
        
        # 3. Disable deletion protection if enabled
        try:
            cognito.update_user_pool(
                UserPoolId=user_pool_id,
                DeletionProtection='INACTIVE'
            )
            print(f"✅ Deletion protection disabled for: {user_pool_id}")
        except Exception as e:
            print(f"⚠️ Deletion protection update failed: {e}")
        
        # 4. Delete User Pool
        cognito.delete_user_pool(UserPoolId=user_pool_id)
        print(f"✅ Cognito User Pool deleted: {user_pool_id} (region: {region})")
        return True
    except Exception as e:
        print(f"⚠️ Cognito deletion failed: {e}")
        return False

def cleanup_local_files():
    """Delete locally generated files"""
    current_dir = Path(__file__).parent
    files_to_delete = [
        current_dir / "deployment_info.json",
        current_dir / "Dockerfile",
        current_dir / ".dockerignore", 
        current_dir / ".bedrock_agentcore.yaml",
        current_dir / "mcp_server" / "mcp_deployment_info.json",
        current_dir / "mcp_server" / "Dockerfile",
        current_dir / "mcp_server" / ".dockerignore",
        current_dir / "mcp_server" / ".bedrock_agentcore.yaml",
    ]
    
    deleted_count = 0
    for file_path in files_to_delete:
        if file_path.exists():
            file_path.unlink()
            print(f"✅ File deleted: {file_path.name}")
            deleted_count += 1
    
    if deleted_count > 0:
        print(f"✅ Local file cleanup complete! ({deleted_count} files deleted)")
    else:
        print("📁 No local files to delete.")



def main():
    print("🧹 Portfolio Architect System Cleanup")
    
    # Load deployment information
    portfolio_info, mcp_info = load_deployment_info()
    
    if not portfolio_info and not mcp_info:
        print("⚠️ No deployment information found.")
        return
    
    # Confirmation
    response = input("\nAre you sure you want to delete all resources? (y/N): ")
    if response.lower() != 'y':
        print("❌ Cancelled")
        return
    
    print("\n🗑️ Deleting AWS resources...")
    
    # 1. Delete Portfolio Architect Runtime
    if portfolio_info and 'agent_arn' in portfolio_info:
        region = portfolio_info.get('region', 'us-west-2')  # Default fallback
        delete_runtime(portfolio_info['agent_arn'], region)
    
    # 2. Delete MCP Server Runtime
    if mcp_info and 'agent_arn' in mcp_info:
        region = mcp_info.get('region', 'us-west-2')  # Default fallback
        delete_runtime(mcp_info['agent_arn'], region)
    
    # 3. Delete ECR repositories
    if portfolio_info and 'ecr_repo_name' in portfolio_info and portfolio_info['ecr_repo_name']:
        region = portfolio_info.get('region', 'us-west-2')
        delete_ecr_repo(portfolio_info['ecr_repo_name'], region)
    
    if mcp_info and 'ecr_repo_name' in mcp_info and mcp_info['ecr_repo_name']:
        region = mcp_info.get('region', 'us-west-2')
        delete_ecr_repo(mcp_info['ecr_repo_name'], region)
    
    # 4. Delete IAM roles (IAM is global service, no region needed)
    if portfolio_info and 'iam_role_name' in portfolio_info:
        delete_iam_role(portfolio_info['iam_role_name'])
    
    if mcp_info and 'iam_role_name' in mcp_info:
        delete_iam_role(mcp_info['iam_role_name'])
    
    # 5. Delete Cognito resources
    if mcp_info and 'user_pool_id' in mcp_info:
        region = mcp_info.get('region', 'us-west-2')
        delete_cognito_resources(mcp_info['user_pool_id'], region)
    
    print("\n🎉 AWS resource cleanup complete!")
    
    # 6. Clean up local files
    if input("\nDo you also want to delete locally generated files? (y/N): ").lower() == 'y':
        cleanup_local_files()
    else:
        print("📁 Local files will be preserved.")

if __name__ == "__main__":
    main()