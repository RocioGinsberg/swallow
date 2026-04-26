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

Phase 60 的核心风险不是自主 CLI coding path "降智"：aider / claude-code / codex 的代码库上下文主路径是 tool-loop 自主读文件，而不是 retrieval repo chunk。真正需要控制的是代码库问答 / 代码分析任务被误路由到 HTTP 后缺少 repo 上下文，以及 route 判定过宽导致 non-agent fallback / test route 被误收紧。方案已收窄为 capability-based 判定，并把 repo source 降级为 explicit override 或 legacy fallback 辅助源，整体风险评级为**中**，可控。

# Phase 60 Risk Assessment: 路径感知的 Retrieval Policy

## 风险矩阵

| 风险 | 影响范围 | 可逆性 | 依赖复杂度 | 综合评级 |
|------|---------|--------|-----------|---------|
| R1: 代码库任务误路由到 HTTP 后上下文不足 | 中（HTTP codebase Q&A / analysis 质量） | 高（改 route 或 S3 override 可恢复） | 低 | **中** |
| R2: `executor_family` 默认值 / 非自主 CLI route 干扰 | 中（fallback / test route retrieval） | 高（capability guard + fallback 可恢复） | 低 | **中** |
| R3: legacy fallback 继续携带 repo 噪声 | 低（非主路径 fallback 输出质量） | 高（policy 可继续收紧） | 低 | **低** |
| R4: 测试覆盖不足导致 regression | 中（已有 220 个 CLI 测试） | 高（测试可补） | 低 | **低-中** |
| R5: `"notes"` source_type 双重含义 | 低（CLI 去掉 notes 可能丢失部分 .md 上下文） | 高（override 可恢复） | 低 | **低** |

---

## 风险详情

### R1: 代码库任务误路由到 HTTP 后上下文不足

**描述**：Phase 60 不再把 HTTP `execution` / `extraction` / `retrieval` task_family 自动配置为 `["repo", "notes", "knowledge"]`。如果代码库问答、源码分析或代码修改任务被错误路由到 HTTP executor，而 operator 又没有显式请求 repo source，HTTP prompt 将只获得 `["knowledge", "notes"]`，可能缺少当前 repo 文件上下文。

**可能性**：中。当前系统已有 route capability / execution_kind 信号，但 operator 也可能显式选择 HTTP route，或 future router 对 task intent 判断不准。该风险来自误路由，而不是 CLI agent 去掉 repo chunk 后能力下降。

**影响**：中。HTTP executor 不具备自主 repo exploration loop；如果任务确实依赖当前工作区代码，knowledge / notes 无法替代源码读取。

**缓解**：
1. 代码库问答 / 代码修改任务优先路由到 `autonomous_cli_coding` family，由 aider / claude-code / codex tool-loop 主动读取 repo
2. S3 的 explicit override 机制：operator 可通过 `task_semantics["retrieval_source_types"] = ["repo", "notes", "knowledge"]` 明确请求 repo chunk
3. 若后续需要 HTTP 源码分析，应新增更精确的 source intent 或单独 route policy，而不是恢复所有 HTTP execution 默认 repo

**验收**：S2/S3 完成后，HTTP execution / extraction / retrieval 默认不含 repo；override case 可以恢复 repo；代码库任务的推荐路由在文档中明确指向 autonomous CLI coding route。

---

### R2: `executor_family` 默认值 / 非自主 CLI route 干扰

**描述**：`TaskState` 的 `route_executor_family` 字段默认值为 `"cli"`。此外，`executor_family="cli"` 还覆盖 `local-mock` / `local-note` / `local-summary` / `mock-remote` 等非自主 fallback / test route。若 policy 只按 `executor_family == "cli"` 判断，会错误把这些路径收紧为 `["knowledge"]`。

**可能性**：中。主路径调用顺序为：路由选择 → `build_task_retrieval_request()` → retrieval；但直接构造 `TaskState` 的测试、fallback route 和 future bypass path 都可能暴露默认值问题。

**影响**：中。非自主 route 不具备 CLI agent 的自主 repo exploration 能力，误过滤 repo / notes 会降低 fallback 路径质量，也会让测试语义混乱。

**缓解**：
1. S1 不使用裸 `executor_family == "cli"`，而是使用 capability guard：`supports_tool_loop=True` 且 `execution_kind="code_execution"` 时才进入 autonomous CLI coding policy
2. route capability 缺失或不完整时不进入 autonomous CLI coding policy；未知 route fallback 到 `["knowledge", "notes"]`，明确识别的 non-autonomous local fallback 才保留 legacy 三源
3. 测试覆盖 autonomous CLI route、non-autonomous CLI route、`route_executor_family=""` fallback 三类行为

**验收**：S1 测试中包含 `local-aider/local-codex` 等 autonomous CLI case、`local-summary/local-mock` 等 non-autonomous CLI case，以及 `route_executor_family=""` 的 fallback case。

---

### R3: legacy fallback 继续携带 repo 噪声

**描述**：为避免误伤 `local-summary` / `local-note` / `local-mock` / `mock-remote` 等非自主 route，Phase 60 允许明确识别的 `legacy_local_fallback` family 暂保留 `["repo", "notes", "knowledge"]`。这会保留一部分旧 repo chunk 噪声。

**可能性**：中。fallback route 不具备自主 repo exploration，因此直接收紧可能带来兼容风险；短期保留旧行为更安全。

**影响**：低。这些 route 不是 Phase 60 的核心价值路径；repo 噪声只影响 fallback / test / deterministic 输出，不影响 autonomous CLI 与 HTTP 主策略。

**缓解**：
1. 文档中明确 legacy fallback 是兼容分支，不是主设计目标
2. 测试固定 autonomous CLI / HTTP / legacy fallback 的差异，避免后续误把 legacy fallback 扩成全局默认
3. 若真实使用证明 fallback 不需要 repo，可在后续 phase 继续收紧

**验收**：S1/S2 测试覆盖 legacy fallback 保留旧三源，同时覆盖未知 route 不默认启用 repo。

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

**描述**：`"notes"` source_type 由 `MARKDOWN_ADAPTER` 处理，覆盖所有 `.md` 文件（包括 `docs/`、`results/` 等），而非 staged knowledge raw。Phase 60 将 HTTP 默认收紧为 knowledge + notes，仍会保留 markdown 文档检索；autonomous CLI coding path 去掉 notes 后，CLI agent 在 retrieval 阶段将不再获得 `.md` chunk。

**可能性**：低。CLI agent 在执行过程中可以自主读取 `.md` 文件，retrieval 阶段的 notes chunk 对 CLI path 的实际贡献有限。

**影响**：低。CLI agent 的自主探索能力覆盖了这个缺口。若特定场景需要 notes，operator 可通过 override 恢复。

**缓解**：
1. S3 的 explicit override 机制
2. 若后续发现自主 CLI coding path 需要 notes，可在 policy 表中调整为 `("autonomous_cli_coding", "*"): ["knowledge", "notes"]`

**验收**：S1 完成后，观察 CLI 相关测试是否有因去掉 notes 导致的失败；若有，优先评估是否应由 CLI tool-loop 显式读取文档，而不是恢复默认 notes chunk。

---

## 调用顺序核实清单（S1 实现前 Codex 需确认）

Codex 在实现 S1 之前，需要核实以下调用点的 `route_executor_family` 写入时机：

- [ ] `orchestrator.py` 主任务执行路径：`select_route()` → `build_task_retrieval_request()` 的顺序
- [ ] `orchestrator.py` fan-out 子任务路径：子任务执行是否复用父任务 retrieval request，而不是重新按未初始化 state 构造 request
- [ ] `harness.py` 中是否有直接调用 `build_task_retrieval_request()` 的路径（context_brief 显示 harness 只做透传，但需确认）
- [ ] non-autonomous CLI route（`local-summary` / `local-note` / `local-mock` / `mock-remote`）是否明确落入 `legacy_local_fallback`，并仅作为兼容分支保留旧三源
- [ ] HTTP execution / extraction / retrieval 是否默认使用 `["knowledge", "notes"]`，需要 repo 时是否只能通过 explicit override 恢复

若发现调用顺序或 route capability 缺失问题，在 S1 的 PR 中一并修复，不延后到 S2/S3。

---

## 整体评估

Phase 60 的改动面集中在 `orchestrator.py` 的一个函数，不触碰 retrieval 管线内部，不修改 models 的核心字段（S3 只添加可选 key），不修改路由逻辑。主要风险（R1/R2）均有明确的缓解路径：代码库任务走 autonomous CLI route 或 explicit override；非自主 fallback route 通过 capability guard 保持兼容。

**综合评级：中（可控）**

建议 Codex 在 S1 实现时优先核实 R2（调用顺序），这是唯一可能导致静默错误的风险。其余风险在测试阶段可以发现和修复。
