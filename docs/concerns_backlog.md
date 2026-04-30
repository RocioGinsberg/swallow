# Concerns Backlog

> **Document discipline**
> Owner: Human
> Updater: Claude / Codex
> Trigger: review 产出新的 CONCERN、triage 结果变化、已记录 concern 状态变化
> Anti-scope: 不维护 phase 实现历史、不替代 review_comments.md、不记录与 review 无关的临时想法

Review 过程中产出的 CONCERN 项集中追踪。每项记录来源 phase、内容、当前状态。

定期回顾（每 3-5 个 phase），清理已解决或已过时的条目。

最近一次 triage：2026-04-26（Phase 60 启动前）。结论：当前 Open 项没有必须并入 Phase 60 的 blocker；retrieval-adjacent concern（sqlite-vec WARN 竞态、embedding dimensions import 固化）仍保留，但 Phase 60 只做 retrieval request source 默认策略收紧与 explicit override，不顺手修改 retrieval adapter / embedding 配置层，也不把 repo chunk 重新设计成 HTTP 代码库问答的核心路径。

---

## Open

| Phase | Slice | CONCERN | 消化时机 |
|-------|-------|---------|---------|
| 45 | Slice 2: conversation tree restoration | `_select_chatgpt_primary_path()` 在极低概率的”同深度、同 create_time 多叶节点”场景下，最终回退到 `sequence/node_id` 选主路径，确定性存在平台无关启发式偏差 | 后续若 eval 或真实导出样本显示 precision 下降，再单独调整主路径选择策略 |
| 49 | S4: sqlite-vec RAG Pipeline | `retrieval.py` 的 `_sqlite_vec_warning_emitted` 是模块级全局变量，多线程/多进程场景下存在竞态（两个线程可能各自发出一次 WARN）。当前 asyncio 单线程主路径无实际影响 | Phase 51 引入多进程 worker 前，改为 `threading.Event` 或 `asyncio.Event` |
| 50 | S1: Meta-Optimizer 结构化提案 | `extract_route_weight_proposals_from_report()` 从 markdown 文本反向解析 `route_weight` 提案，依赖 `build_meta_optimizer_report()` 的文本格式稳定性。格式变更会导致 `swl route weights apply` 静默返回空列表并抛出 ValueError | 后续 phase 若需程序化消费提案，改为直接序列化 `list[OptimizationProposal]` 到 JSON artifact |
| 50 | S2: 一致性审计自动触发 | `_FAIL_SIGNAL_PATTERNS` 包含 `\bfail(?:ed\|ure)?\b`，可能匹配 LLM 输出中描述”过去失败”的上下文句子，产生 false fail verdict。当前 verdict 不影响任务 state，误判代价低 | 后续 phase 在 audit prompt 中明确要求 LLM 输出 `- verdict: pass/fail/inconclusive` 行，减少对关键词扫描的依赖 |
| 57 | S1: Neural Embedding | `VECTOR_EMBEDDING_DIMENSIONS = resolve_swl_embedding_dimensions()` 在模块 import 时固化，与同文件 `VectorRetrievalAdapter.embedding_dimensions` 的 `default_factory` 延迟求值模式不一致。当前无实际影响 | 后续 phase 如需在同一进程中切换 embedding 维度（如 eval 场景），再统一为延迟求值或注入式配置 |
| 58 | S2: clipboard + generic_chat_json | `_is_open_webui_export` 收窄后，原先 auto-detect 为 `open_webui_json` 的 flat `[{"role":..., "content":...}]` list 现在走 `generic_chat_json` parser，auto-detect 语义发生变更 | 低影响；如后续 issue 出现可恢复 flat list 检测让 Open WebUI 优先 |
| 59 | S1: Route + Alias | tag-level release docs 仍未完整同步 Phase 58/59 能力：`AGENTS.md` / `README.md` 仍显示 `v1.2.0`，且 `AGENTS.md` 当前系统能力章节未新增 `local-codex` 一等 CLI route 描述 | Release-doc sync debt；下一次 tag-level 文档同步时补齐，不并入 Phase 60 implementation slice |
| 61 / 63 | deferred: durable proposal artifact lifecycle | Phase 63 已把 `_PENDING_PROPOSALS` 收敛为 `PendingProposalRepo` 并新增 duplicate guard,但仍是进程内 in-memory registry,不做 durable proposal artifact、evict 或 cleanup。长进程内累积与跨进程恢复仍未解决 | 后续 Self-Evolution / durable proposal artifact phase |
| 61 / 63 | canonical path `librarian_side_effect` §5 漂移 | Phase 63 M0 audit 确认 `librarian_side_effect` token 已存在于 canonical knowledge apply 路径,让 Orchestrator 触发 canonical 写入;INVARIANTS §5 Orchestrator 行 canonK 列仍为 `-`。Phase 63 final scope 明确不修改这一路径、不修改 INVARIANTS §5 | 后续 governance phase 单独评估 canonical librarian side-effect token 与 §5 矩阵一致性 |
| 63 | review M2-1: vestigial `staged_candidate_count` payload | 删除 `_route_knowledge_to_staged` 后,task 事件 payload 中 `staged_candidate_count` 字段仍保留但永远为 0。保留字段是为兼容既有事件 schema,但长期看是历史包袱 | 后续事件 schema 演进 phase 可移除或标 deprecated |
| 63 | review M2-5: `_apply_route_review_metadata` reconciliation 过长 | `governance.py` 内 `_apply_route_review_metadata` 仍沉淀约 250 行 meta-optimizer review reconciliation 逻辑。写路径已通过 `RouteRepo`,但业务整理逻辑可读性与边界仍偏重 | 后续可重构到 `meta_optimizer` 或独立 `route_review_apply.py` |
| 63 | review M3-1: `events` / `event_log` upgrade divergence | Phase 63 开始在 `append_event` 中双写既有 `events` 与新增 `event_log`;新写入同事务一致,但既有 DB 升级后历史 `events` 行不会 backfill 到 `event_log` | Phase 64 候选 H 规划事件 truth 切换时 backfill 或声明 cutoff 策略 |
| 64 | review M2-2: chat-completion guard indirect URL binding gap | `test_specialist_internal_llm_calls_go_through_router` 能识别直接 URL 字面量与直接 `resolve_new_api_chat_completions_url()` 调用,但不做跨语句 def-use 分析;`endpoint = resolve_new_api_chat_completions_url(); httpx.post(endpoint, ...)` 这类间接绑定不会命中。当前代码安全,但守卫强度依赖实现风格 | 后续若 Specialist / 基础设施层引入间接 chat-completion URL 路径,评估守卫精化 |
| 65 | closeout known gap: review application artifact outside SQLite transaction | `_apply_route_review_metadata` 的 review record application artifact 仍在 SQLite truth commit 后写入文件系统;Phase 65 已将失败语义收敛为 warning-only,避免 caller 误判 truth 写入失败,但未引入 outbox / stale marker / retry queue 等更强一致性机制 | 后续若 operator 需要强审计 artifact 保证,评估 outbox 或 stale marker 方案 |
| 65 | closeout known gap: audit snapshot size policy absent | `route_change_log` / `policy_change_log` 的 before/after payload 使用完整 JSON snapshot;Phase 65 intentionally 让超大 payload 写入失败时整体 ROLLBACK,但未定义 size cap、truncation policy 或外部 blob 存储策略 | 后续若 route/policy metadata 明显膨胀或 SQLite row size 成为问题,单独设计 audit snapshot size policy |
| 65 | closeout known gap: full migration runner deferred | Phase 65 只建立 fresh DB 首次建表与 `schema_version: 1` / `swl migrate --status`;真正的 v1 -> v2 migration runner、migration file discovery、apply protocol 仍未实装 | Phase 66+ 首次需要 schema upgrade 时补完整 migration runner |
| 66 | high audit finding: JSON/JSONL IO helper ownership | Phase 66 audit found repeated JSON object / JSONL loader patterns across truth, orchestration, knowledge/retrieval, and surface paths. `audit_index.md` dedupes Block 1/2/4/5 findings under the Block 4 high duplicate-helper view; root issue is shared IO helper ownership and explicit error-policy variants | Follow-up design/cleanup phase; decide strict vs missing-empty vs malformed-empty helper contracts before touching callsites |
| 66 | design-needed: SQLite transaction envelope helper | Phase 66 audit found repeated route / policy / audit-trigger / MPS policy SQLite transaction envelopes. This is real duplication, but Phase 65 intentionally favored namespace clarity and explicit rollback behavior | Follow-up design phase; evaluate helper/context-manager only if route rollback redo and namespace-specific audit rows remain explicit |
| 66 | design-needed: table-driven CLI dispatch | Phase 66 Block 5 found no dead CLI subcommand, but `cli.py` maintains parallel parser registration and dispatch chains with 80+ parser entries | CLI cleanup phase; start with read-only artifact/report commands before governance write paths |
| 66 | design-needed: sync/async orchestration and executor duplication | Phase 66 Block 2 found duplicated sync/async debate, subtask, HTTP executor, and CLI executor control flow | Follow-up design/cleanup phase; extract pure result/payload helpers first, without hiding control-plane sequence |
| 66 | design-needed: artifact-name registry / owner table | Phase 66 audit found task artifact names repeated across orchestrator, harness, retrieval allow-lists, and CLI artifact printers | Follow-up design phase; decide which artifacts are stable public surface, retrievable, or intentionally private |
| 66 | design-needed: runtime provider / executor defaults | Phase 66 audit found provider/model/executor defaults spread across runtime config, executor configs, cost estimation, dialect data, CLI, and doctor diagnostics | Follow-up design phase; decide whether defaults live in runtime config, route metadata, route policy, or executor-registry-adjacent runtime data |
| 66 | design-needed: taxonomy / authority / capability constants | Phase 66 audit found taxonomy, memory-authority, capability, specialist, and validator strings repeated across model, planner, dispatch, capability enforcement, and specialist modules | Follow-up cleanup phase; import shared constants where `models.py` is already the owner, leaving behavior-specific messages local |
| 66 | design-needed: retrieval source policy ownership | Phase 66 Block 2 found retrieval source types and route-family retrieval source policy split across task semantics, models, retrieval defaults, and orchestrator route-family logic | Follow-up design phase; decide whether source-type constants and route-family policy belong with retrieval config |
| 66 | design-needed: policy-result report/event pipeline | Phase 66 Block 2 found repeated evaluator/result/report/event plumbing across validation, compatibility, execution-fit, retry, stop, execution-budget, checkpoint, and harness code | Follow-up cleanup phase; evaluate a shared policy-result protocol or report/event helper without moving policy semantics out of their modules |

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
