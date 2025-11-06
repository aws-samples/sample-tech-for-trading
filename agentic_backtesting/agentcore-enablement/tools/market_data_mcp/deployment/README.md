# Market Data MCP Server Deployment

This directory contains deployment and infrastructure scripts for the Market Data Lambda function as an AgentCore MCP server.

## Directory Structure

```
tools/market_data_mcp/
├── lambda_function.py          # Core Lambda function code
├── requirements.txt            # Lambda dependencies  
├── README.md                   # Tool documentation
└── deployment/                 # This directory
    ├── .env                    # Environment configuration
    ├── .env.example           # Environment template
    ├── README.md              # This file
    ├── deploy_all.sh          # Master deployment script
    ├── deploy_lambda.sh       # Lambda deployment
    ├── create_mcp_gateway.sh  # Gateway creation
    ├── setup_gateway_target.sh # Gateway target setup
    ├── setup_s3_tables.sh     # S3 Tables setup
    ├── create_s3_tables.sh    # Alternative S3 setup
    ├── setup_s3_tables.py     # S3 data population
    ├── migrate_clickhouse_to_s3tables.py # Data migration
    ├── query_s3_table.py      # S3 Tables querying
    └── requirements_migration.txt # Migration dependencies
```

## Overview

The Market Data MCP server provides comprehensive market data for backtesting, including:
- Historical price data for different investment sectors
- Technical indicators (SMA 20, SMA 50)
- Market statistics (volatility, returns, max drawdown)
- Volume data

## Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **AgentCore CLI** installed and configured
3. **jq** for JSON processing
4. **zip** utility for creating deployment packages

### Required AWS Permissions

Your AWS credentials need permissions for:
- Lambda functions (create, update, invoke)
- IAM roles and policies (create, attach)
- AgentCore Gateway operations

## Deployment Scripts

### 1. `deploy_lambda.sh`
Deploys the Lambda function that provides market data.

**What it does:**
- Creates/updates the `market-data-mcp` Lambda function
- Sets up IAM execution role if needed
- Tests the function deployment
- Handles both initial deployment and updates

**Usage:**
```bash
./deploy_lambda.sh
```

### 2. `create_mcp_gateway.sh`
Creates the AgentCore MCP Gateway.

**What it does:**
- Creates the `market-data-mcp-gateway` MCP gateway
- Sets up IAM role for gateway operations
- Enables semantic search functionality
- Handles gateway creation (not updates)

**Usage:**
```bash
./create_mcp_gateway.sh
```

### 3. `setup_gateway_target.sh`
Connects the Lambda function to the MCP gateway as a target.

**What it does:**
- Creates a gateway target pointing to the Lambda function
- Defines the MCP tool schema for `get_market_data`
- Requires gateway ARN and URL from previous step

**Usage:**
```bash
./setup_gateway_target.sh
```

### 4. `deploy_all.sh`
Master script that runs all deployment steps in sequence.

**Usage:**
```bash
./deploy_all.sh
```

## Quick Start

### Step 1: Setup Environment File
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env if you want to customize names or region
# The scripts will automatically update this file with deployment outputs
```

### Step 2: Complete Deployment
```bash
# Option A: Run all steps automatically
./deploy_all.sh

# Option B: Run individual steps with manual verification
./deploy_lambda.sh
./create_mcp_gateway.sh
# Check .env file and update GATEWAY_ARN and GATEWAY_URL if needed
./setup_gateway_target.sh
```

### Step 3: Manual Environment File Updates
After running `create_mcp_gateway.sh`, you may need to manually update your `.env` file:

1. Look for these values in the script output:
   - `'gatewayArn': 'arn:aws:bedrock-agentcore:...'`
   - `'gatewayUrl': 'https://...'`

2. Update your `.env` file:
   ```bash
   GATEWAY_ARN="arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/your-gateway-id"
   GATEWAY_URL="https://your-gateway-id.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp"
   ```

## Configuration

### Environment File (.env)
The deployment uses a `.env` file to store configuration and pass values between scripts:

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Customize if needed:**
   ```bash
   # Edit these values before deployment
   FUNCTION_NAME="market-data-mcp"
   GATEWAY_NAME="market-data-mcp-gateway"
   TARGET_NAME="market-data-lambda-target"
   REGION="us-west-2"
   ```

3. **Auto-updated values:**
   The scripts automatically update these values:
   - `LAMBDA_FUNCTION_ARN` - Set by deploy_lambda.sh
   - `GATEWAY_ARN` - Set by create_mcp_gateway.sh (may need manual update)
   - `GATEWAY_URL` - Set by create_mcp_gateway.sh (may need manual update)
   - `TARGET_ARN` - Set by setup_gateway_target.sh

### Manual Updates Required
Due to output parsing limitations, you may need to manually update the `.env` file after running `create_mcp_gateway.sh`:

- Look for `gatewayArn` and `gatewayUrl` in the script output
- Update `GATEWAY_ARN` and `GATEWAY_URL` in your `.env` file
- Ensure values are properly quoted

## MCP Tool Schema

The deployed MCP server exposes one tool:

### `get_market_data`
**Description:** Get comprehensive market data for backtesting

**Parameters:**
- `investment_area` (required): Investment sector
  - Options: "Technology", "Healthcare", "Finance", "Energy"

**Returns:**
- Historical price data (1 year)
- Technical indicators (SMA 20, SMA 50)
- Market statistics (returns, volatility, drawdown)
- Volume information

## Testing

### Test Lambda Function Directly
```bash
aws lambda invoke \
  --function-name market-data-mcp \
  --payload '{"investment_area": "Technology"}' \
  response.json && cat response.json
```

### Test MCP Gateway
```bash
curl -X POST 'YOUR_GATEWAY_URL' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_market_data",
      "arguments": {
        "investment_area": "Technology"
      }
    }
  }'
```

## Using in Your Agent

### AgentCore Configuration
Add the MCP server to your agent's configuration:

```json
{
  "mcp_servers": {
    "market_data": {
      "url": "YOUR_GATEWAY_URL",
      "auth": {
        "type": "oauth",
        "token_endpoint": "YOUR_TOKEN_ENDPOINT",
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET"
      }
    }
  }
}
```

### Example Agent Usage
```python
# In your agent code
market_data = await call_mcp_tool(
    "get_market_data",
    {"investment_area": "Technology"}
)

print(f"Current price: ${market_data['price_data']['final_price']}")
print(f"Total return: {market_data['statistics']['total_return_pct']}%")
```

## Troubleshooting

### Common Issues

1. **Environment File Missing**
   ```bash
   # Copy the example file
   cp .env.example .env
   ```

2. **Gateway ARN/URL Not Found**
   - Check the output from `create_mcp_gateway.sh`
   - Manually update `.env` file with `gatewayArn` and `gatewayUrl` values
   - Ensure values are properly quoted in `.env`

3. **Permission Denied**
   - Ensure AWS CLI has sufficient permissions
   - Check IAM roles are created correctly

4. **Gateway Creation Fails**
   - Verify AgentCore CLI is installed and configured
   - Check region settings

5. **Lambda Invocation Errors**
   - Check CloudWatch logs for the Lambda function
   - Verify the function is deployed correctly

6. **Gateway Target Setup Fails**
   - Ensure `.env` file has correct GATEWAY_ARN and GATEWAY_URL
   - Verify the Lambda function exists

### Step-by-Step Debugging

1. **Check .env file:**
   ```bash
   cat .env
   # Verify all required values are set
   ```

2. **Verify Lambda deployment:**
   ```bash
   aws lambda get-function --function-name market-data-mcp
   ```

3. **Check gateway status:**
   ```bash
   agentcore gateway list
   ```

### Logs and Monitoring

- **Lambda Logs:** CloudWatch Logs `/aws/lambda/market-data-mcp`
- **Gateway Logs:** Check AgentCore Gateway logs
- **Script Output:** Review the detailed output from each script

## Cleanup

To remove all resources:

```bash
# Delete Lambda function
aws lambda delete-function --function-name market-data-mcp

# Delete IAM roles (if not used elsewhere)
aws iam delete-role --role-name market-data-lambda-role
aws iam delete-role --role-name market-data-gateway-role

# Delete gateway (use AgentCore CLI)
agentcore gateway delete --name market-data-mcp-gateway
```

## Support

For issues with:
- **Lambda deployment:** Check AWS Lambda documentation
- **AgentCore Gateway:** Check AgentCore documentation
- **MCP protocol:** Check Model Context Protocol specification