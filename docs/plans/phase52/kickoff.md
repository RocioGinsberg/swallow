---
author: claude
phase: 52
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase52/context_brief.md
  - docs/roadmap.md
  - docs/design/ORCHESTRATION.md
---

## TL;DR
Phase 52 完成执行层的两件事：用 Aider / Claude Code 替换 codex/cline 具名路径，实装 `AsyncCLIAgentExecutor` 作为通用 subprocess 执行基础，并为 Warp-Oz 等未来并行执行器保留可插拔配置位；在此之上落地 Strategy Router 的路由规则，使 fan-out/fan-in 并行拓扑可以真正分发给多个异步执行单元（本 phase 以 Aider 多实例 + HTTP 路径作为 fan-out 目标验证）。

# Phase 52 Kickoff: 执行器重构与并行拓扑落地

## 基本信息

| 字段 | 值 |
|------|-----|
| Phase | 52 |
| Primary Track | Core Loop |
| Secondary Track | Execution Topology |
| 目标 tag | v0.9.0 (Execution Era) |
| 前置 phase | Phase 51 (v0.8.0) |

## 战略定位

Phase 51 完成了策略闭环——系统现在能感知自身状态并提出优化建议。Phase 52 的使命是让执行层真正对齐设计蓝图：**把 codex/cline 这两个已经不再是目标执行器的具名路径清理掉，换上 Aider / Claude Code 两条工程路径，打通 fan-out/fan-in 并行拓扑，并让 Strategy Router 能够根据任务特征选择正确的路径**。

`ORCHESTRATION.md §5.1-5.2` 定义的工程链路接力与并行调查链路，在当前代码里没有对应的执行器实现。Phase 52 补上这个缺口。

## 执行器路径重新定义

设计蓝图（`ORCHESTRATION.md §2.1, §5.1-5.2`）定义了多条 CLI agent 路径：

| 路径 | 执行器 | 适用场景 | Phase 52 状态 |
|------|--------|---------|-------------|
| 日常/局部施工 | **Aider** | 代码修改、局部重构、高频迭代 | ✅ 本 phase 落地 |
| 复杂任务/高层方案 | **Claude Code** | 跨文件改造、架构级修改、需要强推理的任务 | ✅ 本 phase 落地 |
| 并行调查 | **Warp-Oz**（多实例，本地） | 独立子问题并行探索 | ⏸ 可扩展占位，不落地（付费依赖） |
| 受控模型调用 | **HTTP path** | 已有原生 async 实现 | 不改动 |

**Warp-Oz 调整说明**：Oz agent 目前需要付费订阅，项目开发阶段不引入实际依赖。保留以下扩展位，未来付费接入时可直接启用：

- `AsyncCLIAgentExecutor` 通用执行器支持任意 `CLIAgentConfig`
- Strategy Router 的 `complexity_hint == "parallel"` 信号不绑定具体执行器，由 `task_family_score` 决定并行目标
- `AsyncSubtaskOrchestrator` 已具备 fan-out 并发能力，任何 executor 都可作为并行单元

fan-out 并行的本 phase 验收目标：**Aider 多实例 + HTTP 路径**。Warp-Oz 作为后续 phase 的可插拔接入点。

codex / cline 不再是目标执行器，其具名路径在本 phase 清理。

## 目标 (Goals)

1. **实装 `AsyncCLIAgentExecutor`**：用 `asyncio.create_subprocess_exec` 替代 `subprocess.run`，作为所有 CLI agent 路径的通用 async 执行基础。Aider / Claude Code 各自有一个 `CLIAgentConfig`，复用这个执行器；同一基础设施为 Warp-Oz 等未来执行器预留接入位。

2. **清理 codex/cline 具名路径**：从 `run_prompt_executor` / `run_prompt_executor_async` 的 if-chain 中移除 codex/cline 分支，清理 `CODEX_CONFIG`、`CLINE_CONFIG`、`run_codex_executor`、`run_cline_executor`。`CLIAgentExecutor` 空壳一并移除。

3. **实装 Strategy Router 路由规则**：基于任务特征（`task_family`、`source_kind`、`complexity_hint`）决定走哪条路径。规则优先级：capability guard → task_family_score → complexity_hint → quality_weight。

4. **落地 fan-out/fan-in 并行拓扑**：补全 `_run_subtask_orchestration_async` 的 summary artifact 与子任务级 timeout 守卫。Phase 52 以 Aider 多实例和 HTTP 路径作为验收场景。`AsyncSubtaskOrchestrator` 已具备 `asyncio.gather + Semaphore` 基础，任何 executor 可作为 fan-out 单元。

5. **消化 C2 concern**：`schedule_consistency_audit` 从 `threading.Thread` 迁移到 `asyncio.create_task`，统一并发原语。

## 非目标 (Non-Goals)

- **不落地其他 Specialist Agent**：Ingestion / Literature / Quality Reviewer 等留待 Phase 53。
- **不改动 HTTP path**：`run_http_executor_async` 已是原生 async，不在本 phase 触碰。
- **不实装 DAG 编排**：子任务间有显式依赖的 DAG 拓扑标记为高级功能，不在本 phase。
- **不做 Brainstorm 模式**：`ORCHESTRATION.md §2.5` 的 Brainstorm 链路留待后续 phase。
- **不做多租户或分布式部署**：系统仍为单机本地优先。
- **不改动 Librarian / Meta-Optimizer**：Phase 51 已稳定，不在本 phase 触碰。

## Slice 拆解

### S1: AsyncCLIAgentExecutor + 执行器路径重构

**目标**：实装通用 async subprocess 执行基础，替换 codex/cline，接入 Aider / Claude Code。

**交付物**：
- `AsyncCLIAgentExecutor`：内部用 `asyncio.create_subprocess_exec`，支持 stdout 流式读取、timeout、fallback
- `AIDER_CONFIG` / `CLAUDE_CODE_CONFIG`：两份 `CLIAgentConfig`
  - Aider：`aider --yes-always`（或 `--no-auto-commits`，视需要）
  - Claude Code：`claude --print`（非交互模式）
- **Warp-Oz 占位**：`CLIAgentConfig` 数据结构保留足够通用性（`fixed_args` / `bin_env_var` 模式），未来付费接入 Oz 时仅需新增一份 config，无需改执行器
- `run_prompt_executor_async` 中 codex/cline 分支替换为 aider/claude-code
- 清理 `CODEX_CONFIG`、`CLINE_CONFIG`、`run_codex_executor`、`run_cline_executor`、`CLIAgentExecutor` 空壳
- 同步版本 `run_prompt_executor` 保留兼容路径（通过 `asyncio.run` 包装 async 版本），或直接移除同步具名分支

**验收条件**：
- `run_prompt_executor_async` 中 aider/claude-code 路径不再经过 `asyncio.to_thread`
- 现有 executor protocol 测试全部通过
- `shutil.which` 检测失败时正确触发 fallback

**C2 消化**（附属于 S1）：
- `schedule_consistency_audit` 改为 `asyncio.create_task`
- 在 `run_task_async` 末尾调用时不再是同步 threading 调用
- 注意：`asyncio.create_task` 要求在事件循环内调用，需确认调用点上下文

### S2: Strategy Router 路由规则

**目标**：让 Strategy Router 能根据任务特征选择 aider / claude-code / http，并在并行信号下触发 fan-out（不绑定具体执行器）。

**路由规则设计**：

```
1. capability guard（最高优先级）
   - route.unsupported_task_types 包含当前 task_family → 排除该路由

2. task_family_score（次优先级）
   - 按 task_family_scores[task_family] 降序排列候选路由

3. complexity_hint（任务特征信号）
   - complexity_hint == "high" → 优先 claude-code
   - complexity_hint == "low" / "routine" → 优先 aider
   - complexity_hint == "parallel" → 设置 parallel_intent=True，触发 fan-out（执行器仍按 task_family_score 排序选择，典型为 aider 或 http）

4. quality_weight（兜底）
   - 无 complexity_hint 时按 quality_weight 排序
```

**交付物**：
- `complexity_hint` 字段加入 `TaskSemantics`（或 `TaskCard.input_context`）
- Strategy Router 消费 `complexity_hint` 并映射到路由候选
- `RouteSelection.policy_inputs` 增加 `complexity_hint` 与 `parallel_intent` 记录
- CLI `swl route select --task-id <id>` 可查看路由决策过程（dry-run）

**验收条件**：
- `complexity_hint = "high"` 时 Strategy Router 选出 claude-code 路由
- `complexity_hint = "parallel"` 时 `RouteSelection.policy_inputs["parallel_intent"] = True`，上游触发 fan-out
- capability guard 正确排除 unsupported 路由

### S3: Fan-out / Fan-in 汇总与守卫

**目标**：在现有 `AsyncSubtaskOrchestrator` 基础上补齐 summary artifact 与子任务级 timeout 守卫，使 fan-out 链路可闭环可审计。

**现状确认**（对 context_brief 的修正）：`AsyncSubtaskOrchestrator._run_level` 已使用 `asyncio.gather + Semaphore`，`subtask_extra_artifacts_lock` 已是 `asyncio.Lock`。并发原语已就位，S3 不再需要"实装"并发，而是补强可观测性与健壮性。

**交付物**：
- 子任务级 timeout 守卫：`_run_single_card` 外层 `asyncio.wait_for`，超时后清理子进程、tempdir 并返回 `ExecutorResult(failure_kind="subtask_timeout")`
- `asyncio.gather(..., return_exceptions=True)`：保证单任务异常不 cancel 其他任务（配合 `_run_single_card` 内部 try/except，默认不会抛，作为 defensive 分支）
- `subtask_summary.md` artifact：所有子任务完成后产出结构化汇总（每个 subtask 的 card_id / goal / executor / status / artifact refs），进入 Review Gate 或 waiting_human
- `MAX_SUBTASK_WORKERS` 暴露为环境变量 / config（默认保持现值）

**验收条件**：
- 4 个 mock 子任务 + Aider mock binary 并发执行，总耗时接近单任务耗时（而非 4 倍）
- 单个子任务超时不影响其他子任务，孤儿进程被清理
- summary artifact 包含所有子任务的结果引用
- HTTP 路径多实例场景（`httpx.AsyncClient` 并发）作为辅助验证

## 设计边界

- **`AsyncCLIAgentExecutor` 是通用基础**：Aider / Claude Code 复用它，不各自实现 subprocess 逻辑。Warp-Oz 未来接入时仅需新增一份 `CLIAgentConfig`，不改执行器。
- **Strategy Router 只做策略判断**：不负责 endpoint 健康探测、HTTP payload 方言适配——这些属于 Provider Router（`ORCHESTRATION.md §2.1`）。
- **fan-out 无中间同步点**：子任务之间无依赖，`asyncio.gather` 直接并发。有依赖的 DAG 拓扑不在本 phase。
- **Warp-Oz 延后接入**：Oz agent 当前为付费产品，项目开发阶段不引入外部依赖。保留 `CLIAgentConfig` 插槽作为扩展位，未来可通过新增 config + 配置环境变量快速接入（`oz agent run --prompt` 本地，或 `oz agent run-cloud --environment` 云端）。
- **codex/cline 清理不保留兼容别名**：两者已不是目标执行器，直接移除。如有测试依赖，改为 mock 路径。

## 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| `asyncio.create_subprocess_exec` 在不同 OS 下行为差异 | 中 | 测试覆盖 Linux/macOS，Windows 不在支持范围 |
| `asyncio.create_task` 在非事件循环上下文调用失败 | 中 | 确认 `run_task_async` 调用点，必要时用 `loop.call_soon_threadsafe` 过渡 |
| `asyncio.gather` 中单任务异常导致其他任务被 cancel | 中 | 使用 `return_exceptions=True`，各子任务独立处理异常 |
| Aider / Claude Code binary 不在 PATH | 低 | `shutil.which` 检测失败时走现有 fallback 机制 |
| `threading.Lock` → `asyncio.Lock` 替换遗漏 | 低 | grep 全量检查 `threading.Lock` 在 async 上下文的使用（注：`subtask_extra_artifacts_lock` 已是 `asyncio.Lock`） |

## 验收条件（Phase 级别）

- `run_prompt_executor_async` 中无 `asyncio.to_thread(run_codex_executor, ...)` 或 `asyncio.to_thread(run_cline_executor, ...)`
- Strategy Router 路由规则有单元测试覆盖两条 CLI 路径（aider / claude-code）+ HTTP 路径 + parallel_intent 信号
- fan-out 并行拓扑有集成测试：4 个 mock 子任务并发执行，summary artifact 正确产出
- `schedule_consistency_audit` 不再使用 `threading.Thread`
- 全量 pytest 通过

## 依赖与前置条件

- Phase 51 (v0.8.0) 已稳定：`MetaOptimizerAgent`、`RouteCapabilityProfile`、`AuditTriggerPolicy` 均已落地
- `ORCHESTRATION.md` 设计蓝图已确认（§2.1, §5.1-5.2, §5.6）
- Aider / Claude Code 的 binary 接口已知（`CLIAgentConfig` 可配置）
- Warp-Oz 延后接入（付费依赖），`CLIAgentConfig` 保留扩展位
