# Quant Agent (orchestrator)

Deployed as a single AgentCore Runtime: **`paper_quant_agent`**. It handles both
strategy sources — a research paper PDF or manually typed buy/sell conditions —
plus a chat mode for analyzing historical backtests.

## Files

- `quant_agent.py` — entrypoint. Routes by payload:
  - `{"pdf_base64": ...}` → pypdf text extraction → PaperIdeaExtractor agent →
    strategy JSON → 4-step workflow
  - `{"prompt": ...}` → 4-step workflow directly (manual buy/sell conditions)
  - `{"mode": "chat", ...}` → history-analysis assistant
- `config.py` — env/config, AWS clients, AgentCore Memory helpers
- `tools/` — Strands tools: strategy generator (calls the Strategy Generator
  Runtime), market data via MCP Gateway, backtest in Code Interpreter sandbox,
  results summary, cross-session backtest history (semantic LTM + all-session scan)
- `deploy_to_agentcore.sh` — deploys the runtime

## Deploy

```bash
./deploy_to_agentcore.sh    # deploys as paper_quant_agent
```

Requires the Python starter-toolkit CLI (`bedrock-agentcore-starter-toolkit`);
set `AGENTCORE_BIN` if it lives in a venv, and `EXECUTION_ROLE` to reuse a role
that can invoke the downstream runtimes.
