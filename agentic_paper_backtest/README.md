# Agentic Paper Backtest - Multi-Agent Strategy Backtesting

Backtest trading strategies with a multi-agent system built on Strands and Amazon Bedrock
AgentCore. Two ways to provide a strategy:

- **Upload a trading research paper (PDF)** — AI agents extract the trading idea,
  generate executable strategy code, fetch historical market data, and backtest it
- **Type buy/sell conditions manually** — the same pipeline runs on your own idea

This project supersedes the former `agentic_backtesting` sample: the two codebases were
merged (one backend source, one frontend that supports both strategy sources).

## Inspiration

This solution is inspired by [a talk from Aaron Linsky, CTO of AIA Labs at Bridgewater
Associates](https://aws.amazon.com/ar/video/watch/5b319684c66/), about their journey
integrating generative AI and large language models into their investment processes.
Aaron discusses how Bridgewater is leveraging Amazon Bedrock to build an "Artificial
Investment Associate" that can analyze data, generate hypotheses, and improve itself
over time. He shares insights on their implementation approach, the benefits of using
multiple AI models, and advice for other organizations embarking on generative AI
initiatives.

This sample explores those ideas at a smaller scale: multiple specialized agents
(idea extraction, code generation, backtesting, analysis) collaborate on an investment
research workflow, with evaluation and optimization loops that let the system's quality
be measured and improved over time.

## Disclaimer

**This project is for educational and research purposes only.** The backtesting results,
trading strategies, and any analysis provided by this system do not constitute financial
advice. Past performance does not guarantee future results.

## How It Works

```
Frontend (PDF upload OR manual buy/sell conditions)
  └─> Quant Agent (AgentCore Runtime, orchestrator)
        0. [PDF mode only] pypdf extracts text; PaperIdeaExtractor agent converts the
           paper into a JSON strategy config (OHLCV-indicator buy/sell conditions)
        1. Strategy Generator Runtime  -> Backtrader code
        2. Market Data Gateway (MCP)   -> historical OHLCV from S3 Table
        3. Code Interpreter sandbox    -> backtest execution
        4. Results Summary Runtime     -> analysis report
```

The user chooses the **target stock** and **backtest window** (plus optional stop loss /
take profit / max positions) in the frontend; in PDF mode these override anything in
the paper. A chat assistant analyzes historical backtests across sessions (AgentCore
Memory with a semantic long-term strategy).

## Layout

- `backend-agents/` — all agents:
  - `quant-agent/` — the orchestrator, deployed as a single runtime
    (`paper_quant_agent`) handling both PDF and manual strategy input —
    see [its README](./backend-agents/quant-agent/README.md)
  - `strategy-generator-agent/` — converts strategy JSON to Backtrader code (Runtime)
  - `result-summarizer-agent/` — analyzes backtest results (Runtime)
  - `strategy-generator-a2a-agent/` — optional A2A variant
- `frontend/` — Next.js app: PDF upload or manual input, Cognito login, chat with
  markdown rendering, interactive architecture diagram
- `eval/` — AgentCore Evaluation assets: 3 custom evaluators + scripts + guidance
  ([eval/README.md](./eval/README.md))
- `docs/` — architecture and UI screenshots
- `DEPLOYMENT_GUIDE.md` — full infrastructure setup (Gateway, Cognito, S3 Tables, agents)

## Deployment

### Backend (AgentCore, AWS profile `default`)

```bash
cd backend-agents/quant-agent
# .env is pre-populated with the shared us-east-2 resources
./deploy_to_agentcore.sh    # deploys the paper_quant_agent runtime
```

The strategy-generator / result-summarizer runtimes each have their own
`deploy_to_agentcore.sh`; see `DEPLOYMENT_GUIDE.md` for the full stack
(Market Data Gateway, Cognito, S3 Tables).

### Frontend (local)

```bash
cd frontend
# set AGENTCORE_ARN in .env.local to the paper_quant_agent runtime ARN
npm install
npm run dev    # http://localhost:3000
```

### Frontend (AWS: ECS + ALB + CloudFront)

CloudFront is the only public entry point; the ALB only accepts traffic from the
CloudFront origin-facing prefix list and requires an `X-Origin-Verify` secret header,
and ECS tasks run in private subnets.

The site requires Cognito login (app-layer JWT auth): the Next.js middleware verifies
the Cognito access token from an httpOnly cookie and redirects unauthenticated visitors
to `/login`. Set `COGNITO_USER_POOL_ID` / `COGNITO_APP_CLIENT_ID` in `.env.local`
(users are admin-created only; the app client uses USER_PASSWORD_AUTH without a secret).

```bash
cd frontend
./deploy.sh            # full deploy: ECR + Docker build/push + CloudFormation stack
./frontend-deploy.sh   # code-only update (rebuild image, force new ECS deployment)
./infra-deploy.sh      # infrastructure-only update
```

Default stack: `agentcore-paper-backtest` (us-east-2), ECR: `agentcore-paper-backtest-ecr`.
To update a second deployment (e.g. the legacy stack), override
`STACK_NAME=... ECR_REPO_NAME=... ./frontend-deploy.sh`.

## Limitations

- Text-based PDFs only (scanned/image PDFs are not OCR'd)
- Papers relying on data beyond daily OHLCV (fundamentals, sentiment, options) are
  approximated with the closest price/volume proxy — the approximation is noted in the
  extracted strategy summary
- Market data currently available for AMZN only (S3 Table)
