# Design: Frontend

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Next.js 14 App Router                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Pages:                                                     │
│  ├── / (Home)         → Strategy builder form               │
│  ├── /workflow         → Architecture visualization + jobId │
│  └── /results          → Polling + results display          │
│                                                             │
│  API Routes:                                                │
│  ├── POST /api/execute-backtest-async → Start job           │
│  ├── GET  /api/execute-backtest-async → Poll status         │
│  └── GET  /api/health                → Health check         │
│                                                             │
│  State:                                                     │
│  └── BacktestContext (React Context API)                    │
│      └── result: AgentOutput | null                         │
│      └── error: string | null                               │
│                                                             │
│  Services:                                                  │
│  └── AgentCoreAPI (singleton)                               │
│      └── executeBacktest() → POST + poll loop               │
│      └── parseAgentResponse() → JSON/regex parser           │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼ InvokeAgentRuntimeCommand
         AWS Bedrock AgentCore
         (Quant Agent Runtime)
```

## Component Structure

### Pages
| File | Purpose |
|------|---------|
| `app/page.tsx` | Strategy form with real-time validation, side panel preview |
| `app/workflow/page.tsx` | Interactive SVG architecture diagram, click-to-learn modals |
| `app/results/page.tsx` | Async polling (5s interval, 5min timeout), metrics + AI analysis display |
| `app/layout.tsx` | Root layout wrapping app with `BacktestProvider` |

### UI Components (`components/ui/`)
| Component | Purpose |
|-----------|---------|
| `AnimatedButton` | Primary/secondary/accent variants, loading state, Framer Motion |
| `GlassCard` | Reusable glass-morphism card with blur levels and glow options |
| `GlassInput` | Text input with glass styling, error state (red glow), label/icon |
| `GlassSelect` | Animated dropdown with descriptions, "Coming Soon" disabled options |
| `LoadingSpinner` | Configurable spinner with optional overlay mode |

### State Management
- **BacktestContext** (`lib/BacktestContext.tsx`): React Context wrapping entire app via `BacktestProvider`
- **AgentCoreAPI** (`lib/agentcore-api.ts`): Singleton service class for API calls + response parsing
- **In-memory Map** (API route): Server-side job result storage with global persistence

### Type Definitions (`types/strategy.ts`)
- `StrategyInput`: name, stock_symbol, backtest_window, max_positions, stop_loss, take_profit, buy/sell conditions
- `AgentOutput`: metrics (return, drawdown, Sharpe), analysis (executive_summary, detailed_analysis, recommendations)
- `AgentCoreResponse`: success, analysis, raw_response, session_id, error

## Styling
- **Tailwind CSS 3.3.0** with custom theme in `tailwind.config.ts`
- Glass-morphism: `.glass-card`, `.glass-button`, `.glass-input` utilities
- Dark theme palette: dark-primary/secondary/tertiary, accent-blue/purple/green
- Custom blur (glass: 10px, heavy: 20px) and shadow (glow-blue, glow-purple)
- Framer Motion 10.18.0 for animations

## Infrastructure
- **Dockerfile**: Multi-stage (base → deps → builder → runner), Node.js 22-alpine, standalone output, non-root user (UID 1001), port 3000
- **ECS CloudFormation** (`ecs-cloudformation.yaml`):
  - VPC: 2 public + 2 private subnets, NAT Gateway
  - ALB: public subnets, inbound restricted to CloudFront prefix list (`pl-3b927c52`)
  - ECS Fargate: private subnets, inbound from ALB SG only on port 3000
  - Auto-scaling: min 2 / max 50, CPU 70% + request count 1000/target
  - CloudFront: HTTPS redirect, all methods forwarded, TTL 0 (no caching)

## Key Dependencies
- next: 14.2.0, react: 18.2.0, typescript: 5
- @aws-sdk/client-bedrock-agentcore: 3.700.0
- framer-motion: 10.18.0
- tailwindcss: 3.3.0
- chart.js: 3.9.1 + react-chartjs-2: 4.3.1
- uuid: 9.0.1, clsx: 2.0.0
