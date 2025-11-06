#!/bin/bash

# Deploy AgentCore Backtesting Agent
# Single agent with Strands tools and Gateway integration

# TODO: Modify this shell script to be cdk instead 

set -e

echo "🚀 Deploying AgentCore Backtesting Agent"
echo "======================================="

AGENT_NAME="backtest_agent"
AGENT_FILE="agent.py"
REQUIREMENTS_FILE="requirements.txt"
UPDATE_MODE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --update)
            UPDATE_MODE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--update]"
            echo "  --update: Update existing agent instead of creating new one"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "📋 Configuration:"
echo "   Agent: $AGENT_NAME"
echo "   File: $AGENT_FILE"
echo "   Update mode: $UPDATE_MODE"

# Check prerequisites
echo ""
echo "📋 Checking prerequisites..."

if ! command -v agentcore &> /dev/null; then
    echo "❌ AgentCore CLI not found. Please install it first:"
    echo "   pip install bedrock-agentcore-starter-toolkit"
    exit 1
fi

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "❌ $REQUIREMENTS_FILE not found."
    exit 1
fi

if [ ! -f "$AGENT_FILE" ]; then
    echo "❌ $AGENT_FILE not found."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Load Gateway configuration from MCP tools
echo ""
echo "🔗 Loading Gateway configuration..."
MCP_TOOLS_ENV="tools/market_data_mcp/.env"

if [ -f "$MCP_TOOLS_ENV" ]; then
    source "$MCP_TOOLS_ENV"
    
    if [ -n "$GATEWAY_URL" ]; then
        export AGENTCORE_GATEWAY_MCP_URL="$GATEWAY_URL"
        echo "✅ Gateway URL loaded: $GATEWAY_URL"
        echo "🌐 Environment variable set: AGENTCORE_GATEWAY_MCP_URL"
    else
        echo "⚠️  Gateway URL not found in $MCP_TOOLS_ENV"
        echo "💡 Agent will deploy without Gateway integration"
        echo "   Deploy MCP tools first: cd tools/market_data_mcp && ./deploy_all.sh"
    fi
else
    echo "⚠️  MCP tools environment file not found: $MCP_TOOLS_ENV"
    echo "💡 Agent will deploy without Gateway integration"
    echo "   Deploy MCP tools first: cd tools/market_data_mcp && ./deploy_all.sh"
fi

# Function to check if agent exists
agent_exists() {
    agentcore status --agent "$AGENT_NAME" &>/dev/null
    return $?
}

# Handle existing agent
echo ""
if agent_exists; then
    if [ "$UPDATE_MODE" = true ]; then
        echo "🔄 Agent $AGENT_NAME exists - updating..."
        echo "🗑️ Destroying existing agent..."
        agentcore destroy --agent "$AGENT_NAME" --force
        echo "⏳ Waiting for cleanup..."
        sleep 5
        echo "✅ Existing agent destroyed"
    else
        echo "⚠️ Agent $AGENT_NAME already exists!"
        echo "   Use --update flag to update existing agent"
        echo "   Or manually destroy: agentcore destroy --agent $AGENT_NAME --force"
        exit 1
    fi
else
    echo "🆕 Creating new agent: $AGENT_NAME"
fi

# Configure the agent
echo ""
echo "⚙️ Configuring backtesting agent..."
agentcore configure \
    --entrypoint "$AGENT_FILE" \
    --name "$AGENT_NAME" \
    --requirements-file "$REQUIREMENTS_FILE" \
    --disable-memory \
    --non-interactive

echo "✅ Configuration completed"

# Deploy the agent
echo ""
echo "🚀 Deploying to AgentCore Runtime..."
agentcore launch --agent "$AGENT_NAME"

# Wait for deployment
echo "⏳ Waiting for deployment to complete..."
sleep 15

# Get agent status
echo ""
echo "📊 Getting agent status..."
agentcore status --agent "$AGENT_NAME"

# Extract ARN for reference
AGENT_ARN=$(agentcore status --agent "$AGENT_NAME" 2>/dev/null | grep -o 'arn:aws:bedrock-agentcore:[^[:space:]]*' | head -1)

echo ""
echo "🎉 Agent Deployed Successfully!"
echo "=============================="
echo ""
echo "📋 Agent Details:"
echo "   Name: $AGENT_NAME"
echo "   ARN: $AGENT_ARN"
echo "   Architecture: Single agent with Strands tools"
echo ""
echo "🔧 Available Strands Tools:"
echo "   ✅ fetch_market_data_via_gateway - Market data via Gateway"
echo "   ✅ generate_trading_strategy - Strategy code generation"
echo "   ✅ run_backtest - Backtesting execution"
echo "   ✅ create_results_summary - Results processing"
echo "   ✅ execute_full_backtest_workflow - Complete workflow"
echo ""
echo "🧪 Test Commands:"
echo ""
echo "   # Test complete workflow"
echo "   agentcore invoke '{\"initial_investment\": 10000, \"investment_area\": \"Technology\", \"buy_condition\": \"price above moving average\", \"sell_condition\": \"price below moving average\"}' --agent $AGENT_NAME"
echo ""
echo "   # Test conversational interface"
echo "   agentcore invoke '{\"prompt\": \"Help me backtest a moving average strategy with \\$5000 in tech stocks\"}' --agent $AGENT_NAME"
echo ""
echo "   # Test Gateway integration"
echo "   agentcore invoke '{\"prompt\": \"Fetch market data for Healthcare sector\"}' --agent $AGENT_NAME"
echo ""
echo "🔗 Management Commands:"
echo "   # Update agent after code changes"
echo "   ./deploy_agent.sh --update"
echo ""
echo "   # Check agent status"
echo "   agentcore status --agent $AGENT_NAME"
echo ""
echo "   # View agent logs"
echo "   agentcore logs --agent $AGENT_NAME"
echo ""
echo "   # Destroy agent"
echo "   agentcore destroy --agent $AGENT_NAME --force"
echo ""
echo "🌐 Gateway Integration:"
if [ -n "$AGENTCORE_GATEWAY_MCP_URL" ]; then
    echo "   ✅ Gateway URL configured: $AGENTCORE_GATEWAY_MCP_URL"
    echo "   🔗 Agent can access Market Data MCP server"
    echo ""
    echo "   Note: OAuth token will be handled automatically by AgentCore"
else
    echo "   ❌ Gateway URL not configured"
    echo "   💡 To enable Gateway integration:"
    echo "      1. Deploy MCP tools: cd tools/market_data_mcp && ./deploy_all.sh"
    echo "      2. Ensure GATEWAY_URL is set in tools/market_data_mcp/.env"
    echo "      3. Re-run this script: ./deploy_agent.sh --update"
fi

echo ""
echo "🎉 Deployment Complete! Your agent is ready to use."