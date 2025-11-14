#!/bin/bash

set -e

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo "🔧 Loading configuration from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default configuration
AWS_REGION="${AWS_REGION:-us-east-1}"

echo "=================================================="
echo "📦 Deploying Strategy Quant Agent"
echo "=================================================="
echo ""

if [ -f "quant_agent.py" ]; then
    echo "✅ Agent file found: quant_agent.py"
    echo ""
    
    # Configure the agent
    echo "📝 Configuring agent..."
    agentcore configure \
        --entrypoint quant_agent.py \
        --name quant_agent \
        --requirements-file requirements.txt
    
    # Launch the agent
    echo "🚀 Launching agent to AgentCore..."
    agentcore launch --auto-update-on-conflict
    
    echo "✅ Strategy Quant deployed successfully!"
    echo ""
    
    # Check status
    echo "📊 Checking agent status..."
    agentcore status --agent quant_agent
    
    # Test invoke
    echo ""
    echo "🧪 Testing agent invocation..."
    agentcore invoke '{"prompt": "how is the strategy performance: {\"name\": \"EMA Crossover Strategy\", \"stock_symbol\": \"AMZN\", \"backtest_window\": \"1Y\", \"max_positions\": 1, \"stop_loss\": 5, \"take_profit\": 10, \"buy_conditions\": \"10-period SMA crosses above 30-period SMA (bullish momentum)\", \"sell_conditions\": \"10-period SMA crosses below 30-period SMA (bearish momentum)\", \"average\": 30}"}'

else
    echo "❌ Agent file not found: quant_agent.py"
fi

