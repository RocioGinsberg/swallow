---
author: codex
phase: 59
slice: closeout
status: final
depends_on:
  - docs/plans/phase59/kickoff.md
  - docs/plans/phase59/design_decision.md
  - docs/plans/phase59/risk_assessment.md
  - docs/plans/phase59/review_comments.md
---

## TL;DR

Phase 59 已完成实现、review follow-up 与收口同步。系统现在把 `local-codex` 作为真实内建 CLI route 接入，并完成 `codex exec` 配置、同步/异步 dispatch，以及 `swl doctor` 下的 CLI agent binary probe。Claude review 的唯一 BLOCK 已修复；剩余 1 条 CONCERN 仅为 tag-level `AGENTS.md` 能力描述补充，不阻塞进入 merge gate。当前状态为 **ready for human PR / merge gate**。

# Phase 59 Closeout

## 结论

Phase 59 `Codex CLI Route Integration` 已完成实现、review 跟进与收口同步，当前分支状态为 **PR synced / ready for human merge gate**。

本轮围绕 kickoff 定义的 3 个 slices，完成了从 route 到 executor 再到 operator doctor surface 的最小闭环：

- S1：注册真实 `local-codex` route，并移除历史 alias 兼容
- S2：补齐 `codex exec` 的 `CLIAgentConfig` 与同步 / 异步 dispatch
- S3：把 aider / claude-code / codex 的 binary 探测纳入 `swl doctor`

Claude review 已完成，结论为 1 个 BLOCK、1 个 CONCERN。BLOCK 已在本轮收口前修复；CONCERN 为 `AGENTS.md` tag-level 能力描述缺口，已保留在 `docs/concerns_backlog.md`，不阻塞 merge。

## 已完成范围

### Slice 1: real `local-codex` route

- `src/swallow/router.py` 中 `ROUTE_NAME_ALIASES` 已清空
- 同时移除两条历史兼容：
  - `local-codex -> local-aider`
  - `local-cline -> local-claude-code`
- `_build_builtin_route_registry()` 新增真实 `local-codex` `RouteSpec`
- route 关键字段：
  - `executor_name="codex"`
  - `backend_kind="local_cli"`
  - `model_hint="codex"`
  - `dialect_hint="plain_text"`
  - `fallback_route_name="local-summary"`
- `src/swallow/dialect_data.py` 新增 `EXECUTOR_ALIASES["codex"] = "codex"`

对应 commits：

- `6eda794` `feat(route): register real local codex route`
- `5b02955` `docs(executor): clean up cline feature`

### Slice 2: `CODEX_CONFIG` + dispatch

- `src/swallow/executor.py` 新增 `CODEX_CONFIG`
- `CLI_AGENT_CONFIGS` 注册 `codex`
- `CODEX_CONFIG` 使用：
  - `executor_name="codex"`
  - `display_name="Codex"`
  - `bin_env_var="AIWF_CODEX_BIN"`
  - `default_bin="codex"`
  - `fixed_args=("exec",)`
  - `output_path_flags=("-o",)`
- `run_prompt_executor()` 与 `run_prompt_executor_async()` 已新增 `codex` dispatch 分支
- 实现保持既有 if-chain，不引入超出 phase 边界的 dispatch 重构

对应 commit：

- `4da921d` `feat(executor): wire codex cli agent config`

### Slice 3: doctor CLI agent probes

- `src/swallow/doctor.py` 新增 `CLIAgentDoctorResult`
- 新增 `diagnose_cli_agents()`，统一探测 aider / claude-code / codex
- `format_executor_doctor_result()` 支持附加 `cli_agents` 区块
- `swl doctor` 与 `swl doctor executor` 现在会输出 CLI agent binary 状态
- exit code 会同时反映 executor preflight 与 CLI agent probe 结果

对应 commit：

- `4026e57` `feat(doctor): add cli agent binary probes`

## 与 kickoff / design 完成条件对照

### 已完成的目标

- `local-codex` 已不再依赖 alias，而是内建 route
- `local-cline` 兼容已移除，避免后续 operator 误解
- `codex` 已进入 `EXECUTOR_ALIASES` 与 `CLI_AGENT_CONFIGS`
- `run_prompt_executor()` / `run_prompt_executor_async()` 已可直接分发到 `codex`
- `swl doctor` / `swl doctor executor` 已能显示 codex binary probe
- 相关 router / executor / doctor / CLI 测试已补齐并完成定向验证

### 与原设计保持一致的边界

- 不重构 dispatch if-chain
- 不改动 complexity bias / route policy 学习逻辑
- 不引入更深的 Codex-specific tool protocol
- 不扩张到新的 provider routing 策略

## Review Follow-up 收口

Claude review 提出 1 个 BLOCK、1 个 CONCERN：

1. `tests/test_cli.py` 中 `test_proposal_review_and_apply_cli_flow` 仍断言 `persisted_weights["local-aider"]`
2. `AGENTS.md` 当前系统能力章节未补入 `local-codex` 一等 route 描述

本轮已完成的 follow-up：

- 修复 route-weight 持久化断言，使其与 alias 移除后的真实行为保持一致：
  - `tests/test_cli.py:5661` 改为 `persisted_weights["local-codex"]`
  - `tests/test_meta_optimizer.py` 中同类断言已同步

保留未收口项：

- `AGENTS.md` concern 继续保留在 `docs/concerns_backlog.md`
- 该项属于 tag-level release docs 同步问题，不属于当前 phase 的高频 / 低频文档更新范围

对应 review follow-up commit：

- `6d21ae8` `fix(phase59): clean up phase block and cocern`

## 当前稳定边界

Phase 59 closeout 后，以下边界应视为当前实现候选的稳定 checkpoint：

- `local-codex` 是真实 route，而非 `local-aider` 的别名入口
- CLI executor 家族现在包含：
  - `local-aider`
  - `local-claude-code`
  - `local-codex`
- `codex` 采用既有 `CLIAgentConfig` 框架接入，不新增第二套执行协议
- operator 可通过 `swl doctor` 直接看到 CLI agent binary 可用性，而不必等到任务执行失败后再排查

## Stop / Go 判断

### Stop 判断

当前 phase 应停止继续扩张，理由如下：

- kickoff 定义的 3 个 slices 均已完成，并已独立提交
- 本轮目标是 Codex CLI route 接入闭环，而不是扩张到更深的 executor abstraction 或 routing learning
- 再继续推进会自然滑向下一阶段问题域，如：
  - dispatch 表驱动重构
  - 更细粒度 CLI capability probing
  - 更复杂的 route policy/operator UX 收口

### Go 判断

下一步应按如下顺序推进：

1. Human 审阅 `docs/plans/phase59/closeout.md` 与 `pr.md`
2. Human 执行收口提交 / push / PR 创建
3. 如 PR review 新增 follow-up，仅处理 merge 前小修

## 当前已知问题 / 后续候选

- `AGENTS.md` "当前系统能力" 章节尚未把 `local-codex` 作为一等 route 写入；该项已登记 backlog，等待下次 tag-level 文档同步时一并处理
- 当前 `swl doctor` 只做 CLI binary / version probe，不验证更深层的非交互执行契约；若后续真实使用中出现误判，再考虑单独起 phase 增强

以上问题均不阻塞进入 merge gate。

## 测试结果

关键验证包括：

```bash
.venv/bin/python -m pytest tests/test_router.py tests/test_executor_protocol.py tests/test_cli.py -k 'codex or route_for_executor or normalize_route_name or normalize_executor_name_supports_aliases'
.venv/bin/python -m pytest tests/test_executor_protocol.py tests/test_cli.py -k 'codex and (dispatch or configs or general_executor or capability_enforcement)'
.venv/bin/python -m pytest tests/test_doctor.py tests/test_cli.py -k 'doctor_executor or diagnose_cli_agents or format_executor_doctor_result or doctor_without_subcommand or doctor_skip_stack'
.venv/bin/python -m pytest tests/test_cli.py -k 'test_proposal_review_and_apply_cli_flow'
```

结果：

- S1 targeted tests: passed
- S2 targeted tests: passed
- S3 targeted tests: passed
- review BLOCK verification: passed

说明：

- 有一次对 `tests/test_meta_optimizer.py` 的 `-k` 过滤未命中测试，但相关断言已完成同步修复

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase59/closeout.md`
- [x] `docs/plans/phase59/review_comments.md`
- [x] `docs/active_context.md`
- [x] `pr.md`

### 条件更新

- [x] `docs/concerns_backlog.md`
- [ ] `current_state.md`
- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- `docs/concerns_backlog.md` 已保留 review 的 tag-level 文档 concern
- `current_state.md` 继续保持 merge 后再同步的恢复语义
- 本轮不更新 `AGENTS.md` / README，因为当前 concern 属于 tag-level 能力描述同步项

## Git / Review 建议

1. 使用当前分支 `feat/phase59-codex-cli-route`
2. 以本 closeout 与 `pr.md` 作为 PR / merge gate 参考
3. 当前仅剩 human 审阅、push、创建 PR 与 merge 决策
4. 如需继续 follow-up，仅处理 review concern 消化或 merge 前小修

## 下一轮建议

如果 Phase 59 merge 完成，下一轮建议回到 `docs/roadmap.md`，优先评估：

- CLI / HTTP executor 体系是否需要统一的 dispatch table 收口
- `swl doctor` 是否需要更强的 runtime contract 预检，而不仅是 binary probe
- route/operator 文档是否需要在下一个 tag-level release docs 中系统收口
