---
author: claude
phase: 52
slice: risk_assessment
status: draft
depends_on:
  - docs/plans/phase52/kickoff.md
  - docs/plans/phase52/design_decision.md
  - docs/plans/phase52/context_brief.md
---

## TL;DR

Phase 52 的核心风险集中在三处：(1) codex/cline 清理的影响面（现有测试、路由注册、默认值链）比表面更深；(2) `asyncio.create_subprocess_exec` + stdout 流式读取在 CLI agent 超长输出场景下可能死锁，需显式 `communicate()` 或限流；(3) `schedule_consistency_audit` 从 daemon thread 迁移到 `asyncio.create_task` 时，task 引用管理与事件循环关闭时的 cancel 顺序需小心处理，否则会导致 audit 静默丢失。其余风险均可通过测试覆盖与 staged rollout 缓解。

---

## 风险矩阵（概率 × 影响）

| ID | 风险 | 概率 | 影响 | 等级 | 消化时机 |
|----|------|-----|-----|------|---------|
| R1 | codex/cline 清理影响面未盘全，破坏现有测试或文档链 | 高 | 中 | **高** | S1 启动前 |
| R2 | `asyncio.create_subprocess_exec` stdout 超长输出死锁 | 中 | 高 | **高** | S1 设计时 |
| R3 | `schedule_consistency_audit` asyncio 迁移丢失 task 引用 | 中 | 高 | **高** | S1' 实施时 |
| R4 | `DEFAULT_EXECUTOR` 默认值链破坏下游逻辑 | 中 | 中 | **中** | S1 实施时 |
| R5 | `AsyncCLIAgentExecutor.execute`（同步入口）的 `asyncio.run` 嵌套 | 中 | 中 | **中** | S1 实施时 |
| R6 | `complexity_hint` 与现有路由 override 优先级冲突 | 低 | 中 | **中** | S2 实施时 |
| R7 | ~~Warp-Oz binary 调用协议与假设不符~~ | — | — | **已移除** | Warp-Oz 延后接入 |
| R8 | 子任务 timeout 守卫 cancel 语义泄漏（cleanup 不完整） | 中 | 中 | **中** | S3 实施时 |
| R9 | Aider / Claude Code 工作区隔离假设（都在 cwd 下工作）导致并行冲突 | 中 | 中 | **中** | S3 设计时 |
| R10 | `asyncio.gather(return_exceptions=True)` 语义改变影响既有 retry 链路 | 低 | 高 | **中** | S3 实施时 |
| R11 | fan-out 场景下 token 成本爆炸（N 倍放大） | 中 | 低 | **低** | S3 实施时 |
| R12 | 新执行器二进制在 CI / dev 环境不可用 | 高 | 低 | **低** | 测试阶段（仅 Aider / Claude Code） |
| R13 | Windows 兼容性意外破坏 | 低 | 低 | **低** | 不处理（明确非目标） |
| R14 | `TaskSemantics` 字段新增破坏持久化向后兼容 | 低 | 中 | **低** | S2 实施时 |

---

## 高风险详解

### R1 — codex/cline 清理影响面未盘全

**描述**：codex/cline 不只存在于 `executor.py`，路由注册（`local-codex` / `local-cline`）、默认值链（`DEFAULT_EXECUTOR`）、fallback recommendations 文案、`dialect_data.py` 的 `CodexFIMDialect` 别名、测试固件、README 示例命令都可能引用。一次不全清理会留下悬空引用。

**触发场景**：
- `grep -r "codex\|cline"` 漏掉大小写变体或字符串拼接中的品牌名
- 测试 fixture 里 hard-code 路由名 `"local-codex"`，改动后测试红屏
- 用户升级后跑既有 TaskState（持久化时 `executor_name="codex"`），resolver 找不到对应 executor

**缓解**：
1. **S1 启动前先全仓盘点**（分类列表）：
   - 源码：`executor.py` / `router.py` / `dialect_data.py` / `dialect_adapters.py` / `models.py` / `orchestrator.py` 默认值
   - 测试：`tests/*.py`（codex/cline 字符串、fixture、参数化）
   - 文档：`README*.md` / `AGENTS.md` / `docs/**`
   - 配置：`.swl/` 运行时目录中可能的残留（路由权重、能力画像、提案 bundle）
2. **迁移策略**：`resolve_executor` 中对 `executor_name in {"codex", "cline"}` 先打 WARN 日志并映射到 aider（过渡一版），下一版再硬性删除
3. **数据库/持久化兼容**：为 `.swl/route_weights.json` / `.swl/route_capabilities.json` 中残留的 `local-codex` 键提供读取时忽略 + WARN 的兼容层，一次 release 后清理
4. **CI 新增 guard test**：`test_no_codex_cline_references.py` 扫描源码，遇 codex/cline 字符串即失败（白名单 changelog / deprecated comment）

**残留风险**：用户自定义脚本引用 `local-codex` 路由名，升级后静默失败。需在 CHANGELOG 中明确标注 breaking change，并在 `doctor` 命令中提示存在遗留配置。

---

### R2 — `asyncio.create_subprocess_exec` stdout 超长输出死锁

**描述**：当子进程 stdout/stderr 写入量超过 PIPE buffer（通常 64KB）且主进程未及时读取时，子进程会阻塞 write，进而导致 `await proc.wait()` 永久等待。这是 Python asyncio subprocess 的经典坑。

**触发场景**：
- Aider 修改大文件时打印整个 diff（可能数 MB）
- Claude Code 的 `--print` 模式输出完整会话记录
- Warp-Oz 的 streaming 输出在 debug 模式下冗长

**缓解**：
1. **不用 `stdout=PIPE + proc.wait()` 模式**，改用 `proc.communicate()`：它会并发读取 stdout/stderr 到 memory，避免 PIPE 阻塞
2. **结合 `asyncio.wait_for` 实现 timeout**：
   ```python
   try:
       stdout_bytes, stderr_bytes = await asyncio.wait_for(
           proc.communicate(), timeout=timeout_seconds
       )
   except asyncio.TimeoutError:
       proc.kill()
       await proc.wait()
       # 记录 timeout failure
   ```
3. **输出量上限守卫**：`communicate()` 返回后检查 `len(stdout_bytes)`，超过阈值（默认 10MB）时截断并标注 `failure_kind="output_too_large"`
4. **单元测试**：用 mock 子进程模拟超长输出（写 1MB 到 stdout），验证不死锁 + timeout 正确触发

**残留风险**：`communicate()` 把所有输出加载到内存，极端情况下可能 OOM（如意外循环输出）。通过输出量上限 + timeout 双重守卫缓解。

---

### R3 — `schedule_consistency_audit` asyncio 迁移丢失 task 引用

**描述**：`asyncio.create_task(coro)` 返回的 task 如果没有被任何地方引用，事件循环可能在 GC 时 cancel 该 task（Python 3.11+ 引入的行为警告）。fire-and-forget 语义下，如果直接 `asyncio.create_task(...)` 不存引用，audit 可能在高负载下被 cancel 静默丢失。

**触发场景**：
- `_maybe_schedule_consistency_audit` 调用 `asyncio.create_task(coro)` 后立即返回
- Python 垃圾回收触发，task 引用仅剩事件循环内部弱引用
- 事件循环 OOM 压力下优先 GC 弱引用，task 被 cancel，audit 无产物且无日志

**缓解**：
1. **弱引用集合**模式（模块级）：
   ```python
   _background_audit_tasks: set[asyncio.Task] = set()

   def _schedule_audit_task(coro):
       task = asyncio.create_task(coro)
       _background_audit_tasks.add(task)
       task.add_done_callback(_background_audit_tasks.discard)
       task.add_done_callback(_log_audit_task_result)
   ```
2. **异常捕获**：`_log_audit_task_result(task)` 内部 `try: task.result() except Exception: write event log(...)`，避免异常沉默
3. **事件循环关闭保护**：`run_task_async` 的 outermost `try/finally` 中，在 return 前 `await asyncio.gather(*_background_audit_tasks, return_exceptions=True)` 等待所有 in-flight audit 完成（或短 timeout 后放弃并记录）
4. **单元测试**：人为 trigger GC 后验证 task 仍完成；验证异常被写入 event log

**残留风险**：若 audit 任务本身耗时极长（>1 min），阻塞 `run_task_async` 收尾。可通过 `asyncio.wait_for` 的短 timeout（如 5s）兜底，超时后 detach 并记录 WARN。

---

## 中风险详解

### R4 — `DEFAULT_EXECUTOR` 默认值链

**描述**：`dialect_data.py` 中 `DEFAULT_EXECUTOR` 如果当前是 `"codex"`，改为 `"aider"` 会传导到 `TaskState.executor_name` 默认值、`route_for_executor` fallback、CLI 命令默认参数等多处。

**缓解**：
- 先定位 `DEFAULT_EXECUTOR` 的所有引用（Grep `DEFAULT_EXECUTOR`）
- 将默认改为 `"http"`（已是原生 async）或 `"local"`（summary fallback）更保守——避免在 CI 无 aider binary 时全量失败
- `route_for_executor` 在 executor 未知时已有 `local-codex` fallback，需改为 `local-summary` 或类似不依赖外部 binary 的 mock 路由

---

### R5 — `AsyncCLIAgentExecutor.execute`（同步入口）的 `asyncio.run` 嵌套

**描述**：`AsyncCLIAgentExecutor.execute()` 同步版本若用 `asyncio.run(self.execute_async(...))`，在已经有事件循环的上下文（如测试、CLI）被调用会抛 `RuntimeError: asyncio.run() cannot be called from a running event loop`。

**缓解**：
- 优先让调用方始终走 `execute_async` 路径（`_run_orchestrator_sync` 已用 `asyncio.run` 包装顶层）
- 若必须提供 `execute` 同步入口，用 `asyncio.get_event_loop().run_until_complete(...)`（已废弃但仍可用）或 `asyncio.new_event_loop()` + `run_until_complete`
- 更稳妥：`execute` 方法直接 `raise NotImplementedError("AsyncCLIAgentExecutor only supports execute_async")`，强制调用方使用 async 路径
- 验证：`test_executor_protocol.py` 对 async executor 的同步调用用 `asyncio.run` 而非调用 `.execute()`

---

### R6 — `complexity_hint` 与现有路由 override 优先级冲突

**描述**：`select_route` 中 `executor_override` / `route_mode_override` 已是最高优先级，complexity_hint 若插入位置不当，会覆盖用户显式 override 或被 mode 阻塞。

**缓解**：
- 优先级明确：`executor_override > route_mode ≠ auto > complexity_hint > task_family_score > quality_weight`
- 显式测试：`test_router.py` 增加用例覆盖 `executor_override="http" + complexity_hint="high"` → 仍用 http
- `RouteSelection.policy_inputs` 记录所有输入变量，便于事后审计

---

### R7 — ~~Warp-Oz binary 调用协议与假设不符~~

**已移除**：Warp-Oz 因付费依赖延后接入，Phase 52 不落地 Oz 执行器。`CLIAgentConfig` 保留注释占位，未来接入时需重新评估此风险。

---

### R8 — 子任务 timeout 守卫 cancel 语义泄漏

**描述**：`asyncio.wait_for(_run_single_card(...), timeout=T)` 超时后会 cancel inner task。inner task 中的 subprocess 可能未完成 cleanup（进程仍在跑、临时文件未清理），导致：
- 孤儿进程持续消耗资源
- 临时目录未清理堆积
- 审计 artifact 写了一半

**缓解**：
- `_run_single_card` 内部用 `try/finally`：catch `asyncio.CancelledError`，`finally` 块中 kill subprocess + 清理 tempdir
- `asyncio.create_subprocess_exec` 返回的 proc 对象在 CancelledError 时调用 `proc.kill()` + `await proc.wait()`
- tempdir 使用 `contextlib.AsyncExitStack` 或 `with tempfile.TemporaryDirectory()`（已是），CancelledError 会触发 `__exit__` 清理
- 集成测试：`asyncio.wait_for(..., timeout=0.01)` 触发 cancel，验证 (a) no orphan process via `psutil.Process().children()`，(b) tempdir 不存在

---

### R9 — Aider / Claude Code 工作区隔离假设

**描述**：Aider 默认在 cwd 上工作，Claude Code 也依赖 cwd。fan-out 并行时，多个子任务若共享同一 workspace_root，会产生文件锁、git index 冲突、覆盖写同一文件。

**缓解**：
- 每个 subtask 的 `workspace_root` 独立（`tempfile.TemporaryDirectory()` 已在 `_run_subtask_orchestration_async:2059` 使用）
- 若 subtask 需要访问 parent workspace，通过 read-only copy / git worktree 隔离（本 phase 不做，作为约束记录）
- `CLIAgentConfig.workspace_root_flags` 机制保留：Aider 支持 `--subtree-only` 或类似，Claude Code 支持 `--cwd`（需验证）
- **验收边界**：Phase 52 验收场景限定为"每个 subtask 独立 workspace_root"，跨 subtask 共享 workspace 的并行场景标记为后续 phase 风险

---

### R10 — `asyncio.gather(return_exceptions=True)` 语义变化

**描述**：现有 `AsyncSubtaskOrchestrator._run_level` 使用 `asyncio.gather(*(run_card(card) for card in level))`，**未指定 `return_exceptions=True`**。一个子任务异常会导致 gather 抛异常并 cancel 其他任务。若 S3 改为 `return_exceptions=True`，结果类型从 `list[SubtaskRunRecord]` 变为 `list[SubtaskRunRecord | BaseException]`，下游 `zip(level, gathered_records)` 的逻辑需适配。

**缓解**：
- `_run_single_card` 内部已有 `try/except Exception` 捕获，返回 `SubtaskRunRecord(status="failed")`——原则上 gather 不会抛
- 仍建议显式 `return_exceptions=True` + 处理 `isinstance(rec, BaseException)` 的 defensive 分支
- 回归测试：人为注入 CancelledError / KeyboardInterrupt，验证其他子任务完成

---

## 低风险

### R11 — fan-out token 成本爆炸

**描述**：4 个 Warp-Oz 实例并发，每个独立消费 token，总成本 ~4x。现有 `token_cost_limit` 可能是 per-task 而非 fan-out 总和。

**缓解**：现有 `TaskCard.token_cost_limit` 是 per-card，Phase 52 无需改变。后续可叠加 fan-out 级别预算。

---

### R12 — 新执行器二进制在 CI / dev 不可用

**描述**：CI 环境不会装 Aider / Claude Code / Oz，会导致集成测试失败。

**缓解**：所有集成测试用 mock binary（`tests/fixtures/bin/` 下的 fake executable）或跳过标记 `@pytest.mark.requires_real_binary`。

---

### R13 — Windows 兼容性

**描述**：`asyncio.create_subprocess_exec` 在 Windows 需要 `ProactorEventLoop`，默认的 `SelectorEventLoop` 不支持。

**处理**：**明确非目标**。README 标注 Linux/macOS only，CI 不跑 Windows。

---

### R14 — `TaskSemantics` 字段扩展向后兼容

**描述**：`TaskSemantics` 增加 `complexity_hint` 字段后，旧 TaskState 反序列化可能缺失此字段。

**缓解**：`TaskSemantics.from_dict` 使用 `data.get("complexity_hint", "")` 兜底；`asdict` 默认产出完整字段；现有 `to_dict` 机制已兼容。

---

## 回归风险监控

| 区域 | 监控指标 | 回归信号 |
|------|---------|---------|
| Executor resolver | `test_executor_protocol.py` 全套 | codex/cline 仍被解析 → 清理不彻底 |
| Router | `test_router.py` 路由决策用例 | complexity_hint 场景未生效 |
| Subtask orchestration | `test_subtask_orchestrator.py` 的 fan-out 场景 | 并发数骤降 / summary artifact 缺失 |
| Consistency audit | `test_consistency_audit.py` + event log 检查 | audit 未触发 / threading 残留 |
| 端到端 | 全量 pytest | >5 个 failure → S1 清理未完整 |

---

## 缓解时间线

| Phase | 时间点 | 必须完成的缓解 |
|-------|--------|---------------|
| S1 启动前 | Day 1 | R1 全仓盘点 + R2 subprocess 死锁方案确认 |
| S1 实施 | Day 2-5 | R2 / R4 / R5 落地 |
| S1' 紧随 | Day 5-6 | R3 audit 迁移 + 测试 |
| S2 实施 | Day 7-8 | R6 优先级测试 |
| S3 启动前 | Day 9 | R9 workspace 边界确认 |
| S3 实施 | Day 9-12 | R8 / R10 落地 |
| 测试闭合 | Day 13-14 | 全量回归 + R11 / R12 验证 |

---

## 风险吸收判断

**可以接受的风险**：
- R11（成本放大）：已有 per-card 预算机制兜底
- R12（CI binary 不可用）：mock binary 方案成熟
- R13（Windows）：明确非目标，无需吸收
- R14（字段向后兼容）：`from_dict` 兜底机制简单可靠

**必须在 kickoff 前获得确认的事项**：
- R1：codex/cline 清理策略——直接删除（已在 design_decision 决策 2 选择直接删除，operator 已确认）
- R9：fan-out workspace 隔离策略——每个 subtask 独立 tempdir（已有），跨 subtask 共享 workspace 不在本 phase 范围

**Phase 52 整体风险评级：中**

- 三个高风险均有成熟缓解路径（R7 已移除）
- 工作量比 Phase 51 略小（62h vs 86h）
- 影响面清晰，变更集中在 executor 层
- 可 staged rollout（S1 → S1' → S2 → S3），每步独立可 revert
