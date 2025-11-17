# Agentic Backtesting - Multi-Agent Strategy Backtesting System

A multi-agent system built with Strands for automated trading strategy development and backtesting using historical market data.

## Overview

This system uses 4 specialized agents orchestrated through Strands to transform trading ideas into backtested strategies:

1. **Strategy Generator Agent** - Converts natural language trading ideas into executable Backtrader strategies
2. **Market Data Tool** - Fetches historical market data from S3 Table
3. **Backtest Tool** - Executes backtests using Backtrader framework
4. **Results Summary Agent** - Analyzes performance and generates comprehensive reports

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Quant Agent (Orchestrator)                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Tools:                                                     │  │
│  │ • fetch_market_data_via_gateway                          │  │
│  │ • generate_trading_strategy (calls Strategy Generator)   │  │
│  │ • run_backtest                                           │  │
│  │ • create_results_summary (calls Result Summarizer)      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────┬──────────────────┬──────────────────┬────────────────────┘
      │                  │                  │
      ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐
│  Strategy    │  │   Result     │  │  Market Data Gateway     │
│  Generator   │  │  Summarizer  │  │  (MCP + Cognito Auth)    │
│  Agent       │  │  Agent       │  │                          │
└──────────────┘  └──────────────┘  └────────┬─────────────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │  Lambda         │
                                    │  (S3 Tables)    │
                                    └─────────────────┘
```


## Deployment

For complete deployment instructions, please refer to **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)**.

The deployment guide covers:
- Prerequisites and required tools
- Market Data MCP tool setup with Cognito authentication
- Step-by-step backend agent deployment (Strategy Generator, Result Summarizer, Quant Agent)
- Frontend deployment instructions


## Agent Details

### Orchestrator Agent (Strands)
- Coordinates all agents using Strands framework
- Handles timing and data flow between agents
- Provides unified interface for user interactions
- Deploy to Agentcore Runtime

### Strategy Generator Agent
- Converts natural language to Backtrader strategy code
- Generates executable Python code with proper indicators
- Template-based approach for consistent strategy structure
- Deploy to Agentcore Runtime

### Market Data Tool  
- Connects to S3 Table for historical data
- Deploy to Agentcore Gateway

### Backtest Tool
- Executes strategies using Backtrader framework
- Configurable parameters (initial cash, commission, etc.)
- Returns comprehensive performance metrics

### Results Summary Agent
- Analyzes backtest performance metrics
- Provides performance assessment and recommendations
- Deploy to Agentcore Runtime