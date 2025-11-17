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
- **Node.js** (v18 or later) for frontend deployment
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
   cd agentcore-enablement/tools/market_data_mcp/deployment
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
- `agentcore-enablement/tools/market_data_mcp/deployment/README.md`

#### 1.3.2 Create Cognito User

The Quant Agent uses Cognito authentication to access the Market Data Gateway.

1. **Navigate to AWS Cognito Console:**
   - Go to: https://console.aws.amazon.com/cognito/
   - Select your region (e.g., us-east-1)

2. **Find the User Pool:**
   - Look for the User Pool created in step 1.3.1
   - User Pool ID format: `us-east-1_xxxxxxxxx`

3. **Create a new user:**
   - Click on the User Pool
   - Go to "Users" tab
   - Click "Create user"
   - Fill in the details:
     - **Username**: `mcp-test-user` (or your preferred username)
     - **Email**: Your email address (optional)
     - **Temporary password**: Create a strong password
     - Uncheck "Send an email invitation" if you don't want email verification
     - Check "Mark email address as verified" if providing an email

4. **Set permanent password:**
   - After creating the user, you may need to change the temporary password
   - Use AWS CLI to set a permanent password:
     ```bash
     aws cognito-idp admin-set-user-password \
       --user-pool-id us-east-1_xxxxxxxxx \
       --username mcp-test-user \
       --password "YourStrongPassword123!" \
       --permanent
     ```

5. **Save credentials:**
   - **Username**: `mcp-test-user`
   - **Password**: `YourStrongPassword123!`
   - You'll need these for the Quant Agent `.env` file

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

   # Cognito Authentication Configuration (from steps 1.3.1 and 1.3.2)
   COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
   COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
   COGNITO_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   COGNITO_USERNAME=mcp-test-user
   COGNITO_PASSWORD=YourStrongPassword123!

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

The frontend provides a web interface for interacting with the Quant Agent system.

### Steps:

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend-nextjs
   ```

2. **Follow the deployment instructions:**
   Refer to `frontend-nextjs/README.md` for detailed frontend deployment steps.

   Quick summary:
   ```bash
   # Install dependencies
   npm install
   
   # Configure environment variables
   cp .env.example .env.local
   # Edit .env.local with your Quant Agent Runtime ARN
   
   # Run development server
   npm run dev
   
   # Or build for production
   npm run build
   npm start
   ```

For complete frontend deployment instructions, see: `frontend-nextjs/README.md`

### Test Frontend

1. Open your browser to `http://localhost:3000` (or your deployed URL)
2. Enter a trading strategy query
3. Verify the complete workflow executes successfully


---

## Support and Resources

- **AgentCore Documentation:** https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html


For issues or questions, refer to the individual README files in each component directory.
