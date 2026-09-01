# Quant Agent (orchestrator)

Single codebase serving **two AgentCore Runtimes**:

| Runtime | Used by | Strategy source |
|---|---|---|
| `paper_quant_agent` | `../../frontend` (current deployment) | research paper PDF **or** manual conditions |
| `quant_agent` | legacy deployment (kept for compatibility) | manual buy/sell conditions |

## Files

- `quant_agent.py` — entrypoint. Routes by payload:
  - `{"pdf_base64": ...}` → pypdf text extraction → PaperIdeaExtractor agent →
    strategy JSON → 4-step workflow
  - `{"prompt": ...}` → 4-step workflow directly
  - `{"mode": "chat", ...}` → history-analysis assistant
- `config.py` — env/config, AWS clients, AgentCore Memory helpers
- `tools/` — Strands tools: strategy generator (calls the Strategy Generator
  Runtime), market data via MCP Gateway, backtest in Code Interpreter sandbox,
  results summary, cross-session backtest history (semantic LTM + all-session scan)
- `deploy_to_agentcore.sh` — deploys either runtime; see below

## Deploy

```bash
# default runtime (quant_agent)
./deploy_to_agentcore.sh

# paper-backtest runtime
AGENT_NAME=paper_quant_agent ./deploy_to_agentcore.sh
```

Requires the Python starter-toolkit CLI (`bedrock-agentcore-starter-toolkit`);
set `AGENTCORE_BIN` if it lives in a venv, and `EXECUTION_ROLE` to reuse a role
that can invoke the downstream runtimes.
