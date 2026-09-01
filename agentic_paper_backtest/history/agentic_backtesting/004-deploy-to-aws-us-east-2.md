# 004 - 全栈部署到 us-east-2（AgentCore 后端 + ECS/CloudFront 前端）

## 问题描述

将整个 agentic_backtesting 项目部署到账号 383386985941（profile `default`）的 us-east-2 区域：3 个 agent 上 AgentCore Runtime，市场数据走 Lambda MCP + Gateway + S3 Tables，前端容器跑在 ECS Fargate、ALB 仅允许 CloudFront 访问。

## 部署的资源（us-east-2）

| 资源 | 标识 |
|---|---|
| **CloudFront URL（唯一公网入口）** | https://d10lub5i8fbja9.cloudfront.net |
| quant_agent Runtime | `arn:aws:bedrock-agentcore:us-east-2:383386985941:runtime/quant_agent-BFk0PyAZ7p` |
| strategy_generator Runtime | `arn:aws:bedrock-agentcore:us-east-2:383386985941:runtime/strategy_generator-E0wblRCGBC` |
| results_summary Runtime | `arn:aws:bedrock-agentcore:us-east-2:383386985941:runtime/results_summary-BOjq9i6hfJ` |
| AgentCore Memory | `quant_agent_mem-7P6JhaEFG1`（另有 strategy_generator_mem / results_summary_mem） |
| MCP Gateway | `market-data-mcp-gateway-h9bsn1erm9`（Cognito client_credentials 认证） |
| Cognito | User Pool `us-east-2_RWzbQugPp`，domain `agentcore-e9b857a4` |
| Lambda | `market-data-mcp`（容器镜像，PyIceberg 查 S3 Tables） |
| S3 Tables | bucket `market-data-1781195703`，`daily_data.daily_data`，6394 行 AMZN 日线 |
| ECS | stack `agentcore-backtest-v2`，Fargate 2 任务，私有子网 + NAT |
| ALB | `agentc-LoadB-Z3JfCNVr3JMS-1503677219.us-east-2.elb.amazonaws.com`（外部直连被封） |
| ECR | `agentcore-backtest-ecr`（前端）、`market-data-mcp`（Lambda） |
| SSM | `/agentcore-backtest/origin-verify-secret`（SecureString，CloudFront↔ALB 共享密钥） |

## 部署过程中遇到的 Bug 及修复

### Bug 1：`deploy_to_agentcore.sh` 语法错误（strategy-generator）
- **现象**：`Deploy: command not found`，exit 127
- **根因**：第 14 行注释少了 `#`（`Deploy Strategy Generator Agent` 被当成命令）
- **修复**：补上 `#`

### Bug 2：`agentcore configure` 在非交互环境挂死
- **现象**：`OSError: [Errno 22] Invalid argument`（CLI 弹出 deployment type 选择菜单读不到 stdin）
- **根因**：strategy-generator 的脚本缺 `--non-interactive`（quant/result-summarizer 的脚本有）
- **修复**：加 `--idle-timeout 900 --non-interactive`，与其他两个脚本对齐

### Bug 3：quant-agent 调下游 agent 全部 AccessDenied
- **现象**：CloudWatch 日志 `not authorized to perform: bedrock-agentcore:InvokeAgentRuntime / ListMemories`；表现为 `strategy_code: null`、`results_summary version: unknown`，但回测仍"成功"（LLM 自己写了策略代码 fallback，掩盖了根因）
- **根因**：starter-toolkit 自动建的执行角色只含基础权限，不含调用其他 Runtime 和 ListMemories
- **修复**：往 `AmazonBedrockAgentCoreSDKRuntime-us-east-2-a6f76213c2` 加 inline policy `QuantAgentDownstreamAccess`，资源限定到两个具体 Runtime ARN + `memory/quant_agent_mem-*`（最小权限，无通配 `*` 资源）

### Bug 4：回测结果没存 Memory，chat 模式查不到历史
- **现象**：chat 模式回 "no backtest history"；日志无 "Saving backtest results"
- **根因**：`tools/__init__.py` 用的是 `backtest_tool_sandbox.py`（Code Interpreter 版），它只设置 `config._last_backtest_result`，没调 `config.save_backtest_results_to_memory_sync()`——该调用只存在于本地版 `backtest_tool.py`
- **修复**：sandbox 版在结果解析成功后补调 `save_backtest_results_to_memory_sync(result, strategy_code=strategy_code)`，重新部署后验证：保存日志出现，chat 能列出历史记录

### Bug 5：轮询 jobId 随机 404（多任务内存态）
- **现象**：`/api/execute-backtest-async?jobId=` 轮询交替返回 `processing` 和 404
- **根因**：job 结果存在 Next.js 容器内存里（route.ts 的 Map），ECS 跑 2 个任务且 ALB 轮询分发，CloudFront 不带会话亲和
- **修复**：Target Group 开 `lb_cookie` stickiness（3600s）。浏览器场景下 cookie 自动生效；属最小改动（代码级方案应换 DynamoDB/Redis 存 job 状态，列入后续改进）

### 环境层面的坑（非代码 bug）
- 本机 shell 残留过期的 `AWS_ACCESS_KEY_ID/AWS_SESSION_TOKEN` 环境变量，覆盖了 profile 凭证 → 统一 `unset` 后用 `AWS_PROFILE=default`
- 本机 boto3 版本只认 `AWS_DEFAULT_REGION` 不认 `AWS_REGION`，第一次把 S3 Tables 建到了 us-east-1 → 删除重建到 us-east-2，并在环境脚本同时导出两个变量
- Docker Desktop 不存在，colima VM 有 stale lock → 清理 `in_use_by` 后启动
- 旧 `.bedrock_agentcore.yaml` 指向别的账号（600627331406）/us-east-1 → 备份移除后重新 configure

## 安全配置（双层 ALB 锁定）

1. **网络层**：ALB SG 入站仅允许 CloudFront origin-facing 托管前缀列表 `pl-b6a144df`:80；ECS SG 仅允许 ALB SG:3000；全 VPC 无任何 0.0.0.0/0 入站规则（已逐条审计）
2. **应用层**：CloudFront origin 注入 `X-Origin-Verify: <随机 64 hex>`（存 SSM SecureString，更新栈时复用）；ALB listener 默认动作 fixed-response 403，仅 header 匹配规则转发到 Target Group
3. **验证**：直连 ALB → 超时（SG 拦截）；经 CloudFront → 200

## 如何验证（全部通过）

1. 3 个 Runtime `READY`（list_agent_runtimes）
2. 后端 invoke：EMA crossover AMZN 1Y → `strategy_code` ✓ / `trades: 4` ✓ / `backtest_metrics` ✓ / `versions` 三组件齐 ✓
3. `GET /api/health` 经 CloudFront → 200
4. `POST /api/execute-backtest-async` → jobId → 轮询 4 次后 `complete`，含 trades 与 metrics
5. `/chat` 页 200；`/api/chat` 返回历史记录汇总（3 条 AMZN 回测）
6. 直连 ALB 超时（network 层即被拒）

## 后续可改进点

- job 状态移到 DynamoDB（带 TTL），去掉对 cookie stickiness 的依赖
- CloudFront 换 HTTPS origin（当前 CF→ALB 为 HTTP:80；viewer 侧已强制 HTTPS）
- Gateway 创建时报的 X-Ray trace destination ValidationException 不影响功能，可按提示开 CloudWatch Logs trace destination 消除
- chat 模式 sessionId 每请求新建，可复用实现多轮上下文
