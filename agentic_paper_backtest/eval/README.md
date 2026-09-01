# AgentCore Evaluation for the Paper Quant Agent

Evaluation assets for the orchestrator agent (`paper_quant_agent`, AgentCore Runtime).
Evaluations judge real agent sessions from their OTEL traces — no test harness needed.

## Contents

| File | Purpose |
|---|---|
| `evaluators/workflow-completeness.json` | Custom evaluator (TRACE): 4-step workflow executed in order with correct data flow |
| `evaluators/metrics-faithfulness.json` | Custom evaluator (TRACE): reported metrics match `run_backtest` tool outputs — catches hallucinated numbers |
| `evaluators/paper-extraction-fidelity.json` | Custom evaluator (SESSION): strategy extracted from the PDF is faithful to the paper's core idea |
| `register_evaluators.sh` | Create/update the three custom evaluators (idempotent) |
| `run_eval.sh` | Evaluate one session with builtin + custom evaluators |

## Prerequisites

1. **Python starter-toolkit CLI** (`bedrock-agentcore-starter-toolkit`), not the Node/CDK
   `agentcore` CLI. If it lives in a venv:
   ```bash
   export AGENTCORE_BIN=/path/to/.venv/bin/agentcore
   ```
2. **Tracing must be on** — evaluation reads spans from the `aws/spans` log group
   (CloudWatch Transaction Search):
   - The agent's `requirements.txt` must include `aws-opentelemetry-distro`
     (already added). With `direct_code_deploy`, the observability flag alone
     does NOT emit spans — missing this package is the cause of
     `Error: No spans found for session ...`.
   - Transaction Search must be enabled once per account/region:
     `aws xray get-trace-segment-destination --region us-east-2` should show
     `CloudWatchLogs / ACTIVE`. If not, run
     `aws xray update-trace-segment-destination --destination CloudWatchLogs`.
3. Run commands from the agent directory (so the CLI finds `.bedrock_agentcore.yaml`),
   or pass `-a paper_quant_agent`.

## Quick start

```bash
cd eval

# 1. Register the custom evaluators (one-time; re-run to update instructions)
./register_evaluators.sh

# 2. Evaluate a session
./run_eval.sh <session-id> results.json
```

## Finding a session id to evaluate

Every invocation carries a `runtimeSessionId`:

- **From the frontend**: each backtest job uses a fresh UUID session. Find it in the
  ECS/Next.js logs (`[AgentCore]` lines) or in the runtime's CloudWatch log group
  `/aws/bedrock-agentcore/runtimes/paper_quant_agent-<id>-DEFAULT` — the log stream
  name contains the session id.
- **From a manual invoke**: whatever you passed as `runtimeSessionId`.
- **From spans directly** (last hour):
  ```bash
  aws logs start-query --log-group-name aws/spans --region us-east-2 \
    --start-time $(($(date +%s)-3600)) --end-time $(date +%s) \
    --query-string 'stats count(*) by attributes.session.id, attributes.aws.local.service'
  # then: aws logs get-query-results --query-id <id>
  ```

Spans appear in `aws/spans` a minute or two after the invocation completes.

## What the custom evaluators check

The orchestrator must run 4 tools in strict order (see the system prompt in
`paper_quant_agent.py`): `generate_trading_strategy` → `fetch_market_data_via_gateway`
→ `run_backtest` → `create_results_summary`. Each evaluator targets one failure mode
we care about:

1. **workflow-completeness** (0–4): did the orchestration actually happen as designed?
   Catches skipped steps, reordered calls, and broken data flow between steps. This is
   the orchestrator's core contract.
2. **metrics-faithfulness** (0–2): are the numbers shown to the user exactly what
   `run_backtest` returned? Catches the worst failure for a finance demo — hallucinated
   returns/Sharpe/drawdown. Score 0 on any fabricated number.
3. **paper-extraction-fidelity** (0–4): paper mode only — does the extracted strategy
   reflect the paper's core idea (with paper parameters, disclosed approximations,
   user overrides respected), or did the extractor fall back to a generic strategy?
   Auto-passes with a note for non-paper sessions.

Builtin evaluators used alongside: `Builtin.GoalSuccessRate`, `Builtin.Helpfulness`,
`Builtin.ToolSelectionAccuracy`.

### Authoring notes (API constraints, learned the hard way)

- `llmAsAJudge.modelConfig` is **required** — pick a judge model
  (`bedrockEvaluatorModelConfig.modelId`) and keep `temperature: 0`.
- Evaluator names must match `[a-zA-Z][a-zA-Z0-9_]{0,47}` — no hyphens.
- Instruction placeholders are level-dependent:
  - `TRACE` allows only `{context}`, `{assistant_turn}`, `{expected_response}`,
    `{system_instructions}`
  - `SESSION` additionally allows `{actual_tool_trajectory}`, `{assertions}`, etc.
  `{context}` already contains the tool calls with inputs/outputs, so TRACE
  evaluators can still judge tool usage.

## Reading results

`run_eval.sh` saves JSON like:

```json
{
  "summary": {"total_evaluations": 6, "successful": 6, "failed": 0},
  "results": [
    {"evaluator_name": "Builtin.GoalSuccessRate", "value": 1.0, "label": "Yes",
     "explanation": "..."}
  ]
}
```

- TRACE-level evaluators emit one result per trace (ToolSelectionAccuracy emits one
  per tool call), SESSION-level one per session.
- Each result includes the judge's `explanation` — read it before acting on a score;
  LLM judges can misread unusual sessions.
- Baseline (2026-08-20, session `4aedf1b3-...`, 9 evaluations): all builtins 1.0
  (Helpfulness "Above And Beyond"), workflow_completeness 4/4 "Perfect workflow",
  metrics_faithfulness 2/2 "Faithful", extraction_fidelity 4/4.

## Continuous (online) evaluation

To score live traffic automatically instead of per-session:

```bash
agentcore eval online create --help   # sampling rate, evaluator set, output
```

Results flow to CloudWatch (GenAI Observability dashboard → Agent Core). Start with a
low sampling rate — every evaluated trace costs judge-model tokens (a full 6-evaluator
run on one session costs roughly 30–50k input tokens).

## Cost & limits

- Judges run on Bedrock models in this account; each evaluator call is an LLM call.
- `eval run` reads the most recent 1000 spans of the session (7-day default lookback,
  `-d` to change).
- One runtime session handles one invocation at a time — don't fire concurrent
  invokes with the same session id when generating traces (Strands raises
  ConcurrencyException).
