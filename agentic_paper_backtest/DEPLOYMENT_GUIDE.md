# Deployment Guide

This guide provides step-by-step instructions for deploying the Quantitative Trading Agent System with AgentCore.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deploy Backend Agents](#deploy-backend-agents)
   - [1.1 Strategy Generator Agent](#11-strategy-generator-agent)
   - [1.2 Result Summarizer Agent](#12-result-summarizer-agent)
   - [1.3 Quant Agent](#13-quant-agent)
3. [Deploy Frontend](#deploy-frontend)


---

## Prerequisites

Before starting the deployment, ensure you have:

- **AWS CLI** configured with appropriate credentials
- **AgentCore CLI** installed and configured
- **Docker** installed and running (required for Lambda container deployments)
- **Node.js** (v22 or later) for frontend deployment
- **Python 3.9+** for backend agents
- **jq** for JSON processing
- **zip** utility for creating deployment packages

### Required AWS Permissions

Your AWS credentials need permissions for:
- Bedrock AgentCore operations
- Lambda functions (create, update, invoke)
- IAM roles and policies (create, attach)
- Cognito User Pool operations
- S3 Tables access

---

## Deploy Backend Agents

### 1.1 Strategy Generator Agent

The Strategy Generator Agent converts natural language trading strategies into executable Backtrader code.

#### Steps:

1. **Navigate to the agent directory:**
   ```bash
   cd backend-agents/strategy-generator-agent
   ```

2. **Create environment file from sample:**
   ```bash
   cp .env.sample .env
   ```

3. **Edit `.env` file** (if needed):
   ```bash
   # for exmaple, Customize AWS_REGION if deploying to a different region
   AWS_REGION=us-east-1
   ```

4. **Deploy the agent:**
   ```bash
   chmod +x deploy_to_agentcore.sh
   ./deploy_to_agentcore.sh
   ```

5. **Save the Runtime ARN:**
   After deployment, the script will output the Runtime ARN. Save this value - you'll need it for the Quant Agent configuration.
   
   Example output:
   ```
   Runtime ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/strategy_generator-xxx
   ```


---

### 1.2 Result Summarizer Agent

The Result Summarizer Agent analyzes backtest results and generates comprehensive performance reports.

#### Steps:

1. **Navigate to the agent directory:**
   ```bash
   cd backend-agents/result-summarizer-agent
   ```

2. **Create environment file from sample:**
   ```bash
   cp .env.sample .env
   ```

3. **Edit `.env` file** (if needed):
   ```bash
   # for exmaple, Customize AWS_REGION if deploying to a different region
   AWS_REGION=us-east-1
   ```

4. **Deploy the agent:**
   ```bash
   chmod +x deploy_to_agentcore.sh
   ./deploy_to_agentcore.sh
   ```

5. **Save the Runtime ARN:**
   After deployment, save the Runtime ARN for the Quant Agent configuration.
   
   Example output:
   ```
   Runtime ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/results_summary-xxx
   ```

---

### 1.3 Quant Agent

The Quant Agent orchestrates the entire backtesting workflow, coordinating between strategy generation, market data retrieval, backtesting execution, and results analysis.

#### 1.3.1 Deploy Market Data Tool

Before deploying the Quant Agent, you need to deploy the Market Data MCP tool that provides historical market data.

1. **Navigate to the market data tool directory:**
   ```bash
   cd backend-agents/quant-agent/tools/market_data_mcp/deployment
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` file** (customize if needed):
   ```bash
   FUNCTION_NAME="market-data-mcp"
   GATEWAY_NAME="market-data-mcp-gateway"
   TARGET_NAME="market-data-lambda-target"
   REGION="us-east-1"

   S3_TABLES_BUCKET="market-data-unique-name"
   S3_TABLES_REGION="us-east-1"
   ...
   ```

4. **Run the complete deployment:**
   ```bash
   chmod +x deploy_all.sh
   ./deploy_all.sh
   ```

5. **Save deployment outputs:**
   
   After deployment, note these values from the output:
   
   - **Lambda Function ARN**: `arn:aws:lambda:us-east-1:123456789012:function:market-data-mcp`
   - **Gateway ARN**: `arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/market-data-mcp-gateway-xxx`
   - **Gateway URL**: `https://market-data-mcp-gateway-xxx.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp`
   - **Cognito User Pool ID**: `us-east-1_xxxxxxxxx`
   - **Cognito Client ID**: `xxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Cognito Client Secret**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

   **Note:** If the script doesn't automatically update the `.env` file with Gateway ARN and URL, you may need to manually update them from the script output.

6. **Verify deployment:**
   ```bash
   # Test Lambda function
   aws lambda invoke \
     --function-name market-data-mcp \
     --payload '{"symbol": "AMZN"}' \
     response.json && cat response.json
   ```

For detailed deployment instructions, refer to:
- `backend-agents/quant-agent/tools/market_data_mcp/deployment/README.md`

#### 1.3.2 Authentication Configuration

**Note:** The system now uses **client_credentials** OAuth grant type (machine-to-machine authentication) instead of user password authentication. You no longer need to manually create Cognito users.

The deployment script in step 1.3.1 automatically configures the Cognito App Client with the appropriate settings for client_credentials flow. The Quant Agent authenticates directly using the Client ID and Client Secret.

#### 1.3.3 Deploy Quant Agent

1. **Navigate to the Quant Agent directory:**
   ```bash
   cd backend-agents/quant-agent
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` file with values from previous steps:**
   ```bash
   # AgentCore Gateway Configuration (from step 1.3.1)
   AGENTCORE_GATEWAY_URL=https://market-data-mcp-gateway-xxx.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp

   # Runtime ARNs (from steps 1.1 and 1.2)
   STRATEGY_GENERATOR_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/strategy_generator-XJMGBxAgBL
   BACKTEST_SUMMARY_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/results_summary-zug3B14PlT

   # Cognito Authentication Configuration (from step 1.3.1)
   # Using client_credentials grant (machine-to-machine auth)
   COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
   COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
   COGNITO_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

   # AWS Configuration
   AWS_REGION=us-east-1

   # Debug Settings
   DEBUG=true
   BYPASS_TOOL_CONSENT=true
   ```

4. **Deploy the agent:**
   ```bash
   chmod +x deploy_to_agentcore.sh
   ./deploy_to_agentcore.sh
   ```

5. **Save the Runtime ARN:**
   After deployment, save the Quant Agent Runtime ARN for frontend configuration.
   
   Example output:
   ```
   Runtime ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/quant_agent-xxxxxxxxxx
   ```

#### 1.3.4 Assign IAM Policy to Quant Agent

The Quant Agent needs additional IAM permissions to authenticate with Cognito.

1. **Find the Quant Agent IAM Role:**
   In AWS Agentcore runtime, you can find the IAM role in Agent runtime -> Permissions -> IAM service role, like AmazonBedrockAgentCoreSDKRuntime-us-east-1-xxx.

2. **Create IAM policy file:**
   ```bash
   cat > cognito-policy.json << 'EOF'
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "cognito-idp:AdminInitiateAuth",
           "cognito-idp:AdminRespondToAuthChallenge",
           "cognito-idp:AdminGetUser"
         ],
         "Resource": [
           "arn:aws:cognito-idp:us-east-1:YOUR_ACCOUNT_ID:userpool/YOUR_USER_POOL_ID"
         ]
       }
     ]
   }
   EOF
   ```

   ```bash
   # Replace YOUR_ACCOUNT_ID with your AWS account ID
   # Replace YOUR_USER_POOL_ID with the Cognito User Pool ID from step 1.3.1
   ```

3. **Attach the policy to the Quant Agent role:**
   ```bash
   # Create the policy
   aws iam create-policy \
     --policy-name QuantAgentCognitoAccess \
     --policy-document file://cognito-policy.json
   
   # Attach to the role
   aws iam attach-role-policy \
     --role-name AmazonBedrockAgentCoreSDKRuntime-us-east-1-xxx \
     --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/QuantAgentCognitoAccess
   ```


---

## Deploy Frontend

The frontend provides a web interface for interacting with the Quant Agent system
(PDF upload or manual buy/sell conditions).

### Step 1: Create the login user pool (Cognito)

The frontend requires login. Create a user pool with admin-only signup and an app
client (no secret) with USER_PASSWORD_AUTH, then create your user:

```bash
POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name paper-backtest-frontend-auth \
  --policies 'PasswordPolicy={MinimumLength=6,RequireUppercase=false,RequireLowercase=false,RequireNumbers=false,RequireSymbols=false}' \
  --admin-create-user-config 'AllowAdminCreateUserOnly=true' \
  --query 'UserPool.Id' --output text)

CLIENT_ID=$(aws cognito-idp create-user-pool-client \
  --user-pool-id "$POOL_ID" --client-name paper-backtest-web \
  --no-generate-secret \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --query 'UserPoolClient.ClientId' --output text)

aws cognito-idp admin-create-user --user-pool-id "$POOL_ID" \
  --username demo --message-action SUPPRESS
aws cognito-idp admin-set-user-password --user-pool-id "$POOL_ID" \
  --username demo --password 'YourPassword1' --permanent
```

### Step 2: Run locally

```bash
cd frontend
npm install

cp .env.example .env.local
# Edit .env.local:
#   AGENTCORE_ARN   = the paper_quant_agent runtime ARN (from step 1.3)
#   AWS_REGION      = your region
#   COGNITO_USER_POOL_ID / COGNITO_APP_CLIENT_ID / COGNITO_REGION = from Step 1

npm run dev    # http://localhost:3000 — sign in with the user you created
```

### Step 3 (optional): Deploy to AWS (ECS + ALB + CloudFront)

```bash
cd frontend
./deploy.sh    # creates ECR repo, builds/pushes the image, deploys the
               # CloudFormation stack (VPC, ECS Fargate, ALB locked to
               # CloudFront, CloudFront distribution)
```

The stack reads `AGENTCORE_ARN` and the `COGNITO_*` values from `.env.local`.
Outputs include the CloudFront URL — the only public entry point.

### Test Frontend

1. Open `http://localhost:3000` (or the CloudFront URL) and sign in
2. Upload a research paper PDF **or** switch to manual buy/sell conditions
3. Verify the complete workflow executes and results render
4. Try `/chat` to analyze past backtests across sessions


---

## Support and Resources

- **AgentCore Documentation:** https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html
- **Docker Installation:** https://docs.docker.com/get-docker/

For issues or questions, refer to the individual README files in each component directory.
