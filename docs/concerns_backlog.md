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
| 61 | non-goal: §9 剩余守卫测试 | INVARIANTS §9 共 17 条守卫测试,Phase 61 仅实装与 `apply_proposal()` 直接相关的 3 条(`test_canonical_write_only_via_apply_proposal` / `test_route_metadata_writes_only_via_apply_proposal` / `test_only_apply_proposal_calls_private_writers`),另 14 条(canonical / route / policy / event / artifact 等其他不变量守卫)未实装 | 后续单独 phase 处理;不强求并入紧邻 phase,优先级随 INVARIANTS 漂移风险评估调整 |
| 61 | non-goal: Repository 抽象层完整实装 | DATA_MODEL §4.1 描述完整 `KnowledgeRepo` / `RouteRepo` / `PolicyRepo` 类与 `_promote_canonical` / `_apply_metadata_change` / `_apply_policy_change` 私有方法。Phase 61 采用最小封装(governance.py 直接调现有 store 函数 + 模块级 `_PENDING_PROPOSALS` in-memory 注册表)未实装 Repository 类。`_PENDING_PROPOSALS` 不做生命周期清理,长 process 内存累积;同 proposal_id 第二次 register 会静默覆盖 | 后续 Repository 实装 phase 一并消化:把 in-memory 注册表替换为 durable proposal artifact 层,补 Repository 类 + `_promote_canonical` / `_apply_metadata_change` / `_apply_policy_change` 私有方法,守卫测试同步切换扫描目标 |
| 61 | non-goal: apply_proposal 事务性回滚 | `apply_reviewed_optimization_proposals()` / `_apply_route_review_metadata` 仍记录 `rollback_weights` / `rollback_capability_profiles` 字段,但**不**执行运行时回滚;`save_route_weights → apply_route_weights → save_route_capability_profiles → apply_route_capability_profiles` 四步如中途失败,系统进入"权重已更新但 profile 未更新"的不一致状态。Phase 61 与原代码等价(不引入新风险但也不修复),`apply_proposal()` 名义上是 governance 入口但不提供事务保证 | 后续单独 phase 设计;先在 governance.py docstring 增加事务性警示,再评估是否引入两阶段提交或 staged 应用机制 |
| 62 | design audit: orchestrator stagedK 直写 | `orchestrator.py:3145` 既有 `submit_staged_candidate(...)` 调用,处理 Librarian agent 任务执行中 verified knowledge → staged candidate 转换(librarian-side-effect 等价语义),未走 governance / OperatorToken 通道。INVARIANTS §5 矩阵中 Orchestrator 行 stagedK 列为 `-`,这条路径属于宪法-代码漂移。Phase 62 不在 scope 内修复,本 phase 守卫只覆盖新增 synthesis.py 自身不写 stagedK | 后续治理 phase(类似 Phase 61 模式)消化:扩展 OperatorToken.source 增加 `librarian_side_effect` 类型,把 orchestrator.py:3145 调用接入 governance,补 stagedK 写入唯一入口守卫 |
| 62 | design audit: INVARIANTS §7 集中化函数缺失 | INVARIANTS §7 定义 `swallow.identity.local_actor()` 与 `swallow.workspace.resolve_path()` 为 actor 标识与路径绝对化的唯一中心点,§9 列出对应守卫 `test_no_hardcoded_local_actor_outside_identity_module` / `test_no_absolute_path_in_truth_writes`。但 `find src/swallow/ -name 'identity.py' -o -name 'workspace.py'` 零匹配,这两个模块不存在;现有代码沿用 paths.py 与内联 `.resolve()` / 直接 `"local"` 字符串。守卫测试可能 vacuous(无 import 目标可扫描),宪法-代码漂移 | 与 §9 剩余 14 条守卫一并处理:或者实装两个集中化模块 + 强制守卫,或者修订 INVARIANTS §7 承认现状路径 |

## Won't Fix / By Design

| Phase | Slice | CONCERN | 理由 |
|-------|-------|---------|------|
| 22 | Slice 3: taxonomy guard | taxonomy guard 对所有 contract 生效（含 local-only） | 设计意图如此：taxonomy guard 是全局防线，不限于 remote 路径 |
| 28 | Slice 3: preflight 增强 | `build_stage_promote_preflight_notices()` 返回类型从 `list[str]` 变为 `list[dict[str, str]]`，当前无外部调用者 | 返回类型已稳定，docstring 已明确记录设计意图，无兼容性问题 |

## Resolved

| Phase | CONCERN | 消化 Phase | 消化方式 |
|-------|---------|-----------|---------|
| 49 | CLI operator canonical promotion 的 authority 语义仍未完全统一：`knowledge stage-promote` 的 Wiki 写入已使用 `OPERATOR_CANONICAL_WRITE_AUTHORITY`，但 `task knowledge-promote --target canonical` 仍通过 `LIBRARIAN_MEMORY_AUTHORITY` 进入 decision 层，审计时仍可能混淆 operator 手动 promotion 与 LibrarianAgent 自动 promotion | Phase 61 | M3 将 `task knowledge-promote --target canonical` 的 CLI decision-level `caller_authority` 改为 `operator-gated`，decision 层同时允许 Librarian `canonical-promotion` 与 Operator `operator-gated`，canonical 主写入仍通过 `apply_proposal(OperatorToken(source="cli"), target=CANONICAL_KNOWLEDGE)` |
| Meta Docs Sync | INVARIANTS §0 第 4 条以及 ARCHITECTURE / STATE_AND_TRUTH / EXECUTOR_REGISTRY / INTERACTION 等 7+ 处把 `apply_proposal()` 定义为 canonical / route / policy 写入唯一入口，§9 守卫测试集列出 `test_canonical_write_only_via_apply_proposal` / `test_only_apply_proposal_calls_private_writers` / `test_route_metadata_writes_only_via_apply_proposal` 三条，但 `grep -rn "apply_proposal" src/ tests/` 零匹配，实际 canonical / route / policy 写入由 CLI 子命令直接调底层 store，设计文档与代码出现宪法级漂移 | Phase 61 | 实装 `swallow.governance.apply_proposal()` 三参数入口,收敛 canonical knowledge / route metadata / policy 三类主写入路径,补齐 3 条 INVARIANTS §9 apply_proposal 守卫测试,并通过全量 pytest 与 Meta-Optimizer eval 验证 |
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
