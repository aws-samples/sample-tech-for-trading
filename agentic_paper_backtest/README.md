# Agentic Paper Backtest - Research Paper to Backtested Strategy

Upload a trading research paper (PDF) and let AI agents extract the trading idea,
generate executable strategy code, fetch historical market data, and backtest it.

A sibling project of [`agentic_backtesting`](../agentic_backtesting/): that project takes a
trading idea typed by the user; this one derives the idea from an uploaded research paper,
then reuses the exact same downstream pipeline.

## Disclaimer

**This project is for educational and research purposes only.** The backtesting results,
trading strategies, and any analysis provided by this system do not constitute financial
advice. Past performance does not guarantee future results.

## How It Works

```
PDF upload (frontend)
  └─> Paper Quant Agent (AgentCore Runtime)
        1. pypdf extracts text from the PDF
        2. PaperIdeaExtractor agent converts the paper into a JSON strategy config
           (buy/sell conditions expressed with OHLCV indicators)
        3. Standard 4-step quant workflow (same as agentic_backtesting):
           a. Strategy Generator Runtime  -> Backtrader code
           b. Market Data Gateway (MCP)   -> historical OHLCV from S3 Table
           c. Code Interpreter sandbox    -> backtest execution
           d. Results Summary Runtime     -> analysis report
```

The user chooses the **target stock** and **backtest window** (plus optional stop loss /
take profit / max positions) in the frontend; these override anything in the paper.

## Reused Infrastructure

This project deploys **one new AgentCore Runtime** (`paper_quant_agent`, us-east-2) and
reuses the resources already deployed by `agentic_backtesting`:

- Strategy Generator Runtime (`STRATEGY_GENERATOR_RUNTIME_ARN`)
- Results Summary Runtime (`BACKTEST_SUMMARY_RUNTIME_ARN`)
- Market Data MCP Gateway + Cognito auth (`AGENTCORE_GATEWAY_URL`)
- AgentCore Memory (`quant_agent` prefix)

## Layout

- `backend-agents/paper-quant-agent/` — the orchestrator agent (deployed to AgentCore Runtime)
- `frontend/` — Next.js app with PDF upload (runs locally with `npm run dev`)

## Deployment

### Backend (AgentCore, AWS profile `default`)

```bash
cd backend-agents/paper-quant-agent
# .env is pre-populated with the shared us-east-2 resources
./deploy_to_agentcore.sh
```

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

Stack: `agentcore-paper-backtest` (us-east-2), ECR: `agentcore-paper-backtest-ecr`.

## Limitations

- Text-based PDFs only (scanned/image PDFs are not OCR'd)
- Papers relying on data beyond daily OHLCV (fundamentals, sentiment, options) are
  approximated with the closest price/volume proxy — the approximation is noted in the
  extracted strategy summary
- Market data currently available for AMZN only (same S3 Table as agentic_backtesting)
