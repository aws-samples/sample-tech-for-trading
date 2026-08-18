#!/bin/bash

set -e

# Python starter-toolkit CLI (bedrock-agentcore-starter-toolkit, NOT the Node/CDK CLI).
# Override with AGENTCORE_BIN if your toolkit lives in a venv.
AGENTCORE_BIN="${AGENTCORE_BIN:-agentcore}"

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo "🔧 Loading configuration from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default configuration
AWS_REGION="${AWS_REGION:-us-east-2}"

# Optional: reuse an existing execution role that can invoke the downstream
# runtimes (strategy generator / results summary) and the quant memory.
# If unset, the toolkit auto-creates a role — you must then add those
# permissions manually (see agentic_backtesting/history/004, Bug 3).
EXECUTION_ROLE="${EXECUTION_ROLE:-}"

echo "=================================================="
echo "📦 Deploying Paper Quant Agent"
echo "=================================================="
echo ""

if [ -f "paper_quant_agent.py" ]; then
    echo "✅ Agent file found: paper_quant_agent.py"
    echo ""

    # Ensure .env file is included in deployment
    echo "📝 Configuring agent..."
    if [ ! -f ".env" ]; then
        echo "❌ .env file not found!"
        exit 1
    fi

    ROLE_ARGS=""
    if [ -n "$EXECUTION_ROLE" ]; then
        ROLE_ARGS="--execution-role $EXECUTION_ROLE"
    fi

    "$AGENTCORE_BIN" configure \
        --entrypoint paper_quant_agent.py \
        --name paper_quant_agent \
        $ROLE_ARGS \
        --requirements-file requirements.txt \
        --region "$AWS_REGION" \
        --deployment-type direct_code_deploy \
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

    # Deploy the agent with environment variables
    echo "🚀 Deploying agent to AgentCore with environment variables..."
    "$AGENTCORE_BIN" deploy --auto-update-on-conflict $ENV_ARGS

    echo "✅ Paper Quant Agent deployed successfully!"
    echo ""

    # Check status
    echo "📊 Checking agent status..."
    "$AGENTCORE_BIN" status --agent paper_quant_agent

    # Smoke test: plain strategy prompt (no PDF) exercises the full 4-step workflow
    echo ""
    echo "🧪 Testing agent invocation (plain strategy pass-through)..."
    "$AGENTCORE_BIN" invoke '{"prompt": "how is the strategy performance: {\"name\": \"EMA Crossover Strategy\", \"stock_symbol\": \"AMZN\", \"backtest_window\": \"1Y\", \"max_positions\": 1, \"stop_loss\": 5, \"take_profit\": 10, \"buy_conditions\": \"10-period SMA crosses above 30-period SMA (bullish momentum)\", \"sell_conditions\": \"10-period SMA crosses below 30-period SMA (bearish momentum)\", \"average\": 30}"}'

else
    echo "❌ Agent file not found: paper_quant_agent.py"
fi
