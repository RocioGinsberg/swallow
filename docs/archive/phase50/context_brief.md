---
author: claude
phase: 50
slice: context-analysis
status: draft
depends_on: ["docs/roadmap.md", "docs/plans/phase49/closeout.md"]
---

TL;DR: Phase 50 的三个目标模块（Meta-Optimizer、ConsistencyAudit、RouteRegistry）均已有基础实现，但彼此孤立——缺少将审计质量信号反哺路由权重的集成层。所有近期 commit 均为文档，代码无变更，可直接在 main 上切分支开始。

## 变更范围

**直接影响模块**：
- `src/swallow/meta_optimizer.py` — `build_optimization_proposals()`, `run_meta_optimizer()`, `MetaOptimizerSnapshot`
- `src/swallow/consistency_audit.py` — `run_consistency_audit()`, `ConsistencyAuditResult`
- `src/swallow/router.py` — `RouteRegistry`, `select_route()`, `candidate_routes()`
- `src/swallow/models.py` — 可能需要新增 route weight / audit verdict 数据结构

**间接影响模块**：
- `src/swallow/store.py` — `iter_recent_task_events()` 是 Meta-Optimizer 的数据源，schema 变更会影响提案质量
- `src/swallow/harness.py` — 如果一致性审计需要自动触发，需要在 harness 执行后插入触发点
- `src/swallow/cli.py` — 新的 CLI 入口（`swl audit auto-trigger`, `swl route weights`）

## 近期相关变更 (git history)

| Commit | 描述 | 相关模块 |
|--------|------|---------|
| da8ba56 | docs(agents): move out gemini from workflow | 文档 |
| f901113 | docs(design): update new design introduce files | 文档 |
| ca3ea43 | feat(retrieval): add sqlite-vec fallback pipeline | Phase 49 最后实现 commit |
| 4c0364d | feat(knowledge): introduce librarian agent boundary | Phase 49 |
| 08cc7cf | feat(knowledge): add sqlite knowledge migration | Phase 49 |
| 1bc523b | feat(knowledge): add sqlite-backed knowledge store | Phase 49 |

近 15 条 commit 全为文档或 Phase 49 实现，无 Phase 50 相关代码变更。

## 关键上下文

**Meta-Optimizer 现状**：
- `build_optimization_proposals()` 产出纯文本启发式建议，无结构化 verdict
- 提案写入 artifact 文件，不写回任何可被路由器消费的状态
- `workflow_optimization_proposal` 在 roadmap 中提及但代码中未实现

**ConsistencyAudit 现状**：
- 只能手动调用（CLI `swl task consistency-audit <task-id>`）
- 审计结论（pass/fail/risk_level）未结构化捕获，只写入 markdown artifact
- `ConsistencyAuditResult.status` 字段存在但仅用于错误处理，不传递给路由层

**RouteRegistry 现状**：
- 路由权重完全静态，`RouteSpec` 无 weight 字段
- `candidate_routes()` 匹配策略确定性，无概率加权
- fallback chain 硬编码在 route spec 中，无动态调整

**隐含耦合**：
- Meta-Optimizer 依赖 `iter_recent_task_events()` 的文件 mtime 排序，SQLite 路径下行为需确认
- `run_consistency_audit()` 内部调用 `route_by_name()` 解析 auditor route，未知 route 静默失败
- 如果在 harness 中插入自动审计触发，需要避免阻塞主执行路径（应为 async 或 fire-and-forget）

## 风险信号

- `iter_recent_task_events()` 在 SQLite 模式下的实现路径（`_iter_recent_task_events_file` 仍走文件）需确认是否已切换到 SQLite 查询，否则 Meta-Optimizer 在 SQLite-primary 环境下读不到最新事件
- route weight 持久化位置未定：写入 SQLite 还是独立配置文件？需在 design 阶段明确，避免引入新的"双重真相"
