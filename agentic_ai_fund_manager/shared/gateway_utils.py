"""
gateway_utils.py
Common utility functions for AgentCore Gateway

This module provides functions needed for AWS Bedrock AgentCore Gateway deployment.
- IAM role creation for Gateway
- Gateway creation and management
- Gateway Target creation
"""

import boto3
import json
import time


def create_agentcore_gateway_role(gateway_name, region):
    """
    Create IAM role for AgentCore Gateway
    
    Creates an IAM role with necessary permissions for Gateway to invoke
    Lambda functions and access other AWS services.
    
    Args:
        gateway_name (str): Gateway name (included in role name)
        region (str): AWS region
        
    Returns:
        dict: Created IAM role information
    """
    print("🔐 Creating Gateway IAM role...")
    
    iam_client = boto3.client('iam')
    agentcore_gateway_role_name = f'{gateway_name}-role'
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    
    # Permission policy for Gateway usage
    role_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "GatewayPermissions",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:*",
                "bedrock:*",
                "agent-credential-provider:*",
                "iam:PassRole",
                "secretsmanager:GetSecretValue",
                "lambda:InvokeFunction"
            ],
            "Resource": "*"
        }]
    }
    
    # Trust policy allowing Bedrock AgentCore service to use this role
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AssumeRolePolicy",
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock-agentcore.amazonaws.com"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": f"{account_id}"
                },
                "ArnLike": {
                    "aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"
                }
            }
        }]
    }

    assume_role_policy_document_json = json.dumps(assume_role_policy_document)
    role_policy_document = json.dumps(role_policy)
    
    try:
        # Create new IAM role
        agentcore_gateway_iam_role = iam_client.create_role(
            RoleName=agentcore_gateway_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json,
            Description='AgentCore Gateway execution role for Lambda invocation and AWS service access'
        )
        print("✅ New IAM role creation complete")
        time.sleep(10)
        
    except iam_client.exceptions.EntityAlreadyExistsException:
        print("♻️ Deleting existing role and recreating...")
        
        # Delete existing inline policies
        policies = iam_client.list_role_policies(
            RoleName=agentcore_gateway_role_name,
            MaxItems=100
        )
        
        for policy_name in policies['PolicyNames']:
            iam_client.delete_role_policy(
                RoleName=agentcore_gateway_role_name,
                PolicyName=policy_name
            )
        
        # Delete existing role
        iam_client.delete_role(RoleName=agentcore_gateway_role_name)
        
        # Create new role
        agentcore_gateway_iam_role = iam_client.create_role(
            RoleName=agentcore_gateway_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json,
            Description='AgentCore Gateway execution role for Lambda invocation and AWS service access'
        )
        print("✅ Role recreation complete")

    # Attach permission policy
    try:
        iam_client.put_role_policy(
            PolicyDocument=role_policy_document,
            PolicyName="AgentCorePolicy",
            RoleName=agentcore_gateway_role_name
        )
        print("✅ Permission policy attachment complete")
    except Exception as e:
        print(f"⚠️ Policy attachment error: {e}")

    return agentcore_gateway_iam_role


def delete_existing_gateway(gateway_name, region):
    """
    Delete existing Gateway (delete Targets first)
    
    Args:
        gateway_name (str): Gateway name to delete
        region (str): AWS region
    """
    try:
        print("🔍 Checking existing Gateway...")
        gateway_client = boto3.client('bedrock-agentcore-control', region_name=region)
        gateways = gateway_client.list_gateways().get('items', [])

        for gw in gateways:
            if gw['name'] == gateway_name:
                gateway_id = gw['gatewayId']
                print(f"🗑️ Deleting existing Gateway: {gateway_id}")
                
                # Delete Targets first
                targets = gateway_client.list_gateway_targets(gatewayIdentifier=gateway_id).get('items', [])
                for target in targets:
                    print(f"🗑️ Deleting Target: {target['targetId']}")
                    gateway_client.delete_gateway_target(
                        gatewayIdentifier=gateway_id,
                        targetId=target['targetId']
                    )
                
                time.sleep(3)
                
                # Delete Gateway
                gateway_client.delete_gateway(gatewayIdentifier=gateway_id)
                print("✅ Existing Gateway deletion complete")
                time.sleep(3)
                break
        else:
            print("ℹ️ No existing Gateway to delete")
                
    except Exception as e:
        print(f"⚠️ Error during Gateway deletion (ignoring and proceeding): {str(e)}")
        pass


def create_gateway(gateway_name, role_arn, auth_components, region):
    """
    Create AgentCore Gateway
    
    Args:
        gateway_name (str): Gateway name
        role_arn (str): IAM role ARN for Gateway execution
        auth_components (dict): Cognito authentication components
        region (str): AWS region
        
    Returns:
        dict: Created Gateway information
    """
    print("🌉 Creating Gateway...")
    gateway_client = boto3.client('bedrock-agentcore-control', region_name=region)
    
    # JWT authentication configuration
    auth_config = {
        'customJWTAuthorizer': {
            'allowedClients': [auth_components['client_id']],
            'discoveryUrl': auth_components['discovery_url']
        }
    }
    
    gateway = gateway_client.create_gateway(
        name=gateway_name,
        roleArn=role_arn,
        protocolType='MCP',
        authorizerType='CUSTOM_JWT',
        authorizerConfiguration=auth_config,
        description=f'{gateway_name} - MCP Gateway for AI agent integration'
    )
    
    print(f"✅ Gateway creation complete: {gateway['gatewayId']}")
    return gateway


def create_gateway_target(gateway_id, target_name, target_config, region):
    """
    Create Gateway Target (expose Lambda functions as MCP tools)
    
    Args:
        gateway_id (str): Gateway ID
        target_name (str): Target name
        target_config (dict): Target configuration
        region (str): AWS region
        
    Returns:
        dict: Created Target information
    """
    print("🎯 Creating Gateway Target...")
    gateway_client = boto3.client('bedrock-agentcore-control', region_name=region)
    
    tool_count = len(target_config["mcp"]["lambda"]["toolSchema"]["inlinePayload"])
    print(f"📋 Target configuration: {tool_count} tools configured")
    
    # Create Gateway Target
    target = gateway_client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name=target_name,
        targetConfiguration=target_config,
        credentialProviderConfigurations=[{
            'credentialProviderType': 'GATEWAY_IAM_ROLE'
        }]
    )
    
    print(f"✅ Gateway Target creation complete: {target['targetId']}")
    return target