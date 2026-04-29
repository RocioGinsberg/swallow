---
author: claude
phase: phase63
slice: kickoff
status: final-after-m0
depends_on: ["docs/plans/phase63/context_brief.md", "docs/plans/phase63/design_audit.md", "docs/plans/phase63/model_review.md", "docs/plans/phase63/m0_audit_report.md", "docs/plans/phase63/design_decision.md", "docs/roadmap.md", "docs/design/INVARIANTS.md", "docs/design/DATA_MODEL.md", "docs/concerns_backlog.md", "src/swallow/governance.py"]
---

TL;DR(final-after-m0): Phase 63 治理守卫收口(候选 G)。**4 slice / 3 milestone**(M0 已完成):M1 §7 集中化 / M2 删除 `_route_knowledge_to_staged` dead code + Repository 抽象层骨架 + bypass 守卫 / M3 §9 守卫 batch(NO_SKIP 6/8 条启用,2 条暂缓 G.5)。**M0 audit 后 scope 大幅收窄**:删除 dead code 替代 token 引入(生产 0 触发);S5 SQLite transaction 推迟到 Phase 64(候选 H);NO_SKIP 红灯 2 条拆 Phase 63.5(候选 G.5)。INVARIANTS §5 矩阵不动,non-goals 恢复"不修改 INVARIANTS 任何文字"。对外可观测行为零变化。

## 当前轮次

- track: `Governance`
- phase: `Phase 63`
- 主题: 治理守卫收口(Governance Closure)第一段
- 入口: Direction Gate 已通过(2026-04-29 Human 选定候选 G);M0 audit 已完成(`m0_audit_report.md`)

## Phase 63 / G.5 / H 三段式分工(2026-04-29 M0 audit 后定型)

| Phase | 候选 | 工作内容 | 依赖 |
|-------|------|---------|------|
| **Phase 63(本 phase)** | 候选 G | §7 集中化 + 删 stagedK dead code + Repository 抽象层骨架 + §9 守卫批量(NO_SKIP 6/8 条) | 无 |
| Phase 63.5 | 候选 G.5 | 修复 M0 audit 暴露的 2 条 NO_SKIP 红灯(executor.py fallback_route 边界 + agent_llm.py 改走 Provider Router) | Phase 63 完成 |
| Phase 64 | 候选 H | Truth Plane SQLite 一致性(route metadata / policy 迁 SQLite + `apply_proposal` `BEGIN IMMEDIATE` + 审计 log)| Phase 63 + G.5 完成 |

5 条 Phase 61/62 漂移 Open 的消化映射:

| Open | 消化 phase |
|------|-----------|
| §9 14 条守卫缺失 | Phase 63(12 条)+ G.5(2 条) |
| Repository 抽象层未实装 | Phase 63 |
| `apply_proposal` 事务回滚缺失 | Phase 64 |
| `orchestrator.py:3145` stagedK 直写 | Phase 63(删 dead code) |
| §7 集中化函数缺失 | Phase 63 |

## 目标(Goals)

- **G1: §7 集中化函数 + 守卫真实化**
  - 引入 `swallow/identity.py`(导出 `local_actor()`)与 `swallow/workspace.py`(导出 `resolve_path()`)
  - 把现有 actor-semantic `"local"` 字面量与 `.resolve()` 调用全部改走集中化函数(disambiguate `execution_site="local"` 站点语义,后者保留)
  - 实装 `test_no_hardcoded_local_actor_outside_identity_module` / `test_no_absolute_path_in_truth_writes` 两条守卫,使其非 vacuous
  - 扩展 `ACTOR_SEMANTIC_KWARGS` 闭集(authoritative 列表见 `design_decision.md` §S1)

- **G2: 删除 `_route_knowledge_to_staged` dead code**
  - **M0 audit 已确认**`orchestrator.py:3131-3175 _route_knowledge_to_staged` 在生产 ROUTE_REGISTRY 中**0 触发**(built-in routes 无 `taxonomy_memory_authority ∈ {canonical-write-forbidden, staged-knowledge}`)
  - 删除函数体 + `orchestrator.py:3688` 调用点 = 零行为变化
  - 调整两个测试 mock 路由(`tests/test_cli.py:8839 restricted-specialist` / `tests/test_meta_optimizer.py:692 meta-optimizer-local`)使其不依赖删除路径
  - **不引入** `librarian_side_effect` token 给 stagedK 路径(`librarian_side_effect` 在 Phase 61 已存在于 canonical knowledge 路径,本 phase 不动)
  - **不修改** INVARIANTS §5 矩阵任何文字
  - cli.py:2590 / ingestion/pipeline.py 4 处合规调用不动

- **G3: Repository 抽象层骨架 + `_PENDING_PROPOSALS` 收敛 + Repository bypass 守卫**
  - 引入 `swallow/truth/knowledge.py` / `swallow/truth/route.py` / `swallow/truth/policy.py`(对应 DATA_MODEL §4.1 `KnowledgeRepo` / `RouteRepo` / `PolicyRepo`)
  - 最小封装:Repository 类只做 `_promote_canonical` / `_apply_metadata_change` / `_apply_policy_change` 等私有写方法,内部调用现有 store 函数(签名映射详见 `design_decision.md` §S3);**不引入事务管理**(留给 Phase 64)
  - `governance.py` 的 `save_route_weights` / `save_route_capability_profiles` / `apply_route_weights` / `apply_route_capability_profiles` 直接 import 改为 Repository 调用
  - `_PENDING_PROPOSALS` 由 Repository 管理:**key 为 `(target, proposal_id)` 元组**,同一 key 第二次 register 时抛 `DuplicateProposalError`(不再静默覆盖)
  - **新增 2 条 Repository bypass 守卫**:`test_only_governance_calls_repository_write_methods` + `test_no_module_outside_governance_imports_store_writes`,确保 Repository 私有方法不被绕过

- **G4: §9 剩余 12 条守卫批量实装(NO_SKIP 6/8 条启用)**
  - 行为合规类 6 条(其中 2 条 NO_SKIP 暂缓 G.5,以 `pytest.skip` 占位)
  - ID & 不变量类 5 条
  - UI 边界 1 条
  - 配套 SQLite trigger 基础设施(若 `test_append_only_tables_reject_update_and_delete` 需要)
  - 完结后 §9 标准表 17 条全部存在(15 条立即生效 + 2 条 G.5 占位)

## 非目标(Non-Goals,final-after-m0)

- 不重写既有 store 函数本身(`store.py` / `knowledge_store.py` / `mps_policy_store.py` 等);Repository 只做最小封装
- **不修改 INVARIANTS 任何文字**(M0 audit 后 §S2 = 删 dead code,无需 §5 矩阵更新;非目标恢复到原始严格版本)
- 不引入新 LLM 调用路径(三条 Path 不变)
- 不修改 Phase 60-62 任何功能的可观测行为(staged candidate 写入语义、apply_proposal 签名、MPS Path A 编排均保持等价)
- **不引入 SQLite transaction wrapping**(推迟到 Phase 64 候选 H)
- **不引入 staged 应用 / 失败回滚 / `apply_proposal` 事务回滚**(推迟到 Phase 64 候选 H)
- **不引入新 OperatorToken source**(`librarian_side_effect` 是 Phase 61 既有,本 phase 不扩展用法)
- 不引入 Operator-facing CLI 扩展
- 不引入新 SQLite 大表(`test_append_only_tables_reject_update_and_delete` 涉及的 trigger 是既有 4 张表的合规化,无新表)
- 不引入并发 / 多 actor / authn / authz(INVARIANTS §8 永久非目标)
- 不在本 phase 完成 Repository 抽象层的全部职责(durable proposal artifact 层 / `_PENDING_PROPOSALS` evict 是后续方向)
- **不在本 phase 修复 NO_SKIP 红灯 2 条**(`test_path_b_does_not_call_provider_router` + `test_specialist_internal_llm_calls_go_through_router`;移到 Phase 63.5)
- **不在本 phase 修复 `librarian_side_effect` token 在 canonical knowledge 路径的 §5 漂移**(Phase 61 引入,登记新 Open 到 concerns_backlog,后续治理 phase 消化)

## 设计边界

- 严格遵循 INVARIANTS §0 四条不变量,所有改动验证不引入新漂移
- 集中化函数(`identity.py` / `workspace.py`)是**唯一**的 actor 字面量与路径绝对化入口;Phase 63 内不允许例外
- Repository 抽象层是 governance.py 与 store 函数之间的**唯一**桥梁;governance.py 不再直接 import store 函数
- §9 守卫测试是**可执行的不变量证明**,任一 NO_SKIP 守卫红灯不得 merge(暂缓 G.5 的 2 条以 `pytest.skip` 占位,不算红灯)
- 删除 `_route_knowledge_to_staged` 是 dead code 清理,需要测试 mock 同步调整以保持原有断言意图

## 完成条件

- 全量 pytest 通过(包括新 §9 12 条守卫测试 + 3 条额外架构守卫:DuplicateProposal + 2 条 Repository bypass)
- INVARIANTS §9 标准表 17 条全部存在于 `tests/test_invariant_guards.py`(15 条通过 + 2 条 G.5 占位 skip)
- `grep -n '"local"' src/swallow/` 在 `identity.py` 之外的 actor-semantic 命中数为 0(`execution_site="local"` 站点语义不计)
- `find src/swallow/ -name 'identity.py' -o -name 'workspace.py'` 两个文件均存在
- `governance.py` 不再直接 import `save_route_weights` / `apply_route_weights` / `save_route_capability_profiles` / `apply_route_capability_profiles`(全部走 `truth/route.py` Repository)
- `_PENDING_PROPOSALS` 重复 register 抛 `DuplicateProposalError`
- `grep -n '_route_knowledge_to_staged' src/swallow/orchestrator.py` 命中 0(已删除)
- `grep -n 'submit_staged_candidate' src/swallow/orchestrator.py` 命中 0(随删除连带消失)
- `git diff docs/design/INVARIANTS.md` 无任何改动(包括 §5 矩阵)
- **2 条 Repository bypass 守卫**(`test_only_governance_calls_repository_write_methods` + `test_no_module_outside_governance_imports_store_writes`)通过
- **ACTOR_SEMANTIC_KWARGS 闭集已扩展**(authoritative 列表见 `design_decision.md` §S1,移除 `action`,加入常见 actor kwargs)
- `docs/plans/phase63/closeout.md` 完成 + `docs/concerns_backlog.md` 标注:
  - 5 条 Phase 61/62 Open 中 3 条标 Resolved(§7 集中化 / Repository 抽象层 / orchestrator stagedK 直写)
  - §9 守卫 12 条 + 事务回滚 1 条**部分 Resolved**(本 phase 实装 12 条中 10 条立即生效 / 2 条 G.5 启用)
  - 事务回滚标 **expected resolution: Phase 64**
  - 新增 1 条 Open:**`librarian_side_effect` 在 canonical knowledge 路径的 §5 漂移**(Phase 61 引入,本 phase scope 外)
- `git diff --check` 通过

## Slice 拆解(详细见 `design_decision.md`)

| Slice | 主题 | Milestone | 风险评级 |
|-------|------|-----------|---------|
| S0 | M0 Pre-implementation audit | M0(已完成) | 已合并 |
| S1 | §7 集中化函数 + 2 条守卫真实化 + 扩展 ACTOR_SEMANTIC_KWARGS 闭集 | M1 | 中(6) |
| S2 | 删除 `_route_knowledge_to_staged` dead code | M2 | 低(3) |
| S3 | Repository 抽象层骨架 + `_PENDING_PROPOSALS` 重复检测 + 2 条 Repository bypass 守卫 | M2 | **高(7)** |
| S4 | §9 剩余 12 条守卫批量实装(NO_SKIP 6/8 条启用,2 条 G.5 占位) | M3 | 低(4) |

Milestone 分组:
- **M0**(已完成):S0 audit-only;`m0_audit_report.md` 已 commit (`c3637b1`)
- **M1**(单独 review):S1 是后续 slice 的基础前置(集中化函数提供给 §9 守卫)
- **M2**(S2 + S3 同轮 review):S2 单独 commit(删 dead code + 测试 mock 调整)/ S3 三个 commit(KnowledgeRepo / RouteRepo / PolicyRepo 各一);**§5 矩阵不动**,M2 内无 docs(design) commit
- **M3**(单独 review):批量守卫实装,大量纯增量 test 文件

**slice 数量 4 个**(M0 已完成不计入剩余),完全符合"≤5 slice"指引。

## Eval 验收

不适用。Phase 63 全部为治理 / 守卫 / 抽象层重构,无降噪 / 提案有效性 / 端到端体验质量梯度;pytest(含新 §9 12 条守卫 + 3 条架构守卫)即足以验收。

## 风险概述(详细见 `risk_assessment.md`)

- **S3 Repository 抽象层**为本 phase 唯一高风险 slice(7 分),涉及 governance.py 的依赖图重塑;详见 `risk_assessment.md` R3
- **§9 12 条守卫批量激活**可能暴露既有代码中其他未发现的漂移(R6);M0 audit 已 pre-empt 大范围 NO_SKIP 红灯,触发概率低
- **`"local"` 字面量 disambiguation** 是 S1 的关键设计决策点,扩展 ACTOR_SEMANTIC_KWARGS 闭集后做错会导致守卫漏报(R2)
- **测试 mock 调整**(S2)可能改变现有测试断言意图,Codex 实装时需保证等价性(R16,新增)
- **删 dead code 风险低**:M0 audit 已确认生产 0 触发,删除是零行为变化;但要确保未来添加 staged-knowledge 路由时,Codex 在新 phase 内引入合规实装(Specialist 内部),不要不假思索地"恢复"删除的代码

## Branch Advice

- 当前分支:`feat/phase63-governance-closure`(已切出)
- 建议操作:Human Design Gate 通过后,Codex 在该分支上实装 S1 → S2 → S3 → S4
- 建议 PR 范围:全部 4 个 slice 一次 PR;review milestone 分 3 个(M1 / M2 / M3)
- M0 已合并,作为 PR base

## 完成后的下一步

- Phase 63 closeout 后,触发 `roadmap-updater` subagent 同步 §三差距表(治理守卫收口标 [部分已消化])
- 进入 Phase 63.5(候选 G.5):修复 M0 audit 暴露的 2 条 NO_SKIP 红灯
- G.5 完成后进入 Phase 64(候选 H):Truth Plane SQLite 一致性
- 候选 D(Planner / DAG)在 H 完成后再评估
