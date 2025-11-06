# AgentCore Gateway Setup with Cognito Authentication

This guide explains how to configure the AgentCore Gateway integration with Cognito authentication to fetch market data.

## Overview

The updated `agent.py` now connects to your AgentCore Gateway:
- **Gateway URL**: `https://market-data-mcp-gateway-lryjsuyell.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp`
- **Authentication**: Cognito User Pool (`us-east-1_eAn2oP0lv`)

## Configuration Steps

### 1. Update Environment Variables

Edit the `.env` file in the `agentcore-enablement` directory:

```bash
# AgentCore Gateway Configuration
AGENTCORE_GATEWAY_URL=https://market-data-mcp-gateway-lryjsuyell.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp

# Cognito Authentication Configuration
COGNITO_USER_POOL_ID=us-east-1_eAn2oP0lv
COGNITO_CLIENT_ID=your_actual_client_id_here
COGNITO_CLIENT_SECRET=your_actual_client_secret_here
COGNITO_USERNAME=your_cognito_username_here
COGNITO_PASSWORD=your_cognito_password_here

# AWS Configuration
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
```

### 2. Get Cognito Credentials

You need to obtain the following from your Cognito User Pool:

1. **Client ID**: From the Cognito User Pool App Client
2. **Client Secret**: From the Cognito User Pool App Client (if enabled)
3. **Username**: Your Cognito user account username
4. **Password**: Your Cognito user account password

### 3. Install Required Dependencies

Make sure you have all required Python packages:

```bash
pip install boto3 httpx python-dotenv bedrock-agentcore strands
```

## Code Changes Made

### 1. Enhanced Authentication
- Added Cognito authentication with secret hash generation
- Implemented proper JWT token handling
- Added error handling for authentication failures

### 2. Gateway Communication
- Updated `fetch_market_data_via_gateway()` to use Cognito authentication
- Added proper request formatting for the lambda function
- Implemented response parsing for market data

### 3. Fallback Mechanism
- Added fallback data generation when gateway is unavailable
- Maintains functionality even if authentication fails
- Clear indication of data source (gateway vs fallback)

## Testing

### 1. Test Environment Variables
```bash
cd agentcore-enablement
python test_gateway_connection.py
```

This will check if all required environment variables are set.

### 2. Test Market Data Fetch
```bash
python test_fetch_market_data.py
```

This will test the `fetch_market_data_via_gateway` function with AMZN.

### 3. Test Full Gateway Connection
```bash
python test_gateway_connection.py
```

This will test the complete authentication and gateway call flow.

## Expected Behavior

### Successful Gateway Connection
When properly configured, you should see:
```
🌐 AgentCore Gateway: Fetching AMZN data via MCP...
🔐 Authenticating with Cognito User Pool: us-east-1_eAn2oP0lv
✅ Cognito authentication successful
🌐 Calling AgentCore Gateway: https://market-data-mcp-gateway-...
📤 Sending request to gateway with payload: {'symbol': 'AMZN', 'limit': 252}
📥 Gateway response status: 200
✅ Successfully fetched data from AgentCore Gateway
```

### Fallback Mode
If authentication fails or gateway is unavailable:
```
❌ AgentCore Gateway: Failed to fetch via Gateway - [error details]
⚠️ Using fallback data for AMZN
```

## API Request Format

The gateway expects requests in this format:
```json
{
    "symbol": "AMZN",
    "limit": 252,
    "start_date": "2024-01-01",  // optional
    "end_date": "2024-12-31"     // optional
}
```

## Response Format

The gateway returns data in this format:
```json
{
    "success": true,
    "data": {
        "symbol": "AMZN",
        "data_points": 252,
        "period_start": "2024-01-01",
        "period_end": "2024-12-31",
        "price_data": {
            "initial_price": 150.00,
            "final_price": 180.00,
            "min_price": 140.00,
            "max_price": 190.00,
            "dates": [...],
            "prices": [...],
            "volumes": [...]
        },
        "statistics": {
            "total_return_pct": 20.00,
            "avg_daily_volume": 50000000
        },
        "technical_indicators": {
            "current_sma_20": 175.00,
            "current_sma_50": 170.00
        }
    }
}
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify Cognito credentials in `.env`
   - Check if user exists in the User Pool
   - Ensure client secret is correct (if app client uses secret)

2. **Gateway Connection Errors**
   - Verify gateway URL is correct
   - Check network connectivity
   - Ensure gateway is running and accessible

3. **Permission Errors**
   - Verify AWS credentials have necessary permissions
   - Check Cognito User Pool policies
   - Ensure gateway has proper IAM roles

### Debug Mode

Set `DEBUG=true` in your `.env` file for more detailed logging.

## Integration with Existing Code

The updated `fetch_market_data_via_gateway` function maintains the same interface:

```python
# Fetch data by symbol (preferred)
result = fetch_market_data_via_gateway(symbol="AMZN")

# Fetch data by investment area (backward compatibility)
result = fetch_market_data_via_gateway(investment_area="Technology")
```

The function will automatically:
1. Authenticate with Cognito
2. Call the AgentCore Gateway
3. Parse and return the market data
4. Fall back to generated data if gateway fails

This ensures your existing code continues to work while gaining real market data capabilities.