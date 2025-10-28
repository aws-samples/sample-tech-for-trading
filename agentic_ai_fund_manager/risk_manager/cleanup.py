"""
cleanup.py

Risk Manager System Cleanup Script
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
    
    # Risk Manager information
    risk_manager_info = None
    risk_manager_file = current_dir / "deployment_info.json"
    if risk_manager_file.exists():
        with open(risk_manager_file) as f:
            risk_manager_info = json.load(f)
    
    # Gateway information
    gateway_info = None
    gateway_file = current_dir / "gateway" / "gateway_deployment_info.json"
    if gateway_file.exists():
        with open(gateway_file) as f:
            gateway_info = json.load(f)
    
    # Lambda information
    lambda_info = None
    lambda_file = current_dir / "lambda" / "lambda_deployment_info.json"
    if lambda_file.exists():
        with open(lambda_file) as f:
            lambda_info = json.load(f)
    
    # Lambda Layer information
    layer_info = None
    layer_file = current_dir / "lambda_layer" / "layer_deployment_info.json"
    if layer_file.exists():
        with open(layer_file) as f:
            layer_info = json.load(f)
    
    return risk_manager_info, gateway_info, lambda_info, layer_info

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

def delete_gateway(gateway_id, region):
    """Delete Gateway"""
    try:
        client = boto3.client('bedrock-agentcore-control', region_name=region)
        
        # Delete targets first
        targets = client.list_gateway_targets(gatewayIdentifier=gateway_id).get('items', [])
        for target in targets:
            client.delete_gateway_target(
                gatewayIdentifier=gateway_id,
                targetId=target['targetId']
            )
        
        time.sleep(3)
        client.delete_gateway(gatewayIdentifier=gateway_id)
        print(f"✅ Gateway deleted: {gateway_id} (region: {region})")
        return True
    except Exception as e:
        print(f"⚠️ Gateway deletion failed: {e}")
        return False

def delete_lambda_function(function_name, region):
    """Delete Lambda function"""
    try:
        lambda_client = boto3.client('lambda', region_name=region)
        lambda_client.delete_function(FunctionName=function_name)
        print(f"✅ Lambda function deleted: {function_name} (region: {region})")
        return True
    except Exception as e:
        print(f"⚠️ Lambda function deletion failed: {e}")
        return False

def delete_lambda_layer(layer_name, region):
    """Delete Lambda Layer"""
    try:
        lambda_client = boto3.client('lambda', region_name=region)
        
        # List all versions of the layer
        versions = lambda_client.list_layer_versions(LayerName=layer_name)
        
        # Delete each version
        for version in versions['LayerVersions']:
            version_number = version['Version']
            lambda_client.delete_layer_version(
                LayerName=layer_name,
                VersionNumber=version_number
            )
            print(f"✅ Lambda Layer version deleted: {layer_name} v{version_number}")
        
        return True
    except Exception as e:
        print(f"⚠️ Lambda Layer deletion failed {layer_name}: {e}")
        return False

def delete_s3_bucket(bucket_name, region):
    """Delete S3 bucket (including objects)"""
    try:
        s3 = boto3.client('s3', region_name=region)
        
        # Check if bucket exists
        try:
            s3.head_bucket(Bucket=bucket_name)
        except:
            print(f"ℹ️ S3 bucket does not exist: {bucket_name}")
            return True
        
        # Delete all objects in bucket
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                objects = [{'Key': obj['Key']} for obj in page['Contents']]
                s3.delete_objects(Bucket=bucket_name, Delete={'Objects': objects})
        
        # Delete bucket
        s3.delete_bucket(Bucket=bucket_name)
        print(f"✅ S3 bucket deleted: {bucket_name} (region: {region})")
        return True
    except Exception as e:
        print(f"⚠️ S3 bucket deletion failed {bucket_name}: {e}")
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
        current_dir / "gateway" / "gateway_deployment_info.json",
        current_dir / "lambda" / "lambda_deployment_info.json",
        current_dir / "lambda_layer" / "layer_deployment_info.json",
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
    print("🧹 Risk Manager System Cleanup")
    
    # Load deployment information
    risk_manager_info, gateway_info, lambda_info, layer_info = load_deployment_info()
    
    if not risk_manager_info and not gateway_info and not lambda_info and not layer_info:
        print("⚠️ No deployment information found.")
        return
    
    # Confirmation
    response = input("\nAre you sure you want to delete all resources? (y/N): ")
    if response.lower() != 'y':
        print("❌ Cancelled")
        return
    
    print("\n🗑️ Deleting AWS resources...")
    
    # 1. Delete Risk Manager Runtime
    if risk_manager_info and 'agent_arn' in risk_manager_info:
        region = risk_manager_info.get('region', 'us-west-2')
        delete_runtime(risk_manager_info['agent_arn'], region)
    
    # 2. Delete Gateway
    if gateway_info and 'gateway_id' in gateway_info:
        region = gateway_info.get('region', 'us-west-2')
        delete_gateway(gateway_info['gateway_id'], region)
    
    # 3. Delete Lambda function
    if lambda_info and 'function_name' in lambda_info:
        region = lambda_info.get('region', 'us-west-2')
        delete_lambda_function(lambda_info['function_name'], region)
    
    # 4. Delete Lambda Layer
    if layer_info and 'layer_name' in layer_info:
        region = layer_info.get('region', 'us-west-2')
        delete_lambda_layer(layer_info['layer_name'], region)
    
    # 5. Delete S3 bucket (for Layer deployment)
    if layer_info and 's3_bucket' in layer_info:
        region = layer_info.get('region', 'us-west-2')
        delete_s3_bucket(layer_info['s3_bucket'], region)
    
    # 6. Delete ECR repository
    if risk_manager_info and 'ecr_repo_name' in risk_manager_info and risk_manager_info['ecr_repo_name']:
        region = risk_manager_info.get('region', 'us-west-2')
        delete_ecr_repo(risk_manager_info['ecr_repo_name'], region)
    
    # 7. Delete IAM roles
    if risk_manager_info and 'iam_role_name' in risk_manager_info:
        delete_iam_role(risk_manager_info['iam_role_name'])
    
    if gateway_info and 'iam_role_name' in gateway_info:
        delete_iam_role(gateway_info['iam_role_name'])
    
    # Lambda role uses auto-generated name pattern
    if lambda_info and 'function_name' in lambda_info:
        lambda_role_name = f"{lambda_info['function_name']}-role"
        delete_iam_role(lambda_role_name)
    
    # 8. Delete Cognito resources
    if gateway_info and 'user_pool_id' in gateway_info:
        region = gateway_info.get('region', 'us-west-2')
        delete_cognito_resources(gateway_info['user_pool_id'], region)
    
    print("\n🎉 AWS resource cleanup complete!")
    
    # 9. Clean up local files
    if input("\nDo you also want to delete locally generated files? (y/N): ").lower() == 'y':
        cleanup_local_files()
    else:
        print("📁 Local files will be preserved.")

if __name__ == "__main__":
    main()