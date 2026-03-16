# Requirements: Frontend

## Overview
Next.js 14 web application with glass-morphism UI for configuring trading strategies, visualizing the multi-agent architecture, and displaying AI-powered backtest results.

## Functional Requirements

### REQ-1: Strategy Configuration
- **Given** a user visits the home page
- **When** they fill in the strategy form (name, stock symbol, backtest window, max positions, stop-loss %, take-profit %, buy/sell conditions)
- **Then** the form validates in real-time with error messages
- **Then** a side panel shows strategy preview and validation status
- **Then** on submit, it POSTs to `/api/execute-backtest-async` and navigates to workflow page with jobId

### REQ-2: Architecture Visualization
- **Given** a user is on the workflow page
- **When** the page loads
- **Then** an interactive SVG diagram displays the multi-agent architecture (Client, Orchestrator, Market Data Tool, Strategy Generator, Backtest Tool, Results Summary, Memory Storage)
- **Then** clicking a component shows a modal with its capabilities and AgentCore integration details
- **Then** animated data flow visualization runs during interaction

### REQ-3: Results Display
- **Given** a backtest job has been submitted
- **When** the user navigates to the results page
- **Then** the page polls `/api/execute-backtest-async?jobId={id}` every 5 seconds (max 60 attempts / 5 min timeout)
- **Then** on completion, it displays: performance overview (initial investment, final value, total return, max drawdown), strategy details, Sharpe ratio
- **Then** AI agent analysis is shown: executive summary, detailed analysis, concerns & recommendations (high/medium priority)

### REQ-4: Async Backtest API
- **Given** the frontend API route receives a strategy configuration
- **When** POST `/api/execute-backtest-async` is called
- **Then** it invokes the Quant Agent via `BedrockAgentCoreClient` + `InvokeAgentRuntimeCommand`
- **Then** it returns a jobId immediately for async polling
- **Then** results are stored in an in-memory Map with global persistence

### REQ-5: Health Check
- **Given** the ECS load balancer needs to verify service health
- **When** GET `/api/health` is called
- **Then** it returns `{ status: 'healthy' }`

## Non-Functional Requirements

### REQ-6: UI/UX
- Glass-morphism design with dark theme and accent colors (blue #00d4ff, purple, green)
- Framer Motion animations (hover, tap, slide-up, fade-in, float, pulse-glow)
- Responsive layouts using Tailwind CSS grid
- Custom scrollbar styling

### REQ-7: Deployment
- Multi-stage Docker build (base → deps → builder → runner) on Node.js 22-alpine
- ECS Fargate with ALB + CloudFront CDN
- ALB restricted to CloudFront prefix list only (no direct public access)
- ECS in private subnets, ALB in public subnets
- Auto-scaling: 2-50 tasks, CPU target 70%, request count target 1000/target

### REQ-8: Stock Symbol Support
- Available symbols: AAPL, MSFT, GOOGL, TSLA, AMZN, NVDA, META, NFLX
- Currently only AMZN has data available in S3 Tables

### REQ-9: Mock Mode
- Support `NEXT_PUBLIC_USE_MOCK_DATA` env var for development without backend
