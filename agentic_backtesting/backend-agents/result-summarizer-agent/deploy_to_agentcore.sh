#!/bin/bash

set -e

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo "🔧 Loading configuration from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default configuration
AWS_REGION="${AWS_REGION:-us-east-1}"

# Deploy Results Summary Agent
echo "=================================================="
echo "📦 Deploying Results Summary Agent"
echo "=================================================="
echo ""

if [ -f "results_summary.py" ]; then
    echo "✅ Agent file found: results_summary.py"
    echo ""
    
    # Configure the agent
    echo "📝 Configuring agent..."
    agentcore configure \
        --entrypoint results_summary.py \
        --name results_summary \
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
    
    echo "✅ Results Summary deployed successfully!"
    echo ""
    
    # Check status
    echo "📊 Checking agent status..."
    agentcore status --agent results_summary
    
    # Test invoke
    echo ""
    echo "🧪 Testing agent invocation..."
    agentcore invoke '{"initial_value": 100000, "final_value": 125000, "total_return": 25.0, "symbol": "AMZN"}'
    
else
    echo "❌ Agent file not found: results_summary.py"
fi
