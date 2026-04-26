---
author: codex
phase: 60
slice: closeout
status: final
depends_on:
  - docs/plans/phase60/kickoff.md
  - docs/plans/phase60/design_decision.md
  - docs/plans/phase60/risk_assessment.md
  - docs/plans/phase60/review_comments.md
---

## TL;DR

Phase 60 已完成实现、review follow-up 与收口同步。系统现在把 retrieval source 选择从固定三源升级为 route-aware policy：autonomous CLI coding route 默认只取 `knowledge`，HTTP route 默认聚焦 `knowledge + notes`，legacy fallback route 保留旧三源兼容，同时支持 `TaskSemantics.retrieval_source_types` 显式 override。Claude review 的 1 个 BLOCK 与 1 个 CONCERN 均已修复；当前状态为 **ready for human PR / merge gate**。

# Phase 60 Closeout

## 结论

Phase 60 `Route-Aware Retrieval Policy` 已完成实现、review 跟进与验证，当前分支状态为 **PR synced / ready for human merge gate**。

本轮围绕 kickoff 定义的 3 个 slices，完成了 retrieval request 构造层的最小闭环收口：

- S1：用 route capability family 替代固定三源，把 autonomous CLI coding route 收紧为 `knowledge-only`
- S2：显式固化 HTTP route 的默认策略为 `knowledge + notes`，不再把 repo chunk 当作 HTTP 默认代码库问答路径
- S3：引入 `TaskSemantics.retrieval_source_types` 显式 override，并保证 create / planning handoff / task semantics report 全链路保留该配置

Claude review 已完成，结论为 1 个 BLOCK、1 个 CONCERN。两项都已在收口前修复，当前无剩余 phase-specific blocker。

## 已完成范围

### Slice 1: route-aware policy family

- `src/swallow/orchestrator.py` 顶部新增 `_RETRIEVAL_SOURCE_POLICY`
- `_retrieval_policy_family()` 基于以下信号判定 retrieval policy family：
  - `route_executor_family`
  - `route_capabilities.supports_tool_loop`
  - `route_capabilities.execution_kind`
  - `route_capabilities.deterministic`
- 新增 `autonomous_cli_coding` / `legacy_local_fallback` / `api` / 全局 fallback 四类语义
- autonomous CLI coding route 默认 source_types 收紧为 `["knowledge"]`
- legacy fallback / deterministic CLI route 保留 `["repo", "notes", "knowledge"]`
- 未知 route 或 capability 缺失时回退到 `["knowledge", "notes"]`
- 引入 taxonomy-based Specialist guard，避免 specialist-style CLI path 被误归为 autonomous coding route

对应 commits：

- `b595fa7` `feat(retrieval): add phase60 s1 route-aware source policy`

### Slice 2: explicit HTTP policy

- policy 表新增显式 `("api", "*") -> ["knowledge", "notes"]`
- HTTP path 对 planning / review / execution / extraction / retrieval 默认均不自动启用 repo
- `tests/test_cli.py` 补齐 HTTP task_family 覆盖，确认 `source_kind` 变化不会把 repo chunk 放回默认主链

对应 commits：

- `f248dd1` `test(retrieval): cover explicit http source policy`

### Slice 3: explicit override

- `TaskSemantics` 新增 `retrieval_source_types: list[str] | None`
- `src/swallow/task_semantics.py` 新增 `normalize_retrieval_source_types()`：
  - 允许 `repo` / `notes` / `knowledge` / `artifacts`
  - 保序去重
  - 非法值或空列表显式抛 `ValueError`
- `create_task()` 支持写入 `retrieval_source_types`
- `update_task_planning_handoff()` 在 merge semantics 时保留已有 override
- `build_task_retrieval_request()` 显式 override 优先于 policy 默认值
- `build_task_semantics_report()` 显示当前 retrieval source 是 explicit override 还是 `policy_default`

对应 commits：

- `7527873` `feat(retrieval): add explicit retrieval source overrides`

### 长期设计锚点同步

本轮同时刷新了与 Phase 60 强绑定的长期设计文档，确保后续 phase 不再回到旧的“HTTP + repo chunk 默认代码库问答”思路：

- `docs/design/KNOWLEDGE.md`
- `docs/design/AGENT_TAXONOMY.md`
- `docs/design/ARCHITECTURE.md`
- `docs/roadmap.md`
- `docs/plans/phase60/kickoff.md`

对应 commit：

- `2180b55` `docs(phase60): align roadmap and kickoff with executor ecology`

## 与 kickoff / design 完成条件对照

### 已完成的目标

- autonomous CLI coding route 默认不再携带 `"repo"` source
- HTTP route 默认稳定聚焦 `["knowledge", "notes"]`
- legacy local fallback route 继续保留旧三源兼容
- `"repo"` 只通过 explicit override 或 legacy fallback 返回主链
- Specialist / explicit input_context 路径未被误收紧
- `TaskSemantics.retrieval_source_types` 可覆盖默认 policy
- override 的合法性校验、去重与持久化已经落地
- 所有 slices 都具备对应 pytest 覆盖

### 与设计保持一致的边界

- policy 仍只在 `build_task_retrieval_request()` 构造层生效
- 未修改 `retrieve_context()` / `harness.py:run_retrieval()`
- 未修改 `infer_task_family()` 分类逻辑
- 未新增 source_type
- 未新增 `--retrieval-sources` CLI flag
- 未激活 `RetrievalRequest.strategy` 的额外语义

## Review Follow-up 收口

Claude review 指出 1 个 BLOCK、1 个 CONCERN：

1. `tests/test_cli.py::test_failed_task_events_include_failure_payloads` 仍沿用旧 retrieval 语义，断言 `validation_status == "passed"` 与 `retrieval_count == 1`
2. `tests/test_meta_optimizer.py` 中仍残留 `local-aider` alias 断言

本轮已完成的 follow-up：

- 将失败生命周期测试断言同步到 Phase 60 新语义：
  - `validation.completed.status` 由 `passed` 改为 `warning`
  - 最终 `validation_status` 由 `passed` 改为 `warning`
  - `retrieval_count` 由 `1` 改为 `0`
- 清理 `tests/test_meta_optimizer.py` 中两处 `local-aider` 期望值：
  - rollback route weight 改为 `local-codex`
  - rollback capability profile 改为 `local-codex`

对应 commit：

- `fb5410f` `test(phase60): fix review regression assertions`

review follow-up 完成后，Phase 60 当前无未解决 BLOCK / CONCERN。

## 当前稳定边界

Phase 60 closeout 后，以下边界应视为当前实现候选的稳定 checkpoint：

- retrieval source policy 已从固定三源切换为 route-aware selection，但仍只作用于 request 构造层
- autonomous CLI coding route 的代码库上下文主路径是 agent 自主文件探索，而不是预灌 repo chunk
- HTTP route 的默认职责是知识复用、规划、审查与摘要，不是代码库问答的默认主链
- `notes` 继续代表 Markdown / 文档现场，`knowledge` 继续代表治理后的长期知识，`repo` 继续只是局部源码 chunk
- Specialist path 继续以 explicit input_context / artifacts / governed knowledge flow 为主，不通过通用 retrieval policy 重新定义其输入协议
- explicit override 已是稳定 operator escape hatch，但暂未暴露新的 CLI flag

## Stop / Go 判断

### Stop 判断

当前 phase 应停止继续扩张，理由如下：

- kickoff 定义的 S1 / S2 / S3 全部完成，并已独立提交
- review follow-up 已吸收，无剩余 merge blocker
- 再继续扩张会自然滑向下一轮问题域，例如：
  - router policy 对 HTTP / CLI 的更强约束
  - operator-facing retrieval override CLI surface
  - retrieval source 策略的更细粒度 task-family 专用化

### Go 判断

下一步应按如下顺序推进：

1. Human 审阅 `docs/plans/phase60/closeout.md` 与 `pr.md`
2. Human push 当前分支并创建 / 更新 PR
3. Human 基于当前 closeout、review 结论与全量测试结果做 merge 决策

## 当前已知问题 / 后续候选

- `docs/concerns_backlog.md` 中 Phase 59 的 tag-level release-doc sync debt 仍保持 open；该项属于 README / AGENTS tag-level 同步，不阻塞 Phase 60 merge
- Phase 60 当前只提供 task semantics 层的 explicit override，尚未增加独立 CLI 参数；若 operator 真实使用中频繁需要该能力，再评估是否单独起 phase 扩 operator 入口
- HTTP / CLI / Specialist 的生态位边界已在设计文档中明确，但 router 是否需要更强的默认路线约束，仍属于后续 phase 候选

以上问题均不阻塞进入 merge gate。

## 测试结果

关键验证包括：

```bash
.venv/bin/python -m pytest tests/test_cli.py -k "build_task_retrieval_request or run_task_passes_explicit_retrieval_request_to_harness"
.venv/bin/python -m pytest tests/test_cli.py -k "retrieval_source or build_task_retrieval_request or planning_handoff_preserves_existing_retrieval_source_override or create_task_persists_explicit_retrieval_source_override or create_task_rejects_invalid_explicit_retrieval_source_override or run_task_passes_explicit_retrieval_request_to_harness"
.venv/bin/python -m pytest tests/test_cli.py::CliLifecycleTest::test_failed_task_events_include_failure_payloads tests/test_meta_optimizer.py::MetaOptimizerTest::test_review_and_apply_approved_route_weight_proposals tests/test_meta_optimizer.py::MetaOptimizerTest::test_review_and_apply_approved_route_capability_boundary_proposals -q
.venv/bin/python -m pytest tests/ --ignore=tests/eval
```

结果：

- S1 / S2 targeted tests: passed
- S3 targeted tests: passed
- review follow-up targeted tests: passed
- full non-eval suite: `535 passed`

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase60/closeout.md`
- [x] `docs/plans/phase60/review_comments.md`
- [x] `docs/active_context.md`
- [x] `pr.md`

### 条件更新

- [ ] `current_state.md`
- [ ] `docs/concerns_backlog.md`
- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- `current_state.md` 仍保持 main / merge 前稳定恢复语义，待 Phase 60 真正 merge 后再同步
- 本轮 review 无残留 Phase 60 concern，因此 `docs/concerns_backlog.md` 无需新增条目
- `AGENTS.md` / README 属于 tag-level 对外能力说明，不在本轮 merge 前 closeout 中更新

## Git / Review 建议

1. 使用当前分支 `feat/phase60-retrieval-policy`
2. 以本 closeout 与 `pr.md` 作为 PR / merge gate 参考
3. 当前仅剩 human 审阅、push、创建 / 更新 PR 与 merge 决策
4. 如需继续 follow-up，仅处理 merge 前小修，不再扩张 Phase 60 范围

## 下一轮建议

如果 Phase 60 merge 完成，下一轮建议回到 `docs/roadmap.md`，优先评估：

- retrieval source override 是否需要 operator-facing CLI / API surface
- HTTP / CLI route 选择是否需要更强的默认 guard，减少代码库任务误路由到 HTTP
- retrieval policy 与 router policy 之间是否需要更明确的职责收口
