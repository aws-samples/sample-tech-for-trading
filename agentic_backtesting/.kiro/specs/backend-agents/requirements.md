# Requirements: Backend Agents

## Overview
Multi-agent backtesting system using AWS Bedrock AgentCore, Strands Agent SDK, and Backtrader to convert natural language trading strategies into executable backtests with AI-powered analysis.

## Functional Requirements

### REQ-1: Strategy Generation
- **Given** a user provides a trading strategy configuration (name, symbol, buy/sell conditions, stop-loss, take-profit, max positions)
- **When** the strategy generator agent receives the configuration
- **Then** it produces executable Backtrader Python strategy code using Claude Sonnet 4 (temperature 0.3)

### REQ-2: Market Data Retrieval
- **Given** a backtest requires historical OHLCV data for a specific stock symbol
- **When** the quant agent calls the market data gateway
- **Then** data is fetched from S3 Tables (Apache Iceberg) via AgentCore Gateway + Lambda (MCP JSON-RPC 2.0 protocol) with Cognito authentication
- **Then** default 252 trading days of data is returned

### REQ-3: Backtest Execution
- **Given** a generated strategy and fetched market data
- **When** the backtest tool runs
- **Then** a Backtrader Cerebro engine executes the strategy over historical data and extracts performance metrics (Sharpe ratio, Sortino ratio, max drawdown, total return, win rate)

### REQ-4: Results Summary & Analysis
- **Given** completed backtest results stored in AgentCore Memory
- **When** the results summary agent processes the metrics
- **Then** it returns a JSON report with executive summary, detailed analysis, red flag detection (overfitting, unrealistic returns), and actionable recommendations using Amazon Nova Pro model

### REQ-5: Orchestration
- **Given** a user request from the frontend
- **When** the quant agent (orchestrator) receives the request
- **Then** it executes a strict 4-step sequential workflow: (1) generate strategy, (2) fetch market data, (3) run backtest, (4) create results summary
- **Then** results are persisted to AgentCore Memory with session-based organization

### REQ-6: Agent Communication
- **Given** agents deployed as separate AgentCore Runtimes
- **When** agents need to communicate
- **Then** the quant agent invokes other runtimes synchronously via `bedrock-agentcore` boto3 client using Runtime ARNs
- **Then** market data is accessed via AgentCore Gateway with Cognito OAuth bearer tokens

## Non-Functional Requirements

### REQ-7: Deployment
- Agents deploy to AgentCore Runtime via `agentcore` CLI
- Market data Lambda deploys as container image (Python 3.12) to ECR + Lambda (512MB, 60s timeout)
- AgentCore Gateway provides MCP protocol layer with Cognito auth

### REQ-8: Security
- Market data access secured via Cognito OAuth + bearer tokens
- Agent invocation via IAM-scoped Runtime ARNs
- S3 Tables access via IAM role-based SigV4 signing

### REQ-9: Configurability
- Model IDs configurable via environment variables
- Temperature, region, runtime ARNs, Cognito credentials all environment-driven
- `.env` files per agent directory
