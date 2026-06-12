# Version Tracking Implementation

This document describes the version tracking feature added to the agentic backtesting system.

## Overview

All components (frontend + 3 backend agents) now expose version information for troubleshooting purposes.

## Version Sources

### Default (Auto-generated)
- Format: `YYYYMMdd_HHmmss` (e.g., `20260428_143022`)
- Generated at build/startup time
- Unique per deployment

### Override via Environment Variables

**Backend Agents:**
```bash
export AGENT_VERSION="v1.2.3-abc123"
```

**Frontend:**
```bash
export NEXT_PUBLIC_APP_VERSION="v1.2.3-abc123"
```

## Version Display

### In Application
- Versions appear at the bottom of the results page
- Format: `Frontend: X | Backend Agents: Quant: Y | Strategy: Z | Summary: W`
- Small gray text, non-intrusive

### In Logs
Each backend agent logs its version at startup:
```
🔧 Strategy Generator Configuration:
   Version: 20260428_143022
   Model ID: us.anthropic.claude-opus-4-7
   Region: us-east-1
```

## API Response Structure

The quant-agent now includes a `versions` object in its response:

```json
{
  "result": "...",
  "strategy_code": "...",
  "trades": [...],
  "trade_summary": {...},
  "backtest_metrics": {...},
  "versions": {
    "quant_agent": "20260428_143022",
    "strategy_generator": "20260428_143022",
    "results_summary": "20260428_143022"
  }
}
```

## CI/CD Integration

To set consistent versions across all components in CI/CD:

```yaml
# Example GitHub Actions
env:
  VERSION: ${{ github.sha }}

steps:
  - name: Build Backend
    env:
      AGENT_VERSION: ${{ env.VERSION }}
    run: |
      docker build --build-arg AGENT_VERSION=$VERSION ...

  - name: Build Frontend
    env:
      NEXT_PUBLIC_APP_VERSION: ${{ env.VERSION }}
    run: |
      npm run build
```

## Troubleshooting

### Version Not Showing
1. Check that env vars are set before starting the service
2. Check startup logs for version output
3. Verify frontend build included the version constant

### Version Mismatch
- Different versions between agents usually indicates incomplete deployment
- Check that all services were restarted after deployment
- Verify same Docker image tag or git commit was used for all agents

## Files Modified

See `history/001-add-version-tracking-for-troubleshooting.md` for detailed change log.

### Backend
- `backend-agents/strategy-generator-agent/strategy_generator.py`
- `backend-agents/result-summarizer-agent/results_summary.py`
- `backend-agents/quant-agent/quant_agent.py`

### Frontend
- `frontend/lib/version.ts` (new)
- `frontend/app/api/execute-backtest-async/route.ts`
- `frontend/app/results/page.tsx`
- `frontend/types/strategy.ts`
