---
author: claude
phase: 61
created_at: 2026-04-28
status: draft
depends_on:
  - docs/plans/phase61/design_decision.md
  - docs/plans/phase61/kickoff.md
  - docs/plans/phase61/risk_assessment.md
  - docs/plans/phase61/context_brief.md
---

TL;DR: has-blockers — 4 slices audited, 7 issues found (2 BLOCKER / 3 CONCERN / 2 NIT)

---

## Audit Verdict

Overall: **has-blockers**

两个 BLOCKER 都集中在 `_load_proposal_artifact()` 的输入语义上,以及派生写入的触发语义问题。如果不修订,Codex 在 S2/S3 实施时必须自行补设计决策——而且两个方向都有合理的不同选择,任何一种都会影响 governance.py 的内部结构。

---

## Issues by Slice

### Slice S1: governance 模块 + 类型 + 骨架

- [CONCERN] `OperatorToken` dataclass 设计中新增了 `actor` 字段(`actor: str`,由 `swallow.identity.local_actor()` 获取),但 SELF_EVOLUTION.md §3.1.1 的权威定义只有 `source` / `reason` 两个字段,没有 `actor`。`reason` 在设计文档中是 `str | None = None`(可为空),但 design_decision §B 写为"必填,审计要求"。Codex 如果按 design_decision 实现会生成与 SELF_EVOLUTION 不同的 dataclass 签名。在 S1 这是类型定义层,一旦确定后续 slices 全部依赖——需在 S1 动手前明确哪份文档的字段列表以何为准。

- [NIT] S1 验收条件中"`OperatorToken` 拒绝非法 source(类型检查 + 单元测试)"——`Literal` type hint 在 Python 运行时不会自动拒绝非法值,需要显式 `__post_init__` 或 validator。验收条件没说明用哪种机制。Codex 需要自行决定,两种实现方式(runtime check vs 纯 type hint)在测试写法上有差异。

---

### Slice S2: Canonical 写路径收敛 + 守卫测试 1

- [BLOCKER] `orchestrator.py:2664-2667` 的 `save_canonical_registry_index` / `save_canonical_reuse_policy` 调用是**无条件**刷新,发生在 `append_canonical_record`(line 2956,仅在 `decision_type == "promote"` 时调用)之前的一段独立代码中。也就是说:存在 canonical record 没有新增但派生写入仍然发生的场景(例如 task 完成时刷新索引)。design_decision §D 伪代码把这两个派生写入放进 `_apply_canonical()` 内部,作为"随主写入一并发生"的副作用——但代码现状中 orchestrator.py:2664-2667 的语义是"读取现有 canonical registry 并刷新派生",与"apply canonical record 后派生"是不同的触发条件。如果 Codex 把这两处收敛进 `apply_proposal()`,会把原本"任意时机刷新"的调用变成"必须通过 proposal apply"的调用——这会改变 orchestrator 初始化 / task startup 场景下的刷新行为,造成派生索引不同步的 bug。

  设计需要明确:orchestrator 里这两个非 apply-scoped 的"读取全量 canonical registry 并重建索引"调用是否也要收敛?如果不收敛,守卫测试的白名单规则里 orchestrator.py 也需要是豁免文件,这会使守卫测试失去对 orchestrator 的约束力。

- [CONCERN] S2 对 orchestrator.py:2664-2667 的 `OperatorToken.source` 赋值方案在 design_decision 中只提到"task knowledge-promote,经 Orchestrator,source=cli"——但从代码看这两处(line 2664-2667 和 line 2963-2965)都是在 task 执行过程中由 Orchestrator 内部逻辑触发,不是直接的 CLI 调用。Orchestrator 内部路径用 `source="cli"` 是否准确?SELF_EVOLUTION §3.1 对 `"cli"` 的定义是"Operator 通过 CLI 命令显式触发"。如果 Orchestrator 是作为 CLI 命令的执行者(即 `swl task run` 触发 `task knowledge-promote`),用 `"cli"` 说得通——但如果 Orchestrator 在无 CLI 的 daemon 模式或 API 调用中执行,`"cli"` 语义就不准确了。Codex 需要决定时会做一个假设,建议设计文档明确这条路径的 source 语义。

- [CONCERN] 守卫测试 1 (`test_canonical_write_only_via_apply_proposal`) 设计为 AST 扫描 `src/` 中对 `append_canonical_record` 和 `persist_wiki_entry_from_record` 的直接调用。design_decision §S2 验收条件的 grep 列表为:`append_canonical_record | persist_wiki_entry_from_record`。但 `save_canonical_registry_index` / `save_canonical_reuse_policy` 是 canonical truth 写入的一部分,grep 验收条件里没有列它们。如果守卫测试只扫描主写入函数,而忽略派生写入函数,则 orchestrator.py:2664-2667 中的直接调用在收敛后仍然存在时守卫不报警——守卫假阴。需明确:派生写入函数是否也在守卫扫描范围内?

---

### Slice S3: Route metadata 写路径收敛 + 守卫测试 2/3

- [BLOCKER] `apply_reviewed_optimization_proposals()` 不接受 `proposal_id: str` 参数——它接受 `review_path: Path`(review record 文件路径),内部处理 N 个 `ProposalReviewEntry`,每条有自己的 `entry.proposal_id`。design_decision §D 的 `apply_proposal(proposal_id, operator_token, target)` 签名假设每次调用对应一个 proposal artifact。

  但 Meta-Optimizer 的实际 apply 路径是"一次 apply review record,内含多个已审阅的 proposals"——这是批量写入,不是逐个 proposal_id 的单条写入。更关键的是:`apply_reviewed_optimization_proposals()` 的 proposal_id 是 `ProposalReviewEntry` 的 ID,不是一个可以在 `.swl/artifacts/proposals/<proposal_id>.json` 找到对应 artifact 的 ID(Meta-Optimizer 的 artifact 是 bundle 文件 `OptimizationProposalBundle`,不是单独的 per-proposal artifact)。

  `_load_proposal_artifact(proposal_id)` 内部假设去 `.swl/artifacts/proposals/<proposal_id>.json` 加载,但 Meta-Optimizer 的 proposal 存在 bundle 文件里。这个 schema 不匹配不是适配问题——Codex 无法在没有设计决策的情况下决定如何桥接。

  设计需要明确:S3 是把 `apply_reviewed_optimization_proposals()` 整体包进一个 `apply_proposal()` 调用(用 bundle/review 路径作为 proposal_id 的代理),还是拆成 N 个 per-entry `apply_proposal()` 调用?前者意味着 `proposal_id` 语义是 review record ID 而非单条 proposal ID;后者意味着循环调用并要面对事务性问题(见风险评估补遗)。

- [NIT] S3 完成后 `test_only_apply_proposal_calls_private_writers` 是聚合断言(canonical + route + policy),但此时 S4(policy 收敛)尚未完成——policy 写路径还未通过 apply_proposal。这个守卫在 S3 末尾实装并要求 PASS,意味着守卫要么豁免 policy 路径(临时弱化守卫),要么 Codex 在 S3 提前完成 policy 收敛。design_decision 没有明说用哪种方式处理。建议明确:S3 实装该测试时临时 skip policy 断言部分,等 S4 完成后再激活;否则 S3 的守卫测试对 S4 有隐式依赖。

---

### Slice S4: Policy 写路径收敛 + Phase 49 concern 消化

- [READY] S4 改动范围小且边界清晰(`cli.py:2465` 单处 + Phase 49 concern 消化),依赖清楚(S1 骨架 + S2 canonical OperatorToken 模式可复用)。`save_audit_trigger_policy` 在 `consistency_audit.py:194`,调用方是 `cli.py:2465`,单处收敛,无复杂 schema 适配。

---

## Questions for Claude

1. `OperatorToken` dataclass 的字段定义应以哪份文档为准?SELF_EVOLUTION §3.1.1 定义两个字段(`source` / `reason`),design_decision §B 新增了第三个字段 `actor: str`(调用 `identity.local_actor()`)。`reason` 是 `str | None` 还是必填?请在 design_decision 中声明权威定义,覆盖 SELF_EVOLUTION 的现有字段列表(或说明实现时 SELF_EVOLUTION 会在 closeout 补上 `actor` 字段)。

2. `orchestrator.py:2664-2667` 的 `save_canonical_registry_index` / `save_canonical_reuse_policy` 是无条件刷新(非 canonical write 的 side effect),不在 `append_canonical_record` 的 conditional 分支里。这两处是否也要收敛进 `apply_proposal()`?如果是,如何处理"刷新索引但不 apply 新 canonical record"的语义?如果否,守卫测试的白名单规则是什么(orchestrator.py 整文件豁免?还是只豁免这两行)?

3. Meta-Optimizer 的 `apply_reviewed_optimization_proposals()` 是批量操作(一次处理 N 个 approved entries),而 `apply_proposal()` 签名是单 `proposal_id`。S3 是否要修改调用模式:将整个 review record 映射为单一 proposal_id(review_id 即 proposal_id)?还是循环 N 次调用 `apply_proposal()`?如果是后者,中途失败的部分回滚策略是什么?

4. 派生写入 `save_canonical_registry_index` / `save_canonical_reuse_policy` 是否也纳入守卫测试的扫描目标?如果纳入,orchestrator.py 里无条件刷新的两处调用需要同样收敛(见问题 2)。如果不纳入,守卫 1 只保护主写入(`append_canonical_record`)而不保护派生写入,请在守卫测试设计中明确这个边界。

5. `test_only_apply_proposal_calls_private_writers` 在 S3 末尾实装时,S4 的 policy 路径尚未收敛。这个测试是否应该在 S3 仅断言 canonical + route 部分,等 S4 完成后扩展 policy 断言?还是 S4 必须在 S3 的同一 commit group 内完成?

---

## Confirmed Ready

- **S1 骨架**: 改动范围明确(新建单文件),类型定义依赖问题(问题 1)解决后可以直接开始。
- **S4 Policy + Phase 49**: 范围边界清晰,单处 caller 收敛,无 schema 适配挑战。

---

## 决策审视 (Claude 主线预决)

### §B — `"librarian_side_effect"` 第三种 source 值

扩展为三种值是合理的最小侵入选择;让 Librarian 侧效走完整 staged → CLI apply 流程会破坏 task-time 语义,成本更高。`"librarian_side_effect"` 命名对应具体路径(`orchestrator.py:498-499`),语义范围是受控的。

潜在滥用风险:如果未来其他 agent(例如 Meta-Optimizer 的某条新路径)需要系统内部触发 canonical 写入,可能会类比加 `"meta_optimizer_side_effect"`。建议在 governance.py 的 docstring 中写明"新增 source 值必须经 design phase 审批",这比 risk_assessment 当前写法更明确。

`"librarian_side_effect"` 命名可以接受,但它暴露了实现角色名(`librarian`)而非触发模式(`agent_side_effect`)。如果未来有第二个 agent 产生同类侧效,枚举会因为角色命名而爆炸。这是一个设计选择问题而非 BLOCKER——可以实施,但建议 Claude 在 design_decision 中写明命名理由以防止后续混乱。

### §C — harness 5 函数不纳入收敛

从代码层证实:`save_route` / `save_knowledge_policy` / `save_retry_policy` / `save_stop_policy` / `save_execution_budget_policy` 全部定义在 `store.py` 中,签名为 `(base_dir, task_id, payload)`,写入 task-scoped JSON 文件(每个文件路径包含 `task_id`),与系统级 `route_weights.json` / `policy_records` 完全不同。

判定站得住脚。`save_route` 写的是 task 级别的 route 决策记录(路径包含 `task_id`),与 `save_route_weights` 写的全局 `route_weights.json` 是不同的物理 truth。INVARIANTS §5 矩阵的 `route` 列对应系统级 route metadata;harness 这 5 个函数对应 `task` 列的派生记录。守卫测试扫描 `save_route_weights` / `save_route_capability_profiles` 不会误命中这 5 个函数。

### §D — Repository 抽象层不实装

governance.py 直接调 store 函数的实现意味着它是一个 dispatch 层而非真正的 governance 层——没有抽象,只有 routing。这不是 BLOCKER,但有一个具体实施后果:

DATA_MODEL.md §4.1 的 CI 守卫设计是基于 `_promote_canonical` / `_apply_metadata_change` / `_apply_policy_change` 这三个私有方法名的 grep 计数。但本轮实现里这三个私有方法根本不存在——governance.py 内部直接调 `append_canonical_record` / `save_route_weights` / `save_audit_trigger_policy`。

因此 INVARIANTS §9 中 `test_only_apply_proposal_calls_private_writers` 的守卫不能基于 DATA_MODEL 描述的那三个私有方法名来断言——这三个方法名此轮不会创建。守卫测试的实际扫描目标(design_decision 中确认为 `append_canonical_record` / `save_route_weights` / `save_route_capability_profiles` / `save_audit_trigger_policy`)与 DATA_MODEL §4.1 描述的私有方法名是两套不同的 API。design_decision 没有显式声明这个偏离。

**建议**:在 design_decision 中增加一条明确的"与 DATA_MODEL §4.1 的偏离声明":本轮守卫基于现有 store 函数名而非 Repository 私有方法名,Repository 实装后需重写守卫逻辑。

---

## 风险评估补遗

risk_assessment 列出 R1-R6,以下补充两个未被覆盖的实施风险:

**R7: Meta-Optimizer 批量 apply 的事务性**

`apply_reviewed_optimization_proposals()` 内部对 N 个 approved entries 做循环写入:先统一计算 `updated_weights` / `updated_profiles`,最后一次性调用 `save_route_weights` + `save_route_capability_profiles`。这是应用层事务——如果中间 apply 失败,提供了 `rollback_weights` / `rollback_capability_profiles` 字段但当前没有回滚执行代码。

如果 S3 把 `save_route_weights` / `save_route_capability_profiles` 替换为两次 `apply_proposal()` 调用,而 `apply_proposal()` 内部 `_emit_event()` 在两次写入之间执行——第一次 apply 成功并 emit event,第二次 apply 失败——系统会处于"route_weights 已更新但 route_capability_profiles 未更新,且 event_log 已记录第一次 apply"的不一致状态。risk_assessment 没有分析这种情况。设计需要说明:route_weights 和 route_capability_profiles 是否需要原子地 apply,或者允许分两步。

**R8: `apply_route_weights` / `apply_route_capability_profiles`(内存刷新)与 `save_*` 的配对关系未在设计中出现**

当前 `apply_reviewed_optimization_proposals()` 在 `save_route_weights` 后立即调用 `apply_route_weights`(内存更新),`save_route_capability_profiles` 后立即调用 `apply_route_capability_profiles`。同样的配对出现在 `cli.py:2493-2494` 和 `cli.py:2560-2561`。

design_decision 完全没提 `apply_route_weights` 和 `apply_route_capability_profiles` 这两个内存刷新函数。如果 Codex 仅把 `save_*` 收敛进 `apply_proposal()` 而不一并处理这两个 `apply_*` 调用,route metadata 变更后内存状态不会更新,直到下次进程重启。这是一个等价性破坏点。设计需要明确 `_apply_route_metadata()` 内部是否要调用 `apply_route_weights()` / `apply_route_capability_profiles()`。

---

## 验收条件审视

**"11 处直接写路径全部收敛"计数与守卫扫描目标的一致性问题**

context_brief 的表格列出 16 个写入点(不是 11 个):其中 `save_canonical_registry_index` 出现 4 次,`save_canonical_reuse_policy` 出现 4 次,`append_canonical_record` 出现 3 次,`persist_wiki_entry_from_record` 出现 2 次,`save_route_weights` 出现 2 次,`save_route_capability_profiles` 出现 2 次,`save_audit_trigger_policy` 出现 1 次。

kickoff 的"11 处直接写路径"是对 unique 调用点的计数(不把每次出现都算一处),但 context_brief 写法会让 Codex 困惑哪些是需要收敛的 site。建议明确:对于派生写入(registry index / reuse policy)是否要求完全消除在 governance.py 以外的调用,还是允许部分保留(特别是问题 2 中的非 proposal-scoped 刷新)。

**`store.py` / `knowledge_store.py` / `router.py` 是不是也是"caller"**

kickoff 完成条件写道:grep 输出"仅在 governance.py 与底层 store 文件中匹配"。这意味着 store 函数的定义文件本身被豁免——这是合理的。但 Codex 可能困惑:`router.py` 同时是 `save_route_weights` 的定义文件和某些操作的 caller(例如 `apply_route_weights` 内部调 `load_route_weights`)。建议在守卫测试 docstring 中明确"底层 store 文件"的白名单列表:`store.py` / `knowledge_store.py` / `router.py` / `consistency_audit.py`。

---

## 与设计文档一致性核查

| 检查项 | 状态 | 备注 |
|--------|------|------|
| INVARIANTS §0 第 4 条 → design_decision G1-G5 | 对齐 | apply_proposal 作为唯一入口的目标明确 |
| INVARIANTS §5 矩阵 `policy` 列 → §C harness 判定 | 对齐 | 代码层验证:harness 函数写 task-scoped 文件,不是系统级 policy_records |
| INVARIANTS §9 三条守卫测试 → S2/S3 | 部分对齐 | 守卫测试名与 §9 一致,但守卫内部扫描目标(store 函数名而非 Repository 私有方法名)与 DATA_MODEL §4.1 描述有偏离,未声明 |
| SELF_EVOLUTION §3.1 签名 → design_decision §A | 对齐 | 采用含 `target` 的三参数签名 |
| SELF_EVOLUTION §3.1 三步流程(load → validate → dispatch) → design_decision §D 伪代码 | 对齐 | 伪代码结构匹配 |
| SELF_EVOLUTION §3.1.1 OperatorToken 字段 → design_decision §B dataclass | **不一致** | 设计文档定义 `source` / `reason` 两个字段;design_decision 增加了 `actor` 字段;`reason` 的必填性也有分歧 |
| INTERACTION §4.2.3 `swl knowledge promote` → 代码实际 `swl knowledge stage-promote` | 未修复(已知偏离) | kickoff 明确说明不在本 phase 修正;可接受 |
| DATA_MODEL §4.1 Repository 模式 → §D 决策跳过 | 未声明偏离 | design_decision 没有对 DATA_MODEL 的偏离做显式声明;守卫测试将扫描 store 函数名而非 `_promote_canonical` 等私有方法名——这个差异需要在 design_decision 中记录 |

---

## 问题分类汇总

### 必须修订项(BLOCKER,实施前需解答)

1. **[BLOCKER] orchestrator.py:2664-2667 的无条件派生刷新语义**:这两处调用不属于 canonical record apply 的 side effect,而是独立的"读取全量 registry 并重建索引"逻辑。收敛进 apply_proposal 会改变语义;不收敛则守卫扫描规则不清晰。需要设计决策。

2. **[BLOCKER] Meta-Optimizer apply 路径的输入 schema 与 `apply_proposal(proposal_id)` 签名不匹配**:`apply_reviewed_optimization_proposals()` 接受 review record 路径(含 N 个 entries),不是单条 proposal_id。governance 层需要明确的输入适配方案——是 review_id 作为 proposal_id,还是循环 N 次调用,或其他方案。如果循环调用,需明确原子性策略。

### 建议修订项(CONCERN,Codex 可实施但需要记录假设)

3. **[CONCERN] `OperatorToken` 字段定义权威性**:design_decision 增加了 SELF_EVOLUTION 未定义的 `actor` 字段,`reason` 必填性有分歧。建议 Claude 在 design_decision 中声明实现采用的权威定义,并在 closeout 时同步 SELF_EVOLUTION。

4. **[CONCERN] orchestrator.py:2664-2667 / 2956 / 2963-2965 的 `source="cli"` 语义**:Orchestrator 内部路径使用 `source="cli"` 的前提是"Orchestrator 始终是 CLI 命令的同步调用者"。如果这个假设成立,需在 design_decision 中明确;如果有非 CLI 触发 Orchestrator 的场景,需使用不同的 source 值。

5. **[CONCERN] `test_only_apply_proposal_calls_private_writers` 在 S3 末尾实装时 policy 路径未收敛**:需明确该测试在 S3 是否临时跳过 policy 断言,或者 S3 和 S4 必须串行且守卫在 S4 完成后才激活。

### 可选改进项(NIT)

6. **[NIT] `OperatorToken.source` 的运行时校验机制**:验收条件未说明用 `__post_init__` 还是纯 type hint。建议明确,以保证守卫测试可以测试非法 source 的拒绝行为。

7. **[NIT] DATA_MODEL §4.1 偏离未声明**:守卫测试的实际扫描目标是 store 函数名,而 DATA_MODEL §4.1 描述的是 Repository 私有方法名。建议在 design_decision 中增加一条"与 DATA_MODEL §4.1 的偏离声明"。
