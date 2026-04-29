---
author: claude
phase: phase63
slice: s3-consistency-check
status: draft
depends_on: ["docs/plans/phase63/design_decision.md", "docs/plans/phase63/kickoff.md"]
---

TL;DR: 11 consistent, 2 inconsistent, 0 not-covered — minor drift on `_PENDING_PROPOSALS` error message format and `RouteRepo._apply_metadata_change` call sequence guard.

## Consistency Report

### 检查范围

- 对比对象: commit `1df5992` (feat(phase63): add truth repository write boundary) vs `docs/plans/phase63/design_decision.md` §S3 and `docs/plans/phase63/kickoff.md` §G3

---

## Item 1 — Repository module structure

**Verdict: MATCH**

- `src/swallow/truth/__init__.py` exists, exports `KnowledgeRepo`, `RouteRepo`, `PolicyRepo`, `PendingProposalRepo`, `DuplicateProposalError` (file:8-14).
- `src/swallow/truth/knowledge.py` has class `KnowledgeRepo` with `_promote_canonical(...)` (knowledge.py:13-51).
- `src/swallow/truth/route.py` has class `RouteRepo` with `_apply_metadata_change(...)` (route.py:13-32).
- `src/swallow/truth/policy.py` has class `PolicyRepo` with `_apply_policy_change(...)` (policy.py:10-23).
- `src/swallow/truth/proposals.py` adds `PendingProposalRepo` per design_decision §S3 scope note — does not introduce read-only methods, transaction wrapping, durable artifact persistence, or evict logic. The `load()` method at proposals.py:25-33 is a retrieval method for in-memory proposal lookup (equivalent to the previous `_PENDING_PROPOSALS[key]` dict access in governance.py:241-244 before the change). This is a direct replacement for the pre-existing internal access pattern, not a new read method on the knowledge/route/policy domain.

---

## Item 2 — governance.py rewiring

**Verdict: MATCH**

`governance.py:9-14` imports from `.router`:

```python
from .router import (
    load_route_capability_profiles,
    load_route_weights,
    normalize_route_name,
    route_by_name,
)
```

`save_route_weights`, `apply_route_weights`, `save_route_capability_profiles`, `apply_route_capability_profiles` are absent from this import block. The `grep -n 'from .router import'` result confirms only line 9 with the four non-write functions remains.

`apply_proposal(proposal_id: str, operator_token: OperatorToken, target: ProposalTarget) -> ApplyResult` 3-argument signature is intact at governance.py:212-216.

Repository writes only happen inside governance.py paths: `_apply_canonical` at governance.py:260, `_apply_route_metadata` at governance.py:285 and governance.py:529, `_apply_policy` at governance.py:563 and governance.py:580.

---

## Item 3 — `_PENDING_PROPOSALS` duplicate detection

**Verdict: MINOR DRIFT**

Key is tuple `(target, normalized_id)` — consistent with design_decision §S3: `key = (target, normalized_id)` at proposals.py:18.

Same `(target, proposal_id)` second register raises `DuplicateProposalError` — consistent, proposals.py:19-21.

Error message includes `proposal_id` (as `normalized_id`) — consistent.

**Drift:** design_decision §S3 states error message must include `target.value` and `proposal_id`. The actual message at proposals.py:21 is:

```
f"Duplicate proposal artifact: {normalized_id} ({target_value})"
```

`target_value` is derived via `str(getattr(target, "value", target))` (proposals.py:20), which yields the correct enum `.value` string. However, the message uses `target_value` in parentheses after `normalized_id`, in reverse order relative to the description in design_decision §S3 ("消息包含 `target.value` 与 `proposal_id`"). The functional requirement — both values present in the message — is satisfied, but the positional order differs from the description. The test at test_governance.py:117 only matches on `"duplicate-proposal"` (the proposal_id substring), not the full format, so the test does not enforce the format strictly.

- 来源: `docs/plans/phase63/design_decision.md` §S3 line 161: "异常消息包含 `target.value` 与 `proposal_id`"
- 当前状态: proposals.py:21 — message is `"Duplicate proposal artifact: {normalized_id} ({target_value})"`, proposal_id comes first, target.value in parens second
- 期望状态: design doc describes both values present; order unspecified but target.value listed first in the description
- 建议: Order does not affect correctness; no code change required. Update design_decision.md to match actual format, or leave as-is since both values are present.

---

## Item 4 — 2 new bypass guards

**Verdict: MATCH**

`test_only_governance_calls_repository_write_methods` at test_invariant_guards.py:304-310: AST scan via `_find_protected_writer_uses` with `protected_names={"_promote_canonical", "_apply_metadata_change", "_apply_policy_change"}` and `allowed_files={"src/swallow/governance.py"}`. Non-vacuous: `_find_protected_writer_uses` iterates over `_src_py_files()` (all `src/swallow/**/*.py`) and would catch any call to these methods outside governance.py.

`test_no_module_outside_governance_imports_store_writes` at test_invariant_guards.py:313-345: AST scan over all `src/swallow/**/*.py` for `ImportFrom` nodes matching the protected store-write set. Allowed list at lines 324-331 covers `{consistency_audit.py, knowledge_store.py, mps_policy_store.py, router.py, store.py, truth/knowledge.py, truth/policy.py, truth/route.py}` — consistent with design_decision §S3 line 158 (governance.py itself does not need to be in the allow-list because it no longer imports the store write functions directly). Non-vacuous.

Note: design_decision §S3 line 158 includes `src/swallow/governance.py` in the allow-list for guard B. The implementation excludes it because governance.py no longer imports any store write function after the rewiring — the allow-list omission is correct and not a drift.

---

## Item 5 — `test_only_apply_proposal_calls_private_writers` updated

**Verdict: MATCH**

test_invariant_guards.py:257-286: `_find_protected_writer_uses` is called with `protected_names` covering `append_canonical_record`, `persist_wiki_entry_from_record`, `save_route_weights`, `save_route_capability_profiles`, `save_audit_trigger_policy`, `save_mps_policy` and `allowed_files` extended to include `src/swallow/truth/knowledge.py`, `src/swallow/truth/route.py`, `src/swallow/truth/policy.py` (lines 275-283). This is the expanded scan target required by design_decision §S3 line 134.

---

## Item 6 — Scope violations

**Verdict: MATCH (no violations)**

- No read method on knowledge/route/policy domain introduced in `truth/knowledge.py`, `truth/route.py`, or `truth/policy.py`.
- No transaction wrapping (`BEGIN IMMEDIATE`, context managers, rollback logic) in any Repository file.
- Original store functions (`save_route_weights`, etc. in `router.py`, `store.py`, `knowledge_store.py`, `mps_policy_store.py`) are not modified (confirmed by `git show 1df5992 --stat` — none of these files appear in the changed file list).
- No durable proposal artifact layer introduced. `PendingProposalRepo` is in-memory only (proposals.py:12: `self._pending: dict[...] = {}`).

---

## Item 7 — Signature 1:1 check

**Verdict: MINOR DRIFT**

**KnowledgeRepo._promote_canonical** — design_decision §S3 table states it forwards to `promote_to_canonical` or `apply_canonical_promotion` from `knowledge_store.py`. The actual implementation (knowledge.py:14-51) calls `persist_wiki_entry_from_record` from `knowledge_store.py` and `append_canonical_record`, `save_canonical_registry_index`, `save_canonical_reuse_policy` from `store.py`. The named forwarding target in the design table was specified "以现有名为准" (as actual name), and the actual functions used are the correct underlying store writers. The design table entry was a placeholder — no mismatch in behavior.

**RouteRepo._apply_metadata_change** — design_decision §S3 states it "sequentially calls `save_route_weights` → `apply_route_weights` → `save_route_capability_profiles` → `apply_route_capability_profiles`" unconditionally. Actual implementation at route.py:21-31 calls them conditionally: only if `route_weights is not None`, only if `route_capability_profiles is not None`. The sequential order within each block is correct. However, the design description implies all four calls always fire; the implementation gates them on None-checks.

- 来源: `docs/plans/phase63/design_decision.md` §S3 line 148: "顺序调用 `save_route_weights` → `apply_route_weights` → `save_route_capability_profiles` → `apply_route_capability_profiles`"
- 当前状态: route.py:21-31 — two guarded blocks, each pair fires only if the corresponding payload is non-None
- 期望状态: design table description implies unconditional sequential call of all four functions
- 建议: The conditional implementation is behaviorally correct and consistent with the `_RouteMetadataProposal` data shape (either field may be absent). The design description was imprecise. No code change required; update design_decision.md §S3 signature table to reflect conditional call semantics.

**PolicyRepo._apply_policy_change** — forwards to `save_audit_trigger_policy(base_dir, audit_trigger_policy)` from `consistency_audit.py` or `save_mps_policy(base_dir, kind, value)` from `mps_policy_store.py`. Signatures match store functions at consistency_audit.py:194 and mps_policy_store.py:59 respectively. Return type is `tuple[str, Path]` matching the actual store function return types.

The commit_summary.md (docs/plans/phase63/commit_summary.md) does not contain an explicit signature mapping table in the PR body as required by design_decision §S3 line 152: "S3 PR body 必须包含一份 actual signature mapping table". The commit_summary describes the change at a high level without the 1:1 table.

- 来源: `docs/plans/phase63/design_decision.md` §S3 line 152: "S3 PR body 必须包含一份 actual signature mapping table"
- 当前状态: commit_summary.md contains no signature mapping table
- 期望状态: explicit Python signature mapping in PR body
- 建议: Add the mapping table to commit_summary.md or the PR description before final merge. Not a code defect; documentation gap only.

---

## 一致项 (summary)

- [CONSISTENT] `truth/__init__.py` exports correct symbols
- [CONSISTENT] `KnowledgeRepo._promote_canonical`, `RouteRepo._apply_metadata_change`, `PolicyRepo._apply_policy_change` exist with expected names
- [CONSISTENT] `governance.py` no longer imports `save_route_weights` / `apply_route_weights` / `save_route_capability_profiles` / `apply_route_capability_profiles`
- [CONSISTENT] `apply_proposal` 3-arg signature unchanged
- [CONSISTENT] `_PENDING_PROPOSALS` is now a `PendingProposalRepo` instance; duplicate key raises `DuplicateProposalError`
- [CONSISTENT] `proposals.py` introduces no durable persistence, no transactions, no evict logic
- [CONSISTENT] Guard A (`test_only_governance_calls_repository_write_methods`) non-vacuous AST scan, allow-list `{governance.py}`
- [CONSISTENT] Guard B (`test_no_module_outside_governance_imports_store_writes`) non-vacuous AST scan, correct allow-list
- [CONSISTENT] `test_only_apply_proposal_calls_private_writers` updated with `truth/*.py` in allowed_files
- [CONSISTENT] No store functions modified; no read methods on Repository domain classes
- [CONSISTENT] No transaction wrapping introduced

## 不一致项

- [INCONSISTENT] `DuplicateProposalError` message format — minor
  - 来源: `docs/plans/phase63/design_decision.md` §S3 line 161
  - 当前状态: `proposals.py:21` — `"Duplicate proposal artifact: {normalized_id} ({target_value})"` (proposal_id first, target.value second)
  - 期望状态: design states both values present; wording implies target.value listed first
  - 建议: Both values are present and functional; update design_decision.md to match actual format. No code change required.

- [INCONSISTENT] `RouteRepo._apply_metadata_change` call sequence + missing PR signature mapping table — minor
  - 来源: `docs/plans/phase63/design_decision.md` §S3 line 148 (call sequence) and line 152 (signature mapping table requirement)
  - 当前状态: `route.py:21-31` — conditional per-None guards on weights and profiles; `commit_summary.md` has no 1:1 signature mapping table
  - 期望状态: design describes unconditional sequential four-call sequence; PR body must include signature mapping table
  - 建议: Call semantics are correct; description was imprecise. Add signature mapping table to PR description. No code change required.

---

## Top-level verdict: **minor-drift**

Two items are minor drift (message field ordering in error text; imprecise description of conditional call sequence; missing PR-body signature table). No behavioral or architectural violations. No scope violations. All bypass guards are non-vacuous and correctly implemented.
