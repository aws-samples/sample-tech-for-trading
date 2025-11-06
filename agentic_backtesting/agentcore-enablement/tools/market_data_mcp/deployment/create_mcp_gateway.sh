#!/bin/bash

# Create AgentCore MCP Gateway for Market Data
# This script can be used for both initial creation and updates

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
else
    echo "❌ Environment file not found: $ENV_FILE"
    exit 1
fi

# Gateway-specific configuration
ROLE_NAME="market-data-gateway-role"

# Function to update environment file
update_env_var() {
    local key="$1"
    local value="$2"
    if grep -q "^${key}=" "$ENV_FILE"; then
        sed -i.bak "s|^${key}=.*|${key}=\"${value}\"|" "$ENV_FILE"
    else
        echo "${key}=\"${value}\"" >> "$ENV_FILE"
    fi
    rm -f "${ENV_FILE}.bak"
}

echo "🚀 Creating AgentCore MCP Gateway..."
echo "🌍 Region: $REGION"
echo "📛 Gateway Name: $GATEWAY_NAME"

# Check if gateway already exists
echo "🔍 Checking if MCP gateway already exists..."
EXISTING_GATEWAY=""
if command -v agentcore >/dev/null 2>&1; then
    # Try to get existing gateway info (this might fail if gateway doesn't exist)
    EXISTING_GATEWAY=$(agentcore gateway list 2>/dev/null | grep "$GATEWAY_NAME" || true)
fi

if [ -n "$EXISTING_GATEWAY" ]; then
    echo "⚠️  Gateway '$GATEWAY_NAME' already exists"
    echo "📋 Existing gateway info: $EXISTING_GATEWAY"
    echo "💡 To update the gateway, you may need to destroy and recreate it"
    echo "   or use the setup_gateway_target.sh script to update the target"
    exit 0
fi

# Get or create execution role for gateway
echo "🔐 Setting up IAM role for gateway..."
ROLE_ARN=""

if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
    echo "📋 Using existing IAM role: $ROLE_NAME"
    ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
else
    echo "🆕 Creating IAM role: $ROLE_NAME"
    
    # Create trust policy for AgentCore Gateway
    cat > gateway-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "bedrock-agentcore.amazonaws.com",
                    "lambda.amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
    
    # Create role
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file://gateway-trust-policy.json \
        --description "Execution role for Market Data MCP Gateway"
    
    # Create and attach policy for Lambda invocation
    cat > gateway-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction",
                "lambda:GetFunction"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}
EOF
    
    # Create policy
    POLICY_ARN=$(aws iam create-policy \
        --policy-name "market-data-gateway-policy" \
        --policy-document file://gateway-policy.json \
        --query 'Policy.Arn' --output text)
    
    # Attach policy to role
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "$POLICY_ARN"
    
    ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
    
    echo "⏳ Waiting for role to be ready..."
    sleep 15
    
    # Cleanup temporary files
    rm -f gateway-trust-policy.json gateway-policy.json
fi

echo "🔗 Using role ARN: $ROLE_ARN"

# Create MCP Gateway using AgentCore CLI and capture output
echo "🏗️  Creating MCP Gateway..."
echo "📋 Command: agentcore gateway create-mcp-gateway --region \"$REGION\" --name \"$GATEWAY_NAME\" --role-arn \"$ROLE_ARN\" --enable-semantic-search"

# Run the command and capture both stdout and stderr
set +e  # Temporarily disable exit on error to capture output
GATEWAY_OUTPUT=$(agentcore gateway create-mcp-gateway \
    --region "$REGION" \
    --name "$GATEWAY_NAME" \
    --role-arn "$ROLE_ARN" \
    --enable_semantic_search 2>&1)
GATEWAY_EXIT_CODE=$?
set -e  # Re-enable exit on error

echo "📋 Gateway creation output:"
echo "$GATEWAY_OUTPUT"
echo "📊 Exit code: $GATEWAY_EXIT_CODE"

# Check if the command succeeded
if [ $GATEWAY_EXIT_CODE -eq 0 ] && echo "$GATEWAY_OUTPUT" | grep -q "gatewayArn"; then
    # Extract values using Python to parse the dictionary-like output
    GATEWAY_ARN=$(echo "$GATEWAY_OUTPUT" | python3 -c "
import sys, re
content = sys.stdin.read()
match = re.search(r\"'gatewayArn': '([^']+)'\", content)
print(match.group(1) if match else '')
")
    
    GATEWAY_ID=$(echo "$GATEWAY_OUTPUT" | python3 -c "
import sys, re
content = sys.stdin.read()
match = re.search(r\"'gatewayId': '([^']+)'\", content)
print(match.group(1) if match else '')
")
    
    GATEWAY_URL=$(echo "$GATEWAY_OUTPUT" | python3 -c "
import sys, re
content = sys.stdin.read()
match = re.search(r\"'gatewayUrl': '([^']+)'\", content)
print(match.group(1) if match else '')
")
    
    GATEWAY_STATUS=$(echo "$GATEWAY_OUTPUT" | python3 -c "
import sys, re
content = sys.stdin.read()
match = re.search(r\"'status': '([^']+)'\", content)
print(match.group(1) if match else '')
")
    
    # Update environment file
    update_env_var "GATEWAY_ARN" "$GATEWAY_ARN"
    update_env_var "GATEWAY_ID" "$GATEWAY_ID"
    update_env_var "GATEWAY_URL" "$GATEWAY_URL"
    update_env_var "GATEWAY_ROLE_ARN" "$ROLE_ARN"
    update_env_var "GATEWAY_STATUS" "$GATEWAY_STATUS"
    update_env_var "GATEWAY_CREATED_AT" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    
    echo ""
    echo "🎉 MCP Gateway creation completed!"
    echo "📝 Gateway Name: $GATEWAY_NAME"
    echo "🌍 Region: $REGION"
    
    if [ -n "$GATEWAY_ARN" ] && [ -n "$GATEWAY_URL" ]; then
        echo "🔗 Gateway ARN: $GATEWAY_ARN"
        echo "🌐 Gateway URL: $GATEWAY_URL"
        echo "📊 Status: $GATEWAY_STATUS"
        echo "💾 Environment updated: $ENV_FILE"
    else
        echo ""
        echo "⚠️  IMPORTANT: Please manually update your .env file with the following values:"
        echo "   Look for 'gatewayArn' in the output above and update GATEWAY_ARN="
        echo "   Look for 'gatewayUrl' in the output above and update GATEWAY_URL="
        echo "   Look for 'status' in the output above and update GATEWAY_STATUS="
        echo ""
        echo "📝 Edit $ENV_FILE and update these variables before proceeding to the next step"
    fi
else
    echo "❌ Failed to create gateway (exit code: $GATEWAY_EXIT_CODE)"
    echo "📋 Error output: $GATEWAY_OUTPUT"
    echo ""
    echo "🔍 Troubleshooting tips:"
    echo "   1. Check if AgentCore CLI is properly installed and configured"
    echo "   2. Verify AWS credentials have proper permissions"
    echo "   3. Check if the region is supported for AgentCore"
    echo "   4. Ensure the IAM role ARN is valid and accessible"
    exit 1
fi

echo ""
echo "💡 Next steps:"
echo "   1. Verify the .env file has been updated with GATEWAY_ARN and GATEWAY_URL"
echo "   2. Run ./setup_gateway_target.sh to connect your Lambda function to this gateway"
echo ""
echo "📋 To get gateway details later, you can use:"
echo "   agentcore gateway list"