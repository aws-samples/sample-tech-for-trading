"""
cognito_utils.py
Common utility functions for Cognito authentication

This module provides all functions needed for OAuth2 authentication using AWS Cognito.
- User Pool management
- Resource Server management  
- M2M Client management
- OAuth2 token acquisition
"""

import boto3
import requests
import time


def get_or_create_user_pool(cognito, user_pool_name, region):
    """
    Get or create Cognito User Pool
    
    Args:
        cognito: Cognito client
        user_pool_name (str): User pool name
        region (str): AWS region
    
    Returns:
        str: User pool ID
    """
    print("🔍 Checking Cognito User Pool...")
    
    # Check existing user pools
    response = cognito.list_user_pools(MaxResults=60)
    for pool in response["UserPools"]:
        if pool["Name"] == user_pool_name:
            user_pool_id = pool["Id"]
            print(f"♻️ Using existing user pool: {user_pool_id}")
            return user_pool_id
    
    # Create new user pool
    print("🆕 Creating new user pool...")
    created = cognito.create_user_pool(
        PoolName=user_pool_name,
        DeletionProtection='INACTIVE'  # Disable deletion protection for easier cleanup
    )
    user_pool_id = created["UserPool"]["Id"]
    
    # Create domain
    domain_prefix = user_pool_id.replace("_", "").lower()
    try:
        cognito.create_user_pool_domain(
            Domain=domain_prefix,
            UserPoolId=user_pool_id
        )
    except cognito.exceptions.InvalidParameterException:
        # Ignore if domain already exists
        pass
    
    print(f"✅ User pool creation complete: {user_pool_id}")
    return user_pool_id


def get_or_create_resource_server(cognito, user_pool_id, resource_server_id, resource_server_name, scopes):
    """
    Get or create Cognito Resource Server
    
    Args:
        cognito: Cognito client
        user_pool_id (str): Cognito User Pool ID
        resource_server_id (str): Resource server identifier
        resource_server_name (str): Resource server name
        scopes (list): Scope list
    
    Returns:
        str: Resource server ID
    """
    print("🔍 Checking resource server...")
    
    try:
        cognito.describe_resource_server(
            UserPoolId=user_pool_id,
            Identifier=resource_server_id
        )
        print(f"♻️ Using existing resource server: {resource_server_id}")
        return resource_server_id
        
    except cognito.exceptions.ResourceNotFoundException:
        print("🆕 Creating new resource server...")
        cognito.create_resource_server(
            UserPoolId=user_pool_id,
            Identifier=resource_server_id,
            Name=resource_server_name,
            Scopes=scopes
        )
        print(f"✅ Resource server creation complete: {resource_server_id}")
        return resource_server_id


def get_or_create_m2m_client(cognito, user_pool_id, client_name, resource_server_id, scope_names=None):
    """
    Get or create Machine-to-Machine client
    
    Args:
        cognito: Cognito client
        user_pool_id (str): User pool ID
        client_name (str): Client name
        resource_server_id (str): Resource server ID
        scope_names (list): Scope name list (default: ["read", "write"])
    
    Returns:
        tuple: (client ID, client secret)
    """
    print("🔍 Checking M2M client...")
    
    if scope_names is None:
        scope_names = ["read", "write"]
    
    # Check existing clients
    response = cognito.list_user_pool_clients(UserPoolId=user_pool_id, MaxResults=60)
    for client in response["UserPoolClients"]:
        if client["ClientName"] == client_name:
            describe = cognito.describe_user_pool_client(
                UserPoolId=user_pool_id, 
                ClientId=client["ClientId"]
            )
            client_id = client["ClientId"]
            client_secret = describe["UserPoolClient"]["ClientSecret"]
            print(f"♻️ Using existing M2M client: {client_id}")
            return client_id, client_secret
    
    # Generate scope strings
    oauth_scopes = [f"{resource_server_id}/{scope}" for scope in scope_names]
    
    # Create new M2M client
    print("🆕 Creating new M2M client...")
    created = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=client_name,
        GenerateSecret=True,
        AllowedOAuthFlows=["client_credentials"],
        AllowedOAuthScopes=oauth_scopes,
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
        ExplicitAuthFlows=["ALLOW_REFRESH_TOKEN_AUTH"]
    )
    
    client_id = created["UserPoolClient"]["ClientId"]
    client_secret = created["UserPoolClient"]["ClientSecret"]
    print(f"✅ M2M client creation complete: {client_id}")
    
    return client_id, client_secret


def get_token(user_pool_id, client_id, client_secret, scope_string, region):
    """
    Acquire Cognito OAuth2 token
    
    Args:
        user_pool_id (str): Cognito User Pool ID
        client_id (str): Client ID
        client_secret (str): Client secret
        scope_string (str): OAuth2 scope string
        region (str): AWS region
    
    Returns:
        dict: Token information or error message
    """
    try:
        # Generate domain from User Pool ID (same method as get_or_create_user_pool)
        domain_prefix = user_pool_id.replace("_", "").lower()
        url = f"https://{domain_prefix}.auth.{region}.amazoncognito.com/oauth2/token"
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope_string,
        }

        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as err:
        return {"error": str(err)}