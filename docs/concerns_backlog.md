# Concerns Backlog

Review 过程中产出的 CONCERN 项集中追踪。每项记录来源 phase、内容、当前状态。

定期回顾（每 3-5 个 phase），清理已解决或已过时的条目。

---

## Open

| Phase | Slice | CONCERN | 消化时机 |
|-------|-------|---------|---------|
| 21 | Slice 2: acknowledge | `acknowledge_task()` 中 `route_mode="summary"` 硬编码，未来需参数化 | acknowledge 支持操作员选择 route_mode 时 |
| 25 | Slice 1: enforcement 映射表 | `canonical_write_guard` 是注入的审计标记而非 RouteCapabilities 原生字段，当前无代码检查此字段来阻止实际写入 | 引入真正的 canonical write 运行时拦截时（Phase 24 staged 路由已覆盖写入拦截） |
| 28 | Slice 3: preflight 增强 | `build_stage_promote_preflight_notices()` 返回类型从 `list[str]` 变为 `list[dict[str, str]]`，当前无外部调用者 | 如 preflight API 被外部脚本/工具使用时需注意兼容 |
| 29 | Slice 3: structured_markdown | `StructuredMarkdownDialect.format_prompt()` 与 `build_executor_prompt()` 存在信息收集逻辑重复 | 增加第 3 个及以上 dialect 时应提取公共数据收集层 |
| 32 | S3: LibrarianExecutor | `LibrarianExecutor.execute()` 直接操作 state + 多层持久化（save_state / save_knowledge_objects / append_canonical_record），偏离 Phase 31 建立的"executor 只产出 result，state mutation 归 orchestrator"原则 | 引入并发编排或 executor retry 时需将 side effect 收回 orchestrator（建议 Phase 33/34 kickoff 记录） |

## Won't Fix / By Design

| Phase | Slice | CONCERN | 理由 |
|-------|-------|---------|------|
| 22 | Slice 3: taxonomy guard | taxonomy guard 对所有 contract 生效（含 local-only） | 设计意图如此：taxonomy guard 是全局防线，不限于 remote 路径 |

## Resolved

| Phase | CONCERN | 消化 Phase | 消化方式 |
|-------|---------|-----------|---------|
| 24 | stage-promote 缺少 canonical 去重检查 | Phase 26 | Slice 1 修正 key 生成激活 supersede + Slice 2 前置检查提示 |
| 33 | `_run_subtask_orchestration` 中子任务 tempdir 会丢失 executor 额外 artifact | Phase 33 | 在 tempdir 清理前收集非标准子任务 artifact，并以 `subtask_{index}_attempt{n}_` 前缀回填到父任务 artifacts 目录 |
