# Market Data MCP Server Deployment

## Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **Docker** installed and running
3. **AgentCore CLI** installed and configured
4. **Python 3.11+** with pip

## Step-by-Step Deployment

### Step 0: Install Dependencies

Install required Python dependencies:

```bash
pip install bedrock-agentcore strands-agents bedrock-agentcore-starter-toolkit
```

### Step 1: Configure Environment

```bash
cd deployment
cp .env.example .env
# Edit .env with your AWS region and settings
```

### Step 2: Setup S3 Tables and Migrate Data

```bash
./setup_s3_tables.sh
```

### Step 3: Deploy Lambda Function (Container)

```bash
./deploy_lambda.sh
```

### Step 4: Create MCP Gateway

```bash
./create_mcp_gateway.sh
```

### Step 5: Setup Gateway Target

```bash
./setup_gateway_target.sh
```

## Testing

### Test Lambda Function

```bash
aws lambda invoke \
  --function-name market-data-mcp \
  --payload '{'symbol': 'AMZN', 'start_date': '2024-01-01', 'end_date': '2024-02-29', 'limit': 10}' \
  --region us-east-1 \
  response.json

cat response.json | jq '.'
```

### Test Gateway

```bash
agentcore gateway list --region us-east-1
```

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

## Alternative: One-Command Deployment

```bash
./deploy_all.sh
```

