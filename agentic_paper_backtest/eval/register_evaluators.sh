#!/bin/bash
# Register (or update) the custom evaluators in this directory with AgentCore.
# Idempotent: if an evaluator with the same name exists, it is updated.
#
# Requires the Python starter-toolkit CLI (bedrock-agentcore-starter-toolkit);
# override with AGENTCORE_BIN if it lives in a venv.
set -e

AGENTCORE_BIN="${AGENTCORE_BIN:-agentcore}"
AWS_REGION="${AWS_REGION:-us-east-2}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

declare -a EVALUATORS=(
  "paper_backtest_workflow_completeness|TRACE|Checks the 4-step quant workflow executed in order with correct data flow|workflow-completeness.json"
  "paper_backtest_metrics_faithfulness|TRACE|Checks reported metrics match run_backtest tool outputs (no hallucinated numbers)|metrics-faithfulness.json"
  "paper_backtest_extraction_fidelity|SESSION|Checks the strategy extracted from the PDF is faithful to the paper|paper-extraction-fidelity.json"
)

for entry in "${EVALUATORS[@]}"; do
  IFS='|' read -r NAME LEVEL DESC FILE <<< "$entry"
  CONFIG="$SCRIPT_DIR/evaluators/$FILE"
  echo "── $NAME ($LEVEL)"

  # Find existing evaluator id by name (custom evaluator ids are name-suffixed)
  EXISTING_ID=$("$AGENTCORE_BIN" eval evaluator list 2>/dev/null \
    | grep -oE "${NAME}-[a-zA-Z0-9]+" | head -1 || true)

  if [ -n "$EXISTING_ID" ]; then
    echo "   updating existing: $EXISTING_ID"
    "$AGENTCORE_BIN" eval evaluator update \
      --evaluator-id "$EXISTING_ID" \
      --config "$CONFIG" \
      --description "$DESC"
  else
    "$AGENTCORE_BIN" eval evaluator create \
      --name "$NAME" \
      --config "$CONFIG" \
      --level "$LEVEL" \
      --description "$DESC"
  fi
done

echo ""
echo "✅ Done. List all evaluators with:"
echo "   $AGENTCORE_BIN eval evaluator list"
