#!/usr/bin/env python3

import boto3
import json
import secrets
import string
from botocore.exceptions import ClientError

# Configuration
COGNITO_USER_POOL_ID = "us-east-1_eAn2oP0lv"
COGNITO_CLIENT_ID = "5jajojm4ullslg0cqu98ffcfaa"
REGION = "us-east-1"
TEST_USERNAME = "mcp-test-user"

def generate_temp_password():
    """Generate a temporary password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for i in range(12))
    return password

def create_test_user():
    """Create a test user in Cognito User Pool"""
    
    cognito_client = boto3.client('cognito-idp', region_name=REGION)
    
    try:
        # Check if user already exists
        try:
            user = cognito_client.admin_get_user(
                UserPoolId=COGNITO_USER_POOL_ID,
                Username=TEST_USERNAME
            )
            print(f"✅ Test user '{TEST_USERNAME}' already exists")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] != 'UserNotFoundException':
                raise e
        
        # Create new user
        temp_password = generate_temp_password()
        
        print(f"🆕 Creating test user '{TEST_USERNAME}'...")
        
        response = cognito_client.admin_create_user(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=TEST_USERNAME,
            TemporaryPassword=temp_password,
            MessageAction='SUPPRESS',  # Don't send welcome email
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': 'test@example.com'
                }
            ]
        )
        
        print(f"✅ User created successfully")
        print(f"Temporary password: {temp_password}")
        
        # Set permanent password
        permanent_password = generate_temp_password()
        
        cognito_client.admin_set_user_password(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=TEST_USERNAME,
            Password=permanent_password,
            Permanent=True
        )
        
        print(f"✅ Permanent password set: {permanent_password}")
        
        return True
        
    except ClientError as e:
        print(f"❌ Failed to create user: {e}")
        return False

def get_user_token():
    """Get access token for the test user"""
    
    cognito_client = boto3.client('cognito-idp', region_name=REGION)
    
    try:
        # First, check what auth flows are available
        client_info = cognito_client.describe_user_pool_client(
            UserPoolId=COGNITO_USER_POOL_ID,
            ClientId=COGNITO_CLIENT_ID
        )
        
        auth_flows = client_info['UserPoolClient'].get('ExplicitAuthFlows', [])
        print(f"Available auth flows: {auth_flows}")
        
        if not auth_flows:
            print("⚠️  No explicit auth flows configured. Need to enable auth flows.")
            return None
        
        # Try admin authentication (if available)
        if 'ALLOW_ADMIN_USER_PASSWORD_AUTH' in auth_flows:
            print("🔑 Trying admin user password auth...")
            
            # This would require knowing the user's password
            # For now, just show what would be needed
            print("💡 To get token, you would need:")
            print("   1. User's password")
            print("   2. Call admin_initiate_auth with ADMIN_USER_PASSWORD_AUTH")
            
        return None
        
    except ClientError as e:
        print(f"❌ Failed to get token: {e}")
        return None

def check_client_configuration():
    """Check and potentially update client configuration"""
    
    cognito_client = boto3.client('cognito-idp', region_name=REGION)
    
    try:
        client_info = cognito_client.describe_user_pool_client(
            UserPoolId=COGNITO_USER_POOL_ID,
            ClientId=COGNITO_CLIENT_ID
        )
        
        client_config = client_info['UserPoolClient']
        
        print("📋 Current client configuration:")
        print(f"  Client Name: {client_config.get('ClientName')}")
        print(f"  Auth Flows: {client_config.get('ExplicitAuthFlows', [])}")
        print(f"  Generate Secret: {client_config.get('GenerateSecret', False)}")
        print(f"  Supported Identity Providers: {client_config.get('SupportedIdentityProviders', [])}")
        
        # Check if we need to update auth flows
        current_flows = client_config.get('ExplicitAuthFlows', [])
        needed_flows = ['ALLOW_ADMIN_USER_PASSWORD_AUTH', 'ALLOW_USER_PASSWORD_AUTH']
        
        missing_flows = [flow for flow in needed_flows if flow not in current_flows]
        
        if missing_flows:
            print(f"\n⚠️  Missing auth flows: {missing_flows}")
            print("💡 To enable authentication, you would need to update the client with:")
            print("   aws cognito-idp update-user-pool-client \\")
            print(f"     --user-pool-id {COGNITO_USER_POOL_ID} \\")
            print(f"     --client-id {COGNITO_CLIENT_ID} \\")
            print(f"     --explicit-auth-flows {' '.join(current_flows + missing_flows)}")
        else:
            print("✅ Auth flows are properly configured")
        
        return client_config
        
    except ClientError as e:
        print(f"❌ Failed to check client config: {e}")
        return None

def main():
    print("🚀 Cognito Test User Setup")
    print(f"User Pool: {COGNITO_USER_POOL_ID}")
    print(f"Client ID: {COGNITO_CLIENT_ID}")
    print("=" * 60)
    
    # Check client configuration
    client_config = check_client_configuration()
    
    if client_config:
        # Try to create test user
        if create_test_user():
            # Try to get token
            get_user_token()
    
    print("\n" + "=" * 60)
    print("💡 NEXT STEPS:")
    print("1. If auth flows are missing, update the Cognito client")
    print("2. Create test user with known password")
    print("3. Use admin_initiate_auth to get access token")
    print("4. Test MCP gateway with the token")

if __name__ == "__main__":
    main()
