# Concerns Backlog

Review 过程中产出的 CONCERN 项集中追踪。每项记录来源 phase、内容、当前状态。

定期回顾（每 3-5 个 phase），清理已解决或已过时的条目。

---

## Open

| Phase | Slice | CONCERN | 消化时机 |
|-------|-------|---------|---------|
| 45 | Slice 2: conversation tree restoration | `_select_chatgpt_primary_path()` 在极低概率的“同深度、同 create_time 多叶节点”场景下，最终回退到 `sequence/node_id` 选主路径，确定性存在平台无关启发式偏差 | 后续若 eval 或真实导出样本显示 precision 下降，再单独调整主路径选择策略 |

## Won't Fix / By Design

| Phase | Slice | CONCERN | 理由 |
|-------|-------|---------|------|
| 22 | Slice 3: taxonomy guard | taxonomy guard 对所有 contract 生效（含 local-only） | 设计意图如此：taxonomy guard 是全局防线，不限于 remote 路径 |
| 28 | Slice 3: preflight 增强 | `build_stage_promote_preflight_notices()` 返回类型从 `list[str]` 变为 `list[dict[str, str]]`，当前无外部调用者 | 返回类型已稳定，docstring 已明确记录设计意图，无兼容性问题 |

## Resolved

| Phase | CONCERN | 消化 Phase | 消化方式 |
|-------|---------|-----------|---------|
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
