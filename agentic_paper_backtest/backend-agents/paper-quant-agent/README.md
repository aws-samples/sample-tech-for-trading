# Paper Quant Agent

Orchestrator agent deployed to Amazon Bedrock AgentCore Runtime. Accepts a base64-encoded
research paper PDF, extracts the trading idea, and runs the standard 4-step backtest
workflow (strategy generation → market data → backtest → summary).

## Files

- `paper_quant_agent.py` — entrypoint. PDF text extraction (pypdf), PaperIdeaExtractor
  agent, and the quant workflow agent. Copied and extended from
  `agentic_backtesting/backend-agents/quant-agent/quant_agent.py`.
- `config.py` — env/config, AWS clients, AgentCore Memory helpers (unchanged from quant-agent)
- `tools/` — Strands tools (unchanged from quant-agent): strategy generator (calls the
  shared Strategy Generator Runtime), market data via MCP Gateway, backtest in Code
  Interpreter sandbox, results summary, backtest history
- `deploy_to_agentcore.sh` — configure + launch via `agentcore` CLI (profile `default`)
- `.env` — shared us-east-2 resource ARNs/URLs (copied from quant-agent)

## Payload contract

Paper mode:
```json
{
  "pdf_base64": "<base64 PDF>",
  "paper_name": "momentum.pdf",
  "stock_symbol": "AMZN",
  "backtest_window": "5Y",
  "max_positions": 1,
  "stop_loss": 5,
  "take_profit": 10
}
```

Response adds `extracted_strategy` (the JSON strategy derived from the paper, including
`paper_summary`) on top of the standard quant_agent response shape.

Also supported: `{"mode": "chat", "prompt": ...}` (history analysis) and
`{"prompt": ...}` pass-through without a PDF (used by the deploy smoke test).
