#!/bin/bash
# Deploy the quant agent to AgentCore Runtime.
#
# The same codebase serves two runtimes:
#   ./deploy_to_agentcore.sh                          # deploys as quant_agent (default)
#   AGENT_NAME=paper_quant_agent ./deploy_to_agentcore.sh   # deploys the paper-backtest runtime
#
# Requires the Python starter-toolkit CLI (bedrock-agentcore-starter-toolkit),
# NOT the Node/CDK "agentcore". Override with AGENTCORE_BIN if it lives in a venv.
# Optionally set EXECUTION_ROLE to reuse a role that can already invoke the
# downstream runtimes (see agentic_backtesting/history/004, Bug 3).
set -e

AGENTCORE_BIN="${AGENTCORE_BIN:-agentcore}"
AGENT_NAME="${AGENT_NAME:-quant_agent}"
EXECUTION_ROLE="${EXECUTION_ROLE:-}"

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo "🔧 Loading configuration from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default configuration
AWS_REGION="${AWS_REGION:-us-east-2}"

echo "=================================================="
echo "📦 Deploying Quant Agent as '$AGENT_NAME'"
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

    ROLE_ARGS=""
    if [ -n "$EXECUTION_ROLE" ]; then
        ROLE_ARGS="--execution-role $EXECUTION_ROLE"
    fi

    "$AGENTCORE_BIN" configure \
        --entrypoint quant_agent.py \
        --name "$AGENT_NAME" \
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
    echo "🚀 Deploying '$AGENT_NAME' to AgentCore..."
    "$AGENTCORE_BIN" deploy --agent "$AGENT_NAME" --auto-update-on-conflict $ENV_ARGS

    echo "✅ '$AGENT_NAME' deployed successfully!"
    echo ""

    # Check status
    echo "📊 Checking agent status..."
    "$AGENTCORE_BIN" status --agent "$AGENT_NAME"

    # Smoke test: plain strategy prompt exercises the full 4-step workflow
    echo ""
    echo "🧪 Testing agent invocation..."
    "$AGENTCORE_BIN" invoke --agent "$AGENT_NAME" '{"prompt": "how is the strategy performance: {\"name\": \"EMA Crossover Strategy\", \"stock_symbol\": \"AMZN\", \"backtest_window\": \"1Y\", \"max_positions\": 1, \"stop_loss\": 5, \"take_profit\": 10, \"buy_conditions\": \"10-period SMA crosses above 30-period SMA (bullish momentum)\", \"sell_conditions\": \"10-period SMA crosses below 30-period SMA (bearish momentum)\", \"average\": 30}"}'

else
    echo "❌ Agent file not found: quant_agent.py"
fi
