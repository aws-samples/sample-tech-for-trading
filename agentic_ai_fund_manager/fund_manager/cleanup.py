"""
cleanup.py

Fund Manager System Cleanup Script
Delete and clean up all AWS resources
"""

import json
import boto3
import time
import sys
from pathlib import Path

def load_deployment_info():
    """Load deployment information"""
    current_dir = Path(__file__).parent
    
    # Fund Manager information
    advisor_info = None
    advisor_file = current_dir / "deployment_info.json"
    if advisor_file.exists():
        with open(advisor_file) as f:
            advisor_info = json.load(f)
    
    # Memory information
    memory_info = None
    memory_file = current_dir / "agentcore_memory" / "deployment_info.json"
    if memory_file.exists():
        with open(memory_file) as f:
            memory_info = json.load(f)
    
    return advisor_info, memory_info

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
        
        # Delete policies
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

def delete_memory(memory_id, region):
    """Delete AgentCore Memory"""
    try:
        from bedrock_agentcore.memory import MemoryClient
        memory_client = MemoryClient(region_name=region)
        memory_client.delete_memory(memory_id=memory_id)
        print(f"✅ Memory deleted: {memory_id} (region: {region})")
        return True
    except Exception as e:
        print(f"⚠️ Memory deletion failed: {e}")
        return False

def cleanup_local_files():
    """Delete locally generated files"""
    current_dir = Path(__file__).parent
    files_to_delete = [
        current_dir / "deployment_info.json",
        current_dir / "Dockerfile",
        current_dir / ".dockerignore", 
        current_dir / ".bedrock_agentcore.yaml",
        current_dir / "agentcore_memory" / "deployment_info.json",
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
    print("🧹 Fund Manager System Cleanup")
    
    # Load deployment information
    advisor_info, memory_info = load_deployment_info()
    
    if not advisor_info and not memory_info:
        print("⚠️ No deployment information found.")
        return
    
    # Confirmation
    response = input("\nAre you sure you want to delete all resources? (y/N): ")
    if response.lower() != 'y':
        print("❌ Cancelled")
        return
    
    print("\n🗑️ Deleting AWS resources...")
    
    # 1. Delete Fund Manager Runtime
    if advisor_info and 'agent_arn' in advisor_info:
        region = advisor_info.get('region', 'us-west-2')
        delete_runtime(advisor_info['agent_arn'], region)
    
    # 2. Delete ECR repository
    if advisor_info and 'ecr_repo_name' in advisor_info and advisor_info['ecr_repo_name']:
        region = advisor_info.get('region', 'us-west-2')
        delete_ecr_repo(advisor_info['ecr_repo_name'], region)
    
    # 3. Delete IAM role
    if advisor_info and 'iam_role_name' in advisor_info:
        delete_iam_role(advisor_info['iam_role_name'])
    
    # 4. Delete AgentCore Memory
    if memory_info and 'memory_id' in memory_info:
        region = memory_info.get('region', 'us-west-2')
        delete_memory(memory_info['memory_id'], region)
    
    print("\n🎉 AWS resource cleanup complete!")
    
    # 5. Clean up local files
    if input("\nDo you also want to delete locally generated files? (y/N): ").lower() == 'y':
        cleanup_local_files()
    else:
        print("📁 Local files will be preserved.")

if __name__ == "__main__":
    main()