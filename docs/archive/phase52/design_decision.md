---
author: claude
phase: 52
slice: design
status: draft
depends_on:
  - docs/plans/phase52/kickoff.md
  - docs/plans/phase52/context_brief.md
  - docs/design/ORCHESTRATION.md
  - src/swallow/executor.py
  - src/swallow/router.py
  - src/swallow/orchestrator.py
  - src/swallow/subtask_orchestrator.py
---

## TL;DR

Phase 52 用通用 `AsyncCLIAgentExecutor` 承载 Aider / Claude Code 两条 CLI 路径，同步移除 codex/cline 具名分支与同步 `CLIAgentExecutor` 空壳；Warp-Oz 因付费依赖延后接入，保留 `CLIAgentConfig` 扩展位。路由层通过在 `TaskSemantics` 新增 `complexity_hint` 字段改造 `select_route`，使其能根据任务特征在 aider / claude-code / http 之间选择，`parallel` 信号触发 fan-out 但不绑定具体执行器。现有 `AsyncSubtaskOrchestrator` 已提供 `asyncio.gather + Semaphore` 的 fan-out 原语，S3 仅补 summary artifact 汇总、子任务级 timeout 守卫与 fan-out 集成验证（以 Aider 多实例 + HTTP 路径为目标）；`schedule_consistency_audit` 的 `threading.Thread → asyncio.create_task` 迁移作为 S1 尾部独立提交。

## Implementation Note

2026-04-24 follow-up：Phase 52 实际落地的是 **async executor entrypoint + Runtime v0 harness bridge**。`AsyncCLIAgentExecutor.execute_async()` 已成为统一 async 入口，但底层仍通过 `_run_harness_execution_async()` 以 `asyncio.to_thread(...)` 包装同步 harness，而不是在本 phase 内直接把 harness 改造成 `asyncio.create_subprocess_exec` 主链。原文中对“原生 async subprocess 主链”的描述应视为设计目标，不是本 phase 的最终实现状态。

---

## 上下文纠偏

Context brief 中"`_run_subtask_orchestration_async` 尚未实装跨模型并行分发"与"`threading.Lock` 需替换为 `asyncio.Lock`"两条描述不准确。实际现状：

- `src/swallow/subtask_orchestrator.py:300-306`：`AsyncSubtaskOrchestrator._run_level` 已使用 `asyncio.Semaphore(min(max_workers, len(level)))` + `asyncio.gather(*(run_card(card) for card in level))`
- `src/swallow/orchestrator.py:2038`：`subtask_extra_artifacts_lock = asyncio.Lock()` 已是 asyncio 原语
- Level-by-level 执行（基于 `depends_on` 拓扑排序），每 level 内部并发，符合 fan-out 语义

这意味着 S3 真实范围不是"实装 fan-out"，而是：
1. **接入 Warp-Oz** 作为合法的 fan-out 目标执行器（而非仅 mock / local）
2. **补 summary artifact** 结构化汇总（当前每个 subtask 独立 artifact，无顶层汇总）
3. **补子任务级 timeout 守卫**（现有逻辑依赖 executor 自身 timeout，无 orchestrator 层超时 cancel）
4. **并发控制 knob**：`MAX_SUBTASK_WORKERS` 是否暴露为配置项、是否基于 route capacity 动态调整

S3 工作量比 kickoff 所述小，但质量与可观测性维度需要补强。

---

## 核心设计决策

### 决策 1：通用 `AsyncCLIAgentExecutor` vs 每个 agent 独立实现

**问题**：Aider / Claude Code / Warp-Oz 三条 CLI 路径是否共享一个通用 async 执行器，还是各自实现？

**候选方案**：
- A. 每个 agent 独立 `AiderExecutor` / `ClaudeCodeExecutor` / `WarpOzExecutor`：每个类含自己的 subprocess 逻辑
- B. 通用 `AsyncCLIAgentExecutor` + 三个 `CLIAgentConfig`：执行器一个，配置三份
- C. 混合：基础框架共享，特殊处理（如 Warp-Oz 的 cloud environment 参数）每个 agent 内部实现

**选择方案**：B（通用执行器 + 配置驱动）

**理由**：
- 现有 `CLIAgentConfig` 模式（`src/swallow/executor.py:143-175`）已验证可行，codex/cline 就是同一个 `CLIAgentExecutor` + 两份 config
- 两条路径的核心逻辑完全一致：拼命令、启子进程、读 stdout、timeout、fallback。差异仅在 binary 名、fixed_args 与可选的 output path flag
- 维护成本低：新增执行器仅加一份 config，不改执行器
- 后续 Warp-Oz（`oz agent run --prompt`）或云端 Oz（`oz agent run-cloud --environment`）接入时仅需新增 config，不改执行器代码

**实现**：

```python
AIDER_CONFIG = CLIAgentConfig(
    executor_name="aider",
    display_name="Aider",
    bin_env_var="AIWF_AIDER_BIN",
    default_bin="aider",
    fixed_args=("--yes-always", "--no-auto-commits"),
    workspace_root_flags=(),  # Aider 默认使用 cwd
)

CLAUDE_CODE_CONFIG = CLIAgentConfig(
    executor_name="claude-code",
    display_name="Claude Code",
    bin_env_var="AIWF_CLAUDE_CODE_BIN",
    default_bin="claude",
    fixed_args=("--print",),  # 非交互模式
    workspace_root_flags=(),
)

# Warp-Oz 扩展占位（付费依赖，不在 Phase 52 落地）
# WARP_OZ_CONFIG = CLIAgentConfig(
#     executor_name="warp-oz",
#     display_name="Warp Oz",
#     bin_env_var="AIWF_WARP_OZ_BIN",
#     default_bin="oz",
#     fixed_args=("agent", "run", "--prompt"),
#     workspace_root_flags=(),
# )
```

`AsyncCLIAgentExecutor` 的核心实现：

```python
class AsyncCLIAgentExecutor:
    def __init__(self, config: CLIAgentConfig) -> None:
        self.config = config

    async def execute_async(self, base_dir, state, card, retrieval_items):
        prompt = build_formatted_executor_prompt(state, retrieval_items)
        return await run_cli_agent_executor_async(
            self.config, state, retrieval_items, prompt
        )

    def execute(self, base_dir, state, card, retrieval_items):
        # 同步入口：asyncio.run 包装 async 版本
        return asyncio.run(self.execute_async(base_dir, state, card, retrieval_items))
```

实现后校正：Phase 52 当前并未把 Runtime v0 harness 改写为原生 async subprocess 主链；实际稳定实现是 async executor 入口统一后，通过 `_run_harness_execution_async()` 桥接既有同步 harness。若后续 phase 继续收紧 Runtime，才再把这段设计目标下推到 harness / subprocess 层。

---

### 决策 2：codex/cline 直接删除 vs 保留兼容别名

**问题**：移除 codex/cline 是否保留 executor resolver 的兼容别名？

**候选方案**：
- A. 直接删除所有代码路径，测试中的 codex/cline 依赖改为 mock 或 aider
- B. 保留 `CODEX_CONFIG` / `CLINE_CONFIG` 不变，仅不再推荐使用
- C. resolve_executor 中将 codex/cline 映射为 aider 作为兼容过渡

**选择方案**：A（直接删除）

**理由**：
- codex/cline 未在任何对外稳定接口中承诺存在（README / AGENTS.md 不强调）
- 保留死代码会持续产生维护负担（每次重构都要考虑兼容路径）
- 编排蓝图 §附录 A 明确反对"品牌定义职责"——codex/cline 是品牌名残留
- 兼容别名容易误导：用户以为还在用 codex，实际走 aider，调试成本高

**影响面盘点**（需在 S1 实现时全部处理）：
- `src/swallow/executor.py`：`CODEX_CONFIG`、`CLINE_CONFIG`、`CLI_AGENT_CONFIGS`、`run_codex_executor`、`run_cline_executor`、`CLIAgentExecutor`、`run_prompt_executor*` 中的 codex/cline 分支、`build_failure_recommendations` 中的 Codex 文案
- `src/swallow/router.py`：`local-codex` / `local-cline` 路由定义
- `src/swallow/dialect_data.py`：`DEFAULT_EXECUTOR`（目前可能是 codex，需改为 aider 或 http）
- `src/swallow/models.py`：`TaskState.executor_name` / `route_name` 的默认值
- `tests/`：搜索 "codex" / "cline" 字符串，按影响替换
- `README*.md` / `AGENTS.md`：示例命令更新

---

### 决策 3：`complexity_hint` 字段放置位置

**问题**：复杂度信号放在哪一层对象里？

**候选方案**：
- A. `TaskSemantics.complexity_hint`：作为语义层面的标注，与 `priority_hints` / `next_action_proposals` 并列
- B. `TaskCard.input_context["complexity_hint"]`：作为 card 级别的路由输入
- C. 独立字段 `TaskState.complexity_hint`：顶层状态字段，直接参与路由判断

**选择方案**：A（`TaskSemantics.complexity_hint`）

**理由**：
- 语义归属正确：complexity 是任务语义的一部分，和 `priority_hints` 同层
- 持久化已有：`TaskSemantics` 在 `task_semantics.py` 中已是可序列化字段，Strategy Router 可以在 `select_route` 里通过 `state.task_semantics.get("complexity_hint")` 读取
- 解耦干净：TaskCard 是执行层对象（goal + input_context），不应承载策略层语义
- 后续扩展方便：complexity 之外，未来可能还需 `domain_hint`、`risk_hint` 等，都属于 semantics

**取值约定**：
- `"low"` / `"routine"`：日常改动 → aider
- `"high"`：复杂改动 → claude-code
- `"parallel"`：可拆分的独立子任务集合 → warp-oz fan-out
- `""`（未设定）：fallback 到 `task_family_score + quality_weight`

**获取方式**：
- 从 operator 手工设置（Intake 阶段的交互）
- 从 Planner 分析结果推断（未来可接 Meta-Optimizer 提案）

---

### 决策 4：路由决策改造 `select_route` vs 新增 `route_for_task`

**问题**：路由规则是改造现有 `select_route`，还是新增独立的 `route_for_task` 函数？

**候选方案**：
- A. 改造 `select_route`：所有路由逻辑统一在一个入口
- B. 新增 `route_for_task`：保留 `select_route` 作为底层原语，`route_for_task` 在其上加策略层
- C. Strategy Router 升级为 class：封装状态与多种选择策略（任务型、资源型、降级型）

**选择方案**：A（改造 `select_route`，新增内部策略函数）

**理由**：
- 避免"两套路由逻辑"的长期维护负担
- `select_route`（`src/swallow/router.py:760`）已承担策略入口角色：它消费 `executor_override` / `route_mode_override` / `state.route_mode` / `state.task_semantics`
- 新增 `complexity_hint` 处理只需在 `candidate_routes` 之前增加一层过滤 / 加权
- 保持向后兼容：`executor_override` 与 `route_mode` 显式路径继续最高优先级

**实现结构**：

```python
def select_route(state, executor_override=None, route_mode_override=None) -> RouteSelection:
    # ...原有 override / route_mode 判断...

    # 新增：complexity_hint 影响候选排序
    complexity_hint = _resolve_complexity_hint(state)
    task_family = infer_task_family(state)

    candidates, match_kind = ROUTE_REGISTRY.candidate_routes(
        executor_name=selected_executor,
        # ...
        task_family=task_family,
    )

    # 新增：complexity_hint 重排序
    candidates = _apply_complexity_bias(candidates, complexity_hint)

    route = candidates[0] if candidates else route_for_executor(selected_executor)
    return RouteSelection(route=route, reason=..., policy_inputs={..., "complexity_hint": complexity_hint})
```

`_apply_complexity_bias(candidates, hint)` 的规则：
- `hint == "high"`：提升 `claude-code` 路由优先级
- `hint == "low"` / `"routine"`：提升 `aider` 路由优先级
- `hint == "parallel"`：返回 `warp-oz` 候选（若存在），上游 `_run_orchestrator_async` 据此决定是否进入 Subtask Orchestrator fan-out 路径

---

### 决策 5：fan-out 触发机制（不绑定具体执行器）

**问题**：`complexity_hint == "parallel"` → fan-out 的触发语义是什么？

**候选方案**：
- A. Strategy Router 直接返回特定路由（如 warp-oz），由该实例内部处理并行
- B. Strategy Router 返回 parallel_intent 信号，Planner 按 signal 拆分为 N 个 subtask，`AsyncSubtaskOrchestrator` 分发给 N 个执行器实例（执行器由 task_family_score 决定）
- C. Strategy Router 无感知，Planner 自行决定是否启动并行

**选择方案**：B（路由层 + Planner 协同，执行器不绑定）

**理由**：
- `ORCHESTRATION.md §2.3` 明确要求平台级 subtask orchestration 由 Swallow 控制，不依赖 executor-native subagents
- §5.2 定义的并行调查链路："Planner 拆出独立子问题 → Subtask Orchestrator 分发" —— Planner 是拆分主体，执行器是分发目标
- 不绑定 Warp-Oz：fan-out 目标可以是 Aider 多实例、HTTP 多实例、或未来的 Warp-Oz——由 task_family_score 和 quality_weight 决定
- 复用现有 `AsyncSubtaskOrchestrator` 基础设施，不引入新的并行模型

**实现**：

1. Strategy Router 感知 `complexity_hint == "parallel"` 后：
   - 设置 `RouteSelection.policy_inputs["parallel_intent"] = True`
   - 返回按 task_family_score 排序的最优路由作为 default executor
2. Planner（未来阶段）或 operator 手工拆分 subtask cards
3. `_run_subtask_orchestration_async` 消费 cards，分发给执行器实例
4. Fan-in：`AsyncSubtaskOrchestrator.run()` 已返回 `SubtaskOrchestratorResult`，S3 在其上叠加结构化 summary artifact

**Phase 52 验收场景**：Aider mock binary 多实例 + HTTP 路径多实例。Warp-Oz 作为后续 phase 的可插拔接入点。

**非目标**：Phase 52 不实装 Planner 的自动拆分——需要人工提供 subtask cards 或由后续 phase 的 Planner 产出。

---

### 决策 6：S3 范围重新定义

**问题**：`AsyncSubtaskOrchestrator` 已实装 `asyncio.gather + Semaphore`，S3 的实质工作是什么？

**候选方案**：
- A. 只做 Warp-Oz 集成验证，summary artifact 留后续
- B. 接入 Warp-Oz + summary artifact + 子任务级 timeout 守卫
- C. 在 B 之上加 Planner 自动拆分 + 动态并发 knob

**选择方案**：B（集成验证 + 汇总 + 守卫，不做动态 Planner）

**理由**：
- C 的 Planner 自动拆分涉及复杂度评估模型，超出 Phase 52 的"执行器重构"主线
- A 太保守：fan-out 已具备，缺少汇总 artifact 会让并行调查链路无法闭环
- B 是最小可用集：确保链路可跑通、产物可审计、可回收

**交付物**：

1. **Fan-out 集成验证**：`AsyncCLIAgentExecutor(AIDER_CONFIG)` 在 `AsyncSubtaskOrchestrator._run_level` 的 `asyncio.gather` 上下文中可并发执行；HTTP 路径多实例作为辅助验证；集成测试以 mock binary 验证
2. **Summary artifact**：在 `_run_subtask_orchestration_async` 的尾部（所有 retry / debate 汇总后）产出 `subtask_summary.md`，结构：
   - Overall status（completed / partial / failed）
   - 每个 subtask 的 card_id / goal / executor / final status / artifact refs
   - Fan-in conclusion（operator 可审阅的结构化摘要）
3. **子任务级 timeout 守卫**：在 `_run_single_card` 外层包一层 `asyncio.wait_for(..., timeout=card.reviewer_timeout_seconds or DEFAULT_SUBTASK_TIMEOUT)`，超时后 `asyncio.CancelledError` 转换为 `ExecutorResult(status="failed", failure_kind="subtask_timeout")`

**不做**：
- `MAX_SUBTASK_WORKERS` 的动态调整（暴露为 config，但不基于 route capacity 自动调整）
- Planner 自动拆分
- 跨 phase 的并行回放（recovery semantics）

---

### 决策 7：`schedule_consistency_audit` 迁移时机

**问题**：C2 concern（`threading.Thread → asyncio.create_task`）何时消化？

**候选方案**：
- A. S1 范围内完成，与执行器重构绑定
- B. 作为独立的 S1' 提交，S1 完成后紧接着做
- C. S3 完成后统一并发原语审查时处理

**选择方案**：B（S1 尾部独立提交）

**理由**：
- S1 已承担执行器核心重构，再绑定审计迁移会让 commit 过大，不利于 review
- C 时机太晚：S2/S3 都依赖 async 主路径，若审计迁移出问题会污染后续 slice
- B 提供清晰的隔离点：S1 主体先绿，独立提交做 audit 迁移，失败可单独 revert

**实现注意**：
- `_maybe_schedule_consistency_audit`（`orchestrator.py:234`）当前同步调用，改为 async 函数
- 调用点在 `run_task_async` 末尾（`orchestrator.py:3517`），已在 async 上下文，可直接 `asyncio.create_task(_maybe_schedule_consistency_audit_async(...))`
- fire-and-forget 语义：task 引用存入 `_background_audit_tasks: set[asyncio.Task]`（弱引用集合）避免被 GC 提前取消；`task.add_done_callback(_background_audit_tasks.discard)`
- 异常处理：`task.add_done_callback` 里捕获 `task.exception()` 并写入 event log，不重抛

---

## 与蓝图的对齐

| 蓝图要点 | Phase 52 实现 | 对齐度 |
|---------|-------------|--------|
| **§2.1 Strategy Router 复杂度评估** | `complexity_hint` 驱动 aider / claude-code 分流 | ✅ 完全对齐 |
| **§2.3 平台级 subtask orchestration** | 执行器作为黑盒执行单元，由 `AsyncSubtaskOrchestrator` 控制 | ✅ 完全对齐 |
| **§5.1 工程链路接力** | Aider 日常施工 / Claude Code 复杂修改 | ✅ 完全对齐 |
| **§5.2 并行调查链路** | Planner 拆分 → Subtask Orchestrator → 多实例分发 | ⚠️ Planner 拆分暂手工；Warp-Oz 延后 |
| **§5.6 fan-out/fan-in** | `asyncio.gather + Semaphore` 已具备，补 summary artifact | ✅ 补强后完全对齐 |
| **附录 A 品牌定义职责反模式** | 清理 codex/cline 品牌名残留 | ✅ 完全对齐 |

---

## 集成点

### 1. 与 Strategy Router 的集成

- **入口**：`select_route` 消费 `state.task_semantics["complexity_hint"]`
- **输出**：`RouteSelection` 增加 `policy_inputs["complexity_hint"]` 与 `policy_inputs["parallel_intent"]`
- **影响**：现有测试需补充 complexity_hint 场景；不破坏默认行为（hint 为空时走现有逻辑）

### 2. 与 Executor Resolver 的集成

- **修改**：`resolve_executor` 移除 codex/cline 分支，新增 aider / claude-code / warp-oz
- **保留**：librarian / meta-optimizer / mock / http / local fallback 不变
- **影响**：`tests/test_executor_protocol.py` 中 codex/cline 参数化用例替换为 aider/claude-code

### 3. 与 AsyncSubtaskOrchestrator 的集成

- **修改**：`_run_single_card` 外层增加 `asyncio.wait_for` timeout 守卫
- **新增**：`_run_subtask_orchestration_async` 尾部产出 `subtask_summary.md` artifact
- **影响**：现有 subtask artifact 写入逻辑不变，summary 为增量产出

### 4. 与 Consistency Audit 的集成

- **修改**：`_maybe_schedule_consistency_audit` 改为 async，通过 `asyncio.create_task` 调度
- **新增**：`_background_audit_tasks` 弱引用集合，done_callback 记录异常
- **影响**：审计触发不再依赖 daemon thread，事件循环关闭时自动 cancel

---

## 明确的非目标

- **不接入 Warp-Oz**：Oz agent 当前为付费产品，项目开发阶段不引入外部付费依赖。`CLIAgentConfig` 保留扩展位，未来可通过新增 config 快速接入
- **不引入云端 Oz**：`oz agent run-cloud --environment` 的动态参数需扩展 `CLIAgentConfig`，留待 Warp-Oz 接入时一并处理
- **不做 Planner 自动拆分**：Phase 52 不实装"从 goal 自动推断 subtask cards"——需人工/后续 phase 提供
- **不接 Meta-Optimizer complexity_hint 提案**：complexity_hint 由 operator 或未来 Planner 提供，不作为 Meta-Optimizer 自动提案类型
- **不改 HTTP 路径**：`run_http_executor_async` 已是原生 async，零改动
- **不引入云端 Oz**：`oz agent run-cloud --environment` 的动态参数需扩展 `CLIAgentConfig`，留待后续 phase
- **不做 Windows 支持**：`asyncio.create_subprocess_exec` 在 Windows 下的 `ProactorEventLoop` 兼容性不在本 phase 验证
- **不动 Librarian / Meta-Optimizer**：Phase 51 稳定边界不触碰
- **不实装 DAG 拓扑**：有依赖关系的子任务树留待后续 phase

---

## 验收条件

| Slice | 验收条件 |
|-------|---------|
| **S1** | ✓ `AsyncCLIAgentExecutor` 实装 ✓ Aider / Claude Code config 可用 ✓ Warp-Oz config 注释占位 ✓ codex/cline 相关代码全量清除 ✓ `run_prompt_executor_async` 中无 `asyncio.to_thread(run_codex_executor)` ✓ 现有 executor protocol 测试通过（参数化替换为新 agent 名）✓ `schedule_consistency_audit` 改为 `asyncio.create_task`，异常记录到 event log |
| **S2** | ✓ `TaskSemantics.complexity_hint` 字段落地并持久化 ✓ `select_route` 消费 complexity_hint 并影响候选排序 ✓ `RouteSelection.policy_inputs` 记录 complexity_hint 与 parallel_intent ✓ 单元测试覆盖 high / low / parallel / "" 四种 hint 场景 ✓ CLI `swl route select --task-id` dry-run 可打印决策过程 |
| **S3** | ✓ Aider mock binary 在 `AsyncSubtaskOrchestrator._run_level` 下可并发执行 ✓ HTTP 路径多实例并发作为辅助验证 ✓ `subtask_summary.md` artifact 产出并包含所有子任务 ref ✓ 子任务级 timeout 守卫生效（单任务超时不影响其他任务）✓ `asyncio.gather` 使用 `return_exceptions=True` 或等价机制保证局部失败不 cancel 其他任务 |

---

## 实现时间估算

| 任务 | 估算工时 |
|------|---------|
| S1 - AsyncCLIAgentExecutor + 清理 codex/cline | 18h |
| S1' - schedule_consistency_audit asyncio 迁移 | 4h |
| S2 - Strategy Router complexity_hint | 10h |
| S3 - Fan-out 集成验证 + summary artifact + timeout 守卫 | 12h |
| 测试与集成 | 14h |
| 文档更新（README / AGENTS.md / 示例） | 4h |
| **总计** | **62h** |

---

## 提交序列建议

1. `refactor(executor): introduce AsyncCLIAgentExecutor` — 新增通用 async 执行器，保留老路径
2. `feat(executor): add aider / claude-code configs` — 新执行器接入 resolver，Warp-Oz config 注释占位
3. `refactor(executor): remove codex/cline specialized paths` — 清理老路径
4. `fix(audit): migrate consistency audit scheduling to asyncio.create_task` — C2 消化
5. `feat(router): add complexity_hint driven route selection` — S2
6. `feat(orchestrator): add subtask summary artifact and timeout guard` — S3 主干
7. `test(parallel): add fan-out integration coverage with mock executors` — S3 集成测试
8. `docs(phase52): refresh examples for aider / claude-code` — 文档同步
