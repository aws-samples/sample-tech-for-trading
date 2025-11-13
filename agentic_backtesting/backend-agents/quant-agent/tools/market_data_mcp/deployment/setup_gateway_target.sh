#!/bin/bash

# Setup Lambda as target for AgentCore MCP Gateway
# This script can be used for both initial setup and updates

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

echo "🚀 Setting up Lambda as MCP Gateway target..."
echo "🌍 Region: $AWS_REGION"
echo "⚡ Lambda Function: $FUNCTION_NAME"
echo "🌐 Gateway Name: $GATEWAY_NAME"
echo "🎯 Target Name: $TARGET_NAME"

# Validate required environment variables
if [ -z "$LAMBDA_FUNCTION_ARN" ]; then
    echo "❌ Lambda function ARN not found in environment!"
    echo "💡 Please run ./deploy_lambda.sh first"
    exit 1
fi

if [ -z "$GATEWAY_ARN" ] || [ -z "$GATEWAY_URL" ]; then
    echo "❌ Gateway ARN or URL not found in environment!"
    echo "💡 Please ensure your .env file has been updated with:"
    echo "   GATEWAY_ARN=arn:aws:bedrock-agentcore:region:account:gateway/gateway-id"
    echo "   GATEWAY_URL=https://gateway-id.gateway.bedrock-agentcore.region.amazonaws.com/mcp"
    echo ""
    echo "📝 Check the output from ./create_mcp_gateway.sh and update .env file manually"
    exit 1
fi

if [ -z "$GATEWAY_ROLE_ARN" ]; then
    echo "❌ Gateway role ARN not found in environment!"
    echo "💡 Please run ./create_mcp_gateway.sh first"
    exit 1
fi

echo "🔗 Lambda ARN: $LAMBDA_FUNCTION_ARN"
echo "🔗 Gateway ARN: $GATEWAY_ARN"
echo "🌐 Gateway URL: $GATEWAY_URL"
echo "🔐 Gateway Role ARN: $GATEWAY_ROLE_ARN"

# Create Lambda configuration for MCP Gateway
echo "📝 Creating Lambda target configuration..."
cat > lambda-target-config.json << EOF
{
    "lambdaArn": "$LAMBDA_FUNCTION_ARN",
    "toolSchema": {
        "inlinePayload": [
            {
                "name": "get_market_data",
                "description": "Get comprehensive tick data for backtesting including price history, technical indicators, and statistics for a specific stock symbol",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Stock symbol to get tick data for. Examples: AAPL, MSFT, GOOGL, NVDA, JNJ, PFE, JPM, BAC, XOM, CVX"
                        },
                        "investment_area": {
                            "type": "string",
                            "description": "Investment sector (backward compatibility). Options: Technology, Healthcare, Finance, Energy"
                        }
                    },
                    "required": []
                }
            }
        ]
    }
}
EOF

echo "📊 Lambda target configuration:"
cat lambda-target-config.json | jq '.'

# Create MCP Gateway Target
echo "🎯 Creating MCP Gateway target..."
echo "📋 Command: agentcore gateway create-mcp-gateway-target --gateway-arn \"$GATEWAY_ARN\" --gateway-url \"$GATEWAY_URL\" --role-arn \"$GATEWAY_ROLE_ARN\" --region \"$AWS_REGION\" --name \"$TARGET_NAME\" --target-type \"lambda\" --target-payload \"$(cat lambda-target-config.json)\""

# Run the command and capture both stdout and stderr
set +e  # Temporarily disable exit on error to capture output
TARGET_OUTPUT=$(agentcore gateway create-mcp-gateway-target \
    --gateway-arn "$GATEWAY_ARN" \
    --gateway-url "$GATEWAY_URL" \
    --role-arn "$GATEWAY_ROLE_ARN" \
    --region "$AWS_REGION" \
    --name "$TARGET_NAME" \
    --target-type "lambda" \
    --target-payload "$(cat lambda-target-config.json)" 2>&1)
TARGET_EXIT_CODE=$?
set -e  # Re-enable exit on error

echo "📋 Target creation output:"
echo "$TARGET_OUTPUT"
echo "📊 Exit code: $TARGET_EXIT_CODE"

if [ $TARGET_EXIT_CODE -eq 0 ]; then
    # Parse the JSON response to extract target information
    TARGET_ID=$(echo "$TARGET_OUTPUT" | grep -o "'targetId': '[^']*'" | sed "s/'targetId': '//;s/'//")
    TARGET_STATUS_PARSED=$(echo "$TARGET_OUTPUT" | grep -o "'status': '[^']*'" | sed "s/'status': '//;s/'//")
    
    # Update environment file on success
    update_env_var "TARGET_ARN" "${GATEWAY_ARN}/target/${TARGET_ID}"
    update_env_var "TARGET_STATUS" "$TARGET_STATUS_PARSED"
    update_env_var "TARGET_CREATED_AT" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    
    echo "✅ Gateway target created successfully!"
    echo "🆔 Target ID: $TARGET_ID"
    echo "📊 Status: $TARGET_STATUS_PARSED"
else
    echo "❌ Failed to create gateway target (exit code: $TARGET_EXIT_CODE)"
    echo "📋 Error output: $TARGET_OUTPUT"
    echo ""
    echo "🔍 Troubleshooting tips:"
    echo "   1. Check if the gateway ARN and URL are correct"
    echo "   2. Verify the role has proper permissions"
    echo "   3. Ensure the Lambda function exists and is accessible"
    echo "   4. Check if the target name already exists"
    exit 1
fi

echo ""
echo "🧪 Testing the gateway target..."

# Create test payload
TEST_PAYLOAD='{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "get_market_data",
        "arguments": {
            "symbol": "AAPL"
        }
    }
}'

echo "📤 Test payload:"
echo "$TEST_PAYLOAD" | jq '.'

echo ""
echo "💡 To test the gateway, you can use:"
echo "curl -X POST '$GATEWAY_URL' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'Authorization: Bearer <YOUR_TOKEN>' \\"
echo "  -d '$TEST_PAYLOAD'"

# Cleanup
rm -f lambda-target-config.json

echo ""
echo ""
echo "🎉 Gateway target setup completed!"
echo "📝 Target Name: $TARGET_NAME"
echo "🔗 Lambda ARN: $LAMBDA_FUNCTION_ARN"
echo "🌐 Gateway URL: $GATEWAY_URL"
echo "💾 Environment updated: $ENV_FILE"
echo ""
echo "📋 Summary of created resources:"
echo "   ✅ Lambda Function: $FUNCTION_NAME"
echo "   ✅ MCP Gateway: $GATEWAY_NAME"
echo "   ✅ Gateway Target: $TARGET_NAME"
echo ""
echo "🔧 Your MCP server is now ready to use in your agent!"
echo "💡 Add the gateway URL to your agent's MCP configuration"