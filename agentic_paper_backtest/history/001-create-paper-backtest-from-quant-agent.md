# 001 - 创建 agentic_paper_backtest（论文 PDF 驱动的回测系统）

## 问题描述

需要一个新系统：用户上传交易研究论文 PDF，AI agent 解析论文、提取交易思路，然后按 agentic_backtesting 相同的步骤取行情数据并回测。用户可在前端指定目标股票、回测窗口并上传 PDF。后端部署 AgentCore（profile default），前端本地运行。

## 设计与实现

### 架构（复用优先）

```
frontend (Next.js, 本地) --pdf_base64--> paper_quant_agent (AgentCore Runtime, us-east-2)
    1. pypdf 提取 PDF 文本（截断 60k chars）
    2. PaperIdeaExtractor agent → JSON 策略配置（OHLCV 指标表达的买卖条件）
    3. 复用 4 步工作流：
       strategy_generator Runtime → 市场数据 MCP Gateway → Code Interpreter 回测 → results_summary Runtime
```

只新增一个 Runtime，其余（Strategy Generator、Results Summary、Market Data Gateway、Cognito）全部复用 agentic_backtesting 已部署资源。

### 关键决策

1. **PDF 解析放 agent 端而非前端**：AgentCore Runtime payload 上限 100MB，base64 PDF 直接入 payload；pypdf 做确定性文本抽取，LLM 只负责"文本→交易规则"
2. **用户参数强制覆盖**：`extract_trading_idea()` 在 LLM 输出后强制写入用户指定的 symbol/window/stop_loss 等，防止 LLM 从论文里带出别的标的
3. **复用 quant_agent 执行角色**：`AmazonBedrockAgentCoreSDKRuntime-us-east-2-a6f76213c2` 已含 InvokeAgentRuntime（两个下游 Runtime）+ Memory 权限，避免重新踩 agentic_backtesting history 004 的 Bug 3（AccessDenied）
4. **前端 job 结果剥离 pdf_base64**：避免轮询响应和日志携带整个 PDF

## 涉及的文件/代码位置

- `backend-agents/paper-quant-agent/paper_quant_agent.py` — 新入口 + PaperIdeaExtractor + `_run_quant_workflow()`
- `backend-agents/paper-quant-agent/tools/`、`config.py` — 从 quant-agent 原样复制
- `backend-agents/paper-quant-agent/deploy_to_agentcore.sh` — starter-toolkit CLI 部署
- `frontend/app/page.tsx` — PDF 上传表单
- `frontend/app/api/execute-backtest-async/route.ts` — paper 模式 payload、extracted_strategy 透传
- `frontend/app/results/page.tsx` — 展示提取出的买卖条件

## 部署过程中遇到的问题及修复

### 问题 1：PATH 上的 `agentcore` 不是 starter-toolkit
- **现象**：`error: unknown command 'configure'`
- **根因**：`/opt/homebrew/bin/agentcore` 是 Node/CDK 版 CLI（deploy 走 CDK 项目模型）；Python 版 starter-toolkit 未装在系统 PATH
- **修复**：脚本用 `AGENTCORE_BIN` 指向 workshop venv 的 CLI（bedrock-agentcore-starter-toolkit 0.3.5），命令由 `launch` 换成 `deploy`

### 问题 2：新 endpoint 数据面传播延迟
- **现象**：Runtime/endpoint 均 READY，但 invoke 报 `No endpoint or agent found with qualifier 'DEFAULT'`
- **根因**：新建 Runtime 后 DEFAULT endpoint 在数据面有数分钟传播延迟；且本机 shell 有 `AWS_REGION=us-east-1` 残留，dev server 继承后需依赖 .env.local 覆盖
- **修复**：等待数分钟后用 Node SDK 验证通过；重启 dev server 时显式 `AWS_REGION=us-east-2`

## 如何验证修复有效（全部通过）

1. 部署冒烟测试：EMA crossover AMZN 1Y → strategy_code ✓ / trades: 4 / win_rate 75% / versions 三组件齐
2. 端到端（用户论文《Research on Predicting Amazon Stock Price Based on Linear Regression and Decision Tree》，AMZN 1Y）：
   - PDF 7 页 17k chars 解析成功
   - 提取策略：Decision Tree 思路 → HL_PCT/PCT_change/Volume 的 OHLCV 代理（paper_summary 注明了近似）
   - 生成 Backtrader 代码（2642 chars）、取数、回测、汇总全链路完成
   - 该策略条件严格（4 条件同日同时满足才买入），1Y 窗口 0 笔交易——策略行为，非管道缺陷
3. `npm run build` 通过（lint + typecheck）

## 后续可改进点

- 提取的策略过于严格时（0 trades），可让 extractor 输出宽松/严格两档条件或加"至少产生 N 笔交易"的软约束重试
- 扫描版 PDF 支持（OCR / Bedrock 多模态直读 PDF）
- job 状态仍在 Next.js 内存（本地单进程无碍；上云需 DynamoDB）
