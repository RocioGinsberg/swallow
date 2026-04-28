---
author: claude
phase: 61
slice: consistency-check
status: draft
depends_on:
  - docs/plans/phase61/design_decision.md
  - docs/plans/phase61/kickoff.md
  - docs/plans/phase61/risk_assessment.md
  - docs/design/INVARIANTS.md
---

TL;DR: 13 consistent, 1 inconsistent (CONCERN, not BLOCK — line number drift only), 2 not-covered — high-risk R8 save+apply pairing PASSES.

---

## Consistency Report

### 检查范围

- 对比对象: `git diff main...HEAD` (commits c2d4abb / e54f7a3 / e48bf9b / b7f0ecf / 3dc9d93) vs `docs/plans/phase61/design_decision.md` §A–§G, `kickoff.md`, `risk_assessment.md`, `docs/design/INVARIANTS.md` §0 #4, §5, §9

---

### 一致项

- [CONSISTENT] **§A 函数签名**: `apply_proposal(proposal_id: str, operator_token: OperatorToken, target: ProposalTarget) -> ApplyResult` 与 SELF_EVOLUTION §3.1 版本一致。(`governance.py:174-199`)

- [CONSISTENT] **§B OperatorToken**: dataclass frozen=True, 字段 `source: OperatorSource` + `reason: str | None = None`，无 `actor` 字段。三个 Literal 值恰好为 `"cli"`, `"system_auto"`, `"librarian_side_effect"`。`__post_init__` 在 source 无效时抛 `ValueError`。(`governance.py:36-50`)

- [CONSISTENT] **§E 表 9 处 YES caller 全部收敛**: 逐项验证：
  - `cli.py:2340` → `apply_proposal(target=CANONICAL_KNOWLEDGE, source="cli")` (stage-promote, persist_wiki_entry + append_canonical)
  - `cli.py:2504` → `apply_proposal(target=ROUTE_METADATA, source="cli")` (route weights apply)
  - `cli.py:2575` → `apply_proposal(target=ROUTE_METADATA, source="cli")` (route capabilities update)
  - `cli.py:2471` → `apply_proposal(target=POLICY, source="cli")` (audit policy set)
  - `cli.py:2435` → `apply_proposal(target=ROUTE_METADATA, source="cli")` (swl proposal apply)
  - `orchestrator.py:506` → `apply_proposal(target=CANONICAL_KNOWLEDGE, source="librarian_side_effect")`
  - `orchestrator.py:2966` → `apply_proposal(target=CANONICAL_KNOWLEDGE, source="cli")`
  - `meta_optimizer.py:1169` → `apply_proposal(target=ROUTE_METADATA, source="cli")` (via `apply_reviewed_optimization_proposals`)
  - `cli.py` route capabilities already covered above
  所有 9 处主写入均经 governance 入口。静态 grep 验证无残余直接调用。

- [CONSISTENT] **§E 表 7 处 NO (派生写入) 保留不动**: `save_canonical_registry_index` / `save_canonical_reuse_policy` 在守卫测试白名单中全局豁免。`orchestrator.py:2666/2669` (task startup 派生重建) 和 `orchestrator.py:2973/2975` (task knowledge-promote 派生) 均直接调用，未经 apply_proposal，符合设计 §E 判定。

- [CONSISTENT] **§E 表 orchestrator.py:2664-2667 原样保留 (BLOCK 级要求)**: 设计文档要求这 4 行必须不收敛。当前实现中 `save_canonical_registry_index` 在 `orchestrator.py:2666`，`save_canonical_reuse_policy` 在 `orchestrator.py:2669`，均为直接调用，未引入 apply_proposal。注：设计文档援引行号 2664-2667 与实际行号存在偏移（实际 2666/2669），但语义完全吻合。

- [CONSISTENT] **§F adapter**: `apply_reviewed_optimization_proposals(base_dir, review_path)` 签名未变，函数公开保留在 `meta_optimizer.py:1158`。其内部不再直接调 store 函数，改为 `register_route_metadata_proposal(review_path=...) + apply_proposal(target=ROUTE_METADATA, source="cli")`，实际逻辑迁移到 `governance.py:_apply_route_review_metadata()`。CLI `swl proposal apply` 路径在 `cli.py:2427-2441` 独立构造 `register_route_metadata_proposal(review_path=...) + apply_proposal()`，不经 meta_optimizer.py，符合 §F 设计意图。

- [CONSISTENT] **§G save+apply 配对 (R8 高风险项)**: `_apply_route_review_metadata()` (governance.py:517-525) 中顺序为：`save_route_weights → apply_route_weights → save_route_capability_profiles → apply_route_capability_profiles`，与原 `apply_reviewed_optimization_proposals` 逻辑完全一致。`_apply_route_metadata()` (governance.py:274-281) 直接写路径同样保持配对。四步全部存在，顺序正确。R8 PASS。

- [CONSISTENT] **INVARIANTS §9 守卫测试三条全部存在**: `test_canonical_write_only_via_apply_proposal` / `test_route_metadata_writes_only_via_apply_proposal` / `test_only_apply_proposal_calls_private_writers` 全部在 `tests/test_invariant_guards.py:51-101`。

- [CONSISTENT] **守卫测试使用 AST 扫描，仅扫描 src/swallow/**: `_find_protected_writer_uses` 函数使用 `ast.parse` 遍历 `ast.ImportFrom` / `ast.Call` 节点。扫描目标为 `SRC_ROOT = REPO_ROOT / "src" / "swallow"`，`tests/` 目录不在扫描范围内，符合设计 §E "tests/ 整目录豁免"。

- [CONSISTENT] **守卫测试白名单与设计 §E 表一致**: canonical 守卫白名单 `{governance.py, store.py, knowledge_store.py}`；route 守卫白名单 `{governance.py, router.py}`；聚合守卫白名单 `{governance.py, store.py, knowledge_store.py, router.py, consistency_audit.py}`。均与 §E 表精确匹配。

- [CONSISTENT] **Phase 49 concern 已移入 Resolved**: `docs/concerns_backlog.md` Resolved 表第一行记录 Phase 49 concern，消化方式为 "Phase 61 / M3"，描述与 design_decision §S4 吻合。

- [CONSISTENT] **subtask 超时断言放宽合理**: `b7f0ecf` 将 `assertLess(elapsed, 1.35)` 改为 `assertLess(elapsed, 1.75)`，用于测试一个 1s 超时的子任务。注释明确说明上限 (~3.8s full-suite outlier) 与放宽原因。1.75s 阈值仍能捕获 multi-second hang（>3s 情形下 elapsed 会超过 1.75 很多）。符合 active_context 注解要求。

---

### 不一致项

- [INCONSISTENT] **§E 表行号标注与实际代码行号存在偏移**
  - 来源: `design_decision.md:163-181` §E 精确清单标注 `orchestrator.py:2664` / `orchestrator.py:2667` 为不收敛的派生写入位置
  - 当前状态: 实际 `save_canonical_registry_index` 在 `orchestrator.py:2666`，`save_canonical_reuse_policy` 在 `orchestrator.py:2669`（偏移 +2 至 +2 行）
  - 期望状态: 设计文档援引 2664 / 2667
  - 建议: 行号偏移不影响语义正确性——函数调用关系完全符合设计意图，不需要代码修改。建议在 closeout 时将 §E 精确清单的行号注释更新为当前实际行号，避免后续 consistency check 误判。不视为 BLOCK。

---

### 未覆盖项

- [NOT_COVERED] **`_PENDING_PROPOSALS` 全局字典的生命周期管理**
  - 说明: `governance.py:88` 定义 `_PENDING_PROPOSALS: dict[tuple[ProposalTarget, str], object] = {}` 作为模块级全局字典，注册后的 proposal 不会在 `apply_proposal` 调用后自动清除。在长 process（如 CLI 单进程多次调用场景）中，已 apply 的 proposal 会在字典中积累。设计 §F 与 §D 未提及 proposal 注册对象的清理语义。当前测试全部在独立 `tmp_path` 环境，未覆盖重复 proposal_id 场景。
  - 风险: 若同一 proposal_id 在同进程内被 register 两次（内容不同），第二次注册会静默覆盖；若 apply 后不清理，内存缓慢增长。这不是 Phase 61 引入的 blocker，但属于设计文档未说明的行为。

- [NOT_COVERED] **`_apply_route_review_metadata` 中 `route_weight` 类型 proposal 的验证循环与实际写入逻辑分离**
  - 说明: `governance.py:326-335` 先循环 approved_entries 做 route_weight 类型 proposal 的验证（仅 `continue`，不修改 `updated_weights`），实际权重写入在第二循环 `governance.py:477-510` 中完成。两次循环处理相同的 `approved_entries`，第一次循环对 `route_weight` 类型实际上是 dead validation（已验证但不写值，第二次才写）。这是从原 `apply_reviewed_optimization_proposals` 迁移过来的逻辑结构，设计文档未明确要求保留或变更这种分离结构。不影响正确性，但增加了维护复杂度。

