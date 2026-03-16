# Tasks: Backend Agents

## Task 1: Strategy Generator Agent
- [x] Implement `StrategyGeneratorAgent` class with Claude Sonnet 4 integration
- [x] Create `@app.entrypoint` invoke function for AgentCore Runtime
- [x] Build system prompt for converting JSON config to Backtrader strategy code
- [x] Add environment-based model/temperature configuration
- [x] Create `deploy_to_agentcore.sh` deployment script
- [x] Add `.env.sample` with required variables

## Task 2: Market Data MCP Lambda
- [x] Implement `lambda_handler` with PyIceberg S3 Tables integration
- [x] Support symbol, date range, and limit filters
- [x] Create Dockerfile for Python 3.12 container image
- [x] Create `deploy_lambda.sh` for ECR + Lambda deployment
- [x] Create `create_mcp_gateway.sh` for AgentCore Gateway setup
- [x] Create `setup_gateway_target.sh` for Gateway-to-Lambda binding
- [x] Create `deploy_all.sh` orchestration script

## Task 3: Backtest Tool
- [x] Implement `BacktestTool` class with Backtrader Cerebro engine
- [x] Strategy code execution and class detection
- [x] Market data validation and feed creation
- [x] Broker configuration (initial cash, commission)
- [x] Analyzer setup (Sharpe, Sortino, drawdown, trade stats)
- [x] Results extraction and metric computation

## Task 4: Quant Agent (Orchestrator)
- [x] Implement Strands Agent with 4 `@tool` functions
- [x] `generate_trading_strategy` — invoke Strategy Generator Runtime
- [x] `fetch_market_data_via_gateway` — call Gateway with Cognito auth
- [x] `run_backtest` — execute BacktestTool with strategy + data
- [x] `create_results_summary` — invoke Results Summary Runtime
- [x] Enforce strict sequential execution in system prompt
- [x] Integrate AgentCore Memory for session-based result persistence
- [x] Create `deploy_to_agentcore.sh` deployment script

## Task 5: Results Summary Agent
- [x] Implement `ResultsSummaryAgent` with Amazon Nova Pro integration
- [x] `analyze_results()` for metric analysis
- [x] Red flag detection (overfitting, unrealistic returns)
- [x] JSON output: executive_summary, detailed_analysis, recommendations
- [x] Create `deploy_to_agentcore.sh` deployment script

## Task 6: Security & Authentication
- [x] Cognito OAuth integration for Gateway access (bearer tokens)
- [x] HMAC-SHA256 secret hash signing
- [x] IAM role-scoped Runtime ARN invocations
- [x] S3 Tables SigV4 signing via IAM roles

## Task 7: Documentation & Configuration
- [x] DEPLOYMENT_GUIDE.md with step-by-step instructions
- [x] `.env.sample` files for each agent
- [x] README with architecture overview
