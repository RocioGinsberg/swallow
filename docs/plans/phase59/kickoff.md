---
author: claude
phase: 59
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase58/closeout.md
  - docs/plans/phase59/context_brief.md
  - docs/roadmap.md
---

## TL;DR

Phase 59 将 `local-codex` 从 `local-aider` 的 legacy alias 升级为独立 CLI route，让 Codex CLI（`codex-cli`）与 Aider / Claude Code 成为三足鼎立的 CLI agent 生态。scope 限定为 route 注册 + executor 配置 + doctor 探针 + alias 迁移，不做 dispatch 重构或 capability 自动学习。

# Phase 59 Kickoff: Codex CLI Route 接入

## Phase 身份

- **Phase**: 59
- **Primary Track**: CLI / Routing
- **Secondary Track**: —
- **分支建议**: `feat/phase59-codex-cli-route`
- **Roadmap 对应**: 候选 B（CLI Agent 生态完善）

## 背景与动机

当前系统有两个真实 CLI agent route（`local-aider` / `local-claude-code`），以及一个 legacy alias `local-codex -> local-aider`。OpenAI 的 Codex CLI（`codex-cli 0.125.0`）已安装在 workstation 上，具备沙盒代码执行能力，但系统无法将其作为独立路由使用——所有对 `local-codex` 的引用都会静默映射到 Aider 的配置。

这意味着：
1. **路由语义不准确**：telemetry 中的 `physical_route: local-codex` 实际执行的是 aider
2. **能力画像无法独立**：无法为 Codex CLI 设置独立的 `task_family_scores` / `unsupported_task_types`
3. **降级矩阵不完整**：三个 CLI agent 应各有独立降级路径
4. **doctor 无法诊断**：`swl doctor` 只检查 aider binary，不知道 codex 是否可用

Phase 59 的目标是消除 alias，让 Codex CLI 成为系统中的一等公民。

## 目标

1. **G1 — `local-codex` 真实 route 注册**：在 `_build_builtin_route_registry()` 新增独立 `local-codex` RouteSpec，移除 `ROUTE_NAME_ALIASES` 中的 `local-codex -> local-aider` 映射
2. **G2 — `CODEX_CONFIG` executor 配置**：新增 `CLIAgentConfig` 实例，配置 `codex exec` non-interactive 入口
3. **G3 — executor dispatch 对接**：在 `run_prompt_executor()` / `run_prompt_executor_async()` 新增 `codex` 分支
4. **G4 — doctor 探针扩展**：`swl doctor` 能报告 codex binary 可用性

## 非目标

- **dispatch 架构重构**：不把 `run_prompt_executor` if-chain 改为 config-driven dict dispatch。当前 3 个 CLI agent 的 if-chain 可管理，重构应在第 4 个 CLI agent 出现时再考虑
- **capability 自动学习**：不在本轮实现 Codex 的自动 `task_family_scores` 填充。初始画像为空，由 Meta-Optimizer 遥测后续自然积累
- **Cline 兼容恢复**：不在本轮恢复或保留 `local-cline` alias；避免继续制造 route 语义误解
- **complexity bias 修改**：`_apply_complexity_bias()` 当前对 `low/routine` 偏好 aider、`high` 偏好 claude-code。不在本轮为 codex 新增 complexity tier，保持现有偏好不变
- **Codex CLI 深度集成**：不做 Codex 的 session resume、sandbox 配置透传、多模型切换等高级功能
- **route_weights / route_capabilities 迁移工具**：如 `.swl/route_weights.json` 中有 `local-codex` 条目（通过旧 alias 写入），alias 移除后会自然关联到新 route。不需要专门迁移工具

## 设计边界

### S1: Route 注册 + Alias 迁移

**行为**：
- `ROUTE_NAME_ALIASES` 移除 `"local-codex": "local-aider"` 条目
- `_build_builtin_route_registry()` 新增 `local-codex` RouteSpec：
  - `executor_name="codex"`
  - `backend_kind="local_cli"`
  - `dialect_hint="plain_text"`
  - `fallback_route_name="local-summary"`（与 aider / claude-code 对齐）
  - `executor_family="cli"`, `execution_site="local"`
  - `capabilities` = `code_execution` + `supports_tool_loop=True` + `workspace_write`（与 aider / claude-code 对齐）
- `EXECUTOR_ALIASES` 新增 `"codex": "codex"` 显式条目

### S2: Executor 配置 + Dispatch

**行为**：
- `executor.py` 新增 `CODEX_CONFIG = CLIAgentConfig(...)`：
  - `executor_name="codex"`
  - `display_name="Codex"`
  - `bin_env_var="AIWF_CODEX_BIN"`
  - `default_bin="codex"`
  - `fixed_args=("exec",)` — 使用 `codex exec <prompt>` 非交互模式
  - `output_path_flags=("-o",)` — `codex exec -o <path>` 输出到文件
- `CLI_AGENT_CONFIGS` 新增 `CODEX_CONFIG` 条目
- `run_prompt_executor()` / `run_prompt_executor_async()` 新增 `if executor_name == "codex":` 分支

### S3: Doctor 探针

**行为**：
- `diagnose_executor()` 扩展或新增函数，检查 codex binary 可用性
- `swl doctor` 输出中能看到 codex binary 是否在 PATH 中、版本信息
- 保持现有 aider binary 检查不变

## 完成条件

1. **`local-codex` 可作为独立 route 使用**：`swl task create --executor codex` 走 codex 而非 aider
2. **alias 已移除**：`normalize_route_name("local-codex")` 返回 `"local-codex"` 而非 `"local-aider"`
3. **executor dispatch 正确**：`run_prompt_executor` 对 `codex` executor_name 分发到 `CODEX_CONFIG`
4. **doctor 能诊断 codex**：`swl doctor` 输出中包含 codex binary 状态
5. **现有行为无回归**：`local-aider` / `local-claude-code` 行为不变
6. **测试覆盖**：route 注册 / alias 移除 / executor dispatch / doctor 探针均有 pytest 覆盖

## Eval 验收条件

| Slice | 需要 Eval | 说明 |
|-------|----------|------|
| S1 (route + alias) | 否 | 配置变更，pytest 覆盖即可 |
| S2 (executor config + dispatch) | 否 | 确定性 dispatch，pytest 覆盖即可 |
| S3 (doctor) | 否 | binary 探测，pytest + mock 覆盖即可 |

## Branch Advice

- 当前分支: `main`（Phase 58 待合并后）
- 建议操作: 新建分支
- 理由: Phase 58 已收口，Phase 59 应在新 feature branch 上开发
- 建议分支名: `feat/phase59-codex-cli-route`
- 建议 PR 范围: S1-S3 合入单个 PR
