# Design: Backend Agents

## Architecture

```
Frontend (Next.js)
    │
    ▼ invoke_agent_runtime()
┌──────────────────────────────────────────────┐
│  Quant Agent (Orchestrator)                  │
│  AgentCore Runtime · Strands Agent SDK       │
│  4 sequential @tool functions                │
├──────────────────────────────────────────────┤
│                                              │
│  Step 1: generate_trading_strategy()         │
│    └→ invokes Strategy Generator Runtime     │
│                                              │
│  Step 2: fetch_market_data_via_gateway()     │
│    └→ AgentCore Gateway (MCP JSON-RPC 2.0)  │
│       └→ Cognito Auth (bearer token)        │
│       └→ Lambda (PyIceberg → S3 Tables)     │
│                                              │
│  Step 3: run_backtest()                      │
│    └→ BacktestTool (Backtrader Cerebro)     │
│    └→ stores results in AgentCore Memory    │
│                                              │
│  Step 4: create_results_summary()            │
│    └→ reads from AgentCore Memory           │
│    └→ invokes Results Summary Runtime       │
└──────────────────────────────────────────────┘
```

## Component Design

### Quant Agent (Orchestrator)
- **File**: `backend-agents/quant-agent/quant_agent.py`
- Strands Agent with system prompt enforcing sequential-only tool execution
- 4 tools registered via `@tool` decorator
- AgentCore Memory integration for session-based result persistence
- Global `_stored_market_data` dict for cross-tool data sharing

### Strategy Generator Agent
- **File**: `backend-agents/strategy-generator-agent/strategy_generator.py`
- Class: `StrategyGeneratorAgent`
- Entry point: `@app.entrypoint` decorated `invoke()` function
- Input: JSON strategy config → Output: executable Backtrader Python code
- Model: Claude Sonnet 4, temperature 0.3

### Results Summary Agent
- **File**: `backend-agents/result-summarizer-agent/results_summary.py`
- Class: `ResultsSummaryAgent`
- Methods: `analyze_results()`, `process()`
- Input: backtest metrics → Output: JSON analysis report
- Model: Amazon Nova Pro, temperature 0.3

### Backtest Tool
- **File**: `backend-agents/quant-agent/tools/backtest.py`
- Class: `BacktestTool`
- 10+ step execution: code exec → strategy detection → data validation → Cerebro setup → broker config → analyzers → execution → results extraction

### Market Data MCP Lambda
- **File**: `backend-agents/quant-agent/tools/market_data_mcp/lambda_function.py`
- Handler: `lambda_handler(event, context)`
- PyIceberg queries against S3 Tables (Apache Iceberg format)
- Supports filters: symbol, start_date, end_date, limit
- Deployed as container image (Python 3.12, 512MB, 60s timeout)

## Data Flow

```
StrategyInput (JSON)
  → Strategy code (Python string)
  → Market data (OHLCV DataFrame, 252 days default)
  → Backtest metrics (Sharpe, Sortino, drawdown, returns, win rate)
  → AgentCore Memory (session events)
  → Analysis report (JSON: executive_summary, detailed_analysis, recommendations)
```

## Infrastructure

| Component              | Service            | Config                      |
|------------------------|--------------------|-----------------------------|
| Quant Agent            | AgentCore Runtime  | deploy_to_agentcore.sh      |
| Strategy Generator     | AgentCore Runtime  | deploy_to_agentcore.sh      |
| Results Summary        | AgentCore Runtime  | deploy_to_agentcore.sh      |
| Market Data Lambda     | Lambda + ECR       | deployment/deploy_lambda.sh |
| MCP Gateway            | AgentCore Gateway  | deployment/create_mcp_gateway.sh |
| Market Data Store      | S3 Tables (Iceberg)| namespace: daily_data       |
| Authentication         | Cognito User Pool  | Admin-initiated auth flow   |

## Key Dependencies
- strands-agents >= 0.1.0
- boto3 >= 1.26.0
- bedrock_agentcore + starter-toolkit
- backtrader == 1.9.78.123
- pandas >= 1.5.0, numpy >= 1.24.0
- pyarrow >= 10.0.0, pyiceberg >= 0.5.0
- httpx >= 0.24.0
- python-dotenv >= 1.0.0
