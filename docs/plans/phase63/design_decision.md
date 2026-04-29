---
author: claude
phase: phase63
slice: design-decomposition
status: final-after-m0
depends_on: ["docs/plans/phase63/kickoff.md", "docs/plans/phase63/context_brief.md", "docs/plans/phase63/design_audit.md", "docs/plans/phase63/model_review.md", "docs/plans/phase63/m0_audit_report.md", "docs/design/INVARIANTS.md", "docs/design/DATA_MODEL.md", "docs/roadmap.md", "src/swallow/governance.py"]
---

TL;DR(final-after-m0): **5 slice / 4 milestone**(M0 已完成,S5 推迟到 Phase 64 候选 H)。M1=S1 §7 集中化 / M2=S2 删 `_route_knowledge_to_staged` dead code(M0 确认生产 0 触发)+ S3 Repository 抽象层骨架 + 2 条 bypass 守卫 / M3=S4 §9 守卫 batch(NO_SKIP 6/8 启用,2 条暂缓 G.5)。**M0 audit 三决策**:§S2 删 dead code、S5 推迟 Phase 64(filesystem JSON 现状 + P2 兑现独立 phase)、NO_SKIP 红灯拆 G.5。INVARIANTS §5 矩阵不动,non-goals 恢复"不修改 INVARIANTS 任何文字"。

## 方案总述

Phase 63 是宪法层债务收口 phase 的**第一段**。M0 audit 后 scope 大幅收窄:

- **决策 1:§S2 = 删除 dead code**。M0 audit 第 3 项确认 `_route_knowledge_to_staged` 在生产 ROUTE_REGISTRY 中**0 触发**(built-in routes 没有 `taxonomy_memory_authority ∈ {canonical-write-forbidden, staged-knowledge}`),仅在两个测试 mock route 中触发,且都是 Specialist。删除该函数 + 调用点 = 零行为变化,自然消化"orchestrator stagedK 直写"漂移。**不引入新 token,不修改 §5 矩阵**。
- **决策 2:S5 推迟到 Phase 64**。M0 audit 第 2 项确认 route metadata / policy 当前是 JSON + in-memory,不是 SQLite。原 SQLite `BEGIN IMMEDIATE` 方案物理上不可行;filesystem 层 atomic staging 是局部解,不兑现 INVARIANTS P2 "SQLite-primary truth"。正确路径是**把 route/policy 迁入 SQLite**,这是独立 phase 工作量(候选 H,见 `docs/roadmap.md`)。`apply_proposal` 事务回滚 Open 在 Phase 64 内自然解决。
- **决策 3:NO_SKIP 红灯 2 条拆出 G.5**。M0 audit 第 1 项发现 `executor.py:510 fallback_route_for` + `agent_llm.py:57 httpx.post` 是真实治理边界问题(不是机械漂移),Phase 63 内只启用 6 条 NO_SKIP_GUARDS(Phase 61 既有 3 条 + 5 条 §0 第 1 / 第 4 条相关 1)。剩余 2 条 (`test_path_b_does_not_call_provider_router` + `test_specialist_internal_llm_calls_go_through_router`) 在 Phase 63.5(候选 G.5)启用。

**实装路径**:M0(已完成)→ M1 集中化函数 → M2 删 dead code + Repository 骨架 + 2 条 bypass 守卫 → M3 §9 守卫 batch(NO_SKIP 6 条)。**等价性保证**:对外可观测行为零变化(删除的 dead code 生产无触发;Repository 1:1 转发既有 store 函数;§9 守卫只验证不变量,不改业务逻辑)。

**5 条 Phase 61/62 漂移 Open 在 Phase 63 + G.5 + H 内完整消化**:
| Open | 消化 phase | 方式 |
|------|-----------|------|
| §9 14 条守卫缺失 | Phase 63(12 条)+ G.5(2 条) | S1 + S4 |
| Repository 抽象层未实装 | Phase 63 | S3 |
| `apply_proposal` 事务回滚缺失 | Phase 64(候选 H) | SQLite migration + `BEGIN IMMEDIATE` |
| `orchestrator.py:3145` stagedK 直写 | Phase 63 | S2 删 dead code |
| §7 集中化函数缺失 | Phase 63 | S1 |

## Slice 拆解

### S1 — §7 集中化函数 + 2 条 §9 守卫真实化(M1 单独 review)

**目标**:引入 `swallow/identity.py` 与 `swallow/workspace.py`,把 INVARIANTS §7 的 `local_actor()` / `resolve_path()` 集中化要求落到代码;实装 §9 表内 `test_no_hardcoded_local_actor_outside_identity_module` 与 `test_no_absolute_path_in_truth_writes` 两条守卫。

**影响范围**:
- 新增:`src/swallow/identity.py`(导出 `local_actor() -> str`,内部返回 `"local"` 字面量,**唯一**允许的 actor 字面量出现位置)
- 新增:`src/swallow/workspace.py`(导出 `resolve_path(path: Path | str, *, base: Path | None = None) -> Path`,封装 `.resolve()` 调用 + workspace_root 解析)
- 改动(actor-semantic 改走 `local_actor()`):`src/swallow/models.py`(SQL DEFAULT 字符串保持不变;**Python 层 INSERT 时 actor 字段值用 `local_actor()`**;`models.py:297 action="local"` 由 S1 实装时单独 audit 语义)、`src/swallow/store.py`、`src/swallow/orchestrator.py`(actor 写入点)
- 改动(path 绝对化改走 `resolve_path()`):`src/swallow/orchestrator.py` lines 2595-2630+、`src/swallow/executor.py:791`、`src/swallow/literature_specialist.py:80`、`src/swallow/quality_reviewer.py:41`、`src/swallow/ingestion/pipeline.py` lines 52, 125、`src/swallow/web/api.py` lines 12, 35
- 不动(站点语义保留):`src/swallow/router.py` 11+ 处 `execution_site="local"`、`src/swallow/execution_fit.py`、`src/swallow/cost_estimation.py`、`src/swallow/dialect_data.py` 中的 `execution_site="local"`
- 新增:`tests/test_invariant_guards.py` 增加 `test_no_hardcoded_local_actor_outside_identity_module` / `test_no_absolute_path_in_truth_writes`

**关键设计决策**:

- **disambiguation 策略**:守卫用 AST 而非 grep。actor 字面量定义为"出现在 actor-semantic kwarg 上下文中的 `"local"`"。**ACTOR_SEMANTIC_KWARGS 闭集(authoritative)**:
  ```python
  ACTOR_SEMANTIC_KWARGS = frozenset({
      # 直接 actor 标识
      "actor", "actor_name", "actor_id",
      # *_by 模式
      "submitted_by", "performed_by", "created_by", "updated_by",
      "modified_by", "deleted_by", "requested_by", "approved_by",
      "reviewed_by", "applied_by", "committed_by",
      "authored_by", "signed_by", "initiated_by",
      # 调用方 / 主体身份
      "caller", "owner", "owner_id",
      "user", "user_id", "username",
      "principal", "principal_id",
      "operator", "operator_id",
      # 来源标识
      "originator", "agent", "agent_id",
      # Swallow-specific
      "executor_name",
  })
  ```
  此闭集定义在 `tests/test_invariant_guards.py` 顶部作为模块级常量。守卫扫描 AST,识别 `kwarg.arg in ACTOR_SEMANTIC_KWARGS` 且 `kwarg.value` 是 `ast.Constant("local")` 的位置。`execution_site="local"` 是 site-semantic,不在闭集中,守卫不会误报。`action` **不在闭集中**(`models.py:297 action="local"` 的具体语义由 S1 实装时单独 audit:若是 actor 含义,改字段名;若是动作,保留)。

- **DDL DEFAULT 字符串豁免**:`models.py` 中 SQL DDL 字符串内的 `DEFAULT 'local'` 字面量是嵌入在 Python 字符串内的 SQL 字面量,**不在 actor-semantic kwarg 调用语境中**,守卫 AST 扫描自然不会命中(AST 看到的是 `Constant("CREATE TABLE ...")` 整个字符串,不是 kwarg)。Codex 实装时**保持 DDL 中 `DEFAULT 'local'` 不变**,Python 层 INSERT 显式传值时由 `local_actor()` 提供。

- **identity.py 设计**:仅一个函数 `local_actor() -> str`,无参数,返回 `"local"`。未来切换 multi-actor 时只需替换此函数实现,所有调用方零改动。

- **workspace.py 设计**:`resolve_path(path: Path | str, *, base: Path | None = None) -> Path`。**base 解析优先级(authoritative)**:
  1. 显式传入的 `base` 参数(若非 None) → 直接使用
  2. 环境变量 `SWL_ROOT`(若设置且非空)→ 使用为 base
  3. 当前 workspace 根的 fallback:`Path.cwd()`(仅用于无 SWL_ROOT 的开发环境;生产部署应总是设置 SWL_ROOT)

  仅在持久化路径解析时使用 `resolve_path()`。Truth 写入函数禁止接收 `Path.absolute()` 或 `Path.resolve()` 调用结果作为持久化字段(由 §9 `test_no_absolute_path_in_truth_writes` 守卫验证)。

**验收条件**:
- `swallow.identity.local_actor()` / `swallow.workspace.resolve_path()` 存在并被调用
- `grep -rn '"local"' src/swallow/` 在 `identity.py` 与 `tests/` 之外的 **actor-semantic** 命中数为 0(grep + 人工 audit;site-semantic 不计)
- 新增 2 条守卫测试通过
- 全量 pytest 通过(回归无破坏)

**风险评级**:影响范围 3 / 可逆性 2 / 依赖 1 = 6(中);跨多个模块的 import 改动,但每个改动都是机械替换,回滚成本可控。

---

### S2 — 删除 `_route_knowledge_to_staged` dead code(M2 part)

**目标**:删除 `orchestrator.py:3131-3175` 的 `_route_knowledge_to_staged` 函数体 + `orchestrator.py:3688` 的调用点。**M0 audit 确认生产 0 触发**(built-in ROUTE_REGISTRY 无 `taxonomy_memory_authority ∈ {canonical-write-forbidden, staged-knowledge}` 路由;仅 2 个测试 mock route 触发,且都是 Specialist)。删除是零行为变化,自然消化"orchestrator stagedK 直写"漂移,无需 token 引入或 §5 矩阵更新。

**M0 audit 依据**(详见 `docs/plans/phase63/m0_audit_report.md` Audit 3):
- `ROUTE_REGISTRY` 内置路由 0 个匹配阻塞 taxonomy
- 测试 mock 路由(`tests/test_cli.py:8839 restricted-specialist` / `tests/test_meta_optimizer.py:692 meta-optimizer-local`)均为 Specialist
- 没有任何 production 或 test 路由配置 `general-executor / canonical-write-forbidden` 或 `general-executor / staged-knowledge`
- `librarian_side_effect` token 已存在(`governance.py:26`)用于 canonical knowledge apply 路径(Phase 61 引入),与 stagedK 路径无关

**影响范围**:
- 删除:`src/swallow/orchestrator.py:3131-3175` `_route_knowledge_to_staged` 函数体
- 删除:`src/swallow/orchestrator.py:3688` `staged_candidates = _route_knowledge_to_staged(base_dir, state)` 调用点(及任何使用 `staged_candidates` 局部变量的相关行 — 包括 line 3162-3175 的 `append_event(... event_type="task.knowledge_staged" ...)`)
- 调整:测试 mock(`tests/test_cli.py:8839` / `tests/test_meta_optimizer.py:692`)的 `taxonomy_memory_authority` 配置,改为不依赖删除的路径(具体调整由 Codex 在 S2 实装时决定:或改成 `task-memory` taxonomy + 显式 `submit_staged_candidate` 调用;或删除该 mock 路由配置中的 `taxonomy_memory_authority` 设置)
- 不动:`OperatorToken` / `_VALID_OPERATOR_SOURCES` / `ProposalTarget` enum(均不变)
- 不动:`librarian_side_effect` token 在 canonical knowledge apply 路径(Phase 61 引入,本 phase 不动 — 见 §登记 Open)
- 不动:cli.py:2590 `submit_staged_candidate` 调用(Operator path,合规)+ ingestion/pipeline.py 4 处(Specialist path,合规)
- 不动:INVARIANTS §5 矩阵任何文字

**关键设计决策**:

- **为什么删除而不是迁移到 Specialist**:M0 audit 显示生产 0 触发,迁移到 Specialist 是为"未来可能用"做准备,**违反 YAGNI**。如未来真有需要,新 phase 在合规位置(Specialist 内部)实装,不背 Phase 32-36 历史包袱。

- **测试 mock 调整边界**:S2 改动 `tests/test_cli.py` / `tests/test_meta_optimizer.py` 中 mock 路由配置时,确保被改的测试用例**仍验证原有意图**(如 restricted route 的 cli 行为、meta-optimizer 路由解析)。具体改动方式:在 mock 路由 `RouteSpec` 中删除 `taxonomy_memory_authority` 字段,或改为 `task-memory`。Codex 在 S2 PR 中给出每个 mock 改动的前后对比 + 测试断言不变性证明。

- **登记新 Open(`librarian_side_effect` 在 canonical 路径)**:M0 audit 发现 Phase 61 引入的 `librarian_side_effect` token 在 canonical knowledge apply 路径(orchestrator.py:506 `_apply_librarian_side_effects`)实际上让 Orchestrator 触发了 canonical 写入,但 §5 矩阵 Orchestrator 行 canonK 列仍是 `-`。**这是 Phase 61 留下的、本 phase 不在 scope 内的漂移**。S2 内**不修改**这条路径,但 closeout 时登记到 `docs/concerns_backlog.md` 作为新 Open,在后续治理 phase(可能是 H 之后的某个 phase)消化。

**验收条件**:
- `grep -n '_route_knowledge_to_staged' src/swallow/orchestrator.py` 命中 0(已删除)
- `grep -n 'submit_staged_candidate' src/swallow/orchestrator.py` 命中 0(随删除连带消失)
- 全量 pytest 通过(测试 mock 调整后,既有断言保持一致)
- INVARIANTS §5 矩阵文字未修改(`git diff docs/design/INVARIANTS.md` 无 §5 表内容变化)

**风险评级**:影响范围 1 / 可逆性 1 / 依赖 1 = 3(低)。删除生产 0 触发的 dead code,回滚仅需 git revert。

---

### S3 — Repository 抽象层骨架 + `_PENDING_PROPOSALS` 重复检测(M2 part,**高风险**)

**目标**:引入 `swallow/truth/{knowledge,route,policy}.py` 三个 Repository 模块,封装现有 store 写函数;`governance.py` 不再直接 import store 函数,而是经 Repository 调用;`_PENDING_PROPOSALS` 改为 Repository 管理的注册表,重复 `(target, proposal_id)` 第二次 register 抛 `DuplicateProposalError`。新增 2 条 Repository bypass 守卫。

**影响范围**:
- 新增:`src/swallow/truth/__init__.py`、`src/swallow/truth/knowledge.py`(`KnowledgeRepo` 类:`_promote_canonical(...)`)、`src/swallow/truth/route.py`(`RouteRepo` 类:`_apply_metadata_change(...)`)、`src/swallow/truth/policy.py`(`PolicyRepo` 类:`_apply_policy_change(...)`)
- 改动:`src/swallow/governance.py` —— 移除 `from .router import save_route_weights, apply_route_weights, ...` 等直接 import;改为 `from .truth.route import RouteRepo`;`apply_proposal` 内部分发到对应 Repository 方法;`_PENDING_PROPOSALS` 改为 Repository-managed 字典,`register_*` 函数检测 `(target, proposal_id)` 已存在时抛 `DuplicateProposalError`
- 改动:`tests/test_invariant_guards.py` 更新 `test_only_apply_proposal_calls_private_writers`(已存在 Phase 61 实装,扫描目标扩展到 `truth/*.py` 的 `_promote_canonical` / `_apply_*` 方法)
- 新增:`tests/test_invariant_guards.py` 增加 `test_only_governance_calls_repository_write_methods`(消化 model_review Q2 + Q6:验证 Repository 私有写方法只被 governance.py 调用)
- 新增:`tests/test_invariant_guards.py` 增加 `test_no_module_outside_governance_imports_store_writes`(消化 model_review Q6:验证非 governance / 非 truth/* 模块不能直接 import canonical / route / policy 的 store 写函数)
- 新增:`tests/test_governance.py` 增加 `test_duplicate_proposal_id_raises` 测试

**关键设计决策**:

- **Repository 设计原则**:**最小封装**。Repository 类只做一层方法转发,不引入新业务逻辑、不缓存、不做事务管理。每个 Repository 类的写方法保持与现有 store 函数 1:1 对应。**事务管理留给 Phase 64(候选 H)**:H 内 Repository 私有方法切换为 SQL 写,governance 层用 `BEGIN IMMEDIATE` 包,Repository 接口 1:1 不变。

- **现有 store 函数签名映射**:Codex 实装时按以下映射建立 Repository 私有方法。**实装前必须先 grep 现有签名作为最终对照**(签名以 `src/swallow/router.py` / `store.py` / `knowledge_store.py` / `mps_policy_store.py` 当前代码为准):

  | Repository 私有方法 | 转发到 | 来源模块 |
  |---------------------|--------|----------|
  | `KnowledgeRepo._promote_canonical(...)` | `promote_to_canonical` 或 `apply_canonical_promotion`(以现有名为准) | `knowledge_store.py` |
  | `RouteRepo._apply_metadata_change(...)` | 顺序调用 `save_route_weights` → `apply_route_weights` → `save_route_capability_profiles` → `apply_route_capability_profiles` | `router.py` |
  | `RouteRepo.record_health(...)`(public) | `record_route_health` 或同名函数 | `router.py` |
  | `PolicyRepo._apply_policy_change(...)` | `save_policy` / `apply_policy` 或既有 policy store 写函数 | `mps_policy_store.py` 与现有 policy store |

  Codex 实装时:S3 PR body 必须包含一份 actual signature mapping table(列出每个 Repository 私有方法的完整 Python 签名 vs 转发的原 store 函数签名),Claude review 时验证一致性。

- **`_promote_canonical` / `_apply_metadata_change` / `_apply_policy_change` 是 private**:DATA_MODEL §4.1 守卫 `test_only_apply_proposal_calls_private_writers` 验证这些方法只能被 `governance.apply_proposal` 调用,不能被外部直接调用。Repository 类的公开方法**只允许 read**(写权限只通过 governance.apply_proposal)。

- **Repository bypass 守卫策略(消化 model_review Q2 + Q6)**:Python `_underscore` 是约定不强制,需要硬守卫:
  - **守卫 A**(`test_only_governance_calls_repository_write_methods`,§9 表外):AST 扫描 `src/swallow/` 下所有 `.py` 文件中对 `KnowledgeRepo._promote_canonical` / `RouteRepo._apply_metadata_change` / `PolicyRepo._apply_policy_change`(以及任何以 `_` 开头的 Repository 写方法)的调用。允许调用集合 ⊆ `{src/swallow/governance.py}`(governance 内部 dispatch);tests/ 豁免
  - **守卫 B**(`test_no_module_outside_governance_imports_store_writes`,§9 表外):AST 扫描 `src/swallow/` 下所有 `.py` 文件,寻找对 canonical / route / policy store 写函数的 import。允许 import 集合 ⊆ `{src/swallow/governance.py, src/swallow/truth/knowledge.py, src/swallow/truth/route.py, src/swallow/truth/policy.py}`。**例外**:Provider Router 的 `record_health` 等读路径或 health 写路径不在守卫范围内(只针对 canonical / metadata / policy 写函数)
  - 两条守卫都是 §9 表外的"额外架构守卫",不计入 §9 表 17 条守卫

- **`_PENDING_PROPOSALS` key 与 duplicate 检测**:既有实装(governance.py:120 / 154 / 等)使用 `key = (target, normalized_id)` 元组,本 phase 保持元组 key。`register_*` 函数检测 `key in _PENDING_PROPOSALS` 时抛 `DuplicateProposalError`,异常消息包含 `target.value` 与 `proposal_id`。

- **`_PENDING_PROPOSALS` 生命周期**:仍是模块级 in-memory 字典(本 phase 非目标:不引入 durable proposal artifact 层),但增加 register 时的存在检查。**暂不增加 evict / cleanup**(长 process 内存累积仍是 Open),避免本 phase 范围扩张。

- **接口签名稳定性**:`apply_proposal(proposal_id: str, operator_token: OperatorToken, target: ProposalTarget) -> ApplyResult` 三参数签名不变(与 governance.py:209 / DATA_MODEL §4.1 一致);Repository 是 governance 内部实装细节,不 leak 到 governance 调用方。

**验收条件**:
- `grep -n 'from .router import' src/swallow/governance.py` 不命中 `save_route_weights` / `apply_route_weights` / `save_route_capability_profiles` / `apply_route_capability_profiles`
- `swallow.truth.knowledge.KnowledgeRepo._promote_canonical` / `swallow.truth.route.RouteRepo._apply_metadata_change` / `swallow.truth.policy.PolicyRepo._apply_policy_change` 存在
- `test_duplicate_proposal_id_raises` 通过
- `test_only_apply_proposal_calls_private_writers` 守卫扫描目标更新后通过
- `test_only_governance_calls_repository_write_methods` 通过
- `test_no_module_outside_governance_imports_store_writes` 通过
- 全量 pytest 通过(governance 既有测试零破坏)

**风险评级**:影响范围 3 / 可逆性 2 / 依赖 2 = **7(高风险)**。governance.py 是 Phase 61 引入的核心治理入口,本 slice 重塑其依赖图。建议在 Codex 实现时优先做"等价回归测试"——先跑现有 governance 测试套件,再引入 Repository,逐步迁移(KnowledgeRepo / RouteRepo / PolicyRepo 各一个 commit)。

**SCOPE WARNING(phase-guard)**:本 slice 显著重塑 governance.py 内部结构,虽然对外接口签名不变,但 Codex 实现层面需谨慎避免:
- 不要顺手修改 store 函数本身(non-goal)
- 不要给 Repository 引入读方法(本 phase 只做写收敛)
- 不要做 durable proposal artifact 层(后续 phase 方向)
- 不要把事务管理塞进 Repository(留给 Phase 64 候选 H)

---

### S4 — §9 守卫批量实装(NO_SKIP 6/8 条,M3 单独 review)

**目标**:实装 §9 标准表 17 条中尚未实装的 12 条守卫(Phase 61 已实装 3 条;S1 补 2 条;本 slice 补剩余 12 条)。**NO_SKIP_GUARDS 启用 6 条,2 条暂缓 G.5**。

**§9 守卫实装清单**(本 slice 12 条):

**行为合规类(6 条)**:
- `test_no_executor_can_write_task_table_directly`(NO_SKIP)
- `test_state_transitions_only_via_orchestrator`(NO_SKIP)
- `test_validator_returns_verdict_only`(NO_SKIP)
- `test_route_override_only_set_by_operator`
- ⏸ `test_path_b_does_not_call_provider_router`(**暂缓 G.5**:M0 audit 红灯,需修 `executor.py:510 fallback_route_for` 边界)
- ⏸ `test_specialist_internal_llm_calls_go_through_router`(**暂缓 G.5**:M0 audit 红灯,需修 `agent_llm.py:57 httpx.post` 走 Provider Router)

**ID & 不变量类(5 条)**:
- `test_all_ids_are_global_unique_no_local_identity`
- `test_event_log_has_actor_field`
- `test_no_foreign_key_across_namespaces`
- `test_append_only_tables_reject_update_and_delete`(被测表清单:`event_log` / `event_telemetry` / `route_health` / `know_change_log`)
- `test_artifact_path_resolved_from_id_only`

**UI 边界(1 条)**:
- `test_ui_backend_only_calls_governance_functions`

**NO_SKIP_GUARDS 完整白名单(authoritative)**:与 INVARIANTS §0 四条核心不变量直接对应。Phase 63 启用其中 6 条,2 条(LLM 路径相关)在 G.5 启用。

```python
NO_SKIP_GUARDS = {
    # §0 第 1 条 — Control 只在 Orchestrator 和 Operator 手里
    "test_no_executor_can_write_task_table_directly",       # Phase 63 启用
    "test_state_transitions_only_via_orchestrator",         # Phase 63 启用
    "test_validator_returns_verdict_only",                  # Phase 63 启用
    # §0 第 3 条 + §4 — LLM 调用三条路径
    "test_path_b_does_not_call_provider_router",            # G.5 启用
    "test_specialist_internal_llm_calls_go_through_router", # G.5 启用
    # §0 第 4 条 — apply_proposal 唯一入口(Phase 61 已实装,本 phase 不动)
    "test_canonical_write_only_via_apply_proposal",         # Phase 61 既有
    "test_only_apply_proposal_calls_private_writers",       # Phase 61 既有(S3 更新扫描目标)
    "test_route_metadata_writes_only_via_apply_proposal",   # Phase 61 既有
}
```

**影响范围**:
- 改动:`tests/test_invariant_guards.py` 增加 12 条守卫(其中 2 条暂以 `pytest.skip(reason="G.5 will enable, see roadmap candidate G.5")` 占位 — 暂缓但占位让 §9 表实装计数完整)
- 可能改动:`src/swallow/store.py` / migration —— 若 `test_append_only_tables_reject_update_and_delete` 暴露既有 append-only 表缺少 SQLite UPDATE / DELETE trigger,本 slice 内补齐(`CREATE TRIGGER IF NOT EXISTS` 在 store 初始化路径,idempotent)
- 可能新增:`tests/conftest.py` 或 `tests/fixtures/` 引入 SQLite trigger 测试 fixture

**关键设计决策**:

- **守卫实装策略**:静态分析(AST scan)优先,运行时验证次之。每条守卫的验证方式在守卫 docstring 中说明。

- **`test_append_only_tables_reject_update_and_delete` 被测表清单**:S4 实装时,守卫被测表清单**仅包含既有 4 张 append-only 表**:`event_log` / `event_telemetry` / `route_health` / `know_change_log`(DATA_MODEL §4.2)。**Phase 64(候选 H)引入的 `route_change_log` / `policy_change_log` 在 H 内同步扩展该守卫被测表清单**(不再属于本 phase)。

- **SQLite trigger 部署**:DATA_MODEL §4.2 列出的 append-only 表需要 SQLite UPDATE / DELETE trigger 显式 RAISE。S4 实装时审计现有 schema,若 trigger 缺失,补齐;补齐方式为 store 初始化路径 `CREATE TRIGGER IF NOT EXISTS`(idempotent)。这是 S4 唯一可能引入 schema 变化的位置。

- **暴露既有漂移的处理**:若批量激活后发现既有代码触发某条 NO_SKIP 守卫红灯(本 phase 启用的 6 条之一):**优先修代码、不削弱守卫**。修改超出本 slice 范围时,在 risk_assessment 中标注 R6,由 Claude 评审决定是否拆出独立 slice。M0 audit 已 pre-empt 大范围 NO_SKIP 红灯(只发现 2 条,均拆 G.5),所以本 slice 内 NO_SKIP 红灯触发概率低。

- **`test_only_apply_proposal_calls_private_writers` 与 S3 的关系**:此守卫已在 Phase 61 实装,扫描目标为 governance.py 内的 `_apply_canonical` / `_apply_route_metadata` / `_apply_policy`。S3 引入 Repository 抽象层后,该守卫扫描目标应**扩展**到 `truth/{knowledge,route,policy}.py` 的 `_promote_canonical` / `_apply_metadata_change` / `_apply_policy_change`。**S3 验收条件包含此守卫扫描目标更新;不计入 S4 的"12 条新增"计数**(它是修改既有守卫,不是新增)。修改若破坏该守卫由 S3 PR 负责回归。

**验收条件**:
- INVARIANTS §9 标准表 17 条全部存在于 `tests/test_invariant_guards.py`(其中 2 条 `pytest.skip` 占位,reason 标 `G.5 will enable`)
- 12 条新守卫中 10 条通过(2 条 G.5 暂缓 skip)
- `test_append_only_tables_reject_update_and_delete` 在所有 §4.2 既有 4 张 append-only 表上通过
- 全量 pytest 通过

**风险评级**:影响范围 1 / 可逆性 1 / 依赖 2 = 4(低)。

---

## 依赖与顺序

```
S0 (M0, 已完成) ──┬──> S1 (M1, identity/workspace 集中化)
                   └──> 已决策:§S2 = 删 dead code / S5 → Phase 64 / NO_SKIP 2 → G.5

S1 (M1) ──┬──> S4 (M3, §9 守卫批量需要 identity/workspace 集中化函数已存在)
          └──> S3 (M2, Repository 内部 path 处理走 resolve_path())

S2 (M2) ───────> S4 (M3, 删除 dead code 后 §9 守卫批量基线干净)

S3 (M2) ───────> S4 (M3, test_only_apply_proposal_calls_private_writers 扫描目标在 S3 内更新)
```

**Codex 推荐实装顺序**:**S1 → S2 → S3 → S4**(无跨 milestone 倒序)

## Milestone 与 review checkpoint

| Milestone | 包含 slice | review 重点 | 提交节奏 |
|-----------|-----------|------------|---------|
| **M0** | S0(已完成) | M0 audit 报告(`m0_audit_report.md`,已 commit `c3637b1`)| 已合并 |
| **M1** | S1 | identity/workspace 集中化函数设计、扩展 ACTOR_SEMANTIC_KWARGS 闭集、disambiguation 策略 | 单独 milestone commit |
| **M2** | S2 + S3 | dead code 删除等价性(测试 mock 调整)、Repository 接口最小性、Repository bypass 守卫 | 同轮 review;S2 单独 commit / S3 三个 commit(KnowledgeRepo / RouteRepo / PolicyRepo 各一) |
| **M3** | S4 | §9 12 条守卫语义正确性、SQLite trigger 基础设施、NO_SKIP 6 条 + 2 条 skip 占位 | 单独 milestone commit |

## 守卫与测试映射

| Slice | 新增守卫 | §9 表内 | §9 表外 |
|-------|---------|---------|---------|
| S1 | `test_no_hardcoded_local_actor_outside_identity_module` / `test_no_absolute_path_in_truth_writes` | 2 | 0 |
| S2 | (无新增守卫,删 dead code) | 0 | 0 |
| S3 | `test_duplicate_proposal_id_raises` / `test_only_governance_calls_repository_write_methods` / `test_no_module_outside_governance_imports_store_writes` | 0 | 3(governance 测试 + 2 条 Repository bypass 守卫) |
| S4 | 12 条 §9 表内(其中 2 条 G.5 暂缓 skip 占位) | 12 | 0 |
| **合计** | **17 条**(15 条通过 + 2 条 skip 占位) | **14** | **3** |

完结后:INVARIANTS §9 标准表 3(既有 Phase 61 apply_proposal 守卫)+ 14(本 phase 新增 = S1 的 2 + S4 的 12)= **17 条**(其中 2 条 skip 占位待 G.5 启用,15 条立即生效);额外 3 条架构守卫(Repository bypass 防线 + DuplicateProposal)是本 phase 的"防止漂移再生"机制。

## phase-guard 检查

- ✅ 当前方案不越出 kickoff goals(G0-G4 + S1-S4 对应,M0 已完成,5 条 Phase 61/62 漂移 Open 在本 phase + G.5 + H 内消化)
- ✅ kickoff non-goals 已恢复:**不修改 INVARIANTS 任何文字**(M0 audit 后 §S2 = 删 dead code,无需 §5 矩阵更新)
- ✅ slice 数量 4 个(S1-S4),完全符合"≤5 slice"指引(M0 已完成,不计入剩余 slice 数)
- ✅ 仅 1 条高风险 slice(S3 Repository,7 分);S5 推迟到 Phase 64 后,本 phase 风险面收敛
- ✅ M0 audit 三项决策已落实到设计:删 dead code / S5 推迟 / NO_SKIP 拆 G.5
- ✅ 关联文档已同步:`docs/roadmap.md` §三差距表新增 NO_SKIP 红灯 + Truth Plane SQLite 两条;§四 队列加候选 G.5 / 候选 H;§五 推荐顺序 G → G.5 → H → D

## Branch Advice

- 当前分支:`feat/phase63-governance-closure`(已切出,active_context.md 标注)
- 建议操作:Human Design Gate 通过后,Codex 在该分支上实装 S1-S4
- 建议 PR 范围:全部 4 个 slice 一次 PR;review milestone 分 3 个(M1 / M2 / M3),Codex 按 milestone 给出 commit 建议,Human 控制提交节奏

## Model Review Gate

**已完成**(2026-04-29,reviewer = external-model GPT-5):**verdict = BLOCK**。3 BLOCK + 3 CONCERN。详见 `docs/plans/phase63/model_review.md`。

**Claude 消化决策摘要**(本 design_decision 已转 final-after-m0):
- Q1 [BLOCK]:**不更新 §5 矩阵**(§S2 = 删 dead code 后无需扩展 token,自然消化)
- Q5 [BLOCK]:**S5 推迟到 Phase 64**(filesystem JSON 现状不适用 SQLite transaction;P2 兑现作为独立 phase)
- Q6 [BLOCK]:S3 增加 2 条 Repository bypass 守卫(`test_only_governance_calls_repository_write_methods` + `test_no_module_outside_governance_imports_store_writes`)
- Q2 [CONCERN]:Q6 follow-up 已包含
- Q3 [CONCERN]:扩展 ACTOR_SEMANTIC_KWARGS 闭集 + 移除 `action`(已落实)
- Q4 [CONCERN]:M0 audit slice 已完成(report-only NO_SKIP 扫描)

修订后的 design 等待 Human Design Gate 审批。

## 不做的事(详见 kickoff non-goals)

- 不重写 store 函数本身;Repository 只做最小封装(事务管理留给 Phase 64)
- **不修改 INVARIANTS 任何文字**(包括 §5 矩阵)
- 不修改 Phase 60-62 任何对外可观测行为(`_route_knowledge_to_staged` 删除是零行为变化,因为生产 0 触发)
- 不引入新 OperatorToken source(`librarian_side_effect` 是 Phase 61 既有,不动)
- 不引入 SQLite transaction wrapping(推迟到 Phase 64)
- 不引入 staged 应用 / 失败回滚(本 phase 不做 apply_proposal 事务回滚)
- 不引入新 LLM 调用路径
- 不引入 Operator-facing CLI 扩展
- 不在本 phase 完成 durable proposal artifact 层(后续方向)
- 不在本 phase 修复 NO_SKIP 红灯 2 条(Path B / Specialist LLM 路径,移到 G.5)

## 验收条件(全 phase)

详见 `kickoff.md` §完成条件。本 design_decision 与 kickoff 一致,无补充。
