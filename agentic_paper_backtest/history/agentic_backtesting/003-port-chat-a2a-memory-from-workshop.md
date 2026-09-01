# 003 - 从 workshop 仓库移植 Chat / A2A / Memory 功能

## 问题描述

sample 版（本仓库）与 workshop 版（agentic-backtesting-for-quants）同源，但 workshop 版在 agent 功能上是超集。sample 版缺少：

1. **Chat 模式** — 通过对话分析历史回测结果的 Quant Research Assistant
2. **A2A 协议** — 基于 JSON-RPC 2.0 的 agent-to-agent 通信版 Strategy Generator
3. **Memory 集成** — Strategy Generator 跨会话学习（记住过去生成的策略）
4. **健壮的 Memory 解析** — history.py 不支持 AgentCore Memory 的 `conversational` payload 格式

## 根本原因

两个仓库从同一代码库分叉后各自演进：sample 版专注部署（版本追踪、ECS/CloudFront 部署管线），workshop 版专注教学（Lab 5 Chat Memory、Lab 8 A2A 等进阶功能）。功能未双向同步。

## 涉及的文件/代码位置

### 修改的文件

| 文件 | 改动 |
|---|---|
| `backend-agents/quant-agent/quant_agent.py` | 新增 `config._chat_agent`（Quant Research Assistant，挂载 get_backtest_history 工具）；`invoke()` 新增 `mode: "chat"` 分支 |
| `backend-agents/quant-agent/config.py` | 新增 `_chat_agent` 全局变量 |
| `backend-agents/quant-agent/tools/history.py` | 采用 workshop 版解析逻辑：支持 `payload`/`conversational` 包装的 Memory 事件格式 |
| `backend-agents/quant-agent/tools/__init__.py` | 新增 A2A 版 strategy generator 的切换注释 |
| `backend-agents/quant-agent/requirements.txt` | 新增 `requests>=2.28.0`（A2A tool 依赖） |
| `backend-agents/quant-agent/.env.example` | 新增 `STRATEGY_GENERATOR_A2A_ARN`（注释状态） |
| `backend-agents/strategy-generator-agent/strategy_generator.py` | 新增 `save_to_memory()` / `get_past_strategies()`；`process()` 注入过去策略作为 context 并保存生成结果；`_ensure_initialized()` 初始化 MemoryClient |
| `backend-agents/strategy-generator-agent/.env.sample` | 新增 `STRATEGY_GENERATOR_MEMORY_ID`（注释状态） |
| `frontend/app/page.tsx` | Header 下新增 chat 入口链接 |

### 新增的文件

- `backend-agents/strategy-generator-a2a-agent/`（strategy_generator_a2a.py、Dockerfile、requirements.txt — 从 workshop 整目录复制）
- `backend-agents/quant-agent/tools/strategy_generator_a2a.py`（SigV4 签名的 A2A 调用 tool）
- `frontend/app/chat/page.tsx`（聊天界面）
- `frontend/app/api/chat/route.ts`（chat API，以 `mode: 'chat'` 调用 AgentCore Runtime）

## 修改前有什么问题

- 用户无法对历史回测做对话式分析，只能跑新回测
- Strategy Generator 每次从零生成，不能借鉴过去成功/失败的策略模式
- history.py 在 Memory 返回 `conversational` 格式时解析不到内容，导致历史记录为空

## 具体做了哪些修改 & 为什么这样修改

- **合并而非覆盖**：sample 版的 VERSION 追踪（`config.VERSION`、返回值中的 `versions` 字段、strategy generator 的 `{"code", "version"}` 返回格式）全部保留，只把 workshop 的新功能合进来
- **Memory 可选降级**：未设置 `STRATEGY_GENERATOR_MEMORY_ID` 时打印警告并禁用 memory（save/get 函数内部 try/except 兜底），不影响主流程
- **A2A 默认不启用**：`tools/__init__.py` 中以注释提供切换开关，需要部署 A2A agent 并设置 ARN 后手动启用，避免破坏现有部署
- **strategy generator 的 invoke() 兼容 `{"prompt": ...}` 包装**：与 workshop 对齐，兼容 invoke_agent_runtime 的两种 payload 形态

## 如何验证修复有效

1. **语法检查**：`python3 -m py_compile` 所有修改的 Python 文件 — 通过
2. **前端类型检查**：`npx tsc --noEmit` — exit 0
3. **功能验证（需部署后）**：
   - 跑一次回测，然后访问 `/chat` 问 "Show me all my backtest results"，应返回历史记录分析
   - 设置 `STRATEGY_GENERATOR_MEMORY_ID` 后连续生成两次同 symbol 策略，第二次日志应出现 "Previously generated strategies for reference"
   - （可选）部署 strategy-generator-a2a-agent，设置 `STRATEGY_GENERATOR_A2A_ARN`，取消 `tools/__init__.py` 注释后跑回测

## 后续可改进点

- chat 模式目前每次请求新建 sessionId，多轮对话没有服务端上下文（依赖前端消息历史）；可改为复用 sessionId 实现真正的多轮记忆
- Strategy Generator Memory 的 session_id 含时分秒，跨会话检索实际依赖同一 memory_id 下的 list_events 行为，可考虑用固定 actor 维度检索策略
- A2A 版与标准版 strategy generator 二选一是 import 级切换，可改为运行时按环境变量选择
