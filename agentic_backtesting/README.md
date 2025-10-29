# Agentic Backtesting - Multi-Agent Trading System

A multi-agent system built with Strands for automated trading strategy development and backtesting using Redshift data.

## Overview

This system uses 4 specialized agents orchestrated through Strands to transform trading ideas into backtested strategies:

1. **Strategy Generator Agent** - Converts natural language trading ideas into executable Backtrader strategies
2. **Market Data Agent** - Fetches historical market data from AWS Redshift
3. **Backtest Agent** - Executes backtests using Backtrader framework
4. **Results Summary Agent** - Analyzes performance and generates comprehensive reports

## Architecture

```
User Input (Trading Idea) 
    ↓
Orchestrator Agent (Strands)
    ↓
Strategy Generator → Market Data → Backtest → Results Summary
    ↓                    ↓             ↓           ↓
Strategy Code      Redshift Data   BT Results   Report
```

## Quick Start

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Redshift credentials

# Run the system
python main.py

# Example interaction:
# > how is the momentum strategy performance that buys AMZN when RSI > 70 and sells when RSI < 30 in last 1 years
```

## Configuration

Set up your `.env` file with Redshift connection details:

```bash
# Redshift Database Configuration
PGHOST=your-redshift-cluster.region.redshift.amazonaws.com
PGPORT=5439
PGUSER=admin
PGPASSWORD=your_password
PGDATABASE=trading
```

## Features

- **Natural Language Processing**: Describe strategies in plain English
- **Automated Pipeline**: Full strategy-to-results execution without manual intervention
- **Redshift Integration**: Direct connection to AWS Redshift for market data
- **Backtrader Framework**: Professional-grade backtesting engine
- **Comprehensive Analysis**: Detailed performance metrics and visualizations
- **Template-Based Generation**: Pre-built strategy templates (RSI, Momentum, Mean Reversion)

## Agent Details

### Orchestrator Agent (Strands)
- Coordinates all agents using Strands framework
- Automatically executes complete pipeline
- Handles timing and data flow between agents
- Provides unified interface for user interactions

### Strategy Generator Agent
- Converts natural language to Backtrader strategy code
- Supports RSI, momentum, and mean reversion strategies
- Generates executable Python code with proper indicators
- Template-based approach for consistent strategy structure

### Market Data Agent  
- Connects to AWS Redshift for historical data
- Implements connection pooling and error handling
- Supports multiple symbols and time periods
- Caches data for performance optimization

### Backtest Agent
- Executes strategies using Backtrader framework
- Configurable parameters (initial cash, commission, etc.)
- Handles multiple data feeds and symbols
- Returns comprehensive performance metrics

### Results Summary Agent
- Analyzes backtest performance metrics
- Generates formatted reports with key statistics
- Provides performance assessment and recommendations
- Supports markdown formatting for clear presentation
