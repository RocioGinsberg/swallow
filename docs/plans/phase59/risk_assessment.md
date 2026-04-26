---
author: claude
phase: 59
slice: risk-assessment
status: draft
depends_on:
  - docs/plans/phase59/design_decision.md
---

## TL;DR

Phase 59 总体风险极低。所有改动均为 additive 配置新增，不修改已有路由、dispatch 或降级逻辑。最大风险点是 `codex exec` 的 stdin prompt 兼容性和 binary 参数稳定性，但现有 `run_cli_agent_executor()` 框架已处理 stdin pipe 和 output capture，Codex CLI 也明确支持 stdin 读取。无高风险 slice，无需 Design Gate 之外的额外人工 gate。

# Phase 59 Risk Assessment

## 风险矩阵总览

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 风险级别 |
|-------|---------|--------|-----------|------|---------| 
| S1: Route 注册 + Alias 迁移 | 1 | 1 | 1 | **3** | 最低 |
| S2: Executor 配置 + Dispatch | 1 | 1 | 2 | **4** | 低 |
| S3: Doctor 探针 | 1 | 1 | 1 | **3** | 最低 |

所有 slice 总分 < 7，无高风险 slice。

## S1: Route 注册 + Alias 迁移 — 详细风险分析

### R1.1 移除 alias 后的 route_weights 影响

**风险**：operator 可能在 `.swl/route_weights.json` 中通过旧 alias 写入过 `local-codex` 权重。移除 alias 后，`normalize_route_name("local-codex")` 返回 `"local-codex"` 而非 `"local-aider"`，权重会关联到新 route。

**缓解**：这是期望行为——旧权重本来就是为"codex"设定的（尽管实际执行的是 aider）。系统只有一个 operator，且 route weights 通常由 Meta-Optimizer 提案生成。即使需要重新校准，只需运行 `swl route weights` 手动调整。

**残余风险**：极低。

### R1.2 `local-cline` alias 意外移除

**风险**：修改 `ROUTE_NAME_ALIASES` 时误删 `local-cline -> local-claude-code` 条目。

**缓解**：设计明确只移除一个条目。pytest 应断言 `normalize_route_name("local-cline")` 仍返回 `"local-claude-code"`。

**残余风险**：几乎为零（有测试保护）。

### R1.3 telemetry 中 `local-codex` 的语义变更

**风险**：旧 telemetry 中 `physical_route: local-codex` 指的是 aider 在执行。新 route 注册后，同一 route name 指的是 codex 在执行。历史 telemetry 解读可能混淆。

**缓解**：telemetry 不回溯修改；operator 理解上下文即可。Meta-Optimizer 的 route health stats 基于事件时间窗口聚合，旧事件自然过期。

## S2: Executor 配置 + Dispatch — 详细风险分析

### R2.1 `codex exec` stdin prompt 兼容性

**风险**：`run_cli_agent_executor()` 通过 stdin pipe 传递 prompt。`codex exec` 的 help 说明："If not provided as an argument (or if `-` is used), instructions are read from stdin. If stdin is piped and a prompt is also provided, stdin is appended as a `<stdin>` block."

**缓解**：stdin pipe 是 `codex exec` 的预期输入方式之一。只需确保 `run_cli_agent_executor()` 不同时传 positional prompt 和 stdin（否则 stdin 会作为额外 block 追加）。当前框架通过 stdin 传递，positional 为空，这正好匹配 codex exec 的 stdin-only 模式。

**残余风险**：低。需在实现时验证 `run_cli_agent_executor()` 的精确 subprocess 参数构造。

### R2.2 `codex exec` output capture

**风险**：`run_cli_agent_executor()` capture stdout 作为 executor 输出。`codex exec` 的输出默认包含事件流，`-o <file>` 将最终 message 写入文件，`--json` 输出 JSONL。

**缓解**：如果使用 `-o <output_path>`，输出路径由 `output_path_flags=("-o",)` 控制，`run_cli_agent_executor()` 已有从文件读取输出的机制。如果直接 capture stdout，需要确认 `codex exec` 的 stdout 内容是否是 agent 最终响应。实现时应测试两种模式，选择最稳定的。

**残余风险**：中低。这是 S2 唯一需要实际验证的点。

### R2.3 `codex` binary 参数不稳定

**风险**：`codex-cli 0.125.0` 处于活跃开发期（OpenAI 产品），`exec` 子命令的 flag 可能变化。

**缓解**：`fixed_args=("exec",)` 只包含核心子命令，不依赖不稳定 flag。`-o` 是输出重定向的标准 pattern，不太可能改动。如未来 flag 变化，只需修改 `CODEX_CONFIG.fixed_args`。

**残余风险**：低。Codex CLI 的 `exec` 子命令在 `--help` 中有明确文档，是 stable 入口。

### R2.4 `codex` binary 不在 PATH

**风险**：在非 workstation 环境（CI / 其他开发者）上 `codex` binary 不存在。

**缓解**：`run_cli_agent_executor()` 已有 binary 不存在时的错误处理（降级到 fallback route）。`AIWF_CODEX_BIN` 环境变量可自定义 binary 路径。Doctor 探针（S3）会预先检查可用性。

## S3: Doctor 探针 — 详细风险分析

### R3.1 `codex --version` 输出格式

**风险**：`diagnose_cli_agents()` 解析 `codex --version` 输出获取版本号。输出格式可能变化。

**缓解**：只需检查 exit code 为 0 即可判断 binary 可用性。版本号解析只是额外信息，格式变化不影响可用性判断。

**残余风险**：几乎为零。

## 系统性风险评估

### 向后兼容性

Phase 59 移除一个 route alias 并新增一个 route。这是 breaking change——但 break 的是 alias 行为（`local-codex` 不再映射到 aider），而这正是我们想要的。所有其他 route（`local-aider` / `local-claude-code` / HTTP routes）行为不变。

### 测试策略

- S1：mock `RouteRegistry`，验证 `local-codex` 独立注册 + `local-cline` alias 保留
- S2：mock `subprocess.run`，验证 `CODEX_CONFIG` dispatch 到正确的 binary + args
- S3：mock `shutil.which` + `subprocess.run`，验证 binary found / not found 两种场景

## 结论

Phase 59 风险极低，所有 slice 总分 ≤ 4。改动完全是 additive（新增配置实例 + 移除一个 alias）。唯一需要实现时验证的点是 `codex exec` 的 stdin/stdout 交互模式，但框架已支持且 Codex CLI 文档明确支持 stdin 输入。建议按设计顺序实施；通过既有 Design Gate 即可。
