---
author: claude
phase: 61
slice: context-analysis
created_at: 2026-04-28
status: draft
depends_on:
  - docs/roadmap.md
  - docs/design/INVARIANTS.md
  - docs/design/ARCHITECTURE.md
  - docs/design/STATE_AND_TRUTH.md
  - docs/design/SELF_EVOLUTION.md
  - docs/design/INTERACTION.md
  - docs/design/EXECUTOR_REGISTRY.md
  - docs/design/DATA_MODEL.md
---

TL;DR: `apply_proposal()` 函数在 `swallow.governance` 模块中完全不存在；canonical / route / policy 三类 truth 的写入当前直接散布在 `cli.py` / `orchestrator.py` / `meta_optimizer.py` 共 10+ 处调用点；INVARIANTS §9 列出的 17 条守卫测试在 `tests/` 中零匹配。

---

## 变更范围

**直接影响模块**

- `src/swallow/governance.py` — 不存在；需新建，放置 `apply_proposal()` 函数
- `src/swallow/cli.py` — canonical 写路径(line 2336–2346)、route 写路径(line 2493, 2560)由其直接调底层
- `src/swallow/orchestrator.py` — canonical 写路径(line 498–499, 2956, 2664–2667, 2963–2965)
- `src/swallow/meta_optimizer.py` — route 写路径:`apply_reviewed_optimization_proposals()`(line 1380, 1387)调 `save_route_weights` / `save_route_capability_profiles`
- `src/swallow/router.py` — `save_route_weights()`(line 644) / `save_route_capability_profiles()`(line 701):route metadata 的实际落盘函数
- `src/swallow/store.py` — `append_canonical_record()`(line 540) / `save_canonical_registry_index()`(line 578) / `save_canonical_reuse_policy()`(line 586):canonical 的实际落盘函数
- `src/swallow/knowledge_store.py` — `persist_wiki_entry_from_record()`(line 293):canonical wiki 写入,目前直接被 `cli.py`(line 2336)和 `orchestrator.py`(line 499)调用

**间接影响模块**

- `src/swallow/consistency_audit.py` — `save_audit_trigger_policy()`(line 194):audit policy 写入,当前被 `cli.py`(line 2465)直接调用;是否属于 INVARIANTS §0-4 的 policy 范畴待 design_decision 阶段确认
- `src/swallow/harness.py` — `save_route()` / `save_knowledge_policy()` / `save_retry_policy()` / `save_stop_policy()` / `save_execution_budget_policy()`:这五个函数写的是 per-task 级别的派生配置(非 INVARIANTS §5 矩阵中的系统级 route/policy truth);不在本 phase 收敛主线,但需在 design_decision 阶段明确边界
- `tests/` — 全部 17 条 INVARIANTS §9 守卫测试均不存在,需新建

---

## 近期相关变更 (git history)

| Commit | 描述 | 相关模块 |
|--------|------|---------|
| d2ae5f5 | docs(meta): roadmap audit and apply_proposal concern | concerns_backlog.md / roadmap.md |
| 9acbc69 | docs(meta): tighten workflow handoffs and milestone cadence | workflow docs |
| e63a8ff | docs(design): refine the design framework throughly | INVARIANTS / ARCHITECTURE 等设计文档 |
| caec0de | merge: Router Related Retrieval Policy | router.py / orchestrator.py / retrieval |
| 50cf314 | docs(phase60): add closeout and merge prep | phase60 closeout |
| fb5410f | test(phase60): fix review regression assertions | tests/test_meta_optimizer.py |
| 7527873 | feat(retrieval): add explicit retrieval source overrides | task_semantics.py / cli.py |
| b595fa7 | feat(retrieval): add phase60 s1 route-aware source policy | orchestrator.py |

---

## 关键上下文

### 1. 设计文档对 apply_proposal 的定义

设计文档中 `apply_proposal` 的引用分布在 9 份文档共 15+ 处：

- **INVARIANTS §0 第 4 条**:宪法级条款"Proposal 与 Mutation 的边界由唯一的 `apply_proposal` 入口在代码里强制"
- **INVARIANTS §5 矩阵脚注**:"canonical knowledge / route metadata / policy 的写入**只有 `apply_proposal` 一个代码入口**"
- **SELF_EVOLUTION.md §3.1**:给出了完整函数签名(位于 `swallow.governance` 模块)、`OperatorToken` 类定义、两种 `source` 值(`"cli"` / `"system_auto"`)
- **DATA_MODEL.md §4.1**:给出了另一个签名变体(省略了 `target` 参数),并描述内部调用 `KnowledgeRepo._promote_canonical` / `RouteRepo._apply_metadata_change` / `PolicyRepo._apply_policy_change` 三个私有方法
- **STATE_AND_TRUTH.md §5.1**、**ARCHITECTURE.md §5 术语表**、**INTERACTION.md §4.1 / §4.2.1 / §4.2.3**、**KNOWLEDGE.md §5**、**AGENT_TAXONOMY.md §3**、**ORCHESTRATION.md §4 / §8**、**EXECUTOR_REGISTRY.md(Librarian 条目、Meta-Optimizer 条目)**、**PROVIDER_ROUTER.md §6.4.1** 均引用

**签名口径分歧**:两份文档给出了不同签名:
- SELF_EVOLUTION.md §3.1:`apply_proposal(proposal_id, operator_token, target) -> ApplyResult`
- DATA_MODEL.md §4.1:`apply_proposal(proposal_id, operator_token) -> None`

前者包含 `target` 参数用于区分 canonical / route / policy;后者省略。`target` 参数影响函数内部 dispatch 设计,是 design_decision 必须解决的 API 稳定化问题。

**调用方说明**:INVARIANTS §5 矩阵中,`Operator (via CLI)` 是 canonical / route / policy 三列的唯一 W 方;INTERACTION.md §4.2.3 对照表中 `swl knowledge promote`、`swl proposal apply` 均映射到 `apply_proposal()` 调用。

**Repository 私有方法**:DATA_MODEL.md §4.1 定义三个私有方法:`KnowledgeRepo._promote_canonical` / `RouteRepo._apply_metadata_change` / `PolicyRepo._apply_policy_change`。这三个方法在代码中均不存在——没有 `KnowledgeRepo` / `RouteRepo` / `PolicyRepo` 类,也没有对应私有方法。

### 2. 代码中实际的写入路径清单

| 写入点 | 文件:行 | 当前 caller | 写入 truth 类型 |
|--------|---------|------------|---------------|
| `persist_wiki_entry_from_record()` | `cli.py:2336` | `swl knowledge stage-promote` | canonical knowledge |
| `append_canonical_record()` | `cli.py:2341` | `swl knowledge stage-promote` | canonical knowledge |
| `save_canonical_registry_index()` | `cli.py:2345` | `swl knowledge stage-promote` | canonical index(派生) |
| `save_canonical_reuse_policy()` | `cli.py:2346` | `swl knowledge stage-promote` | canonical reuse policy(派生) |
| `save_route_weights()` | `cli.py:2493` | `swl route weights apply`(直接解析 proposal 文件) | route metadata |
| `save_route_capability_profiles()` | `cli.py:2560` | `swl route capabilities update`(直接修改 profile) | route metadata |
| `append_canonical_record()` | `orchestrator.py:498` | Librarian executor 侧效 dispatch | canonical knowledge |
| `persist_wiki_entry_from_record()` | `orchestrator.py:499` | Librarian executor 侧效 dispatch | canonical knowledge |
| `save_canonical_registry_index()` | `orchestrator.py:2664` | `task knowledge-promote`(orchestrator 内部) | canonical index(派生) |
| `save_canonical_reuse_policy()` | `orchestrator.py:2667` | `task knowledge-promote` | canonical reuse policy(派生) |
| `append_canonical_record()` | `orchestrator.py:2956` | `task knowledge-promote` | canonical knowledge |
| `save_canonical_registry_index()` | `orchestrator.py:2963` | `task knowledge-promote` | canonical index(派生) |
| `save_canonical_reuse_policy()` | `orchestrator.py:2965` | `task knowledge-promote` | canonical reuse policy(派生) |
| `save_route_weights()` | `meta_optimizer.py:1380` | `swl proposal apply`(via `apply_reviewed_optimization_proposals`) | route metadata |
| `save_route_capability_profiles()` | `meta_optimizer.py:1387` | `swl proposal apply`(via `apply_reviewed_optimization_proposals`) | route metadata |
| `save_audit_trigger_policy()` | `cli.py:2465` | `swl audit policy set` | audit policy(待确认是否属于 §0-4 policy) |

关键观察:**非 CLI / 非 Operator 路径**:orchestrator.py line 498–499 在 Librarian 侧效 dispatch 中直接调 `append_canonical_record` 和 `persist_wiki_entry_from_record`,write_authority 使用 `LIBRARIAN_AGENT_WRITE_AUTHORITY`。这条路径是 Orchestrator 内部代码,非 CLI 触发、非 Operator 直接授权,是最接近 INVARIANTS §0-4 字面违反的位置。

### 3. CLI 入口与实际内部函数的对应

| CLI 子命令 | 实际调用内部函数 | 是否经由统一 governance 层 |
|-----------|---------------|--------------------------|
| `swl knowledge stage-promote` | `persist_wiki_entry_from_record` / `append_canonical_record` / `save_canonical_registry_index` / `save_canonical_reuse_policy` 直接调用 | 否 |
| `swl proposal apply` | `apply_reviewed_optimization_proposals()` → `save_route_weights()` / `save_route_capability_profiles()` | 否;`apply_reviewed_optimization_proposals` 是 meta_optimizer 的领域函数,不是 governance 函数 |
| `swl route weights apply` | `save_route_weights()` 直接调用 | 否 |
| `swl route capabilities update` | `save_route_capability_profiles()` 直接调用 | 否 |
| `swl audit policy set` | `save_audit_trigger_policy()` 直接调用 | 否 |

INTERACTION.md §4.2.3 中描述的对照表与代码的关系:
- `swl knowledge promote` 在设计文档中出现,但实际 CLI 命令是 `swl knowledge stage-promote`(有 `stage-` 前缀),另有 orchestrator 内部的 `task knowledge-promote` 路径
- `swl proposal apply` 存在于代码中,但其内部是 `apply_reviewed_optimization_proposals()`,不是 `apply_proposal()`
- 设计文档中的 governance function 列(`apply_proposal(target=canonical_knowledge)` 等)在代码中完全没有对应实现

### 4. 守卫测试现状

**与 apply_proposal 直接相关的 3 条**:

| 守卫测试名 | 代码中是否存在 |
|-----------|--------------|
| `test_canonical_write_only_via_apply_proposal` | 不存在 |
| `test_only_apply_proposal_calls_private_writers` | 不存在 |
| `test_route_metadata_writes_only_via_apply_proposal` | 不存在 |

**所有 17 条守卫测试**:在 `tests/` 目录下执行 grep,无一条匹配。全部 17 条均为零状态——既无占位(pass)、也无实现,测试文件集中于功能测试,无 invariant guard 专用文件。

### 5. Proposal artifact 的当前形态

**Meta-Optimizer 产出**:`OptimizationProposal` dataclass 在 `src/swallow/models.py:464`,字段包括 `proposal_type` / `severity` / `route_name` / `suggested_weight` / `task_family` / `proposed_task_family_score` / `mark_task_family_unsupported` / `proposal_id` / `rationale`。实际写入路径:`save_route_weights()` / `save_route_capability_profiles()` 以 JSON 文件形式持久化到 `.swl/config/route_weights.json` / `.swl/config/route_capabilities.json`。

**Librarian 产出**:staged knowledge 通过 `src/swallow/staged_knowledge.py` 的 `StagedCandidate` 对象表示,状态机为 `pending → promoted / rejected`。`promote` 操作直接调 `append_canonical_record()` / `persist_wiki_entry_from_record()`。

**与 SELF_EVOLUTION.md §3.1 设计的差距**:
- 设计中 `apply_proposal` 接受 `proposal_id: str`,指向 `.swl/artifacts/proposals/<proposal_id>.json` 的 proposal artifact 文件
- 代码中 Meta-Optimizer 的 proposal 走 bundle → review → application record 三文件流程,有明确的 `proposal_id`,基本具备设计所需的输入语义
- Librarian staged candidate 有 `candidate_id`,可映射为 `proposal_id`,但语义层尚未建立此映射
- `OperatorToken` 类、`ProposalTarget` 类、`ApplyResult` 类均不存在

### 6. 上一 phase 的相关上下文

**Phase 60 相关**:Phase 60 修改了 `orchestrator.py` 中的 retrieval policy 逻辑,但未触碰 canonical / route write 路径。Phase 60 closeout 无与本 phase 重叠的 follow-up。

**concerns_backlog.md 关联条目**:
- Phase 49 concern:"CLI operator canonical promotion 的 authority 语义仍未完全统一:knowledge stage-promote 已使用 OPERATOR_CANONICAL_WRITE_AUTHORITY,但 task knowledge-promote --target canonical 仍通过 LIBRARIAN_MEMORY_AUTHORITY 进入 decision 层" — 这条 concern 与 phase61 直接重叠;`apply_proposal()` 函数化后,caller authority 可统一在 OperatorToken.source 中管理
- Phase 50 concern:"`extract_route_weight_proposals_from_report()` 从 markdown 文本反向解析 route_weight 提案"——`swl proposal apply` 走结构化 JSON review record 路径已解决部分问题;`swl route weights apply` 仍走文本解析路径(cli.py:2473–2495),本 phase 收敛写入入口后可同步清理此路径
- Phase 51 concern 中 `apply_reviewed_optimization_proposals()` 语义问题已在 Phase 51 修复,不直接关联

**knowledge_store.py 的 write_authority 机制**:当前代码已有轻量 authority 字符串机制(`CANONICAL_KNOWLEDGE_WRITE_AUTHORITIES` set,包含 `librarian-agent` / `operator-gated` / `canonical-promotion` / `knowledge-migration` / `test-fixture`)。这套机制是历史积累的 ad-hoc 保护,与 INVARIANTS 设计的 OperatorToken 机制不同,但可作为过渡参考。

### 7. 风险初判

**影响面**:canonical truth 写路径:3 个调用文件(cli.py / orchestrator.py / knowledge_store.py),共约 7 处直接写调用点。route metadata 写路径:3 个文件(cli.py / meta_optimizer.py / router.py),共约 4 处写调用点。合计约 11 处写路径需收敛进 `apply_proposal()`。

**测试改动**:当前无守卫测试。现有功能测试中,`tests/test_cli.py`(最大测试文件)、`tests/test_meta_optimizer.py`、`tests/test_librarian_executor.py`、`tests/test_knowledge_store.py` 中大量用例直接 assert 写路径的副作用(canonical_registry 内容、route_weights 内容),caller 变化后这些 assert 预期值不变,但调用链会变化,可能需要更新 mock 或 fixture。`tests/eval/test_eval_meta_optimizer_proposals.py` 对 proposal apply 有 eval 级测试,也需关注。

**难以收敛的写路径**:
1. `orchestrator.py:498–499` 的 Librarian 侧效 dispatch:这条路径由 Orchestrator 内部调用,不是 CLI 触发。如果 `apply_proposal()` 要求 `OperatorToken.source="cli"`,则此路径需要 `source="system_auto"` 或专门的 Librarian authority token。SELF_EVOLUTION.md §3.1 的 `OperatorToken` 定义中 `system_auto` 仅针对 `staged_review_mode=auto_low_risk`,此路径是 Librarian agent 侧效,语义不同——需 design_decision 阶段明确 OperatorToken 的第三种 source 或设计单独的 token 类型
2. `knowledge_store.py` 的 `persist_wiki_entry_from_record()`:这是 canonical wiki 写入的实际实现,被 cli.py 和 orchestrator.py 直接调用。它是一个低层 store 函数,如果要让 `apply_proposal()` 成为唯一入口,需要决定是把它变成私有方法还是保留为 `apply_proposal()` 内部调用
3. Migration 路径:`knowledge_store.py` 中的 `migrate_file_knowledge_to_sqlite()` 使用 `KNOWLEDGE_MIGRATION_WRITE_AUTHORITY`,这是 bootstrap 级别的写入——是否纳入 `apply_proposal()` 守卫范围需 design_decision 明确
4. `swallow.governance` 模块不存在,`KnowledgeRepo` / `RouteRepo` / `PolicyRepo` Repository 类也不存在:DATA_MODEL.md §4 描述的 Repository 抽象层是设计意图,实际代码以 store 函数 + SQLite 直接操作混合实现

---

## 风险信号

- 写路径总计约 11 处,分布在 3 个文件,全部是 CLI-triggered 或 Orchestrator-internal;没有任何写路径已经经过 `apply_proposal()` 统一入口
- `swallow.governance` 模块、`KnowledgeRepo` / `RouteRepo` / `PolicyRepo` 类、`OperatorToken` 类、`ProposalTarget` 类均不存在;需要从零创建,而非包装已有代码
- 两份设计文档(SELF_EVOLUTION.md vs DATA_MODEL.md)对 `apply_proposal()` 签名有口径分歧(`target` 参数是否存在);需在 design_decision 阶段先稳定 API 签名
- Librarian 侧效路径(orchestrator.py:498–499)是非 CLI、非 Operator 直接授权的 canonical 写路径,收敛此路径时需明确 `OperatorToken.source` 的第三种值或设计替代机制
- 全部 17 条 INVARIANTS §9 守卫测试均为零状态,phase61 完成后应全部落地;但 3 条 apply_proposal 相关测试是 phase61 直接范围,另 14 条属于背景债务
- `INTERACTION.md §4.2.3` 中 `swl knowledge promote` 与代码实际命令名 `swl knowledge stage-promote` 不一致;可在本 phase 写 context 时顺带记录,但修正 CLI 命令名不属于 phase61 核心范围
