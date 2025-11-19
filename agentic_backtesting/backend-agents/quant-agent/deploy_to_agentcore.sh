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
    
    # Ensure .env file is included in deployment
    echo "📝 Configuring agent..."
    if [ ! -f ".env" ]; then
        echo "❌ .env file not found!"
        exit 1
    fi
    
    agentcore configure \
        --entrypoint quant_agent.py \
        --name quant_agent \
        --requirements-file requirements.txt \
        --idle-timeout 900 \
        --non-interactive
    
    # Build environment variables from .env file
    echo "🔧 Preparing environment variables from .env..."
    ENV_ARGS=""
    if [ -f ".env" ]; then
        # Read .env file and build --env arguments
        while IFS='=' read -r key value; do
            # Skip empty lines and comments
            if [[ ! -z "$key" && ! "$key" =~ ^# ]]; then
                # Remove any quotes from value
                value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
                ENV_ARGS="$ENV_ARGS --env $key=$value"
                echo "   ✓ $key"
            fi
        done < .env
    fi
    
    # Launch the agent with environment variables
    echo "🚀 Launching agent to AgentCore with environment variables: $ENV_ARGS"
    agentcore launch --auto-update-on-conflict $ENV_ARGS
    
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

