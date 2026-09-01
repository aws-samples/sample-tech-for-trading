# Backend Agents (merged into agentic_backtesting)

The orchestrator source code for this project lives in
[`../../agentic_backtesting/backend-agents/quant-agent/`](../../agentic_backtesting/backend-agents/quant-agent/).

That single codebase supports both strategy sources — a plain buy/sell-condition
prompt and a research-paper PDF (pypdf extraction + PaperIdeaExtractor agent) —
and is deployed as **two separate AgentCore Runtimes**:

| Runtime | Used by | Deploy command (from quant-agent/) |
|---|---|---|
| `quant_agent` | agentic_backtesting frontend | `./deploy_to_agentcore.sh` |
| `paper_quant_agent` | this project's frontend | `AGENT_NAME=paper_quant_agent ./deploy_to_agentcore.sh` |

Payload contract for paper mode (unchanged):

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

Without `pdf_base64`, the same entrypoint handles plain strategy prompts and
`{"mode": "chat"}` history analysis.
