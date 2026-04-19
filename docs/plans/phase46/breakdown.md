---
author: claude
phase: 46
slice: all
status: draft
depends_on:
  - docs/plans/phase46/kickoff.md
  - docs/plans/phase46/design_decision.md
  - docs/plans/phase46/risk_assessment.md
---

> **TL;DR**: 4 个 slice 的可执行拆解。S1→S2→S3→S4 顺序执行，S2 完成后设 Human gate。每个 slice 包含具体文件变更清单、验收命令和 stop/go 信号。

---

# Phase 46 Breakdown: 模型网关物理层实装

## 执行顺序

```
S1 (基础设施就绪)
  → [go] S2 (HTTP 执行器 + CLI 去品牌化)
    → [Human gate] S3 (方言对齐)
      → S4 (降级矩阵 + Eval)
        → [Human gate] PR
```

---

## S1: 基础设施就绪验证

### 目标
确认 new-api 可达，添加 httpx 依赖，建立 eval 骨架。

### 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `pyproject.toml` | 添加 `httpx` 到 dependencies |
| 修改 | `src/swallow/doctor.py` | 新增 `check_new_api_endpoint()` 检查项 |
| 新增 | `tests/eval/test_http_executor_eval.py` | eval 测试骨架（场景定义 + 空 fixture） |

### 验收命令

```bash
# httpx 可导入
.venv/bin/python -c "import httpx; print(httpx.__version__)"

# doctor 检查项存在
.venv/bin/python -m swallow.doctor 2>&1 | grep -i "new-api"

# eval 骨架可收集
.venv/bin/python -m pytest tests/eval/test_http_executor_eval.py --collect-only -m eval
```

### Stop/Go

- **Go**：httpx 可导入 + eval 骨架可收集 + doctor 报告 new-api 状态
- **Stop**：new-api 端点完全不可达 → 暂停，由 Human 确认基础设施部署

---

## S2: HTTP 执行器核心 + CLI 去品牌化

### 目标
实现 HTTPExecutor，重构 CLI 执行器为配置驱动。

### 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `src/swallow/executor.py` | 新增 `HTTPExecutor`、`CLIAgentExecutor`、`CLIAgentConfig`；重构 `run_executor_inline` 移除 else 兜底；保留 `run_codex_executor` 为 `CLIAgentExecutor(codex_config)` 的委托 |
| 修改 | `src/swallow/router.py` | 在 `_build_builtin_route_registry` 注册 `local-http` 路由；在 `ROUTE_MODE_TO_ROUTE_NAME` 添加 `"http"` 映射 |
| 修改 | `src/swallow/cost_estimation.py` | `MODEL_PRICING` 添加 `"qwen"`、`"glm"`、`"gemini"` 定价 |
| 修改 | `tests/test_executor_protocol.py` | 新增 `HTTPExecutor` 和 `CLIAgentExecutor` 的 protocol 一致性测试 |
| 可能修改 | `src/swallow/models.py` | 如需新增 `route_endpoint` 字段到 `TaskState` |

### 实现要点

**HTTPExecutor 核心流程**：
```
execute(base_dir, state, card, retrieval_items)
  → build_formatted_executor_prompt(state, retrieval_items)
  → 构造 {"model": state.route_model_hint, "messages": [{"role": "user", "content": prompt}]}
  → httpx.post(state.route_endpoint or "http://localhost:3000/v1/chat/completions", json=payload, timeout=timeout)
  → 解析 response.json()["choices"][0]["message"]["content"]
  → 返回 ExecutorResult(executor_name="http", status="completed", output=content, ...)
```

**CLIAgentExecutor 重构策略**（先并行后替换）：
1. 新增 `CLIAgentConfig` dataclass 和 `CLIAgentExecutor` 类
2. 创建 `CODEX_CONFIG` 和 `CLINE_CONFIG` 实例
3. 让 `run_codex_executor` 内部委托给 `CLIAgentExecutor(CODEX_CONFIG).execute(...)`
4. 全量测试通过后，将 `run_codex_executor` 标记为 deprecated wrapper
5. 更新 `run_executor_inline` 的分发逻辑，移除 else 兜底

### 验收命令

```bash
# 全量测试无回归
.venv/bin/python -m pytest --tb=short

# HTTPExecutor protocol 一致性
.venv/bin/python -m pytest tests/test_executor_protocol.py -k "http" -v

# CLIAgentExecutor protocol 一致性
.venv/bin/python -m pytest tests/test_executor_protocol.py -k "cli_agent" -v

# HTTP 路由注册
.venv/bin/python -c "from swallow.router import ROUTE_REGISTRY; print(ROUTE_REGISTRY.get('local-http'))"

# eval（需要 new-api 可达）
.venv/bin/python -m pytest tests/eval/test_http_executor_eval.py -m eval -v
```

### Stop/Go

- **Go**：全量 pytest passed + HTTP 执行器通过 mock 测试 + 真实 new-api 调用返回有效响应
- **Stop**：全量 pytest 有回归 → 先修复再继续；new-api 调用失败 → 检查 S1 的 doctor 输出

### Human Gate

S2 完成后请 Human 验证：
1. 通过 `local-http` 路由发送真实请求到 new-api
2. 确认收到有效 LLM 响应
3. 确认 CLI 重构未破坏现有 `codex` 路径

---

## S3: 方言对齐与多模型路由

### 目标
注册多模型族 HTTP 路由，确保方言严格对齐。

### 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `src/swallow/router.py` | 注册 `http-claude`、`http-qwen`、`http-glm`、`http-gemini`、`http-deepseek` 路由 |
| 可能修改 | `src/swallow/dialect_adapters.py` | 如需为 qwen/glm 新增方言适配器 |
| 修改 | `src/swallow/cost_estimation.py` | 确认所有新模型族的定价已覆盖 |
| 修改 | `tests/eval/test_http_executor_eval.py` | 补充方言正确性 eval 场景 |

### 路由注册规划

| 路由名 | model_hint | dialect_hint | fallback | 说明 |
|--------|-----------|-------------|----------|------|
| `http-claude` | `claude` | `claude_xml` | `http-qwen` | 主力路由 |
| `http-qwen` | `qwen` | `plain_text` | `http-glm` | 一级降级 |
| `http-glm` | `glm` | `plain_text` | `local-cline` | 二级降级 |
| `http-gemini` | `gemini` | `plain_text` | `http-qwen` | 长上下文专用 |
| `http-deepseek` | `deepseek` | `codex_fim` | `http-qwen` | 代码补全专用 |

### 验收命令

```bash
# 全量测试无回归
.venv/bin/python -m pytest --tb=short

# 所有 HTTP 路由已注册
.venv/bin/python -c "
from swallow.router import ROUTE_REGISTRY
for name in ['http-claude', 'http-qwen', 'http-glm', 'http-gemini', 'http-deepseek']:
    r = ROUTE_REGISTRY.maybe_get(name)
    print(f'{name}: {\"OK\" if r else \"MISSING\"} dialect={getattr(r, \"dialect_hint\", \"?\")}')
"

# 方言 eval
.venv/bin/python -m pytest tests/eval/test_http_executor_eval.py -m eval -v
```

### Stop/Go

- **Go**：所有路由注册 + 方言 eval 通过
- **Stop**：方言 substring 误匹配 → 修复 `resolve_dialect_name` 后重试

---

## S4: 降级矩阵与 Eval 护航

### 目标
实现跨执行器族降级链，补齐 Cline CLI 集成，全量 eval 验证。

### 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `src/swallow/executor.py` | HTTPExecutor 降级逻辑 + Cline 的 `CLIAgentConfig` 实例 |
| 修改 | `src/swallow/router.py` | 注册 `local-cline` 路由 + 配置 fallback 链 |
| 修改 | `tests/test_executor_protocol.py` | 降级链测试 + Cline mock 测试 |
| 修改 | `tests/eval/test_http_executor_eval.py` | 补齐全部 eval 场景的完整实现 |

### 降级链配置

```
http-claude → http-qwen → http-glm → local-cline → local-summary
```

降级触发条件：
- HTTP 连接超时（`httpx.ConnectTimeout`）
- HTTP 429 Too Many Requests（触发退避后降级）
- HTTP 5xx Server Error
- 响应解析失败（JSON decode error / missing `choices`）

降级安全机制：
- 已访问路由集合检测，防止循环
- Cline 未安装时自动跳过（`shutil.which("cline") is None`），直接降级到 `local-summary`
- 每次降级记录 `degraded=True` + `original_route` + `fallback_route` 到 `ExecutorResult`

### 验收命令

```bash
# 全量测试无回归
.venv/bin/python -m pytest --tb=short

# 降级链测试
.venv/bin/python -m pytest tests/test_executor_protocol.py -k "fallback" -v

# 全量 eval
.venv/bin/python -m pytest tests/eval/ -m eval -v

# 最终确认测试数量
.venv/bin/python -m pytest --co -q | tail -1
```

### Stop/Go

- **Go**：全量 pytest passed + 全量 eval passed → 准备 PR
- **Stop**：eval 基线未达标 → 调优后重试；降级链有循环 → 修复 fallback 配置

---

## 默认不做的工作

- 不修改 `orchestrator.py` 的主循环逻辑
- 不修改 `harness.py` 的 `run_execution` 入口
- 不修改现有的 `local-codex`、`local-mock`、`local-note`、`local-summary` 路由
- 不为 Gemini 实现 Context Caching / File API
- 不实现 streaming 响应
- 不实现 TensorZero 集成
- 不修改 `.agents/` 下的任何文件
