# Strategy Generator A2A Agent

A2A（Agent-to-Agent，JSON-RPC 2.0）协议版的 Strategy Generator，从 workshop 仓库移植。

## 用途

与 `strategy-generator-agent/` 功能相同（JSON 策略配置 → Backtrader 代码），但通过开放的 A2A 标准协议对外服务：发布 Agent Card，处理 `message/send` 请求，由 `bedrock_agentcore.runtime.serve_a2a` 托管（本地端口 9000）。

## 与标准版的关系

- 默认**不启用**。quant-agent 默认走标准版（`invoke_agent_runtime` 调用）。
- 启用方式：
  1. 部署本 agent 到 AgentCore Runtime
  2. 在 quant-agent 的 `.env` 设置 `STRATEGY_GENERATOR_A2A_ARN`
  3. 取消 `quant-agent/tools/__init__.py` 中 A2A 切换注释

## 文件

- `strategy_generator_a2a.py` — agent 入口（serve_a2a）
- `Dockerfile` / `requirements.txt` — 容器化部署（需 `strands-agents[a2a]`、`bedrock_agentcore[a2a]`）

调用方实现见 `../quant-agent/tools/strategy_generator_a2a.py`（SigV4 签名的 HTTP POST）。
