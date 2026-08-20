#!/bin/bash
# Evaluate a paper_quant_agent session with builtin + custom evaluators.
#
# Usage:
#   ./run_eval.sh <session-id> [output.json]
#
# The session id is the runtimeSessionId used when invoking the agent
# (the frontend generates one per backtest job; see eval/README.md for
# how to find it in CloudWatch).
set -e

AGENTCORE_BIN="${AGENTCORE_BIN:-agentcore}"
AGENT_NAME="${AGENT_NAME:-paper_quant_agent}"

SESSION_ID="$1"
OUTPUT="${2:-eval_results_$(date +%Y%m%d_%H%M%S).json}"

if [ -z "$SESSION_ID" ]; then
  echo "Usage: $0 <session-id> [output.json]"
  exit 1
fi

# Resolve custom evaluator ids by name prefix (created by register_evaluators.sh)
CUSTOM_ARGS=""
for NAME in paper_backtest_workflow_completeness paper_backtest_metrics_faithfulness paper_backtest_extraction_fidelity; do
  ID=$("$AGENTCORE_BIN" eval evaluator list 2>/dev/null | grep -oE "${NAME}-[a-zA-Z0-9]+" | head -1 || true)
  if [ -n "$ID" ]; then
    CUSTOM_ARGS="$CUSTOM_ARGS -e $ID"
  else
    echo "⚠️  Custom evaluator '$NAME' not registered — run ./register_evaluators.sh first"
  fi
done

"$AGENTCORE_BIN" eval run \
  -a "$AGENT_NAME" \
  -s "$SESSION_ID" \
  -e Builtin.GoalSuccessRate \
  -e Builtin.Helpfulness \
  -e Builtin.ToolSelectionAccuracy \
  $CUSTOM_ARGS \
  -A "The agent executed all 4 steps in order: generate_trading_strategy, fetch_market_data_via_gateway, run_backtest, create_results_summary" \
  -A "The final response contains backtest performance metrics including total return and max drawdown" \
  -o "$OUTPUT"

echo ""
echo "✅ Results saved to $OUTPUT"
