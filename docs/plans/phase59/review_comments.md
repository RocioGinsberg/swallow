---
author: claude
phase: 59
slice: review
status: draft
depends_on:
  - docs/plans/phase59/design_decision.md
  - docs/plans/phase59/risk_assessment.md
  - docs/plans/phase59/kickoff.md
---

## TL;DR

Phase 59 实现与 design_decision 对齐，3 个 slice 全部完成，结构清晰。1 个 BLOCK（`test_proposal_review_and_apply_cli_flow` 因 alias 移除后仍断言 `local-aider` key 导致 KeyError）。1 个 CONCERN（`AGENTS.md` 系统能力章节移除了 legacy alias 行但未新增 `local-codex` 一等 route 描述）。修复 BLOCK 后可进入收口。

# Phase 59 Review Comments

## 评审范围

- **分支**: `feat/phase59-codex-cli-route`（5 commits, 16 files, +919/-91 lines）
- **对比基线**: `main`
- **设计文档**: `docs/plans/phase59/design_decision.md` + `risk_assessment.md` + `kickoff.md`
- **测试执行**: `pytest -x -q` — 1 failed（`test_proposal_review_and_apply_cli_flow` KeyError），其余 all passed

---

## S1: Route 注册 + Alias 迁移

### [PASS] `ROUTE_NAME_ALIASES` 清空

- `router.py:43`: `ROUTE_NAME_ALIASES: dict[str, str] = {}` — 同时移除 `local-codex -> local-aider` 和 `local-cline -> local-claude-code`
- 与 kickoff 修订版一致（kickoff 已被修改为"同时清空，移除遗留 `local-cline` 兼容"）
- `normalize_route_name("local-codex")` 现在返回 `"local-codex"`

### [PASS] `local-codex` RouteSpec 注册

- 位置正确：在 `local-aider` 之后、`local-http` 之前
- `executor_name="codex"`, `backend_kind="local_cli"`, `model_hint="codex"`, `dialect_hint="plain_text"`
- `fallback_route_name="local-summary"` — 与 aider / claude-code 对齐
- capabilities 与 aider / claude-code 完全一致（`code_execution`, `supports_tool_loop=True`, `workspace_write`）
- taxonomy 使用 `general-executor` / `task-state`，正确

### [PASS] `EXECUTOR_ALIASES` 新增

- `dialect_data.py`: `"codex": "codex"` 条目新增，位置在 `"aider"` 之后
- `normalize_executor_name("codex")` 返回 `"codex"` 而非 fallback 到 `DEFAULT_EXECUTOR`

### [PASS] 测试覆盖

- `test_route_for_executor_returns_builtin_codex_route` — route 注册验证
- `test_normalize_route_name_keeps_local_codex_stable` — alias 移除后直通验证
- `test_normalize_executor_name_supports_aliases` — 新增 `codex` 断言

### [BLOCK] `test_proposal_review_and_apply_cli_flow` 断言 `local-aider` 但 alias 已不存在

`test_cli.py:5661`: `persisted_weights["local-aider"]` 触发 `KeyError`。

**原因**：该测试创建指向 `local-codex` 的 telemetry 事件，经 Meta-Optimizer 生成 `route_weight` 提案并 apply。旧 alias 时代，`local-codex` 会被 `normalize_route_name()` 映射到 `local-aider`，所以 weight 持久化在 `local-aider` key 下。alias 移除后，weight 正确持久化在 `local-codex` key 下，但测试仍断言 `local-aider`。

**修复**：将 `persisted_weights["local-aider"]` 改为 `persisted_weights["local-codex"]`。

**影响**：这是 Phase 59 S1 引入的预期行为变更。测试应在 S1 commit 中同步更新。

---

## S2: Executor 配置 + Dispatch

### [PASS] `CODEX_CONFIG`

- `executor_name="codex"`, `display_name="Codex"`, `bin_env_var="AIWF_CODEX_BIN"`, `default_bin="codex"`
- `fixed_args=("exec",)` — 使用 `codex exec` non-interactive 模式
- `output_path_flags=("-o",)` — 支持 `codex exec -o <path>` 输出到文件
- 与 design_decision 完全一致

### [PASS] `CLI_AGENT_CONFIGS` 注册

- 新增 `CODEX_CONFIG.executor_name: CODEX_CONFIG`

### [PASS] Dispatch 分支

- `run_prompt_executor()` 和 `run_prompt_executor_async()` 各新增一个 `if executor_name == "codex":` 分支
- 位置在 `claude-code` 之后、`raise UnknownExecutorError` 之前
- 分别调用 `run_cli_agent_executor(CODEX_CONFIG, ...)` / `run_cli_agent_executor_async(CODEX_CONFIG, ...)`

### [PASS] 测试覆盖

- `test_run_prompt_executor_dispatches_codex_to_cli_agent_config` — mock 验证 sync dispatch
- `test_run_prompt_executor_async_dispatches_codex_to_cli_agent_config` — async dispatch
- `test_resolve_executor_routes_http_and_cli_agent_names` — 新增 codex 断言
- `test_cli_agent_configs_cover_aider_and_claude_code` — 新增 CODEX_CONFIG 字段断言

---

## S3: Doctor 探针

### [PASS] `CLIAgentDoctorResult` dataclass

- 新增 `CLIAgentDoctorResult`（`executor_name`, `display_name`, `binary_found`, `launch_ok`, `executor_bin`, `resolved_path`, `version`, `details`）
- 字段设计合理，覆盖 found/not found/launch failure 三种场景

### [PASS] `diagnose_cli_agents()` 实现

- 遍历 `CLI_AGENT_CONFIGS.values()`
- 使用 `shutil.which()` 检查 binary，找到后调用 `_run_command([bin, "--version"])`
- 复用已有 `_run_command()` / `_command_details()` helper，保持一致性
- exit_code 逻辑：任何一个 binary 不可用即 exit_code=1

### [PASS] `format_executor_doctor_result()` 扩展

- 签名新增 `cli_agents: list[CLIAgentDoctorResult] | None = None` — 向后兼容
- 当 cli_agents 非空时输出 `cli_agents:` 区块，每个 agent 一行
- 展示细节条件化：有 resolved_path 显示 path，有 version 显示 version，有 details 且无 version 显示 details

### [PASS] CLI 集成

- `swl doctor` / `swl doctor executor` 均调用 `diagnose_cli_agents()` 并传入 `format_executor_doctor_result()`
- exit code 逻辑正确：`executor_exit_code == 0 and cli_exit_code == 0 and ...`

### [PASS] 测试覆盖

- `test_diagnose_cli_agents_reports_found_and_missing_binaries` — mock 3 个 binary（aider found, claude not found, codex found），验证 exit_code=1 和各项状态
- `test_format_executor_doctor_result_includes_cli_agents_section` — 验证渲染输出包含 `cli_agents:` 和 codex 信息
- `test_doctor_executor_includes_cli_agent_probe_results` — CLI 集成测试

---

## 全局检查

### [PASS] 与 design_decision 的一致性

| 设计约束 | 状态 |
|----------|------|
| 移除 `local-codex -> local-aider` alias | ✓ `ROUTE_NAME_ALIASES = {}` |
| 同时清空 `local-cline` alias | ✓ |
| `local-codex` RouteSpec 注册 | ✓ 所有字段与设计一致 |
| `EXECUTOR_ALIASES["codex"] = "codex"` | ✓ |
| `CODEX_CONFIG` 使用 `codex exec` | ✓ `fixed_args=("exec",)` |
| dispatch 分支添加 | ✓ 同步/异步各一个 |
| doctor 探针 | ✓ `diagnose_cli_agents()` + 渲染 + CLI 集成 |
| 不重构 dispatch if-chain | ✓ |
| 不修改 complexity bias | ✓ |

### [CONCERN] `AGENTS.md` 移除了 legacy alias 行但未补充 `local-codex` 一等 route

`AGENTS.md` diff 只移除了一行（"Legacy route alias 兼容：route lookup / route policy persistence 统一兼容 `local-codex -> local-aider`、`local-cline -> local-claude-code`"），但"当前系统能力"章节未新增 `local-codex` 一等 CLI route 的描述。

**影响**：低。`AGENTS.md` "当前系统能力" 章节按规则只在打新 tag 时更新，不在 phase 级更新。但如果 Phase 59 合并后打 tag，应在 release docs 同步时补充。

**建议**：closeout 中标注此项，等 tag 决策时再同步。

### [PASS] 测试覆盖

直接相关测试全部列举如上。一个 pre-existing test（`test_proposal_review_and_apply_cli_flow`）因 alias 移除未同步更新而失败，属于 BLOCK 项。

### [PASS] eval fixture 更新

- `tests/eval/test_vector_retrieval_eval.py`: 将 `local-cline` 引用改为 `local-claude-code` — 正确反映 alias 移除

### [PASS] 未越出 phase scope

- 无 dispatch 重构
- 无 complexity bias 修改
- 无 capability 自动学习
- 无 Codex CLI 深度集成

---

## 结论

Phase 59 实现质量高，结构与设计完全对齐。1 个 BLOCK 项（test 断言 key 未随 alias 移除更新）需修复后才能进入收口。1 个 CONCERN 项（`AGENTS.md` 缺 `local-codex` 描述）属于 tag-level 文档同步项，不阻塞 merge。修复 BLOCK 后建议直接进入收口。
