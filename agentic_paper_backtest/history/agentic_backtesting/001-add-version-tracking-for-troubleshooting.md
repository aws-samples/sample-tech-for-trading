# Add Version Tracking for Troubleshooting

**Date**: 2026-04-28
**Type**: Feature Enhancement

## Problem Description

When troubleshooting issues in production, it was difficult to determine which version of each backend agent and frontend was deployed. This made it hard to:
- Correlate issues with specific deployments
- Verify that all components were updated after a fix
- Debug version mismatch issues between frontend and backend agents

## Root Cause

No version tracking mechanism existed in the system. Each component (frontend, quant-agent, strategy-generator-agent, results-summarizer-agent) operated independently without exposing version information.

## Files Modified

### Backend Agents

1. **`/Users/awsjacky/projectlocal/sample-tech-for-trading/agentic_backtesting/backend-agents/strategy-generator-agent/strategy_generator.py`**
   - Added `VERSION` variable using `AGENT_VERSION` env var or timestamp default
   - Modified `invoke()` to return `{"code": "...", "version": "..."}` instead of plain string
   - Added version logging at startup

2. **`/Users/awsjacky/projectlocal/sample-tech-for-trading/agentic_backtesting/backend-agents/result-summarizer-agent/results_summary.py`**
   - Added `VERSION` variable using `AGENT_VERSION` env var or timestamp default
   - Modified `invoke()` to include version in response (attempts JSON augmentation, falls back to dict wrapper)
   - Added version logging at startup

3. **`/Users/awsjacky/projectlocal/sample-tech-for-trading/agentic_backtesting/backend-agents/quant-agent/quant_agent.py`**
   - Added `VERSION` variable using `AGENT_VERSION` env var or timestamp default
   - Added global variables `_strategy_generator_version` and `_results_summary_version` to track sub-agent versions
   - Modified strategy_generator response parsing to extract version from new dict format
   - Modified results_summary response parsing to extract version from wrapped response
   - Modified `invoke()` return to include `versions` object with all 3 agent versions
   - Added version logging at startup

### Frontend

4. **`/Users/awsjacky/projectlocal/sample-tech-for-trading/agentic_backtesting/frontend/lib/version.ts`** (NEW)
   - Created new file with `FRONTEND_VERSION` constant
   - Uses `NEXT_PUBLIC_APP_VERSION` env var or timestamp default

5. **`/Users/awsjacky/projectlocal/sample-tech-for-trading/agentic_backtesting/frontend/app/api/execute-backtest-async/route.ts`**
   - Extract `versions` from agent response
   - Include `versions` in the complete result object passed to frontend

6. **`/Users/awsjacky/projectlocal/sample-tech-for-trading/agentic_backtesting/frontend/app/results/page.tsx`**
   - Import `FRONTEND_VERSION` constant
   - Extract `versions` from poll result
   - Display all versions (frontend + 3 backend agents) subtly at bottom of results page

7. **`/Users/awsjacky/projectlocal/sample-tech-for-trading/agentic_backtesting/frontend/types/strategy.ts`**
   - Added optional `versions` field to `AgentOutput` interface

## Specific Changes

### Version Format
- Default: `YYYYMMdd_HHmmss` timestamp (e.g., `20260428_143022`)
- Override: Set `AGENT_VERSION` env var for backend agents, `NEXT_PUBLIC_APP_VERSION` for frontend

### Backend Response Format Changes
- **strategy-generator**: Changed from returning string to `{"code": string, "version": string}`
- **results-summary**: Wraps response with version (tries JSON augmentation, falls back to dict)
- **quant-agent**: Now returns `versions: {quant_agent, strategy_generator, results_summary}`

### Frontend Display
- Versions shown at bottom of results page in small gray text
- Format: `Frontend: X | Backend Agents: Quant: Y | Strategy: Z | Summary: W`
- Non-intrusive, primarily for troubleshooting/debugging

## Rationale

1. **Timestamp default**: Ensures each build has a unique version without manual intervention
2. **Environment variable override**: Allows CI/CD to set consistent versions across all components (e.g., git commit SHA or release tag)
3. **All agents included**: Since strategy-generator and results-summary are called by quant-agent, collecting all versions provides complete troubleshooting info
4. **Response format change**: strategy-generator now returns dict to include version; quant-agent already handled dict responses correctly
5. **Subtle UI placement**: Versions at bottom don't distract from main results but are easily accessible when needed

## Verification Method

### 1. Check Backend Startup Logs
```bash
# Each agent should log version at startup
docker logs <container-id> | grep "Version:"
```

Expected output:
```
🔧 Strategy Generator Configuration:
   Version: 20260428_143022
...
```

### 2. Check Frontend Results Page
1. Run a backtest
2. View results page
3. Scroll to bottom
4. Verify version info displays: `Frontend: X | Backend Agents: Quant: Y | Strategy: Z | Summary: W`

### 3. Test Environment Variable Override
```bash
# Set env var before starting
export AGENT_VERSION="v1.2.3-abc123"
# Start agent
# Check logs and results page
```

### 4. API Response Check
```bash
# Check API response includes versions
curl -X POST <api-url>/execute-backtest-async?jobId=<job-id>
# Response should include: "versions": {"quant_agent": "...", "strategy_generator": "...", "results_summary": "..."}
```

## Future Improvements

1. **Centralized Version Management**
   - Store version in a shared config file or build-time generated file
   - Inject same version into all components during CI/CD

2. **Version Mismatch Warnings**
   - Frontend could warn if backend agent versions are significantly different from each other
   - Could help catch incomplete deployments

3. **Version API Endpoint**
   - Add `/api/version` endpoint to frontend to check versions without running a backtest
   - Useful for health checks and monitoring

4. **Persistent Version Logging**
   - Log versions with each backtest result in AgentCore Memory
   - Enables historical analysis of which version produced which results

5. **Git Integration**
   - CI/CD pipeline could automatically set `AGENT_VERSION` to git commit SHA
   - Provides direct link to source code for each deployed version

## Notes

- This change is backward compatible - if versions are not present, UI gracefully handles it
- Default timestamp version is in `YYYYMMdd_HHmmss` format to be sortable and readable
- Version tracking adds minimal overhead (one env var read per agent initialization)
