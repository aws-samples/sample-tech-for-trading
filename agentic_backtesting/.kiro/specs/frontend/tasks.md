# Tasks: Frontend

## Task 1: Project Setup
- [x] Initialize Next.js 14 with TypeScript and App Router
- [x] Configure Tailwind CSS with custom glass-morphism theme
- [x] Set up global CSS with glass utility classes and animations
- [x] Add Framer Motion for UI animations
- [x] Configure standalone output in `next.config.js`

## Task 2: Strategy Builder Page (/)
- [x] Build strategy configuration form with fields: name, symbol, window, max positions, stop-loss, take-profit, buy/sell conditions
- [x] Implement real-time form validation with error messages
- [x] Add side panel for strategy preview and validation status
- [x] Create stock symbol selector with "Coming Soon" for unavailable symbols
- [x] Submit to `/api/execute-backtest-async` and navigate to workflow page

## Task 3: Workflow Visualization Page (/workflow)
- [x] Create interactive SVG architecture diagram
- [x] Implement click-to-learn modals for each architecture component
- [x] Add animated data flow visualization
- [x] Show component capabilities and AgentCore integration details
- [x] Navigation to results page with jobId

## Task 4: Results Page (/results)
- [x] Implement async polling (5s interval, 60 attempts, 5min timeout)
- [x] Display performance overview: initial investment, final value, total return, max drawdown
- [x] Show strategy details and Sharpe ratio
- [x] Render AI analysis: executive summary, detailed analysis
- [x] Display concerns & recommendations (high/medium priority, testing suggestions)
- [x] Add performance indicators with visual cues based on return %
- [x] Error handling with retry option

## Task 5: Reusable UI Components
- [x] `AnimatedButton` — variants (primary/secondary/accent), sizes, loading state
- [x] `GlassCard` — blur levels, glow options, click handler
- [x] `GlassInput` — error states, label/icon, forwardRef
- [x] `GlassSelect` — animated dropdown, descriptions, disabled options
- [x] `LoadingSpinner` — configurable size, overlay mode

## Task 6: State Management & API Layer
- [x] `BacktestContext` with React Context API (result + error state)
- [x] `AgentCoreAPI` singleton service class
- [x] `executeBacktest()` — POST + poll loop
- [x] `parseAgentResponse()` — JSON and regex fallback parsing
- [x] Mock mode support via `NEXT_PUBLIC_USE_MOCK_DATA`
- [x] Type definitions: `StrategyInput`, `AgentOutput`, `AgentCoreResponse`

## Task 7: API Routes
- [x] POST `/api/execute-backtest-async` — invoke AgentCore, return jobId
- [x] GET `/api/execute-backtest-async` — poll job status from in-memory Map
- [x] GET `/api/health` — health check for ALB target group

## Task 8: Deployment & Infrastructure
- [x] Multi-stage Dockerfile (Node.js 22-alpine, standalone output, non-root user)
- [x] ECS CloudFormation: VPC, ALB, Fargate, CloudFront
- [x] ALB security group restricted to CloudFront prefix list
- [x] ECS security group restricted to ALB only
- [x] Auto-scaling: CPU 70% + request count 1000/target (min 2, max 50)
- [x] Fix OS vulnerability: upgrade node:18-alpine → node:22-alpine + apk upgrade
