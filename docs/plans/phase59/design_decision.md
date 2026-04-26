---
author: claude
phase: 59
slice: design-decision
status: draft
depends_on:
  - docs/plans/phase59/kickoff.md
  - docs/plans/phase59/context_brief.md
---

## TL;DR

Phase 59 拆为 3 个 slice：S1 route 注册 + alias 迁移（最低风险 3 分）、S2 executor 配置 + dispatch（低风险 4 分）、S3 doctor 探针扩展（最低风险 3 分）。S2 依赖 S1（新 route 需先注册），S3 独立。实施时必须同步移除 `ROUTE_NAME_ALIASES` 中 `local-codex` 条目、新增 `EXECUTOR_ALIASES["codex"]`、在两个 dispatcher 函数中添加 codex 分支、并保留 `local-cline` alias 不动。

# Phase 59 Design Decision: Codex CLI Route 接入

## 方案总述

让 `local-codex` 从 `local-aider` 的 legacy alias 升级为独立 CLI route。不修改 dispatch 架构（if-chain 保留），不修改 complexity bias 映射，不引入自动 capability 学习。核心改动：5 个文件新增/修改配置实例与注册条目。

## Slice 拆解

### S1: Route 注册 + Alias 迁移

**目标**：`local-codex` 成为 `_build_builtin_route_registry()` 中的独立 RouteSpec，alias 移除。

**影响范围**：
- `src/swallow/router.py` — `ROUTE_NAME_ALIASES` 移除 `local-codex` 条目；`_build_builtin_route_registry()` 新增 `local-codex` RouteSpec
- `src/swallow/dialect_data.py` — `EXECUTOR_ALIASES` 新增 `"codex": "codex"` 条目
- `tests/test_router.py` — 新增 `local-codex` route 注册测试

**实现要点**：

1. **移除 alias**：
   - `ROUTE_NAME_ALIASES` 从 `{"local-codex": "local-aider", "local-cline": "local-claude-code"}` 改为 `{"local-cline": "local-claude-code"}`
   - `normalize_route_name("local-codex")` 将返回 `"local-codex"` 而非 `"local-aider"`

2. **新增 RouteSpec**：
   ```python
   RouteSpec(
       name="local-codex",
       executor_name="codex",
       backend_kind="local_cli",
       model_hint="codex",
       dialect_hint="plain_text",
       fallback_route_name="local-summary",
       executor_family="cli",
       execution_site="local",
       remote_capable=False,
       transport_kind="local_process",
       capabilities=RouteCapabilities(
           execution_kind="code_execution",
           supports_tool_loop=True,
           filesystem_access="workspace_write",
           network_access="optional",
           deterministic=False,
           resumable=True,
       ),
       taxonomy=TaxonomyProfile(
           system_role="general-executor",
           memory_authority="task-state",
       ),
   )
   ```
   - 位置：插入在 `local-claude-code` 之后、`local-mock` 之前
   - `model_hint="codex"` — 用于 `_filter_model_hint_matches()` 匹配
   - `fallback_route_name="local-summary"` — 与 aider / claude-code 对齐，不把 codex 插入 HTTP 降级链

3. **EXECUTOR_ALIASES 新增**：
   - `dialect_data.py`: `EXECUTOR_ALIASES["codex"] = "codex"`
   - 使 `normalize_executor_name("codex")` 返回 `"codex"` 而非 fallback 到 `DEFAULT_EXECUTOR`

**风险评级**：
- 影响范围: 1（router.py + dialect_data.py，均为配置修改）
- 可逆性: 1（恢复 alias 即可回滚）
- 依赖复杂度: 1（无外部依赖）
- **总分: 3（最低风险）**

**验收条件**：
- `normalize_route_name("local-codex")` 返回 `"local-codex"`
- `ROUTE_REGISTRY.maybe_get("local-codex")` 返回非 None RouteSpec
- `normalize_executor_name("codex")` 返回 `"codex"`
- `local-cline` alias 仍映射到 `local-claude-code`
- pytest 覆盖 alias 移除 + route 注册 + executor name 归一化

---

### S2: Executor 配置 + Dispatch

**目标**：`codex` executor_name 能正确分发到 `CODEX_CONFIG`，经 `codex exec` 执行。

**影响范围**：
- `src/swallow/executor.py` — 新增 `CODEX_CONFIG`；`CLI_AGENT_CONFIGS` 新增条目；`run_prompt_executor()` / `run_prompt_executor_async()` 各新增一个 `if executor_name == "codex":` 分支

**实现要点**：

1. **`CODEX_CONFIG`**：
   ```python
   CODEX_CONFIG = CLIAgentConfig(
       executor_name="codex",
       display_name="Codex",
       bin_env_var="AIWF_CODEX_BIN",
       default_bin="codex",
       fixed_args=("exec",),
       output_path_flags=("-o",),
   )
   ```
   - `fixed_args=("exec",)`：`codex exec <prompt>` 是 non-interactive 模式
   - `output_path_flags=("-o",)`：`codex exec -o <output_path> <prompt>` 将 agent 最终输出写入文件
   - `workspace_root_flags` 留空：`codex exec` 默认使用 cwd 作为 workspace root

2. **CLI_AGENT_CONFIGS 注册**：
   ```python
   CLI_AGENT_CONFIGS = {
       AIDER_CONFIG.executor_name: AIDER_CONFIG,
       CLAUDE_CODE_CONFIG.executor_name: CLAUDE_CODE_CONFIG,
       CODEX_CONFIG.executor_name: CODEX_CONFIG,
   }
   ```

3. **Dispatch 分支**（两个函数各加一段）：
   ```python
   if executor_name == "codex":
       return run_cli_agent_executor(
           CODEX_CONFIG, state, retrieval_items, prompt,
           visited_routes=visited_routes,
           original_route_name=original_route_name,
       )
   ```
   - 位置：紧接 `if executor_name == "claude-code":` 之后、`raise UnknownExecutorError` 之前

4. **codex exec 参数传递方式确认**：
   - `run_cli_agent_executor()` 当前通过 stdin pipe + subprocess 传 prompt。`codex exec` 支持 positional prompt 参数或 stdin（"If not provided as an argument (or if `-` is used), instructions are read from stdin"）
   - 如当前 `run_cli_agent_executor()` 使用 stdin pipe 传 prompt，则 `codex exec` 也可直接兼容（stdin 读取）
   - 如当前使用 positional argument 传 prompt，则 `codex exec` 对长 prompt 可能超出命令行长度限制。需检查 `run_cli_agent_executor()` 实现
   - 万一 stdin 不可用，`codex exec` 也支持 `"prompt"` 作为 positional argument

**风险评级**：
- 影响范围: 1（仅 executor.py，新增配置 + dispatch 分支）
- 可逆性: 1（删除配置 + 分支即回滚）
- 依赖复杂度: 2（依赖 `codex` binary 可用 + `codex exec` stdin 兼容性）
- **总分: 4（低风险）**

**验收条件**：
- `CLI_AGENT_CONFIGS["codex"]` 返回 `CODEX_CONFIG`
- `run_prompt_executor` 对 `executor_name="codex"` 不触发 `UnknownExecutorError`
- pytest mock 覆盖 codex dispatch 分支

---

### S3: Doctor 探针扩展

**目标**：`swl doctor` 输出中包含 codex binary 可用性信息。

**影响范围**：
- `src/swallow/doctor.py` — 扩展 `diagnose_executor()` 或新增 `diagnose_cli_agents()` 函数
- `src/swallow/cli.py` — `swl doctor` 命令下展示 codex 探针结果（如新增函数）

**实现要点**：

1. **方案选择**：新增 `diagnose_cli_agents()` 函数，返回各 CLI agent binary 的可用性和版本信息，保持 `diagnose_executor()` 不变（向后兼容）。

2. **`diagnose_cli_agents()`**：
   - 遍历 `CLI_AGENT_CONFIGS.values()`
   - 对每个 config：`shutil.which(os.environ.get(config.bin_env_var, config.default_bin))`
   - 找到 binary 后尝试 `<bin> --version`，记录版本号
   - 返回 `list[CLIAgentDoctorResult]`，每条包含 `executor_name`, `binary_found`, `binary_path`, `version`

3. **CLI 展示**：
   - `swl doctor` 的 `format_executor_doctor_result()` 之后新增 CLI agents 区块
   - 每个 agent 一行：`codex: found at /path/to/codex (codex-cli 0.125.0)` 或 `codex: not found`

**风险评级**：
- 影响范围: 1（doctor.py + cli.py 展示层）
- 可逆性: 1（新增函数，不改已有行为）
- 依赖复杂度: 1（只依赖 `shutil.which` + subprocess）
- **总分: 3（最低风险）**

**验收条件**：
- `swl doctor` 输出包含 codex binary 状态
- pytest mock 覆盖 binary found / not found 两种场景

---

## 依赖说明

```
S1 (route + alias) — 独立，无前置依赖
S2 (executor config + dispatch) — 依赖 S1 的 EXECUTOR_ALIASES["codex"] 条目
S3 (doctor) — 独立，无前置依赖（读取 CLI_AGENT_CONFIGS，但可以在 S2 的 CODEX_CONFIG 之前实现）
```

**推荐实施顺序**：S1 → S2 → S3

S1 定义 route + executor alias，S2 紧随新增 executor config + dispatch（依赖 S1 的 `"codex"` executor alias），S3 最后（独立的 doctor 探针，可并行但逻辑上放最后更自然）。

## 明确的非目标

1. **不重构 `run_prompt_executor` if-chain** — 3 个 CLI agent 的 if-chain 可管理，不引入 config-driven dispatch
2. **不修改 `_apply_complexity_bias()`** — codex 不进入 complexity bias 映射，保持 low→aider / high→claude-code
3. **不处理 `local-cline` alias** — 保留不动
4. **不做 Codex CLI 深度集成** — 不透传 sandbox 配置、session resume、多模型切换
5. **不引入自动 capability 学习** — 初始 `task_family_scores` 为空
6. **不新增 Python 依赖** — doctor 探针使用 `shutil.which` + `subprocess`
