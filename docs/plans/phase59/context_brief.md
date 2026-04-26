---
author: claude
phase: 59
slice: context-brief
status: draft
depends_on:
  - docs/plans/phase58/closeout.md
  - docs/roadmap.md
---

TL;DR: Phase 58 landed low-friction knowledge capture. Phase 59 targets roadmap candidate B: making `local-codex` a real CLI route instead of a legacy alias to `local-aider`. The key implementation touch points are: `ROUTE_NAME_ALIASES` removal for `local-codex`, new `CODEX_CONFIG` in `CLIAgentConfig`, `EXECUTOR_ALIASES` + `run_prompt_executor` dispatch, `_build_builtin_route_registry()` route registration, degradation matrix placement, `diagnose_executor()` multi-binary probe, and complexity bias update. The `codex` binary (`codex-cli 0.125.0`) is already installed on the workstation.

## 变更范围

- **直接影响模块**:
  - `src/swallow/router.py` — `ROUTE_NAME_ALIASES` 移除 `local-codex -> local-aider`；`_build_builtin_route_registry()` 新增 `local-codex` RouteSpec；`_apply_complexity_bias()` 可能需更新默认偏好映射
  - `src/swallow/executor.py` — `CLI_AGENT_CONFIGS` 新增 `CODEX_CONFIG`；`run_prompt_executor()` / `run_prompt_executor_async()` 新增 `codex` dispatch 分支
  - `src/swallow/dialect_data.py` — `EXECUTOR_ALIASES` 新增 `"codex": "codex"` 条目
  - `src/swallow/doctor.py` — `diagnose_executor()` 当前只检查 aider binary，需扩展为多 CLI agent 探针或新增 `diagnose_cli_agents()` 函数
  - `tests/test_router.py` — alias 测试需更新，`local-codex` 应可直接 resolve 到真实 route
  - `tests/test_meta_optimizer.py` — 现有 fixture 已使用 `local-codex` route name，需验证与真实 route 的兼容性

- **间接影响模块**:
  - `src/swallow/paths.py` — `route_capabilities_path` / `route_weights_path` 无需改动，但 `.swl/route_weights.json` 中如有 `local-codex` 条目，migration 时需处理
  - `src/swallow/models.py` — `RouteSpec` / `RouteCapabilities` / `TaxonomyProfile` 无需改动（复用既有结构）
  - `.swl/route_weights.json` / `.swl/route_capabilities.json` — 如 operator 曾通过 alias 写入 `local-codex` 权重/能力，需确認新 route 注册后这些配置能正确读取

## 近期相关变更 (git history)

| Commit | 描述 | 相关模块 |
|--------|------|---------|
| Phase 54 | FIM dialect 去品牌化：`fim` 为主 key，`codex_fim` 保留 shim | `executor.py`, `router.py` |
| Phase 52 | `AsyncCLIAgentExecutor` + `CLIAgentConfig` 统一 CLI agent 入口 | `executor.py` |
| Phase 46 | CLI 执行器去品牌化：配置驱动的 CLIAgentConfig | `executor.py` |
| Phase 42 | Meta-Optimizer 遥测修正 | `meta_optimizer.py` |
| (legacy) | `ROUTE_NAME_ALIASES` 曾引入 `local-codex -> local-aider` 与 `local-cline -> local-claude-code` | `router.py` |

## 关键上下文

**当前 `local-codex` 只是 alias**

`router.py:43-46`：`ROUTE_NAME_ALIASES` 历史上曾包含 `local-codex -> local-aider` 与 `local-cline -> local-claude-code`。`normalize_route_name()` (L593-600) 在 route lookup / policy persistence 时会把别名归一化到真实 route。Phase 59 的目标是不仅移除 `local-codex` alias，也顺手清空剩余 `local-cline` 兼容，避免继续制造误解。这意味着：
- 任何对 `local-codex` 的路由请求实际走 `local-aider` 的 executor config
- route weights / capability profiles 中写 `local-codex` 会映射到 `local-aider` 的权重
- Meta-Optimizer telemetry / diagnosis 中看到 `local-codex` 时是拿 aider 的配置在运行

**`CLIAgentConfig` 框架已就位**

`executor.py:144-174`：`CLIAgentConfig` dataclass 有 7 个字段：`executor_name`, `display_name`, `bin_env_var`, `default_bin`, `fixed_args`, `output_path_flags`, `workspace_root_flags`。当前只有两个实例：
- `AIDER_CONFIG`: `executor_name="aider"`, `bin_env_var="AIWF_AIDER_BIN"`, `default_bin="aider"`, `fixed_args=("--yes-always", "--no-auto-commits")`
- `CLAUDE_CODE_CONFIG`: `executor_name="claude-code"`, `bin_env_var="AIWF_CLAUDE_CODE_BIN"`, `default_bin="claude"`, `fixed_args=("--print",)`

新增 `CODEX_CONFIG` 需要确定：
- `executor_name`: `"codex"` 最合理（与 `"aider"` / `"claude-code"` 对齐）
- `bin_env_var`: `"AIWF_CODEX_BIN"` 或 `"AIWF_CODEX_CLI_BIN"`
- `default_bin`: `"codex"` — workstation 上已安装 `codex-cli 0.125.0` at `/home/rocio/.nvm/versions/node/v20.20.2/bin/codex`
- `fixed_args`: Codex CLI (`codex-cli`) 的 non-interactive 参数需确认（`codex` 的 `--print` / `--quiet` / `--full-auto` 等选项）

**executor dispatch 是硬编码 if-chain**

`executor.py:575-618` / `621-664`：`run_prompt_executor()` / `run_prompt_executor_async()` 用 `if executor_name == "aider": ...` 分发。新增 `codex` executor_name 需在两个函数各加一个分支。未知 executor 会触发 `UnknownExecutorError`。

`CLI_AGENT_CONFIGS` dict (L171-174) 当前只用于 `AsyncCLIAgentExecutor` 构造；`run_prompt_executor` 的 if-chain 并不从 dict lookup，而是硬编码配置引用。新增 codex 需同步两处。

**EXECUTOR_ALIASES 与 normalize_executor_name**

`dialect_data.py:18-28`：`EXECUTOR_ALIASES` 当前有 `aider`, `claude-code`, `claude_code`, `http`, `mock`, `mock-remote`, `note-only`, `local` 条目。无 `codex` 条目。`normalize_executor_name()` 对未知名称返回原值或 `DEFAULT_EXECUTOR`（`"aider"`）。需新增 `"codex": "codex"` 显式条目。

**Route 注册与降级矩阵**

`_build_builtin_route_registry()` (router.py:276-549) 注册所有 builtin routes。当前 CLI routes：
- `local-aider` → `fallback_route_name="local-summary"`
- `local-claude-code` → `fallback_route_name="local-summary"`

HTTP 降级链：`http-claude → http-qwen → http-glm → local-claude-code → local-summary`。

新增 `local-codex` 需要决定：
1. **降级链位置**：`local-codex` fallback 到哪里？建议 `local-summary`（与 aider / claude-code 对齐）
2. **谁 fallback 到 codex**：当前无 route fallback 到 CLI agent（HTTP routes 都 fallback 到 `local-claude-code` 或其他 HTTP route）。是否让 `http-glm` fallback 到 `local-codex` 而非 `local-claude-code`？或保持不变？
3. **complexity bias**：`_apply_complexity_bias()` 对 `low`/`routine` 偏好 `local-aider`，对 `high` 偏好 `local-claude-code`。`local-codex` 属于哪个 complexity tier？

**能力画像 (capability profile)**

CLI routes 的 capabilities：
- `local-aider`: `code_execution`, `supports_tool_loop=True`, `workspace_write`
- `local-claude-code`: `code_execution`, `supports_tool_loop=True`, `workspace_write`

`local-codex` 应使用相同 capabilities（Codex CLI 具备与 Claude Code 类似的沙盒代码执行能力）。

`task_family_scores` 和 `unsupported_task_types` 在注册时默认为空 dict/list，由 Meta-Optimizer 遥测后续填充或由 operator 手动配置到 `.swl/route_capabilities.json`。

**Doctor 探针只检查 aider**

`doctor.py:308-350`：`diagnose_executor()` 硬编码检查 `AIWF_EXECUTOR_MODE` 默认 `aider`、`AIWF_AIDER_BIN` 默认 `aider`。Phase 59 应扩展为多 CLI agent 探针（或至少新增 codex binary 检查），以便 `swl doctor` 能报告 codex 可用性。

**Dialect 选择**

`local-codex` 的 `dialect_hint` 应为 `"plain_text"`（Codex CLI 接受自由文本 prompt，不需要 XML 或 FIM 标记）。`codex-cli` 的输入是 prompt string，输出是文本结果。

**已有 route policy / telemetry 中的 `local-codex`**

- `tests/test_meta_optimizer.py` fixture 中已使用 `"physical_route": "local-codex"` 和 `"previous_route_name": "local-codex"`。新增真实 route 后，这些 fixture 将直接匹配真实 route name，不再通过 alias 映射。
- `.swl/route_weights.json` 如存在 `local-codex` 条目，`normalize_route_name()` 处理逻辑需调整：从返回 alias target（`local-aider`）改为返回直接匹配（`local-codex`）。

## 风险信号

- **`ROUTE_NAME_ALIASES` 移除 `local-codex` 后的迁移**：如 operator 已在 `.swl/route_weights.json` 中写入过 `local-codex` 权重（通过 alias 映射到 `local-aider`），移除 alias 后权重会直接关联到新的 `local-codex` route。这通常是期望行为，但如果权重是为 aider 调的，可能需要重新校准。实际风险低——当前系统只有一个 operator（你），且 route weights 通常通过 Meta-Optimizer 提案生成。
- **遗留 `local-cline` alias 的误导性**：虽然当前没有真实 Cline route 计划，但保留 `local-cline -> local-claude-code` 会继续暗示存在另一个 CLI executor 家族。Phase 59 可一并清理。
- **Codex CLI 参数稳定性**：`codex-cli 0.125.0` 正处于活跃开发期（OpenAI 产品），CLI flag 可能发生变化。`fixed_args` 应保守设置，只包含稳定的 non-interactive 参数。
- **`run_prompt_executor` if-chain 膨胀**：每新增一个 CLI agent 需在两个 dispatcher 函数各加一个分支。长期可能需要改为 config-driven dispatch（查 `CLI_AGENT_CONFIGS` dict），但 Phase 59 scope 内保持一致性更重要，不应在本轮做 dispatch 重构。
- **doctor 探针只检查单一 binary**：`diagnose_executor()` 最终应支持多 binary 检查。Phase 59 范围内至少应让 `swl doctor` 输出 codex binary 是否可用，具体方案（扩展现有函数 vs. 新增函数）在设计阶段决定。
