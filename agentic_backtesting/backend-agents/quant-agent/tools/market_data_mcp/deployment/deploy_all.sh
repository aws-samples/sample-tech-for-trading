#!/bin/bash

# Master deployment script for Market Data MCP Server
# Deploys Lambda function using containers, creates MCP gateway, and sets up the target

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"

echo "🚀 Starting complete Market Data MCP Server deployment (Container)..."
echo "🌍 Region: $AWS_REGION"
echo ""

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Make scripts executable
chmod +x deploy_lambda.sh
chmod +x create_mcp_gateway.sh
chmod +x setup_gateway_target.sh

echo "📋 Deployment will proceed in 4 steps:"
echo "   1. Setup S3 Tables"
echo "   2. Deploy Lambda function (Container)"
echo "   3. Create MCP Gateway"
echo "   4. Setup Gateway Target"
echo ""

# Check Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Step 1: Setup S3 Tables
echo "🔥 Step 1: Setting up S3 Tables..."
echo "=================================================="
if [ -f "setup_s3_tables.sh" ]; then
    chmod +x setup_s3_tables.sh
    ./setup_s3_tables.sh
else
    echo "⚠️  S3 Tables setup script not found, skipping..."
fi

echo ""
echo "⏳ Waiting 5 seconds before next step..."
sleep 5

# Step 2: Deploy Lambda function (Container)
echo ""
echo "🔥 Step 2: Deploying Lambda function (Container)..."
echo "=================================================="
./deploy_lambda.sh

echo ""
echo "⏳ Waiting 5 seconds before next step..."
sleep 5

# Step 3: Create MCP Gateway
echo ""
echo "🔥 Step 3: Creating MCP Gateway..."
echo "=================================================="
./create_mcp_gateway.sh

echo ""
echo "⏳ Waiting 10 seconds for gateway to be ready..."
sleep 10

# Step 4: Setup Gateway Target
echo ""
echo "🔥 Step 4: Setting up Gateway Target..."
echo "=================================================="
./setup_gateway_target.sh

echo ""
echo "🎉 Complete deployment finished!"
echo ""
echo "📋 Your Market Data MCP Server is now ready!"
echo "🔧 Resources created:"
echo "   ✅ S3 Tables with Iceberg format"
echo "   ✅ Lambda Function: market-data-mcp (Container)"
echo "   ✅ ECR Repository: market-data-mcp"
echo "   ✅ MCP Gateway: market-data-mcp-gateway"
echo "   ✅ Gateway Target: market-data-lambda-target"
echo ""
echo "💡 Next steps:"
echo "   1. Note the gateway URL for your agent configuration"
echo "   2. Configure OAuth credentials if needed"
echo "   3. Add the MCP server to your agent's configuration"
echo ""
echo "🧪 Test your deployment:"
echo "   aws lambda invoke --function-name market-data-mcp --payload '{\"symbol\":\"AMZN\"}' response.json"