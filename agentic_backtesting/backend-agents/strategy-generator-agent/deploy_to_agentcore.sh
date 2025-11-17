#!/bin/bash

set -e

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo "🔧 Loading configuration from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default configuration
AWS_REGION="${AWS_REGION:-us-east-1}"

Deploy Strategy Generator Agent
echo "=================================================="
echo "📦 Deploying Strategy Generator Agent"
echo "=================================================="
echo ""

if [ -f "strategy_generator.py" ]; then
    echo "✅ Agent file found: strategy_generator.py"
    echo ""
    
    # Configure the agent
    echo "📝 Configuring agent..."
    agentcore configure \
        --entrypoint strategy_generator.py \
        --name strategy_generator \
        --requirements-file requirements.txt
    
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
    
    echo "✅ Strategy Generator deployed successfully!"
    echo ""
    
    # Check status
    echo "📊 Checking agent status..."
    agentcore status --agent strategy_generator
    
    # Test invoke
    echo ""
    echo "🧪 Testing agent invocation..."
    agentcore invoke '{"name": "EMA Crossover", "max_positions": 1, "stock_symbol": "AMZN", "buy_conditions": "EMA50 > EMA200", "sell_conditions": "EMA50 < EMA200"}'
    
else
    echo "❌ Agent file not found: strategy_generator.py"
fi
