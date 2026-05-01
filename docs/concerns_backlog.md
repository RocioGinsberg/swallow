# Concerns Backlog

> **Document discipline**
> Owner: Human
> Updater: Claude / Codex
> Trigger: review 产出新的 CONCERN、triage 结果变化、已记录 concern 状态变化
> Anti-scope: 不维护 phase 实现历史、不替代 review_comments.md、不记录与 review 无关的临时想法

Review 过程中产出的 CONCERN 项集中追踪。每项记录来源 phase、内容、当前状态。

定期回顾（每 3-5 个 phase），清理已解决或已过时的条目。

最近一次 triage：2026-05-01（R-entry / backlog hygiene）。结论：当前没有必须在进入真实使用测试前修复的 blocker。原 Open 长表已按 roadmap 候选分组；已映射到 `docs/roadmap.md` 的项目不再作为逐条 Open 膨胀，只在对应候选启动时回读本文件。

Backlog hygiene:

- **Active Open** 只保留：未被 roadmap 覆盖、需要 R 阶段真实样本触发、或需要短期人工决策的 concern。
- **Roadmap-bound** 表示：问题仍存在，但已并入某个候选 phase 的消化范围；不再在 Open 表里逐条滚动。
- **Resolved** 只收录：能从代码、测试、closeout 或 release docs 中确认已经消化的 concern。

---

## R-entry Triage

| 分类 | Concern | 进入真实使用测试前结论 |
|------|---------|------------------------|
| No-go blocker | 无 | 可以进入 R 阶段；不需要新增 bugfix phase |
| 已处理 | subtask timeout wall-clock flaky test | 已移除 brittle elapsed-time 断言，保留 artifact / event / final state 行为断言；full pytest 已通过 |
| 设计-实现复核 | INVARIANTS / ARCHITECTURE / DATA_MODEL / KNOWLEDGE 等设计文档 vs 当前代码 | §0/§5/§7/§9、P2、P3、Path A/B/C、`apply_proposal`、`RawMaterialStore` 均有实现锚点与守卫测试支撑；focused readiness tests `51 passed`, Phase 65 SQLite governance tests `21 passed` |
| R 阶段观察 | conversation primary path 极低概率 tie-break / false fail verdict / generic_chat_json auto-detect / canonical `librarian_side_effect` §5 drift / review artifact outside SQLite transaction | 真实样本中若复现再单独开 bugfix 或 governance slice；不作为进入测试前 blocker |
| 使用边界 | full migration runner deferred / durable proposal artifact lifecycle / object-storage backend absent | R 阶段默认 fresh v1.5 workspace 或现有 v1 backfill；不要把 schema v2 upgrade、跨进程 durable proposal restore、真实 S3/MinIO/OSS backend 当作本轮入口条件 |
| 后续设计债 | Phase 66 design-needed bundle、event backfill、guard strength、audit payload size policy、runtime defaults / taxonomy constants 等 | 已映射到 roadmap 候选 AA/AB/U/W/X/Y/Z；不在实际使用测试前抢修 |

---

## Active Open

| Group | Included Concerns | Current Decision | Next Trigger |
|-------|-------------------|------------------|--------------|
| R-observation quality edge cases | Phase 45 primary path tie-break; Phase 50 false fail verdict keyword scan; Phase 58 `generic_chat_json` / Open WebUI flat-list auto-detect | 低概率或低影响;不作为 R-entry blocker,也不预先开专项 phase | R 阶段真实样本或 eval 显示 precision / verdict / import 质量下降时,开 bugfix 或并入候选 U/Y |
| Provider Router Split (LTO-7) follow-up | (1) `test_route_metadata_writes_only_via_apply_proposal` allowlist still names `provider_router/router.py` only — the actual `save_route_*` writers now live in `route_metadata_store.py`. Guard currently passes due to AST-name semantics, but the allowlist is misaligned with the new module topology. (2) `router.py` reaches into `_`-prefixed names in `route_policy.py` / `route_registry.py` (`_apply_route_policy_payload`, `_normalize_task_family_scores`, `_normalize_unsupported_task_types`, `_routes_from_registry_payload`). (3) `_BUILTIN_ROUTE_FALLBACKS` still lives in `router.py` despite the registry being owned by `route_registry.py`. | (1) **Should fix in LTO-9 (Surface / CLI / Meta Optimizer split)** rather than waiting for LTO-10 — LTO-9 will touch `tests/test_invariant_guards.py` for CLI/surface guards and is a natural carrier. (2)/(3) hygiene-only, can be picked up on touched-surface basis. | (1) opened ticket at LTO-9 entry; (2)/(3) when next change touches `router.py` / `route_policy.py` / `route_registry.py` |
| Orchestration Lifecycle Decomposition (LTO-8) follow-up | (1) `execution_attempts.debate_loop_core` and `debate_loop_core_async` accept 9 callable parameters including `record_round` / `record_exhausted` / `persist_exhausted` / `apply_feedback` / `store_feedback`. The helper holds loop termination control (DEBATE_MAX_ROUNDS=3) and decides *when* the orchestrator-injected callables fire. Callables are append-only telemetry not state-advancement, so `INVARIANTS.md "Control only in Orchestrator / Operator"` is technically respected, but the structural pattern is the close cousin of the `save_state` closure-injection prohibition the audit added in C-2. Future readers may misread this as license for helpers to hold control of state-touching callbacks. (2) `orchestrator.py` reduction in LTO-8 Step 1 is conservative (3853 → 3331 lines, ~14%; cf LTO-7's ~81%). LTO-8 is intentionally multi-step. The roadmap LTO-8 row should read "Step 1 done", not "fully done", to keep further extraction (more orchestrator reduction; eventual harness.py decomposition) visible. | (1) Design follow-up: either (a) split debate loop into pure orchestrator-side controller plus helper-side next-state computer, or (b) document explicitly that `record_*` callables in `debate_loop_core` must be telemetry-only and the loop's termination decision is mechanical. Defer to LTO-11 (Planner / DAG / Strategy Router) where loop control patterns are first-class. (2) Roadmap-bound — ensure post-merge roadmap update reflects partial completion. | (1) revisit at LTO-11; (2) post-LTO-8-Step-1 roadmap update |

## Roadmap-Bound

这些 concern 仍存在,但已经并入 `docs/roadmap.md` 的候选 phase,不再作为逐条 Open 滚动。

| Target | Included Concerns | 消化方式 |
|--------|-------------------|----------|
| 候选 AA: Test Architecture / TDD Harness | Phase 64 chat-completion guard indirect URL binding gap | 在 guard / AST helper 分层中提升守卫表达力,不弱化现有 §9 guard |
| 候选 AB: Interface / Application Boundary Clarification | Phase 63 `events` / `event_log` historical backfill; Phase 65 full migration runner deferred | 进入 application / persistence 边界整理时,定义 migration runner、event cutoff/backfill 策略 |
| 候选 U: Neural Retrieval Observability / Eval / Index Hardening | Phase 49 `_sqlite_vec_warning_emitted`; Phase 57 embedding dimension import-time freeze; Phase 66 retrieval source policy ownership | 借 RAG observability / eval hardening 统一处理 vector fallback 可见性、embedding config 与 source policy ownership |
| 候选 W: Provider Router API Split | Phase 66 runtime provider / executor defaults | Router split 时定义 defaults owner: runtime config / route metadata / route policy / executor-registry-adjacent runtime data |
| 候选 X: Orchestration Facade Decomposition | Phase 63 vestigial `staged_candidate_count`; Phase 66 sync/async orchestration duplication; Phase 66 artifact-name registry / owner table; Phase 66 policy-result report/event pipeline; Phase 66 taxonomy / authority / capability constants touchpoints | 主链路拆分时处理 event payload deprecated 字段、artifact writer ownership、policy result protocol 与 shared constants |
| 候选 Y: Surface Command / Meta Optimizer Module Split | Phase 50 markdown reverse-parse route weight proposals; Phase 61/63 durable proposal artifact lifecycle; Phase 66 table-driven CLI dispatch | CLI / Meta Optimizer 拆分时把 proposal JSON artifact、durable lifecycle、parser/dispatch 对齐作为同一 surface/proposal cleanup |
| 候选 Z: Governance Apply Handler Split | Phase 61/63 `librarian_side_effect` vs INVARIANTS §5 drift; Phase 63 `_apply_route_review_metadata` length; Phase 65 review application artifact outside SQLite transaction; Phase 65 audit snapshot size policy; Phase 66 SQLite transaction envelope helper | 保持 `apply_proposal` 唯一入口,拆私有 handler 时一起处理 canonical side-effect token、route review reconciliation、outbox/stale marker、snapshot size policy 与 tx helper |

## Won't Fix / By Design

| Phase | Slice | CONCERN | 理由 |
|-------|-------|---------|------|
| 22 | Slice 3: taxonomy guard | taxonomy guard 对所有 contract 生效（含 local-only） | 设计意图如此：taxonomy guard 是全局防线，不限于 remote 路径 |
| 28 | Slice 3: preflight 增强 | `build_stage_promote_preflight_notices()` 返回类型从 `list[str]` 变为 `list[dict[str, str]]`，当前无外部调用者 | 返回类型已稳定，docstring 已明确记录设计意图，无兼容性问题 |

## Resolved

| Phase | CONCERN | 消化 Phase | 消化方式 |
|-------|---------|-----------|---------|
| 66 | high audit finding: dead `run_consensus_review(...)` wrapper | Phase 67 M1 | Removed the sync wrapper from `review_gate.py`; `run_review_gate(...)` remains the public sync entry and delegates to `run_consensus_review_async(...)` when reviewer routes are configured |
| 66 | audit_index quick-win bundle: `_pricing_for(...)`, eval-only local embedding ranker, SQLite timeouts, MPS policy choices, retrieval preview/scoring limits, and orchestration/executor timeout defaults | Phase 67 M1 | Removed the module-level cost-estimation helper, annotated the eval-only embedding ranker, named SQLite and executor timeout constants, consumed `MPS_POLICY_KINDS` from its owner with deterministic sorting, named retrieval scoring/preview limits, and documented reviewer-timeout ownership where direct imports would couple modules |
| 66 | high audit finding: JSON/JSONL IO helper ownership | Phase 67 M2 | Added `src/swallow/_io_helpers.py`, removed CLI-private JSON helpers, and moved audited JSON / JSONL read patterns to explicit helper variants. Implementation preserved stricter source behavior where the design text assumed malformed-line skip by adding `read_json_lines_strict_or_empty(...)`; CLI retrieval list reads use `read_json_list_or_empty(...)` to preserve `retrieval.json` payload shape |
| 59 | tag-level release docs sync debt | v1.5.0 release docs | README release snapshot was refreshed to `v1.5.0`; `current_state.md` and `docs/active_context.md` now track the executed `v1.5.0` tag and R-entry checkpoint. `AGENTS.md` remains coordination-only and no longer carries release snapshot state |
| 49 | CLI operator canonical promotion 的 authority 语义仍未完全统一：`knowledge stage-promote` 的 Wiki 写入已使用 `OPERATOR_CANONICAL_WRITE_AUTHORITY`，但 `task knowledge-promote --target canonical` 仍通过 `LIBRARIAN_MEMORY_AUTHORITY` 进入 decision 层，审计时仍可能混淆 operator 手动 promotion 与 LibrarianAgent 自动 promotion | Phase 61 | M3 将 `task knowledge-promote --target canonical` 的 CLI decision-level `caller_authority` 改为 `operator-gated`，decision 层同时允许 Librarian `canonical-promotion` 与 Operator `operator-gated`，canonical 主写入仍通过 `apply_proposal(OperatorToken(source="cli"), target=CANONICAL_KNOWLEDGE)` |
| Meta Docs Sync | INVARIANTS §0 第 4 条以及 ARCHITECTURE / STATE_AND_TRUTH / EXECUTOR_REGISTRY / INTERACTION 等 7+ 处把 `apply_proposal()` 定义为 canonical / route / policy 写入唯一入口，§9 守卫测试集列出 `test_canonical_write_only_via_apply_proposal` / `test_only_apply_proposal_calls_private_writers` / `test_route_metadata_writes_only_via_apply_proposal` 三条，但 `grep -rn "apply_proposal" src/ tests/` 零匹配，实际 canonical / route / policy 写入由 CLI 子命令直接调底层 store，设计文档与代码出现宪法级漂移 | Phase 61 | 实装 `swallow.governance.apply_proposal()` 三参数入口,收敛 canonical knowledge / route metadata / policy 三类主写入路径,补齐 3 条 INVARIANTS §9 apply_proposal 守卫测试,并通过全量 pytest 与 Meta-Optimizer eval 验证 |
| 61 | Repository 抽象层未实装 + duplicate proposal overwrite | Phase 63 | 新增 `swallow.truth.{knowledge,route,policy}` Repository 骨架与私有写方法,`governance.apply_proposal` 经 Repository 调用 canonical / route / policy 写入;新增 `PendingProposalRepo` 与 `DuplicateProposalError`,重复 `(target, proposal_id)` register 不再静默覆盖;补 2 条 Repository bypass 守卫 |
| 62 | `orchestrator.py` stagedK 直写 | Phase 63 | M0 audit 确认 `_route_knowledge_to_staged` 生产 0 触发;Phase 63 删除 dead code 与 Orchestrator `submit_staged_candidate` 调用点,保留 CLI Operator 与 ingestion Specialist 合规路径 |
| 62 | INVARIANTS §7 集中化函数缺失 | Phase 63 | 新增 `swallow.identity.local_actor()` 与 `swallow.workspace.resolve_path()`,生产路径绝对化改走集中化 helper,新增并启用 `test_no_hardcoded_local_actor_outside_identity_module` / `test_no_absolute_path_in_truth_writes` |
| 61 | §9 剩余 2 条 G.5 守卫测试 skip 占位 | Phase 64 | 启用并修复 `test_path_b_does_not_call_provider_router` 与 `test_specialist_internal_llm_calls_go_through_router`;前者通过 Orchestrator 预解析 fallback chain + Executor 只读 `lookup_route_by_name` 收口 Path B selection 边界,后者通过 `router.invoke_completion` + `_http_helpers.py` 收口 Specialist internal chat-completion gateway |
| 61 | `apply_proposal` route metadata writes lacked transactional rollback: `save_route_weights → apply_route_weights → save_route_capability_profiles → apply_route_capability_profiles` could leave SQLite/files and in-memory route state partially updated after mid-sequence failure | Phase 65 | Route/policy truth moved to SQLite; `RouteRepo._apply_metadata_change` and `PolicyRepo._apply_policy_change` now use explicit `BEGIN IMMEDIATE` transactions; route rollback redoes in-memory route registry state from SQLite; `tests/test_phase65_sqlite_truth.py` covers route/policy failure injection windows plus audit rollback |
| 24 | stage-promote 缺少 canonical 去重检查 | Phase 26 | Slice 1 修正 key 生成激活 supersede + Slice 2 前置检查提示 |
| 29 | `StructuredMarkdownDialect.format_prompt()` 与 `build_executor_prompt()` 存在信息收集逻辑重复 | Phase 35 | 新增 `dialect_data.py` 抽取共享 prompt 数据采集层，由 `build_executor_prompt()`、`StructuredMarkdownDialect`、`ClaudeXMLDialect`、`CodexFIMDialect` 统一复用 |
| 35 | `harness.py` / `orchestrator.py` 中 `degraded` 标志基于 `"fallback route" in route_reason` 字符串匹配，措辞变更会导致误判 | Phase 35 | 新增 `TaskState.route_is_fallback` 显式字段，fallback 应用时置位，telemetry 改为直接消费布尔状态 |
| 35 | `meta_optimizer.py` 硬编码 `"executor.completed"` 等事件类型字符串，与 harness/orchestrator 无编译级绑定 | Phase 35 | 在 `models.py` 抽取共享事件类型常量，由 `meta_optimizer.py`、`harness.py`、`orchestrator.py` 与相关测试统一引用 |
| 33 | `_run_subtask_orchestration` 中子任务 tempdir 会丢失 executor 额外 artifact | Phase 33 | 在 tempdir 清理前收集非标准子任务 artifact，并以 `subtask_{index}_attempt{n}_` 前缀回填到父任务 artifacts 目录 |
| 34 | `create_task()` 中 `_apply_route_spec_to_state()` 先写 `executor_name` 后被立即覆盖，语义不清晰 | Phase 34 | 改为 `_apply_route_spec_to_state(..., update_executor_name=False)`，保留行为同时消除无意义覆盖 |
| 32 | `LibrarianExecutor.execute()` 直接操作 state + 多层持久化，偏离 Phase 31 原则 | Phase 36 | S1: execute() 改为返回 side_effects dict，orchestrator 通过 `_apply_librarian_side_effects()` 接管全部持久化 |
| 21 | `acknowledge_task()` 中 `route_mode="summary"` 硬编码 | Phase 36 | S2a: 新增 keyword-only `route_mode` 参数，默认 "summary" 保持兼容 |
| 25 | `canonical_write_guard` 无运行时执行 | Phase 36 | S2b: 新增 `_append_canonical_write_guard_warning()` 在非 Librarian 路径触发 audit warning event |
| 34 | `CodexFIMDialect.format_prompt()` 未转义 FIM 标记 | Phase 36 | S2d: 新增 `_escape_fim_markers()` 对 task_id/title/goal/raw_prompt 转义 |
| 37 | Web API `/api/tasks/{id}/artifacts/{name:path}` 缺少对 `..` 的显式入口校验 | Phase 37 | review follow-up: `build_task_artifact_payload()` 新增 parent-segment 显式校验，FastAPI route 对非法名称返回 400 |
| 37 | `_filter_task_states()` 的 `needs-review` / `all` focus 缺少直接测试覆盖 | Phase 37 | review follow-up: `tests/test_web_api.py` 新增 `needs-review` 与 `all` filter 断言 |
| 36 | `_apply_librarian_side_effects()` 中 save_state → index 重建为顺序执行，中间步骤失败会导致 state 与 index 不一致 | Phase 41 | S1 将 `state / knowledge_objects / evidence/wiki entries / knowledge_partition / knowledge_index / canonical_registry_index / canonical_reuse_policy` 纳入同一批次原子提交，失败时 rollback 到旧文件状态 |
| 40 | `_run_single_task_with_debate()` 与 `_run_subtask_debate_retries()` 核心循环结构近似重复（~170 行），修改 debate 策略需同步两处 | Phase 41 | S2 提取共享 `_debate_loop_core()` 与 `_build_debate_last_feedback()`，统一单任务 / 子任务的 round 管理、feedback 生成与 breaker 判定 |
| 38 | `EVENT_TASK_EXECUTION_FALLBACK` 的 `token_cost` 未计入 Meta-Optimizer route stats 的 `total_cost` / `cost_samples`，fallback 执行成本被遗漏 | Phase 42 | S2 在 `EVENT_TASK_EXECUTION_FALLBACK` 分支中将 `token_cost` 回计到 `previous_route.total_cost` / `cost_samples` |
| 40 | debate 轮次的 executor 事件仍以 `executor.completed` 记录，Meta-Optimizer route health 聚合会将 retry 与正常执行混在一起，膨胀请求计数和失败率 | Phase 42 | S3 新增 `debate_retry_count`，并将带 `review_feedback` 的 executor 事件从 route health / failure fingerprint 计数中隔离，同时保留成本与延迟统计 |
| 48 | `run_task()` 在已有事件循环的上下文中抛出的 RuntimeError 提示不够明确 | Phase 48 | `_run_orchestrator_sync()` 改为显式提示在 FastAPI / notebook / async test 等 async 调用方中应 `await run_task_async(...)` |
| 48 | `DefaultTaskStore.iter_recent_task_events` 在双存储过渡期放大 file store 的 `last_n` 参数，可能扫描大量镜像 JSON 文件 | Phase 48 | recent-events 合并逻辑改为只读取 file-only task 的事件文件，并由 `swl doctor sqlite` 输出迁移建议 |
| 48 | `SqliteTaskStore._checkpoint()` 对每次写入执行 `wal_checkpoint(TRUNCATE)`，高频场景下过重 | Phase 48 | checkpoint 模式改为 `wal_checkpoint(PASSIVE)`，保留只读 Web API 零写入保护，同时降低写入后整理成本 |
| 48 | `_execute_task_card is _ORIGINAL_EXECUTE_TASK_CARD` patch 检测逻辑将测试细节泄漏到生产代码 | Phase 48 | `run_task_async()` 多 card 路径统一走 `_run_subtask_orchestration_async()`，删除 patch 感知分支 |
| 51 | `MetaOptimizerSnapshot` 缺少 `route_task_family_stats`，导致 capability proposal 的依据无法从 snapshot 重建 | Phase 51 | review follow-up: `MetaOptimizerSnapshot` 新增 `route_task_family_stats` 字段，并写入 report / agent payload |
| 51 | `apply_reviewed_optimization_proposals()` 中 `apply_route_weights()` 同时承担“读取当前权重”和“应用到注册表”两种语义 | Phase 51 | review follow-up: 改为显式 `load_route_weights()` 读取当前持久化状态，仅在写入完成后调用一次 `apply_route_weights()` |
| 51 | 设计文档以 `asyncio.create_task` 描述 fire-and-forget 审计触发，当前实现为 `threading.Thread` | Phase 52 | `schedule_consistency_audit` 改为 async 路径，`_maybe_schedule_consistency_audit` 使用 `asyncio.create_task` + background task set 收口 |
| 52 | `codex_fim` 仍是稳定 dialect key，且 `dialect_adapters/codex_fim.py`、部分历史 telemetry / fixture 继续保留 codex 命名语义 | Phase 54 | `codex_fim.py` 重命名为 `fim_dialect.py`，`DialectSpec.name` 切为 `fim`，`BUILTIN_DIALECTS` 以 `fim` 为主键并保留 `codex_fim` shim，router / tests / backlog 同步收口 |
| 51 | `MetaOptimizerAgent.memory_authority = "canonical-write-forbidden"` 语义模糊，容易被误解为"完全只读" | Phase 53 | `MEMORY_AUTHORITY_SEMANTICS` dict 明确区分 canonical write authority 与 artifact write side effect，`AGENT_TAXONOMY.md §5` 补充"允许的 side effect"列 |
