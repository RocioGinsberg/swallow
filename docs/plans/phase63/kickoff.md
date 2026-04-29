---
author: claude
phase: phase63
slice: kickoff
status: revised-after-model-review
depends_on: ["docs/plans/phase63/context_brief.md", "docs/plans/phase63/design_audit.md", "docs/plans/phase63/model_review.md", "docs/roadmap.md", "docs/design/INVARIANTS.md", "docs/design/DATA_MODEL.md", "docs/concerns_backlog.md", "src/swallow/governance.py"]
---

TL;DR(revised-after-model-review): Phase 63 治理守卫收口(候选 G)。**6 slice / 5 milestone**:M0 pre-implementation audit(**3 项**:NO_SKIP guards + store connection + `_route_knowledge_to_staged` 触发场景)/ M1 §7 集中化 / M2 stagedK 治理(**M0-dependent 双方案待定**:方案 A = librarian_side_effect token + §5 更新;方案 D = 下沉 Specialist 内部 + §5 不动)+ Repository 骨架 / M3 §9 守卫批量 / M4 SQLite-transaction-wrapped apply_proposal。范围治理表面收敛,对外可观测行为零变化(SQLite transaction 包裹后 reader 隔离更严格)。

## 当前轮次

- track: `Governance`
- phase: `Phase 63`
- 主题: 治理守卫收口(Governance Closure)
- 入口: Direction Gate 已通过(2026-04-29 Human 选定候选 G)

## 目标(Goals)

- **G0: Pre-implementation audit(新增 - revised-after-model-review)**
  - **3 项 audit**:
    1. NO_SKIP_GUARDS 8 条 report-only 扫描,产出当前红灯位置清单
    2. store 函数 connection 模式 audit(确定 S5 SQLite transaction 实装路径 A/B/C)
    3. **`_route_knowledge_to_staged` 触发场景 audit(2026-04-29 Human 反馈驱动)**:列出当前所有 `taxonomy_memory_authority ∈ {"canonical-write-forbidden", "staged-knowledge"}` 路由对应的 task taxonomy 与 executor type,决定 §S2 / §G2 走方案 A(librarian_side_effect token + §5 矩阵更新)还是方案 D(下沉到 Specialist 内部,§5 矩阵不动)
  - 产出 `docs/plans/phase63/m0_audit_report.md` + `tests/audit_no_skip_drift.py`(report-only)+(可能)`tests/audit_route_knowledge_to_staged.py`
  - Claude 在 M0 报告基础上做**两个**决策:
    - **NO_SKIP scope 决策**:维持 6-slice plan 或拆 Phase 63.5
    - **§S2 方案选择**:方案 A vs 方案 D(决策表见 `design_decision.md` §S0)
  - **此 slice 无代码改动**(仅 audit / 报告);Human 在 M0 完成后审阅决策再继续 M1+

- **G1: §7 集中化函数 + 守卫真实化**
  - 引入 `swallow/identity.py`(导出 `local_actor()`)与 `swallow/workspace.py`(导出 `resolve_path()`)
  - 把现有 actor-semantic `"local"` 字面量与 `.resolve()` 调用全部改走集中化函数(disambiguate `execution_site="local"` 站点语义,后者保留)
  - 实装 `test_no_hardcoded_local_actor_outside_identity_module` / `test_no_absolute_path_in_truth_writes` 两条守卫,使其非 vacuous

- **G2: stagedK 治理通道(orchestrator.py:3145 收敛,**M0-dependent 双方案待定**)**

  > **⚠ 2026-04-29 Human 反馈**:`_route_knowledge_to_staged` 实际是按 `taxonomy_memory_authority` 路由的通用副作用流,不只 Librarian。M0 audit 第 3 项决定本 G 走哪个方案。

  **方案 A(librarian_side_effect token,若 audit 显示涉及 General Executor 等非-Specialist)**:
  - 扩展 `_VALID_OPERATOR_SOURCES` 增加 `librarian_side_effect`(`OperatorToken` dataclass 字段不变,仍为 `source` / `reason`)
  - 扩展 `ProposalTarget` enum 增加 `STAGED_KNOWLEDGE = "staged_knowledge"`
  - 新增 `register_staged_knowledge_proposal(payload: StagedCandidate) -> str` 函数 + `_StagedKnowledgeProposal` dataclass + `_apply_staged_knowledge` 内部分发
  - 把 orchestrator.py:3145 既有 `submit_staged_candidate(...)` 调用改为两步:`register_staged_knowledge_proposal(...) → apply_proposal(proposal_id, OperatorToken(source="librarian_side_effect", reason=...), ProposalTarget.STAGED_KNOWLEDGE)`(对齐既有三参数签名)
  - **更新 INVARIANTS §5 矩阵 Orchestrator 行 stagedK 列**(消化 model_review Q1 BLOCK):从 "-" 改为 "W*(via apply_proposal + librarian_side_effect token)" + 配套注脚解释 token 特权语义。本 phase 内独立 commit `docs(design): update §5 matrix for librarian_side_effect token`

  **方案 D(下沉到 Specialist 内部,若 audit 显示仅 Specialist 类 executor 触发)**:
  - 把 `_route_knowledge_to_staged` 函数体从 `orchestrator.py:3131` 移到对应 Specialist 内部 task hook(类比 Phase 36 S1 `_apply_librarian_side_effects()` 模式)
  - Specialist 直接调 `submit_staged_candidate(...)`(§5 Specialist 行 stagedK = `W`,合规)
  - **不引入 `librarian_side_effect` token**;**不更新 INVARIANTS §5 矩阵**;`OperatorToken` / `_VALID_OPERATOR_SOURCES` / `ProposalTarget` 三个 enum 都不动
  - non-goals **不需要**收紧到允许 §5 矩阵更新

  **共同点**:等价行为(对外不变,staged candidate 写入 staged knowledge 表);cli.py:2590 / ingestion/pipeline.py 4 处合规调用不动

- **G3: Repository 抽象层骨架 + `_PENDING_PROPOSALS` 收敛 + Repository bypass 守卫**
  - 引入 `swallow/truth/knowledge.py` / `swallow/truth/route.py` / `swallow/truth/policy.py`(对应 DATA_MODEL §4.1 `KnowledgeRepo` / `RouteRepo` / `PolicyRepo`)
  - 最小封装层:Repository 类只做 `_promote_canonical` / `_apply_metadata_change` / `_apply_policy_change` 等私有写方法,内部调用现有 store 函数(签名映射详见 `design_decision.md` §S3)
  - `governance.py` 的 `save_route_weights` / `save_route_capability_profiles` / `apply_route_weights` / `apply_route_capability_profiles` 直接 import 改为 Repository 调用
  - `_PENDING_PROPOSALS` 由 Repository 管理:**key 为 `(target, proposal_id)` 元组**(与既有 governance.py 实装一致),同一 key 第二次 register 时抛 `DuplicateProposalError`(不再静默覆盖)
  - **新增 2 条 Repository bypass 守卫**(消化 model_review Q2/Q6):`test_only_governance_calls_repository_write_methods` + `test_no_module_outside_governance_imports_store_writes`,确保 Repository 私有方法不被绕过

- **G4: §9 剩余 14 条守卫批量实装**
  - 行为合规类(6):`test_no_executor_can_write_task_table_directly` / `test_state_transitions_only_via_orchestrator` / `test_path_b_does_not_call_provider_router` / `test_validator_returns_verdict_only` / `test_specialist_internal_llm_calls_go_through_router` / `test_route_override_only_set_by_operator`
  - ID & 不变量类(5):`test_all_ids_are_global_unique_no_local_identity` / `test_event_log_has_actor_field` / `test_no_foreign_key_across_namespaces` / `test_append_only_tables_reject_update_and_delete` / `test_artifact_path_resolved_from_id_only`
  - UI 边界(1):`test_ui_backend_only_calls_governance_functions`
  - 事务回滚守卫(配套 G5)(1):`test_apply_proposal_rollback_executes_on_failure`
  - 其余 1 条由 G1 提供(`test_no_hardcoded_local_actor_outside_identity_module` / `test_no_absolute_path_in_truth_writes` 两条计入 G1 而非 G4)
  - 净计:G4 在 §9 表内补 12 条 + 引入 1 条事务回滚守卫 = 13 条;G1 补 §9 表内 2 条;Phase 63 完结后 §9 表 17 条全部实装(3 既有 + G1 2 条 + G4 12 条 = 17)

- **G5: `apply_proposal` SQLite-transaction-wrapped 事务回滚(消化 model_review Q5 BLOCK)**
  - **改用 SQLite `BEGIN IMMEDIATE` transaction 包裹四步 store 写**:`save → apply → save → apply` 四步序列在单一 SQLite transaction 内执行,任一步失败 → SQLite 原生 ROLLBACK,reader 看不到中间状态
  - 实装路径(M0-dependent):Path A(store 函数已接受外部 connection,首选)/ Path B(store-side connection 参数 refactor,fallback)/ Path C(staged version table,最后 fallback,scope 重评估)
  - 现有 `rollback_weights` / `rollback_capability_profiles` 字段保留作为 audit log `before_snapshot` 来源(不再用作 compensating rollback 输入)
  - 引入 append-only 审计表 `route_change_log` / `policy_change_log`(schema 与 DATA_MODEL §3 既有 `know_change_log` 对齐)
  - **`action` 字段值仅两类**(`"applied"` / `"rolled_back"`):移除 staged 应用方案的 `"rollback_failed"` terminal state(SQLite ROLLBACK 是原子的)
  - 配套 `test_apply_proposal_rollback_executes_on_failure` 守卫(计入 G4),验证 SQLite ROLLBACK + reader 隔离

## 非目标(Non-Goals,revised-after-model-review)

- 不重写既有 store 函数(`store.py` / `knowledge_store.py` / `mps_policy_store.py` 等),Repository 只做最小封装(若 S5 走 Path B,store 函数仅增加可选 `connection` 参数,行为兼容)
- **不修改 INVARIANTS §0 / §1 / §2 / §3 / §4 / §6 / §7 / §8 等核心原则文字**(consume model_review Q1 BLOCK);**§5 矩阵 Orchestrator 行 stagedK 列是否更新由 M0 audit 第 3 项决定**:
  - 方案 A(audit 显示涉及非 Specialist 类 executor)→ §5 矩阵此一行允许更新 + 配套注脚
  - 方案 D(audit 显示仅 Specialist 类 executor 触发)→ §5 矩阵不动
- 不引入新 LLM 调用路径(三条 Path 不变)
- 不修改 Phase 60-62 任何功能的可观测行为(staged candidate 写入语义、apply_proposal 入口签名、MPS Path A 编排均保持等价;**SQLite transaction wrapping 后中间状态对 reader 不可见,语义比原 staged 应用更严格,仍为零行为变化**)
- **不引入 staged 应用 + 失败回滚**(原 design_decision draft 方案,model_review Q5 BLOCK 消化后改用 SQLite native transaction)
- 不引入两阶段提交(SQLite transaction 是单一事务)
- 不引入 Operator-facing CLI 扩展(`librarian_side_effect` token 仅在 orchestrator 内部使用,不暴露 CLI 子命令)
- 不引入新 SQLite 大表(append-only 审计 log 仅 schema 增量)
- 不引入并发 / 多 actor / authn / authz(INVARIANTS §8 永久非目标)
- 不在本 phase 完成 Repository 抽象层的全部职责(`durable proposal artifact 层` / `事务两阶段提交` 是后续方向,本 phase 只到 SQLite native transaction)
- 不在本 phase 完成 staged version table 实装(Path C fallback,只在 M0 audit 后被迫选择时才考虑)

## 设计边界

- 严格遵循 INVARIANTS §0 四条不变量,所有改动验证不引入新漂移
- 集中化函数(`identity.py` / `workspace.py`)是**唯一**的 actor 字面量与路径绝对化入口;Phase 63 内不允许例外
- Repository 抽象层是 governance.py 与 store 函数之间的**唯一**桥梁;governance.py 不再直接 import store 函数
- §9 守卫测试是**可执行的不变量证明**,任一守卫红灯不得 merge
- `librarian_side_effect` token 是**有限特权扩展**,仅 orchestrator 持有,守卫验证 CLI / Specialist 不签发该 token

## 完成条件(revised-after-model-review)

- **M0 报告产出**:`docs/plans/phase63/m0_audit_report.md` 完成,Claude 已基于报告决定 phase scope
- 全量 pytest 通过(包括新 §9 14 条守卫测试 + 4 条额外架构守卫:librarian_side_effect token + DuplicateProposal + 2 条 Repository bypass)
- INVARIANTS §9 标准表 17 条全部实装,不再 vacuous
- `grep -n '"local"' src/swallow/` 在 `identity.py` 之外的 actor-semantic 命中数为 0(`execution_site="local"` 站点语义不计)
- `find src/swallow/ -name 'identity.py' -o -name 'workspace.py'` 两个文件均存在
- `governance.py` 不再直接 import `save_route_weights` / `apply_route_weights` / `save_route_capability_profiles` / `apply_route_capability_profiles`(全部走 `truth/route.py` Repository)
- `_PENDING_PROPOSALS` 重复 register 抛 `DuplicateProposalError`
- `orchestrator.py:3145` 不再直接调 `submit_staged_candidate`,改为两步:`register_staged_knowledge_proposal(payload=...) → apply_proposal(proposal_id, OperatorToken(source="librarian_side_effect", reason=...), ProposalTarget.STAGED_KNOWLEDGE)`(对齐既有 `apply_proposal(proposal_id, operator_token, target)` 三参数签名,governance.py:209 / DATA_MODEL §4.1)
- **`apply_proposal` 内部多步 store 写包在单一 SQLite `BEGIN IMMEDIATE` transaction 内**;mid-failure 测试验证 SQLite ROLLBACK 触发 + reader 不可见中间状态;新增 `route_change_log` / `policy_change_log` 表可观测
- **INVARIANTS §5 矩阵文字已更新**(Orchestrator 行 stagedK 列 + 配套注脚)
- **2 条 Repository bypass 守卫**(`test_only_governance_calls_repository_write_methods` + `test_no_module_outside_governance_imports_store_writes`)通过
- **ACTOR_SEMANTIC_KWARGS 闭集已扩展**(移除 `action`,加入 `created_by` / `updated_by` / `owner` / `user` / `principal` / `agent` 等)
- `docs/plans/phase63/closeout.md` 完成 + `docs/concerns_backlog.md` 5 条 Phase 61/62 Open 标 Resolved
- `git diff --check` 通过

## Slice 拆解(revised-after-model-review,详细见 `design_decision.md`)

| Slice | 主题 | Milestone | 风险评级 |
|-------|------|-----------|---------|
| S0 | Pre-implementation audit(NO_SKIP 扫描 + store connection 模式 + **`_route_knowledge_to_staged` 触发场景** + phase scope 决策 + §S2 方案选择) | M0 | 低(3) |
| S1 | §7 集中化函数 + 2 条守卫真实化 + 扩展 ACTOR_SEMANTIC_KWARGS 闭集 | M1 | 中(6) |
| S2 | stagedK 治理通道(orchestrator.py:3145 收敛)**M0-dependent 双方案待定**:方案 A = OperatorToken 扩展 + §5 矩阵文字更新;方案 D = 下沉到 Specialist 内部 + §5 不动 | M2 | 方案 A: 低-中(5) / 方案 D: 中(6,涉及 Specialist 内部接口改动) |
| S3 | Repository 抽象层骨架 + `_PENDING_PROPOSALS` 重复检测 + **2 条 Repository bypass 守卫** | M2 | **高(7)** |
| S4 | §9 剩余 12+1 条守卫批量实装(NO_SKIP 守卫严格执行) | M3 | 低(4) |
| S5 | **SQLite-transaction-wrapped apply_proposal** + append-only 审计 log | M4 | **高(7)** |

Milestone 分组:
- **M0**(单独 review,新增):Pre-implementation audit slice;Human 在 M0 完成后审阅 scope 决策再继续
- **M1**(单独 review):S1 是后续 slice 的基础前置(集中化函数提供给 §9 守卫)
- **M2**(S2 + S3 同轮 review):两者共同重塑 governance.py 的依赖图;**§5 矩阵 docs(design) 更新独立 commit**
- **M3**(单独 review):批量守卫实装,大量纯增量 test 文件
- **M4**(单独 review):**SQLite transaction wrapping** 是新机制,单独 review 边界更清晰

**slice 数量(6 个)超出"≤5 slice"指引一个**:M0 是 audit-only slice(无代码改动,实质 phase scope 安全网),Human Design Gate 时显式审批此例外。

## Eval 验收

不适用。Phase 63 全部为治理 / 守卫 / 抽象层重构,无降噪 / 提案有效性 / 端到端体验质量梯度;pytest(含新 14 条守卫)即足以验收。

## 风险概述(revised-after-model-review)

- **S3 Repository 抽象层** 与 **S5 SQLite transaction wrapping** 为本 phase 两个高风险 slice
- **§9 14 条守卫批量激活**可能暴露既有代码中其他未发现的漂移(R6);M0 audit 提供 pre-implementation report,根据 NO_SKIP 红灯数量决定是否拆 Phase 63.5
- **`"local"` 字面量 disambiguation** 是 S1 的关键设计决策点,扩展闭集后做错会导致守卫漏报(R2)
- **store 函数 connection 模式 audit 结果**决定 S5 实装路径(A/B/C);若 Path C 触发可能 phase scope 重评估(R13)
- **§5 矩阵文字更新**与"不修改 INVARIANTS 文字"既有 non-goal 有冲突,本 phase 已收紧 non-goals(R12,Human Design Gate 显式审批)
- **`test_append_only_tables_reject_update_and_delete`** 需要 SQLite trigger 基础设施,可能比预期复杂(R7)

## 完成后的下一步

- Phase 63 closeout 后,5 条 Phase 61/62 Open 全部转 Resolved
- Direction Gate 决策下一轮:候选 D(Planner / DAG)还是其他新方向
- 本 phase 实装的 Repository 抽象层骨架是未来候选 D 的有用前置
