---
author: claude/context-analyst
phase: phase66
slice: context-brief
status: draft
depends_on:
  - docs/roadmap.md
  - docs/active_context.md
  - docs/concerns_backlog.md
  - docs/plans/phase61/closeout.md
  - docs/plans/phase62/closeout.md
  - docs/plans/phase63/closeout.md
  - docs/plans/phase64/closeout.md
  - docs/plans/phase65/closeout.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
  - src/swallow/   # 整目录 reference
---

TL;DR: Phase 66 is a read-only audit of `src/swallow/` split into 5 blocks; no code, tests, or docs are modified. The codebase is stable post-v1.4.0 (Phase 65 merged 2026-04-30). Unassigned files from the original 5-block spec total ~9 400 LOC and must be distributed before Codex starts scanning. Highest-risk audit surface is Block 5 (`cli.py` 3 832 lines, `orchestrator.py` 3 882 lines) and Block 4 (multi-era knowledge stack, highest expected dead-code density). Estimated total finding count: 40–80 items across 5 blocks before triage.

---

## 1. 完整覆盖性核查

`find src/swallow -name '*.py'` 返回 70 个文件。原始 5 块拆分覆盖 41 个文件。**29 个文件未分配**，按功能归属建议如下：

### 归入块 2（Orchestration）

| 文件 | LOC | 理由 |
|------|-----|------|
| `harness.py` | 1 950 | 主 run_task / run_task_async 入口，编排主链路顶层 |
| `subtask_orchestrator.py` | 460 | subtask fan-out 编排 |
| `planner.py` | 227 | 部分一等化的 Planner 组件 |
| `execution_budget_policy.py` | 216 | 执行预算策略，与 dispatch_policy 同层 |
| `retry_policy.py` | 172 | 执行重试策略 |
| `stop_policy.py` | 154 | 执行停止策略 |
| `review_gate.py` | 649 | debate/review 循环，编排层协作 |
| `validator.py` | 121 | Validator 实现 |
| `validator_agent.py` | 106 | ValidatorAgent 封装 |
| `models.py` | 1 042 | 核心 dataclass / event type 常量，编排层共享 |
| `runtime_config.py` | 61 | 运行时配置读取 |
| `compatibility.py` | 203 | 兼容性 shim 层 |

块 2 实际 LOC（加入上述文件后）：**≈ 12 168**（原估 6 767 + 5 161）

### 归入块 4（Knowledge & Retrieval）

| 文件 | LOC | 理由 |
|------|-----|------|
| `canonical_registry.py` | 222 | canonical 知识注册表，知识治理层 |
| `canonical_reuse.py` | 66 | canonical 重用策略 |
| `canonical_reuse_eval.py` | 377 | canonical 重用评估，Phase 47-55 沉淀 |
| `canonical_audit.py` | 95 | canonical 审计辅助 |
| `knowledge_index.py` | 113 | 知识索引构建 |
| `knowledge_relations.py` | 121 | 知识关系图 |
| `knowledge_suggestions.py` | 191 | 知识建议生成 |
| `grounding.py` | 84 | grounding 证据绑定 |
| `retrieval_adapters.py` | 767 | 神经 embedding / vector 检索适配 |

块 4 实际 LOC（加入上述文件后）：**≈ 5 827**（原估 3 791 + 2 036）

### 归入块 5（Surface & Tools）

| 文件 | LOC | 理由 |
|------|-----|------|
| `doctor.py` | 489 | `swl doctor` CLI 子命令，Surface 层 |
| `consistency_reviewer.py` | 108 | 一致性审查工具 |
| `capabilities.py` | 78 | capability 常量，Surface 消费 |
| `librarian_executor.py` | 518 | LibrarianAgent Executor 实现，Specialist Surface 层 |
| `ingestion_specialist.py` | 90 | IngestionAgent Executor |
| `literature_specialist.py` | 455 | LiteratureAgent Executor |
| `quality_reviewer.py` | 281 | QualityReviewer Executor |

块 5 实际 LOC（加入上述文件后）：**≈ 8 588**（原估 6 569 + 2 019）

### 特殊文件

- `__init__.py`（5 行）：归入块 1 作为包顶层，无实质内容，audit 可跳过。

---

## 2. 每块真实 LOC（wc -l 实测）

| 块 | 文件集（调整后） | 实测 LOC |
|----|--------------|---------|
| **块 1 — Truth & Governance** | governance.py / truth/*.py / sqlite_store.py / store.py / __init__.py | **2 671** |
| **块 2 — Orchestration** | orchestrator.py / executor.py / synthesis.py / dispatch_policy.py / checkpoint_snapshot.py / execution_fit.py / task_semantics.py / harness.py / subtask_orchestrator.py / planner.py / execution_budget_policy.py / retry_policy.py / stop_policy.py / review_gate.py / validator.py / validator_agent.py / models.py / runtime_config.py / compatibility.py | **≈ 12 168** |
| **块 3 — Provider Router & Calls** | router.py / agent_llm.py / _http_helpers.py / cost_estimation.py / capability_enforcement.py | **1 740** |
| **块 4 — Knowledge & Retrieval** | retrieval.py / retrieval_config.py / knowledge_objects.py / knowledge_partition.py / knowledge_policy.py / knowledge_review.py / knowledge_store.py / staged_knowledge.py / ingestion/*.py / dialect_adapters/*.py / dialect_data.py / canonical_*.py / knowledge_index.py / knowledge_relations.py / knowledge_suggestions.py / grounding.py / retrieval_adapters.py | **≈ 5 827** |
| **块 5 — Surface & Tools** | cli.py / paths.py / identity.py / workspace.py / web/*.py / meta_optimizer.py / consistency_audit.py / mps_policy_store.py / doctor.py / consistency_reviewer.py / capabilities.py / librarian_executor.py / ingestion_specialist.py / literature_specialist.py / quality_reviewer.py | **≈ 8 588** |
| **总计** | 70 个 .py 文件 | **≈ 30 994** |

---

## 3. 每块 audit hotspot 候选与预期 finding 量级

### 块 1 — Truth & Governance（2 671 LOC）

- **最近 churn**：`sqlite_store.py`(10)、`governance.py`(9)、`store.py`(30)——Phase 64/65 的核心战场，review 已把关，finding 期望最少。
- **Audit hotspot**：`store.py` 中可能残留 Phase 65 迁移前的 JSON 写路径（双写 transition 痕迹）；`sqlite_store.py` Phase 65 新建，bootstrap helpers 可能有重复 JSON 解析逻辑。
- **预期 finding 量级**：3–8 项（主要为 store.py 过渡痕迹 + bootstrap helper 重复）

### 块 2 — Orchestration（≈ 12 168 LOC）

- **最近 churn**：`orchestrator.py`(79)、`harness.py`(31)、`models.py`(47)——Phase 60-65 连续修改，但每次都有 review；`executor.py`(37) Phase 64 改过 fallback chain。
- **Audit hotspot**：`orchestrator.py`（3 882 行）是全库最大单文件，Planner 部分构造已抽出但未一等化，可能留有"构造一半的 Planner 残余"；`harness.py`（1 950 行）跨越多代际，可能有 dead async/sync 双路径残余；`models.py` 中 event type 字符串常量是否全被消费存疑（`staged_candidate_count` 已知永远为 0）。
- **预期 finding 量级**：10–20 项（orchestrator dead helper + harness 双路径 + models 未消费字段）

### 块 3 — Provider Router & Calls（1 740 LOC）

- **最近 churn**：`router.py`(23)、Phase 64 重写三层外部化、硬编码已清一波。
- **Audit hotspot**：`router.py` 仍可能有 model hint / dialect name 字面量未外部化（Phase 64 外部化了 registry / policy，但字面量不等于外部化完整）；`capability_enforcement.py` 的 capability 名称列表可能硬编码。
- **预期 finding 量级**：3–6 项（router 字面量残余，finding 数少但质量相关性高）

### 块 4 — Knowledge & Retrieval（≈ 5 827 LOC）

- **最近 churn**：`retrieval.py`(13)——相对低；大量文件自 Phase 47-58 后未动，review 信号老旧。
- **Audit hotspot**：`canonical_reuse_eval.py`（377 行）、`knowledge_review.py`（243 行）、`ingestion/parsers.py`（542 行）——多代际沉淀，重复 helper 最高产区；`retrieval_adapters.py`（767 行）embedding HTTP calls 明确排除在 chat-completion 守卫之外，可能有 dead adapter method；dialect_adapters 只剩 claude_xml + fim，旧 codex_fim 已 rename，检查是否残留 shim 未清。
- **预期 finding 量级**：12–20 项（最高，重复 JSON 读写 helper、多处相同 embedding fallback 模式、知识对象转换重复逻辑）

### 块 5 — Surface & Tools（≈ 8 588 LOC）

- **最近 churn**：`cli.py`(81)——全库最高，但多为新增 subcommand；`meta_optimizer.py`(15)。
- **Audit hotspot**：`cli.py`（3 832 行）是最大风险——大量 `swl <subcommand>` 路径，可能有失活子命令（早期 Phase 29-35 添加、后续流程重写后未使用）、重复参数解析逻辑、重复格式化输出 helper；`meta_optimizer.py`（1 320 行）Phase 62-63 工具化沉淀，report 解析与 proposal 生成可能有重复模式；`librarian_executor.py`（518 行）/`literature_specialist.py`（455 行）Specialist 实现间可能有重复 boilerplate。
- **预期 finding 量级**：12–26 项（cli.py dead subcommand + 重复格式化 helper 为主要来源，finding 数最多）

---

## 4. 已知不应纳入 audit 的条目

### concerns_backlog.md Open 项（Codex audit 应跳过，已记录在案）

- Phase 45：`_select_chatgpt_primary_path()` 多叶节点主路径启发式偏差
- Phase 49：`_sqlite_vec_warning_emitted` 多线程竞态
- Phase 50：`extract_route_weight_proposals_from_report()` 依赖文本格式
- Phase 50：`_FAIL_SIGNAL_PATTERNS` false fail verdict
- Phase 57：`VECTOR_EMBEDDING_DIMENSIONS` import 时固化
- Phase 58：`_is_open_webui_export` auto-detect 语义变更
- Phase 59：release doc 未同步 Phase 58/59 能力
- Phase 61/63：`PendingProposalRepo` 仍 in-memory（durable proposal artifact 未实装）
- Phase 61/63：`librarian_side_effect` INVARIANTS §5 矩阵漂移
- Phase 63 M2-1：`staged_candidate_count` 永远为 0 的 vestigial payload 字段
- Phase 63 M2-5：`_apply_route_review_metadata` 约 250 行 reconciliation 逻辑可读性
- Phase 63 M3-1：`events` / `event_log` 双写历史行不 backfill
- Phase 64 M2-2：chat-completion guard 不做跨语句 def-use 间接 URL binding 分析
- Phase 65 closeout known gaps（3 项）：review artifact 在 SQLite commit 后写 / audit snapshot 无 size cap / 完整 migration runner 未实装

### Phase 65 review 留下的 5 项 known gap（不重复盘点）

1. review record application artifact 仍在 SQLite transaction 外写文件系统（warning-only）
2. audit snapshot（before/after payload）无 size cap / truncation policy
3. full schema migration runner deferred
4. CONCERN-1（事务失败注入矩阵，已 resolved in review follow-up）
5. NOTE-1（DATA_MODEL §8 slug 字段，已 resolved in review follow-up）

注：items 4 / 5 已由 Phase 65 review follow-up 关闭，不再是 open gap。

### Phase 64 review 留下的 indirect chat-completion URL guard gap

状态：**Open**（见 concerns_backlog.md Phase 64 M2-2）。audit 应跳过——这是守卫精化的架构决策，不是代码卫生问题。

### Phase 60-65 各 closeout 显式声明 deferred 的项

- Phase 61：14 条非 apply_proposal §9 守卫测试（已由 Phase 63/64 完整落地，now closed）
- Phase 61：完整 Repository 抽象层 + durable proposal artifact（仍 open，见 backlog）
- Phase 62：N/A（MPS scope 自洽，deferred 无 code hygiene 相关项）
- Phase 63：G.5 两条 NO_SKIP 守卫（已由 Phase 64 关闭）
- Phase 64：SQLite-backed route/policy truth（已由 Phase 65 关闭）
- Phase 65：完整 migration runner / outbox / audit snapshot policy（见 backlog open 项）

---

## 5. Scope 边界提醒

- `tests/` 不进 Phase 66 audit scope
- `docs/design/INVARIANTS.md` 和 `docs/design/DATA_MODEL.md` 不动（audit 不评判宪法合理性，不产生对这两文件的修改建议）
- Phase 66 唯一输出文件类：audit report 文件（`docs/plans/phase66/` 下）
- **严格 read-only**：typo、1 行 dead import、注释错误——一律不顺手修，归类入 backlog，由后续清理 phase 处理
- audit 不评判"架构是否合理"——只看"该清的没清"

---

## 6. 子 report 格式建议

**推荐：5 个子 report 文件 + 1 个总 report 索引**

理由：块间 LOC 差异悬殊（块 3 仅 1 740 行 vs 块 2 约 12 168 行），强制合一会导致单文件过长且跨块 finding 混排时审查困难；5 个子 report 让 Claude 在 design_decision 阶段可按块优先级逐块吸收。

建议 path 模板：

```
docs/plans/phase66/audit_block1_truth_governance.md
docs/plans/phase66/audit_block2_orchestration.md
docs/plans/phase66/audit_block3_provider_router.md
docs/plans/phase66/audit_block4_knowledge_retrieval.md
docs/plans/phase66/audit_block5_surface_tools.md
docs/plans/phase66/audit_index.md   # 汇总各块 finding 计数 + 严重程度分布，供 Claude 决策时用
```

---

## 7. Finding 分类口径（operational definitions）

### dead code

判定：在 `src/swallow/`（不含 `tests/`）中，函数/方法/模块级变量的**所有引用 callsite 数 = 0**。

具体规则：
- 使用 `grep -rn "function_name" src/swallow/ tests/` 两个目录合并检索
- "被自己的测试覆盖但生产路径无调用"算 dead（测试覆盖 ≠ 生产可达）
- `__init__.py` 的公开导出不算 dead（即使生产未直接调用）
- 仅在注释 / docstring 中出现的引用不算 callsite
- `@deprecated` 标注的函数若仍被调用，不算 dead

### 硬编码字面量

判定：满足以下任一条件：
- 在 `src/swallow/` 中跨 **≥ 3 处**出现的相同 magic string（不含测试）
- 在 **任意处**出现的 URL / model name / dialect name / provider name / route name 字面量（这类字面量哪怕只出现一次也应外部化）
- 在 **任意处**出现的 magic number（port / timeout 秒数 / chunk size），且该数字未定义为命名常量

排除：单元测试内部的 fixture 字面量；Python 标准库常量（如 `sys.maxsize`）。

### 重复 helper

判定：跨 **≥ 2 个文件**出现 **≥ 10 行**的高度相似逻辑（差异仅为变量名 / 类型注解 / 轻微格式差异）。

具体模式：
- 多处 `json.loads(path.read_text()) + except FileNotFoundError + return {}` 结构
- 多处相同的 SQLite connection + cursor 样板
- 多处相同的 LLM response 错误处理 / retry wrapper

不算重复：接口同名但实现不同（多态）；测试辅助函数与生产函数同名。

### 抽象机会

判定：在 `src/swallow/`（不含 `tests/`）中，**N ≥ 3 处**出现高度相似的 if-elif 链 / switch 结构 / dataclass 初始化模式，差异仅在于被处理的类型或常量。标记为"潜在抽象点"，**不实际抽象**。

具体示例：N ≥ 3 处的 `if route_type == "X": ... elif route_type == "Y": ...` 结构；N ≥ 3 处的 `SomethingConfig(field_a=..., field_b=..., field_c=...)` 初始化序列。

---

## 8. 风险提醒

| 风险 | 描述 | 缓解建议 |
|------|------|---------|
| Finding 数量差 10x | Codex 主观判定边界过严（只报 100% 确定的 dead code）或过松（把每个条件分支都报为抽象机会），导致 finding 数 5 vs 50 | 在 design_decision 中为每类 finding 给示例；Claude review 子 report 时按口径逐条核查，过松过严均打回 |
| Claude review 工作量 | 5 块 × 约 40-80 items = 单次 review 上百条 finding 审查 | 按块分轮 review；audit_index.md 汇总后 Claude 先审高优先级块（块 5 / 块 4），低优先级块（块 3）后处理 |
| 后续清理 phase 排期 | finding 进 backlog 后若无人推进，代码债仍积压 | Phase 66 closeout 时按严重程度分两档：(a) INVARIANTS 相关 / 影响可读性的高优先进 backlog 显著位置；(b) 低优先级小项合并到下一清理 phase 集中处理 |
| 已知 Open backlog 项重复发现 | Codex 在 audit 中重新发现 concerns_backlog.md 里已有的 Open 项，浪费精力 | Codex 在每块 audit 开始前先通读 concerns_backlog.md Open 表，显式跳过已记录条目 |
| Phase 65 新代码信号不稳定 | sqlite_store.py / truth/*.py 是 Phase 65 新建，代码状态新，audit finding 可能是"设计如此"而非"债务" | 这些文件审计时标注 `(Phase 65 new code)` 并降低 finding 权重；design_decision 中明确 Phase 65 新文件 finding 需额外说明是否是已知 tradeoff |

---

## 9. Branch 建议

`feat/phase66-code-hygiene-audit`

与既往 phase 命名规范一致（`feat/phase64-llm-router-boundary` / `feat/phase65-sqlite-truth`）。

---

## 10. Eval 验收标准

此 phase 不适用功能 eval / 测试新增。验收标准为：

1. **覆盖完整**：5 块子 report + audit_index.md 全部产出，70 个 .py 文件均归入某块（含 `__init__.py` trivial 归入块 1）
2. **分类口径一致**：每条 finding 有明确分类（dead code / 硬编码字面量 / 重复 helper / 抽象机会）并附判定依据
3. **跳过已知 backlog 条目**：concerns_backlog.md Open 表中 14 项已标记条目不重复出现在 audit finding 中
4. **严格 read-only**：audit report 自身是 Phase 66 唯一产出文件；src/ 下零 diff
5. **finding 量级合理**：单块 finding 数 > 30 应附说明（是否口径过松）；单块 finding 数 = 0 应附说明（文件是否真的干净或是否漏扫）

---

## 近期相关变更（git history）

| Commit | 描述 | 相关模块 |
|--------|------|---------|
| b00ed2a | fix(phase65): sqlite truth review follow-up | sqlite_store.py / truth/*.py / governance.py |
| 77991d3 | feat(phase65): persist route and policy truth in sqlite | sqlite_store.py / truth/route.py / truth/policy.py / router.py / cli.py |
| 625948d | refactor(phase64): expose fallback chain resolver | router.py / synthesis.py / orchestrator.py |
| c404f3e | feat(phase64): externalize route selection policy | router.py / governance.py / cli.py |
| 900c38b | feat(phase64): externalize route registry metadata | router.py / governance.py / cli.py |
| d2f03a8 | feat(phase64): route specialist llm calls through router | agent_llm.py / _http_helpers.py / router.py |
| 6ad909e | feat(phase64): allow route fallback overrides | router.py / orchestrator.py |
| afec43c | feat(phase64): pre-resolve executor fallback route chain | orchestrator.py / executor.py |
| 1df5992 | feat(phase63): add truth repository write boundary | truth/*.py / governance.py |
| 088836f | refactor(phase63): remove orchestrator staged knowledge dead code | orchestrator.py |

---

## 关键上下文

- `store.py`（723 行）是 Phase 48 前的旧 JSON 存储层，Phase 48 后 SQLite 为默认后端但 store.py 仍保留 JSON 路径兼容；Phase 65 迁移路由/策略后，store.py 中的 JSON 写路径可能进一步缩减——audit 时应检查 store.py 的 JSON 写方法是否仍有生产调用方（callsite = 0 = dead）。
- `orchestrator.py`（3 882 行，churn 79）是全库行数最大且 churn 最高的文件之一；Phase 63 删除了 `_route_knowledge_to_staged` dead code，但 3 882 行体量说明仍有进一步清理空间；Planner 部分构造已抽出到 `planner.py`（227 行），orchestrator 内可能残留被 planner.py 替代的同等逻辑。
- `cli.py`（3 832 行，churn 81）中早期 Phase 10-30 添加的 subcommand（remote handoff、dispatch acknowledge、canonical reuse report 等）后续流程重构后是否仍挂载在 CLI 树上需核查——失活子命令是 Phase 66 块 5 的主要目标。
- `dialect_adapters/codex_fim.py`（git churn 列显示 5 次，但 `find` 未返回此文件）：实测目录下只有 `fim_dialect.py`，codex_fim 已由 Phase 54 rename；churn 计数来自历史 commit，当前文件系统不存在此文件，无需 audit。
- `retrieval_adapters.py`（767 行）中的 embedding HTTP calls 明确排除在 Phase 64 chat-completion 守卫范围之外（Phase 64 closeout 明确声明）；audit 时这些 HTTP 调用不视为 "indirect chat-completion URL binding" finding。
- `models.py`（1 042 行）中的 `staged_candidate_count` 字段已知 concerns_backlog.md Phase 63 M2-1 记录为"永远为 0 的 vestigial payload"，audit 发现时应标注"已在 backlog 登记"并跳过。
- Phase 66 的 5 块拆分在 Codex 实际执行时，块 2（≈ 12 168 LOC）耗时将远超块 3（1 740 LOC）；design_decision 应明确每块允许的 finding report 最长行数上限，避免块 2 audit report 失控膨胀。

## 风险信号

- `harness.py`（1 950 行）未出现在原始 5 块拆分中，但 churn(31) 排第 5，是 Phase 60 以来 run_task / run_task_async 双路径的主要修改点；归入块 2 后，其 async/sync 双路径中是否存在死分支值得重点检查。
- `models.py`（1 042 行，churn 47）被所有模块 import，若 audit 发现 models.py 中有 dead dataclass field，其清理影响面广，应标注 `(high-impact, cleanup requires cross-block coordination)`。
- `canonical_reuse_eval.py`（377 行）和 `review_gate.py`（649 行）churn 极低，但 LOC 较大，Phase 41-42 沉淀，是 dead code 高概率区。
