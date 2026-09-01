# Refactor: Monolithic to Modular Multi-Agent Architecture

**Date**: 2026-05-05
**Type**: Architectural Refactoring
**Severity**: Major Enhancement

## Problem Description

The original `quant_agent.py` was a monolithic file (~1100 lines) containing:
- Environment configuration logic
- AWS client initialization
- AgentCore Memory management
- Market data fetching (Cognito auth + Gateway integration)
- Strategy generation (AgentCore Runtime invocation)
- Backtest execution
- Results summary generation
- History retrieval

This created several issues:
- Difficult to test individual components
- Hard to maintain and debug
- No clear separation of concerns
- Difficult to version individual tools
- Importing the module loaded everything (no lazy loading benefit for tools)

## Root Cause

Lack of modularization - all functionality was embedded in a single file, making it harder to:
- Understand the codebase
- Reuse components
- Track which version of each tool agent was used
- Isolate issues during debugging

## Files Modified

### New Files Created

1. **config.py**
   - Extracted all environment setup, AWS client initialization, and memory management
   - Centralized VERSION tracking
   - Provides `initialize_clients()` for lazy initialization
   - Contains all global state variables

2. **tools/market_data.py**
   - Market data fetching via AgentCore Gateway
   - Cognito authentication
   - Data extraction and transformation for Backtrader compatibility
   - Copied verbatim from workshop reference

3. **tools/strategy_generator.py**
   - Strategy generation via AgentCore Runtime
   - Version extraction from strategy_generator response
   - Based on workshop reference with version tracking enhancement

4. **tools/results_summary.py**
   - Results analysis via AgentCore Runtime
   - Version extraction from results_summary response
   - Based on workshop reference with version tracking enhancement

5. **tools/backtest_tool.py**
   - Backtest execution using local exec() and BacktestTool
   - Copied verbatim from workshop reference

6. **tools/backtest_tool_sandbox.py**
   - Sandboxed backtest execution via AgentCore Code Interpreter
   - Uploads backtrader package, market data CSV, and runner script
   - More secure than local exec()
   - Copied verbatim from workshop reference

7. **tools/history.py**
   - Historical backtest retrieval from AgentCore Memory
   - Copied verbatim from workshop reference

### Files Modified

1. **quant_agent.py** (REPLACED)
   - Reduced from ~1100 lines to ~170 lines
   - Now only contains:
     - Import statements for config and tools
     - `_ensure_initialized()` function for lazy loading
     - `invoke()` entrypoint function
     - Main server startup code
   - Uses `config.py` for all state management
   - Imports tools from `tools/` package

2. **tools/__init__.py** (UPDATED)
   - Now exports all 6 tool functions:
     - `BacktestTool` (class)
     - `generate_trading_strategy`
     - `fetch_market_data_via_gateway`
     - `run_backtest` (from backtest_tool_sandbox for production)
     - `create_results_summary`
     - `get_backtest_history`

3. **tools/backtest.py** (UPDATED)
   - Replaced with workshop reference version
   - Contains `BacktestTool` class and `TradeRecorder` analyzer
   - Used by both backtest_tool.py and backtest_tool_sandbox.py

## Modifications Made

### Architecture Changes

**Before**: Monolithic single file
```
quant_agent.py (1100+ lines)
├── Config/environment loading
├── AWS client initialization
├── Memory management
├── Market data tool
├── Strategy generator tool
├── Backtest tool
├── Results summary tool
├── History tool
└── Main entrypoint
```

**After**: Modular multi-file structure
```
quant_agent.py (170 lines) - orchestration only
config.py (200 lines) - configuration & state
tools/
├── __init__.py - exports
├── backtest.py - BacktestTool class
├── market_data.py - Gateway integration
├── strategy_generator.py - Strategy agent
├── backtest_tool.py - Local exec version
├── backtest_tool_sandbox.py - Sandbox version (production)
├── results_summary.py - Results agent
└── history.py - Memory retrieval
```

### Key Design Decisions

1. **Config as Separate Module**: All initialization and state management moved to `config.py`
   - Rationale: Enables tools to access shared state (memory clients, stored data) without circular imports
   - Pattern: `import config` then access `config._stored_market_data`, `config._memory_client`, etc.

2. **Sandbox Version for Production**: `tools/__init__.py` imports `run_backtest` from `backtest_tool_sandbox` not `backtest_tool`
   - Rationale: Sandboxed execution is more secure (no local exec() of strategy code)
   - Trade-off: Slightly slower due to file uploads, but worth it for security

3. **Version Tracking Preserved**: Frontend expects `versions` object with 3 version strings
   - `quant_agent`: From config.VERSION (environment or timestamp)
   - `strategy_generator`: Extracted from strategy_generator agent response
   - `results_summary`: Extracted from results_summary agent response

4. **Lazy Initialization Pattern**: Heavy imports (boto3, BedrockModel, Agent) deferred until first invoke()
   - Rationale: Faster container startup time for AgentCore Runtime
   - Implementation: `_ensure_initialized()` called at start of `invoke()`

5. **Global State Management**: Market data and backtest results stored in config module globals
   - `config._stored_market_data`: Set by fetch_market_data_via_gateway
   - `config._last_backtest_result`: Set by run_backtest, read by invoke()
   - Rationale: Tools need to share state without passing data through AgentCore Memory (which may be stale)

## Why This Approach

1. **Separation of Concerns**: Each tool is in its own file, making it easier to:
   - Test individual tools
   - Debug specific functionality
   - Track changes via git history

2. **Version Tracking**: Can now track which version of each tool agent was used for a backtest
   - Important for troubleshooting production issues
   - Enables A/B testing of tool agent versions

3. **Code Reusability**: `BacktestTool` class is used by both backtest_tool.py and backtest_tool_sandbox.py
   - Maximizes code reuse
   - Single source of truth for backtest logic

4. **Security**: Sandbox version isolates strategy code execution
   - Prevents malicious code from accessing agent runtime environment
   - Required for production deployment per AWS best practices

5. **Maintainability**: Smaller files are easier to understand and modify
   - ~200 line files vs 1100 line monolith
   - Clear boundaries between modules

## Verification Method

### Manual Testing
1. Start the agent runtime locally: `python quant_agent.py`
2. Send test payload via AgentCore Gateway or local HTTP client
3. Verify all 4 steps execute (strategy gen -> market data -> backtest -> results)
4. Confirm response includes:
   - `strategy_code` (not empty)
   - `trades` array (not empty if strategy generated trades)
   - `trade_summary` object
   - `backtest_metrics` object
   - `versions` object with 3 version strings

### Automated Testing (Recommended)
```bash
# Unit tests for individual tools
pytest tools/test_market_data.py
pytest tools/test_strategy_generator.py
pytest tools/test_backtest.py

# Integration test for full workflow
pytest test_quant_agent_integration.py
```

### Regression Testing
- Compare output structure before/after refactoring
- Ensure frontend still receives expected response format
- Verify version tracking works (check CloudWatch logs for version output)

## Risks and Mitigations

### Risk 1: Import Errors
- **Risk**: Circular imports or missing imports due to refactoring
- **Mitigation**: All tools import `config` (not vice versa), avoiding circular dependencies
- **Validation**: Run `python quant_agent.py` and check for import errors

### Risk 2: Global State Issues
- **Risk**: Multiple concurrent requests might interfere with each other's global state
- **Mitigation**: Each invoke() resets `_generated_strategy_code` and `_last_backtest_result` before execution
- **Validation**: Load test with concurrent requests, verify responses don't mix data

### Risk 3: Version Extraction Failures
- **Risk**: Strategy_generator or results_summary might not return version in expected format
- **Mitigation**: Fallback to "unknown" if version not found in response
- **Validation**: Check CloudWatch logs for version extraction warnings

### Risk 4: Sandbox Performance
- **Risk**: Sandbox execution slower than local exec()
- **Mitigation**: Acceptable trade-off for security; can optimize by caching backtrader zip
- **Validation**: Measure P99 latency before/after refactoring

## Backward Compatibility

✅ **Fully Compatible**: Response structure unchanged
- `result` (message from agent)
- `strategy_code` (string)
- `trades` (array)
- `trade_summary` (object)
- `backtest_metrics` (object)
- `versions` (object with 3 keys)

Frontend requires NO changes.

## Future Improvements

1. **Add Unit Tests**: Each tool should have pytest tests
   - Mock AgentCore Runtime responses
   - Test error handling paths
   - Verify version extraction logic

2. **Cache Backtrader Zip**: Sandbox version zips backtrader on every request
   - Could cache the zip file in /tmp or S3
   - Would reduce sandbox execution time by ~500ms

3. **Structured Logging**: Replace print() statements with proper logging
   - Use CloudWatch structured logging
   - Add correlation IDs for request tracing

4. **Configuration Validation**: Validate environment variables at startup
   - Fail fast if required variables missing
   - Provide helpful error messages

5. **Tool Versioning**: Add explicit version numbers to each tool
   - Could be git commit hash or semantic version
   - Include in response for better troubleshooting

6. **Metrics and Monitoring**: Add CloudWatch metrics for:
   - Tool execution times
   - Error rates per tool
   - Strategy generation success rate
   - Backtest completion rate

## Related Documentation

- Workshop Reference: `/Users/awsjacky/projectlocal/workshop-agentic-backtesting-project/agentic-backtesting-for-quants/workshop/backend-agents/references/quant-agent/`
- AgentCore Gateway Docs: [link to internal docs]
- Bedrock AgentCore Memory API: [link to AWS docs]
- Code Interpreter Sandbox: [link to internal docs]

## Rollback Plan

If issues found in production:
1. Revert to previous monolithic `quant_agent.py` (backed up as `quant_agent.py.bak`)
2. Remove new files: `config.py`, `tools/*.py` (except backtest.py which existed before)
3. Restore original `tools/__init__.py` (only exported BacktestTool)
4. Redeploy agent runtime

Rollback time estimate: 10 minutes
