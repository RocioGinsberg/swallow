---
author: claude
phase: 60
slice: risk_assessment
status: draft
depends_on:
  - docs/plans/phase60/kickoff.md
  - docs/plans/phase60/design_decision.md
  - docs/plans/phase60/context_brief.md
---

## TL;DR

Phase 60 的核心风险是自主 CLI coding path recall 下降（去掉 repo chunk 后，aider / claude-code / codex 任务若依赖 repo 上下文则可能降质）和 route 判定过宽（`executor_family="cli"` 还覆盖 non-agent fallback / test route）。方案已收窄为 capability-based 判定，整体风险评级为**中**，可控。

# Phase 60 Risk Assessment: 路径感知的 Retrieval Policy

## 风险矩阵

| 风险 | 影响范围 | 可逆性 | 依赖复杂度 | 综合评级 |
|------|---------|--------|-----------|---------|
| R1: 自主 CLI coding path recall 下降 | 中（CLI coding 任务质量） | 高（S3 override 可恢复） | 低 | **中** |
| R2: `executor_family` 默认值 / 非自主 CLI route 干扰 | 中（fallback / test route retrieval） | 高（capability guard + fallback 可恢复） | 低 | **中** |
| R3: `infer_task_family()` 覆盖面不足 | 低（HTTP 细分效果有限） | 高（fallback 保持现有行为） | 低 | **低** |
| R4: 测试覆盖不足导致 regression | 中（已有 220 个 CLI 测试） | 高（测试可补） | 低 | **低-中** |
| R5: `"notes"` source_type 双重含义 | 低（CLI 去掉 notes 可能丢失部分 .md 上下文） | 高（override 可恢复） | 低 | **低** |

---

## 风险详情

### R1: 自主 CLI coding path recall 下降

**描述**：自主 CLI coding path 从 `["repo", "notes", "knowledge"]` 收紧为 `["knowledge"]` 后，原本通过 repo chunk 或 notes chunk 提供的上下文将不再注入 retrieval 结果。若某些 aider / claude-code / codex 任务依赖这些 chunk 作为补充上下文（如任务 goal 中引用了 repo 中的特定文件内容），可能出现 recall 下降。

**可能性**：中。CLI agent（aider / claude-code / codex）在执行过程中会自主读取 repo 文件，因此 retrieval 阶段的 repo chunk 对 CLI path 的实际贡献本就有限。但对于"任务 goal 中包含 repo 路径引用"的场景，retrieval 阶段的 repo chunk 可能提供有价值的预加载上下文。

**影响**：中。CLI 任务质量可能在特定场景下下降，但 CLI agent 的自主探索能力是天然的 recall 补偿机制。

**缓解**：
1. S3 的 explicit override 机制：operator 可通过 `task_semantics["retrieval_source_types"] = ["repo", "notes", "knowledge"]` 恢复原始行为
2. 若后续真实使用中出现 recall 问题，可在 policy 表中为特定 task_family 恢复 repo（如 `("cli", "execution"): ["repo", "knowledge"]`）

**验收**：S1 完成后，在已有 CLI 相关测试中确认无 regression；如有 recall 问题，通过 override 机制修复。

---

### R2: `executor_family` 默认值 / 非自主 CLI route 干扰

**描述**：`TaskState` 的 `route_executor_family` 字段默认值为 `"cli"`。此外，`executor_family="cli"` 还覆盖 `local-mock` / `local-note` / `local-summary` / `mock-remote` 等非自主 fallback / test route。若 policy 只按 `executor_family == "cli"` 判断，会错误把这些路径收紧为 `["knowledge"]`。

**可能性**：中。主路径调用顺序为：路由选择 → `build_task_retrieval_request()` → retrieval；但直接构造 `TaskState` 的测试、fallback route 和 future bypass path 都可能暴露默认值问题。

**影响**：中。非自主 route 不具备 CLI agent 的自主 repo exploration 能力，误过滤 repo / notes 会降低 fallback 路径质量，也会让测试语义混乱。

**缓解**：
1. S1 不使用裸 `executor_family == "cli"`，而是使用 capability guard：`supports_tool_loop=True` 且 `execution_kind="code_execution"` 时才进入 autonomous CLI coding policy
2. route capability 缺失或不完整时 fallback 到 `["repo", "notes", "knowledge"]`
3. 测试覆盖 autonomous CLI route、non-autonomous CLI route、`route_executor_family=""` fallback 三类行为

**验收**：S1 测试中包含 `local-aider/local-codex` 等 autonomous CLI case、`local-summary/local-mock` 等 non-autonomous CLI case，以及 `route_executor_family=""` 的 fallback case。

---

### R3: `infer_task_family()` 覆盖面不足

**描述**：`infer_task_family(state)` 从 `state.task_semantics["source_kind"]` 推断，大多数普通任务可能都被归为 `"execution"`（或 fallback 到默认值）。若 HTTP path 的大多数任务都走 `"execution"` 分支，S2 的 brainstorm/planning 细分效果会很有限。

**可能性**：中。`task_family` 推断依赖 `source_kind` 字段，而 `source_kind` 的填充质量取决于 operator 的任务配置习惯。

**影响**：低。S2 的 fallback 保持现有行为（`["repo", "notes", "knowledge"]`），不引入 regression。HTTP 任务在 task_family 未知时行为与 Phase 59 完全一致。

**缓解**：
1. S2 的 fallback 条目 `("*", "*")` 保证向后兼容
2. 若 `infer_task_family()` 覆盖面不足，可在后续 phase 扩展推断逻辑（不在本 phase 范围）

**验收**：S2 测试覆盖 `task_family="execution"` 和未知 task_family 的 fallback 行为，确认无 regression。

---

### R4: 测试覆盖不足导致 regression

**描述**：`build_task_retrieval_request()` 的改动会影响所有依赖其输出的测试。`tests/test_cli.py` 有大量 CLI 测试，其中部分可能 mock retrieval 输出或断言 source_types。

**可能性**：低-中。大多数测试 mock `retrieve_context()` 而非 `build_task_retrieval_request()`，但需要确认。

**影响**：中。若有测试断言 `source_types=["repo", "notes", "knowledge"]` 且对应 state 是自主 CLI coding route，这些测试会因 policy 变更而失败；非自主 CLI route 的旧断言应继续成立。

**缓解**：
1. S1 实现后立即运行全量 pytest，识别因 policy 变更导致的测试失败
2. 对于合理的测试失败（测试断言了旧的 source_types），更新测试以反映新 policy
3. 对于不合理的测试失败（测试逻辑本身有问题），单独修复

**验收**：S1/S2/S3 完成后，全量 pytest 通过（允许因 policy 变更而更新的测试断言，不允许新的 regression）。

---

### R5: `"notes"` source_type 双重含义

**描述**：`"notes"` source_type 由 `MARKDOWN_ADAPTER` 处理，覆盖所有 `.md` 文件（包括 `docs/`、`results/` 等），而非仅 staged notes。CLI path 去掉 `"notes"` 后，CLI agent 在 retrieval 阶段将不再获得任何 `.md` 文件的 chunk，包括可能有用的文档片段。

**可能性**：低。CLI agent 在执行过程中可以自主读取 `.md` 文件，retrieval 阶段的 notes chunk 对 CLI path 的实际贡献有限。

**影响**：低。CLI agent 的自主探索能力覆盖了这个缺口。若特定场景需要 notes，operator 可通过 override 恢复。

**缓解**：
1. S3 的 explicit override 机制
2. 若后续发现自主 CLI coding path 需要 notes，可在 policy 表中调整为 `("autonomous_cli_coding", "*"): ["knowledge", "notes"]`

**验收**：S1 完成后，观察 CLI 相关测试是否有因去掉 notes 导致的失败；若有，评估是否需要调整 policy。

---

## 调用顺序核实清单（S1 实现前 Codex 需确认）

Codex 在实现 S1 之前，需要核实以下调用点的 `route_executor_family` 写入时机：

- [ ] `orchestrator.py` 主任务执行路径：`select_route()` → `build_task_retrieval_request()` 的顺序
- [ ] `orchestrator.py` fan-out 子任务路径：子任务执行是否复用父任务 retrieval request，而不是重新按未初始化 state 构造 request
- [ ] `harness.py` 中是否有直接调用 `build_task_retrieval_request()` 的路径（context_brief 显示 harness 只做透传，但需确认）
- [ ] non-autonomous CLI route（`local-summary` / `local-note` / `local-mock` / `mock-remote`）是否保持默认三源

若发现调用顺序或 route capability 缺失问题，在 S1 的 PR 中一并修复，不延后到 S2/S3。

---

## 整体评估

Phase 60 的改动面集中在 `orchestrator.py` 的一个函数，不触碰 retrieval 管线内部，不修改 models 的核心字段（S3 只添加可选 key），不修改路由逻辑。主要风险（R1/R2）均有明确的缓解路径和 fallback 机制。

**综合评级：中（可控）**

建议 Codex 在 S1 实现时优先核实 R2（调用顺序），这是唯一可能导致静默错误的风险。其余风险在测试阶段可以发现和修复。
