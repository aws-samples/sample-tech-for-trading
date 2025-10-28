"""
cleanup.py

Financial Analyst System Cleanup Script
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
    info_file = Path(__file__).parent / "deployment_info.json"
    if info_file.exists():
        with open(info_file) as f:
            return json.load(f)
    return None

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

def cleanup_local_files():
    """Delete locally generated files"""
    current_dir = Path(__file__).parent
    files_to_delete = [
        current_dir / "deployment_info.json",
        current_dir / "Dockerfile",
        current_dir / ".dockerignore", 
        current_dir / ".bedrock_agentcore.yaml",
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
    print("🧹 Financial Analyst System Cleanup")
    
    # Load deployment information
    deployment_info = load_deployment_info()
    
    if not deployment_info:
        print("⚠️ No deployment information found.")
        return
    
    # Confirmation
    response = input("\nAre you sure you want to delete all resources? (y/N): ")
    if response.lower() != 'y':
        print("❌ Cancelled")
        return
    
    print("\n🗑️ Deleting AWS resources...")
    
    # 1. Delete Financial Analyst Runtime
    if 'agent_arn' in deployment_info:
        region = deployment_info.get('region', 'us-west-2')  # Default fallback
        delete_runtime(deployment_info['agent_arn'], region)
    
    # 2. Delete ECR repository
    if 'ecr_repo_name' in deployment_info and deployment_info['ecr_repo_name']:
        region = deployment_info.get('region', 'us-west-2')
        delete_ecr_repo(deployment_info['ecr_repo_name'], region)
    
    # 3. Delete IAM role (IAM is global service, no region needed)
    if 'iam_role_name' in deployment_info:
        delete_iam_role(deployment_info['iam_role_name'])
    
    print("\n🎉 AWS resource cleanup complete!")
    
    # 4. Clean up local files
    if input("\nDo you also want to delete locally generated files? (y/N): ").lower() == 'y':
        cleanup_local_files()
    else:
        print("📁 Local files will be preserved.")

if __name__ == "__main__":
    main()