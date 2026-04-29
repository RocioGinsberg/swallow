---
author: claude
phase: phase63
slice: design-audit
status: draft
depends_on: ["docs/plans/phase63/design_decision.md"]
---

TL;DR: has-blockers — 5 slices audited, 9 issues found (2 BLOCKERs, 7 CONCERNs)

## Audit Verdict

Overall: has-blockers

---

## Issues by Slice

### Slice S1: §7 集中化函数 + 2 条守卫真实化

- [CONCERN] **`workspace.py` 的 `base` 默认值来源未具体说明** — design_decision §S1 写明 `base` 默认为 `Path.cwd()` 或 `SWL_ROOT`,但"或"是运行时分支还是环境变量优先级规则没有说清楚。Codex 实装时需要自行决策优先级(SWL_ROOT > cwd 还是反之)。可以实装但需要显式留下 assumption 注释。

- [CONCERN] **actor-semantic kwarg 白名单不完整且没有 closed-set 声明** — R2 缓解策略给出的白名单是 `{"actor","submitted_by","caller","action","actor_name","performed_by"}`,但 design_decision §S1 "关键设计决策"给出的是 `{"actor","submitted_by","caller","action"}`(少了 `actor_name` 和 `performed_by`)。两处白名单不一致,Codex 无法确定以哪个为准。若白名单遗漏真实的 actor 上下文 kwarg,守卫将产生漏报,直接违反 S1 的 non-vacuous 目标。

- [CONCERN] **`models.py` SQL DEFAULT 字符串改写方式未说明** — S1 影响范围列出了 `models.py`(SQL DEFAULT 字符串 + line 297 `action="local"`),但 SQL DEFAULT 字符串(`DEFAULT 'local'`) 是内嵌在 DDL 字符串内的字面量,无法通过调用 `local_actor()` 替换——它在 Python 层不是一个 kwarg 调用。Codex 需要自行决定:是保留 DDL 中的 `DEFAULT 'local'` 字面量(但这会使守卫误报或需要将 DDL 字符串加入守卫豁免名单),还是把默认值移到 Python 层。设计未说明对 DDL 字面量的处理策略。

---

### Slice S2: stagedK 治理通道

- [CONCERN] **`ProposalTarget.STAGED_KNOWLEDGE` 是否已存在未经确认** — design_decision §S2 写道"若 target 模型未含 STAGED_KNOWLEDGE,需要扩展 `ProposalTarget` enum"。这是实装时的条件分支,但设计没有给出现有枚举成员清单,Codex 实装前需要自行 grep 确认。若枚举不存在则 S2 的实装范围会扩大,影响 M2 时间。属于可实装但不确定的前提。

- [BLOCKER] **`test_only_orchestrator_uses_librarian_side_effect_token` 守卫的 AST 扫描目标未定义** — S2 验收条件要求该守卫通过,守卫语义是"CLI / Specialist 不签发该 token"。但设计文档完全没有说明该守卫用什么方式验证:是 AST 扫描 `OperatorToken(source="librarian_side_effect")` 调用位置、是 grep、还是 import 路径检查?Codex 无法在没有守卫实现策略的情况下写出非-vacuous 守卫。注意此守卫被标为 §9 表外(design_decision §守卫与测试映射表),意味着它没有继承 S4 的"AST 优先"策略描述——S2 内没有对应说明。

---

### Slice S3: Repository 抽象层骨架 + `_PENDING_PROPOSALS` 重复检测

- [BLOCKER] **`apply_proposal` 函数签名在 DATA_MODEL 与 design_decision 之间存在不兼容** — DATA_MODEL §4.1 定义的权威签名是:

  ```python
  def apply_proposal(proposal_id: str, operator_token: OperatorToken, target: ProposalTarget) -> ApplyResult:
  ```

  而 design_decision §S2 描述的调用形式是:

  ```python
  governance.apply_proposal(OperatorToken(source="librarian_side_effect", actor=local_actor()), target=ProposalTarget.STAGED_KNOWLEDGE, payload=StagedCandidate(...))
  ```

  差异点有两处:(1) DATA_MODEL 签名第一个参数是 `proposal_id: str`,调用方却没有传 `proposal_id`;(2) DATA_MODEL 签名没有 `payload` 参数,调用方却传了 `payload=StagedCandidate(...)`。kickoff.md §完成条件也写道调用形式包含 `payload=` 参数。Codex 无法在两个权威文档不一致的情况下确定实装签名,且无论选哪个版本都会违反另一个文档的约束。此差异必须在设计层消解后才能开始 S3 和 S2 实装。

- [CONCERN] **Repository 私有方法的完整参数签名未定义** — design_decision §S3 说明"Repository 类只做 1:1 对应原 store 函数转发",验收条件也验证方法存在。但具体 `_promote_canonical(...)` / `_apply_metadata_change(...)` / `_apply_policy_change(...)` 的参数签名完全依赖"原 store 函数签名"——而现有 store 函数签名没有在设计文档中列出。Codex 必须自行阅读 `store.py` / `router.py` / `mps_policy_store.py` 来推导签名。这不是 blocker(可以做),但存在误判原始函数"全部参数"的风险,若有可选参数被遗漏会导致 R3 触发。

- [CONCERN] **`_PENDING_PROPOSALS` 的 `DuplicateProposalError` 检测的 key 语义未精确说明** — design_decision §S3 写道重复 `proposal_id` 第二次 register 时抛异常,key 是 `(target, proposal_id)`。但 kickoff §G3 只写了"重复 `proposal_id`"(没有 target)。若两个不同 target 可以共用同一 proposal_id,则 key 应该包含 target;若 proposal_id 本身全局唯一(ULID),则 target 是冗余的。两处描述不一致,Codex 需要选择其中一个语义——选错会导致测试设计错误。

---

### Slice S4: §9 剩余 13 条守卫批量实装

- [CONCERN] **"skip with TODO comment" 的漂移门槛没有量化** — risk_assessment R6 缓解策略写道:激活守卫后发现既有漂移,优先用 `pytest.skip(reason="known drift, see R6")` 临时跳过,超过 3 条红灯时触发 phase-guard。但设计没有说明哪条守卫绝对不允许 skip(不可 skip 的应当是 §0 四条核心不变量相关的守卫)。Codex 在遭遇 `test_no_executor_can_write_task_table_directly` 或 `test_state_transitions_only_via_orchestrator` 红灯时是否可以 skip?如果这类 §0 级别守卫也可以 skip,违反了 kickoff §设计边界的"守卫红灯不得 merge"要求。需要明确哪些守卫属于不可 skip 集合。

- [CONCERN] **§9 表中的 `test_only_apply_proposal_calls_private_writers` 已在 Phase 61 实装,S3 要求"更新扫描目标"** — design_decision §S3 验收条件要求更新该守卫的扫描目标到 `truth/*.py` 的私有方法。但 S4 的守卫清单和守卫计数(17条总计)是基于"Phase 61 实装 3 条"的基础上计算的,这 3 条包括 `test_only_apply_proposal_calls_private_writers`。S3 对该守卫的修改属于修改既有守卫而非新增,不计入 S4 的"14 条新增"计数。但 S3 验收条件中没有明确说明修改后该守卫仍然属于 §9 表的 17 条之一,也没有说明若修改破坏了该守卫如何归责(S3 vs S4 的 PR 边界)。

- [CONCERN] **`test_append_only_tables_reject_update_and_delete` 的被测表清单未列出** — DATA_MODEL §4.2 列出 4 张 append-only 表(`event_log` / `event_telemetry` / `route_health` / `know_change_log`)。但 S5 引入的 `route_change_log` / `policy_change_log` 也应当是 append-only 表并受该守卫保护(design_decision §S5 明确写道"由 `test_append_only_tables_reject_update_and_delete` 守卫保护")。守卫实装时被测表清单需要包含这两张新表,而这两张表在 S4 实装时尚不存在(S5 在 Codex 推荐顺序中先于 S4)——但 milestone review 顺序是 S4 在 M3,S5 在 M4。Codex 实装 S4 守卫时如何处理 S5 尚未引入的表?守卫是否应当在 S5 完成后才对新表启用?设计没有说明。

---

### Slice S5: 事务回滚 staged 应用 + append-only 审计 log

- [CONCERN] **`route_change_log` / `policy_change_log` 的完整 schema 未对比 `know_change_log` 列出** — design_decision §S5 给出了字段列表:`change_id ULID PK / proposal_id / target / before_snapshot JSON / after_snapshot JSON / outcome {applied,rolled_back} / actor / created_at`。但 DATA_MODEL §3.3 中 `know_change_log` 的字段是 `change_id / target_kind / target_id / action / rationale / timestamp / actor`——两者字段名有多处差异(例如 `timestamp` vs `created_at`、`action` vs `outcome`、缺少 `before_snapshot` / `after_snapshot` 的语义等)。R10 识别了此风险,但设计给出的 S5 schema 并未与 `know_change_log` 对齐,也未说明差异是有意为之还是遗漏。Codex 实装时若发现 R10 风险,无法判断是照 S5 字段列表实装(与 know_change_log 不一致)还是先对齐再实装。

---

## 守卫计数核查

§9 标准表实装计数:

- INVARIANTS §9 列出 17 条守卫,逐条核对如下:

| 守卫名 | 来源 | Phase 63 归属 |
|---|---|---|
| `test_no_executor_can_write_task_table_directly` | §5 矩阵 | S4 行为合规类 |
| `test_state_transitions_only_via_orchestrator` | §0 第 1 条 | S4 行为合规类 |
| `test_path_b_does_not_call_provider_router` | §4 | S4 行为合规类 |
| `test_validator_returns_verdict_only` | §0 第 1 条 | S4 行为合规类 |
| `test_specialist_internal_llm_calls_go_through_router` | §4 Path C | S4 行为合规类 |
| `test_canonical_write_only_via_apply_proposal` | §0 第 4 条 | Phase 61 既有 |
| `test_all_ids_are_global_unique_no_local_identity` | §7 | S4 ID & 不变量类 |
| `test_event_log_has_actor_field` | §7 | S4 ID & 不变量类 |
| `test_no_hardcoded_local_actor_outside_identity_module` | §7 | S1 |
| `test_no_absolute_path_in_truth_writes` | §7 | S1 |
| `test_no_foreign_key_across_namespaces` | DATA_MODEL §2 | S4 ID & 不变量类 |
| `test_append_only_tables_reject_update_and_delete` | DATA_MODEL §4.2 | S4 ID & 不变量类 |
| `test_only_apply_proposal_calls_private_writers` | DATA_MODEL §4.1 | Phase 61 既有(S3 更新扫描目标) |
| `test_artifact_path_resolved_from_id_only` | DATA_MODEL §6 | S4 ID & 不变量类 |
| `test_route_metadata_writes_only_via_apply_proposal` | PROVIDER_ROUTER §6.4 | Phase 61 既有 |
| `test_route_override_only_set_by_operator` | §7.1 | S4 行为合规类 |
| `test_ui_backend_only_calls_governance_functions` | INTERACTION §4.2.1 | S4 UI 边界 |

计数核查结论:17 条 = Phase 61 既有 3 条 + S1 新增 2 条 + S4 新增 12 条。计数平衡,与 design_decision 声明一致。

S4 行为合规类实际为 6 条(含 `test_route_override_only_set_by_operator`),S4 ID & 不变量类为 5 条,S4 UI 边界 1 条,合计 S4 贡献 12 条——与 design_decision §S4 目标一致。

**注意**:`test_apply_proposal_rollback_executes_on_failure` 是 S4 引入的第 13 条守卫(含在"12 §9 表内 + 1 S5 配套事务回滚守卫"),但该守卫**不在** INVARIANTS §9 表的 17 条内。设计文档在这一点上措辞准确,无计数错误。

---

## Questions for Claude

1. **[for BLOCKER S3] `apply_proposal` 函数签名以哪个为准?** DATA_MODEL §4.1 是三参数 `(proposal_id, operator_token, target)`,无 `payload` 参数;但 design_decision §S2 和 kickoff 完成条件均展示了包含 `payload=` 的四参数调用形式。Phase 63 实装前必须明确权威签名,并同步更新 DATA_MODEL §4.1 或 design_decision,两者择一对齐。

2. **[for BLOCKER S2] `test_only_orchestrator_uses_librarian_side_effect_token` 守卫的实现策略是什么?** 是 AST 扫描调用位置、import 路径检查,还是运行时 token 类型验证?需要在 design_decision §S2 中补充,与 S1 / S4 其他守卫的"AST 优先"策略对齐说明。

3. **[for CONCERN S1] actor-semantic kwarg 白名单以哪一份为准?** `{"actor","submitted_by","caller","action"}` (design_decision §S1) vs `{"actor","submitted_by","caller","action","actor_name","performed_by"}` (risk_assessment R2),需要统一到一处并作为 closed-set 常量明确列出。

4. **[for CONCERN S1] DDL 中的 `DEFAULT 'local'` 字面量如何处理?** `models.py` 中 SQL DEFAULT 字符串无法调用 `local_actor()`,守卫 pattern 是否豁免 DDL 字符串内的 `'local'` 字面量?若豁免,豁免逻辑需要在 AST 守卫实现中明确说明。

5. **[for CONCERN S3] `_PENDING_PROPOSALS` 的 duplicate 检测 key 是 `proposal_id` 还是 `(target, proposal_id)`?** kickoff §G3 和 design_decision §S3 两处描述不一致,需要统一。

6. **[for CONCERN S4] 哪些 §9 守卫属于绝对不可 skip 集合?** 即使 R6(既有漂移暴露)触发,某些守卫(特别是 §0 四条核心不变量相关的守卫)应当不允许带 `pytest.skip` 合并。需要在 design_decision §S4 或 risk_assessment R6 中明确列出。

7. **[for CONCERN S4] `test_append_only_tables_reject_update_and_delete` 在 S4 实装时是否应包含 S5 尚未引入的 `route_change_log` / `policy_change_log` 表?** 若不包含,该守卫在 S5 完成后需要再次更新,但 S4 是 M3 而 S5 是 M4——M3 review 时守卫是否允许不覆盖 M4 将引入的表,需要在 milestone 边界中显式说明。

8. **[for CONCERN S5] `route_change_log` / `policy_change_log` 与 `know_change_log` 字段名差异是有意设计还是遗漏?** 若有意不对齐,需要在 design_decision §S5 中注明理由;若应当对齐,需要给出字段对照表。两张新表的完整 DDL(含字段名和类型)应当在 design_decision 中给出,而非仅描述字段列表。

---

## Confirmed Ready

无 slice 被判定为完全无问题。所有 5 个 slice 均有至少一个 CONCERN 或 BLOCKER。

两个 BLOCKER 阻止以下 slice 安全开始实装:
- **S2**:守卫实现策略缺失(BLOCKER)
- **S3**:函数签名冲突(BLOCKER,同时影响 S2 调用形式)

其余 3 个 slice(S1 / S4 / S5)可以在 CONCERN 带显式 assumption 注释的前提下开始实装,但建议在 Claude 明确上述 Questions 3-8 后再动工,以降低返工概率。
