---
author: claude
phase: 51
slice: context_analysis
status: draft
depends_on: ["docs/roadmap.md", "docs/plans/phase49/closeout.md", "docs/design/SELF_EVOLUTION.md", "docs/design/AGENT_TAXONOMY.md"]
---

TL;DR: Phase 51 是从"有感遥测"到"主动优化"的战略跃迁，核心差距是 Meta-Optimizer 提案应用流程缺失、一致性审计仅为手动只读入口。三个实现 commit（`5b2ebb0`、`0004a74`、`8dde2e7`）已完成结构化提案、自动审计触发策略与路由质量权重，Phase 51 已合并为 `v0.7.0+`。

## 变更范围

- **直接影响模块**:
  - `src/swallow/meta_optimizer.py` — `build_optimization_proposals()`, `OptimizationProposal`, `MetaOptimizerSnapshot`, `run_meta_optimizer()`
  - `src/swallow/consistency_audit.py` — `AuditTriggerPolicy`, `load_audit_trigger_policy()`, `save_audit_trigger_policy()`, `evaluate_audit_trigger()`, `schedule_consistency_audit()`
  - `src/swallow/router.py` — `load_route_weights()`, `save_route_weights()`, `apply_route_weights()`, `build_route_weights_report()`
  - `src/swallow/models.py` — `OptimizationProposal` dataclass（proposal_type, route_name, suggested_action, priority, rationale）

- **间接影响模块**:
  - `src/swallow/harness.py` — 自动审计触发点插入位置（执行后 fire-and-forget）
  - `src/swallow/cli.py` — `swl meta-optimize`, `swl task consistency-audit`, `swl route weights` 入口
  - `src/swallow/paths.py` — `optimization_proposals_path()` 新增路径常量

## 近期相关变更 (git history)

| Commit | 描述 | 相关模块 |
|--------|------|---------|
| 434a56c | merge: Policy Closure & Specialist Audit | Phase 51 merge |
| fc8b7d3 | docs(states): phase51 close out | 文档 |
| 8dde2e7 | feat(router): add route quality weights | `router.py` |
| 0004a74 | feat(audit): add auto consistency audit policy | `consistency_audit.py` |
| 5b2ebb0 | feat(meta-optimizer): structure optimization proposals | `meta_optimizer.py`, `models.py` |
| db7f417 | docs(phase51): initialize phase51 | 文档 |
| ec08227 | docs(design): refine design blueprint | 设计文档 |

## 关键上下文

**Phase 51 战略定位**：`SELF_EVOLUTION.md` 要求"proposal-driven self-evolution"——系统可自我观察、生成提案，但所有变更必须经过 operator gate。Phase 51 是实现这条原则的第一个完整闭环：遥测数据 → 结构化提案 → operator 审批 → 手动应用路由权重。`AGENT_TAXONOMY.md` 将 Meta-Optimizer 定义为 `specialist / cloud-backed / read-only / workflow-optimization`，Phase 51 的实现边界与此对齐（只读、提案型，不自动突变）。

**Phase 49 基线**：`LibrarianAgent`（`librarian_executor.py`）已落地为独立 Agent 实体，具备 `execute()` / `execute_async()` 接口与 `KnowledgeChangeLog` 结构化输出。这是 Phase 51 落地 Meta-Optimizer 独立 Agent 的参照模式。

**Meta-Optimizer 实现边界**：Phase 51 实现了结构化 `OptimizationProposal`（含 `proposal_type`、`priority`、`rationale`）与提案持久化（`optimization_proposals_path()`），但 Meta-Optimizer 仍以函数形式存在（`run_meta_optimizer()`），未升级为类似 `LibrarianAgent` 的独立 Agent 实体。这是 roadmap 中标注的"战略级差距"，Phase 51 完成了提案结构化，独立 Agent 生命周期留待后续。

**一致性审计触发策略**：`AuditTriggerPolicy` 支持基于 task 特征、route 质量、成本等维度的可配置触发规则，`schedule_consistency_audit()` 实现 fire-and-forget 异步触发，避免阻塞主执行路径。

**路由质量权重**：`save_route_weights()` / `apply_route_weights()` 写入独立配置文件（非 SQLite），避免引入新的"双重真相"。权重调整仍需 operator 手动执行 `swl route weights apply`，不自动变更生产路由。

**与 Phase 51-52 的耦合点**：Phase 51 的全异步执行器升级（`CLIAgentExecutor` 同步桥接层）与 Phase 51 的 `schedule_consistency_audit()` 异步触发模式共享执行上下文，需确认 Phase 51 改造不破坏已有的 fire-and-forget 语义。Phase 52 的其他 Specialist Agent 落地将复用 `LibrarianAgent` 的 Agent 实体模式，而非 Phase 51 的函数化 Meta-Optimizer 模式。

## 风险信号

- Meta-Optimizer 仍为函数化（`run_meta_optimizer()`），未落地为独立 Agent 实体——roadmap 将此列为 Phase 51 核心目标之一，但实际实现未完成该部分，Phase 52 的 Specialist Agent 生态依赖此模式，需在 Phase 51 或 Phase 52 前补齐。
- `iter_recent_task_events()` 在 SQLite-primary 环境下的实现路径需确认（`_iter_recent_task_events_file` 是否已切换到 SQLite 查询），否则 Meta-Optimizer 在 v0.7.0+ 环境下可能读不到最新事件。
- `run_consistency_audit()` 内部调用 `route_by_name()` 解析 auditor route，未知 route 静默失败——自动触发场景下此行为需有明确的错误处理或降级策略。
