---
author: claude
phase: lto-6-knowledge-plane-facade-solidification
slice: pr-review
status: final
depends_on:
  - docs/plans/lto-6-knowledge-plane-facade-solidification/plan.md
  - docs/plans/lto-6-knowledge-plane-facade-solidification/plan_audit.md
  - docs/plans/lto-6-knowledge-plane-facade-solidification/closeout.md
  - src/swallow/knowledge_retrieval/knowledge_plane.py
  - src/swallow/knowledge_retrieval/_internal_canonical_registry.py
  - src/swallow/knowledge_retrieval/_internal_staged_knowledge.py
  - src/swallow/knowledge_retrieval/_internal_knowledge_store.py
  - src/swallow/knowledge_retrieval/_internal_knowledge_relations.py
  - src/swallow/knowledge_retrieval/_internal_knowledge_suggestions.py
  - src/swallow/knowledge_retrieval/_internal_ingestion_pipeline.py
  - src/swallow/application/commands/knowledge.py
  - tests/test_invariant_guards.py
  - tests/test_knowledge_plane_facade.py
---

TL;DR: recommend-merge — 0 blockers / 1 concern / 2 nits. LTO-6 cleanly absorbs all 7 plan_audit concerns with the right tradeoffs (functional facade kept intentionally fine-grained, M2+M3 atomic, raw_material exception explicit). One concern about facade naming consistency (paired `render_*` / `build_*` aliases inflate API surface).

# LTO-6 PR Review

## Verdict

**recommend-merge** — implementation across 4 commits (`c9697f2` facade contract, `04102c4` internal rename + atomic caller migration, `18b4c15` guard, `1be8a5e` state sync) is mergeable as-is.

This phase delivers exactly the architectural intent recorded in `ARCHITECTURE_DECISIONS.md §3.1`:
1. Knowledge Plane is now a real **functional facade** with domain-named operations, not a barrel file.
2. The 6 lifecycle modules are internalized via `_internal_*` rename in the same package.
3. All 24 previously-bypassing upper-layer call sites are migrated.
4. A production-source guard prevents future bypasses.
5. INVARIANTS §0(canonical write authority via `apply_proposal`)is preserved.

Diff scale: **+1281 / −263** across 48 files; large but mostly mechanical (6 module renames + import-path migrations + 802-line facade module that absorbs ~70 wrapper functions + 239 lines of new facade tests). Risk is low because every behavior-changing path goes through wrapper functions that delegate to unchanged internal implementations.

## Verification of plan_audit Absorption

I verified all 7 concerns + 2 nits from `plan_audit.md`:

### 7 concerns

| ID | Finding | Status | Evidence |
|---|---|---|---|
| C1 | `build_knowledge_projection` god-function risk (9 ops in 1) | **Resolved by decomposition** | Facade exposes them as separate functions: `build_knowledge_objects` / `build_knowledge_index` / `build_knowledge_partition` / `build_review_queue` / `apply_knowledge_review_decision` / `build_canonical_reuse_summary` / etc. (`knowledge_plane.py:417-507`). No omnibus call introduced. |
| C2 | `serve_knowledge_context` Callable injection conflict | **Resolved by same-signature wrappers** | `retrieve_knowledge_context` (line 636) keeps the exact `(workspace_root, query, limit, source_types, request)` signature so `retrieval_flow.py:103` Callable injection still works through the facade. Dialect adapters (`ClaudeXMLDialect`, `FIMDialect`) re-exported as classes (line 25). |
| C3 | `load_task_knowledge` ambiguous return type | **Resolved by separate functions** | Plan's omnibus replaced with `load_task_knowledge_view` (line 169) / `load_task_evidence_entries` (line 177) / `load_task_wiki_entries` (line 181) / `split_task_knowledge_view` (line 165) / `normalize_task_knowledge_view` (line 161) — each with its own return type. No `kind=` mode flag. |
| C4 | M2 + M3 commit atomicity | **Resolved** | Single commit `04102c4 refactor(knowledge): internalize modules and migrate callers` does both the 6 renames and all upper-layer import migrations. `git log` confirms no intermediate uncompilable state. |
| C5 | 26 unclassified imports | **Resolved by full classification** | All previously-unclassified bypasses now route through facade: `persist_executor_side_effects` (line 401), `build_relation_suggestion_application_report` (line 413), `build_review_queue` (line 495), `build_canonical_reuse_evaluation_*` (lines 550-574), `evaluate_knowledge_policy` (line 578). Direct grep across `src/swallow/` (excluding `knowledge_retrieval/` itself) confirms zero remaining bypasses outside the explicit `raw_material` exception. |
| C6 | Guard scope only covers `_internal_*` | **Resolved by full coverage** | `tests/test_invariant_guards.py:244-256` `_knowledge_plane_import_boundary_violation` explicitly rejects ANY `swallow.knowledge_retrieval.*` import outside the package, with two allowed exceptions (`knowledge_plane` and `raw_material`). Three fixture tests verify: rejects `_internal_knowledge_store` (line 286), rejects `retrieval` (line 299), allows facade + raw_material (line 311). |
| C7 | Existing allowlists referencing old paths | **Resolved** | `tests/test_invariant_guards.py:341, 446, 510` all updated to `_internal_knowledge_store.py` and `_internal_ingestion_pipeline.py`. |

### 2 nits

| ID | Finding | Status |
|---|---|---|
| N1 | `_internal_*` naming unusual vs repo convention | **Acknowledged; intentional** | Plan §Internal Module Rename Plan picked same-package `_internal_*` over a nested `internals/` subpackage to keep import rewrites mechanical. Repo precedent is mixed (`_io_helpers.py` has same prefix style at top level). Acceptable. |
| N2 | Behavior preservation testing | **Resolved by characterization tests** | `tests/test_knowledge_plane_facade.py` (239 lines, 6 test functions) characterizes facade behavior. Combined with the unchanged downstream tests passing under the new import paths (745+ tests already exercising the underlying modules), behavior preservation is well covered. |

**7 / 7 concerns absorbed + 2 / 2 nits addressed.** No silent regressions.

## Findings

### [CONCERN] C1 — Paired `render_*` / `build_*` aliases double the facade surface area

**Pattern**: throughout `knowledge_plane.py`, many report-rendering functions exist in pairs:

```python
def render_canonical_registry_index_report(index_record: ...) -> str:
    return _canonical_registry.build_canonical_registry_index_report(index_record)

def build_canonical_registry_index_report(index_record: ...) -> str:
    return render_canonical_registry_index_report(index_record)
```

This pattern repeats ~14 times (`render_canonical_registry_report` + `build_canonical_registry_report`, `render_ingestion_report` + `build_ingestion_report`, `render_ingestion_summary` + `build_ingestion_summary`, `render_knowledge_relation_report` + `build_knowledge_relation_report`, `render_knowledge_relations_report` + `build_knowledge_relations_report`, `render_relation_suggestion_application_report` + `build_relation_suggestion_application_report`, `render_knowledge_index_report` + `build_knowledge_index_report`, `render_knowledge_partition_report` + `build_knowledge_partition_report`, `render_knowledge_decisions_report` + `build_knowledge_decisions_report`, `render_review_queue_report` + `build_review_queue_report`, `render_canonical_audit_report` + `build_canonical_audit_report`, `render_canonical_reuse_report` + `build_canonical_reuse_report`, `render_grounding_evidence_report` + `build_grounding_evidence_report`, `render_knowledge_policy_report` + `build_knowledge_policy_report`).

**Why it matters**: this contradicts `ADAPTER_DISCIPLINE.md §1`(Framework-Default Principle / domain language)and `ARCHITECTURE_DECISIONS.md §3.1` repair direction("define domain language, not just rename"). The reason for two names is presumably: (a) `build_*` is the legacy name used by callers, (b) `render_*` is the new domain language. But after this phase the migration is complete — every caller has had its import path changed. The `build_*` aliases are now backwards-compat with code that does not exist.

**Why it persisted**: avoiding caller signature churn during the M3 migration was the path of least resistance. But the migration commit (`04102c4`) had to touch every caller's import line anyway, so renaming `build_*` → `render_*` simultaneously was already in the diff scope.

**Why this is a concern, not a blocker**: the duplicate aliases work. Tests pass. The only cost is `knowledge_plane.py` being ~50 lines longer than necessary (estimate ~14 alias pairs × 3-4 lines = ~50 lines) and future contributors not knowing which name is canonical. This same problem will reproduce if Wiki Compiler adds new `build_*` entries that mirror existing `render_*` entries.

**Resolution options** (any acceptable; none blocks merge):

- **(a)** keep one form per pair (preferred: `render_*` for report-rendering, `build_*` for object-construction); delete the redundant aliases. Single follow-up commit on `main`, ~50-line diff.
- **(b)** keep both but document the convention in module docstring: "`build_*` is preserved for backward compatibility with pre-LTO-6 caller signatures; new code should use `render_*` for report rendering."
- **(c)** defer to a future "facade naming consolidation" follow-up phase if a Wiki Compiler-driven rename pass is anticipated.

**Recommendation**: option (a). Cost is small and now is the cheapest moment (no external consumers, no API stability promises).

### [NIT] N1 — `audit_canonical_registry` and `render_canonical_audit_report` lazy-import inside the function body

**File**: `src/swallow/knowledge_retrieval/knowledge_plane.py:510-519`

```python
def audit_canonical_registry(base_dir: Path, records: list[dict[str, object]]) -> Any:
    from swallow.knowledge_retrieval import canonical_audit
    return canonical_audit.audit_canonical_registry(base_dir, records)

def render_canonical_audit_report(result: Any) -> str:
    from swallow.knowledge_retrieval import canonical_audit
    return canonical_audit.build_canonical_audit_report(result)
```

This is the only place in the facade that uses runtime `import` inside function body. The other ~35 internal modules are imported at module top (lines 8-25). The closeout (§Implementation Notes) only mentions `truth_governance/sqlite_store.py` lazy imports — this `canonical_audit` lazy import is undocumented.

**Likely reason**: avoiding circular import. `canonical_audit.py` may import from `knowledge_plane` itself (Wiki Compiler / canonical reuse audit machinery has historical coupling).

**Suggestion**: either move to top-level import like the other 19 internal modules (verify no circular import) or add a 1-line comment explaining the cycle. As-is, a future contributor seeing the inconsistency may "fix" the lazy import and trip a circular import.

### [NIT] N2 — `__all__` not declared on `knowledge_plane.py`

The facade module has no `__all__` list. By Python convention, this means `from knowledge_plane import *` would import everything (including the `_canonical_registry` etc. private references at module top). Combined with `Any` re-imports (line 6) and dataclass aliases, the implicit public surface is wider than the explicit one.

**Impact**: low — production code uses explicit `from knowledge_plane import X, Y, Z` and the boundary guard (`tests/test_invariant_guards.py`) catches the wrong direction (importing from non-facade modules), not wildcard imports of facade internals.

**Suggestion**: add `__all__` listing the ~70 public functions and value classes. Makes future API audits / IDE autocomplete cleaner. Defer if not addressed in this phase.

## Confirmed Strengths

These are recorded so the implementation patterns are reusable for future Knowledge Plane work and Wiki Compiler:

- **Functional facade form is correctly applied**: every export is a wrapping function with domain naming + delegating body, not a `from X import Y as Y` barrel re-export. The decision to keep the facade fine-grained (~70 functions) over the plan's tentative "6-10 ops" is the right call given the actual call-site diversity (verified plan_audit C1/C2/C3).
- **`apply_proposal` ownership unbroken**: facade exposes `persist_task_knowledge_view` and `decide_staged_knowledge` (status mutation only) but NO `register_canonical_proposal` or `apply_proposal` wrapper. `application/commands/knowledge.py:21-26` still imports those directly from `truth_governance.governance`. Canonical write authority remains exclusively with `truth_governance`. INVARIANTS §0 cardinal rule preserved.
- **Guard test design is comprehensive**: three fixture tests prove the guard's negative cases (rejects `_internal_*`, rejects facade-covered modules) AND the positive case (allows facade + raw_material exception). This style is reusable for future boundary phases (D2 driven ports, D4 Phase B/C).
- **`raw_material` exception is explicit, not implicit**: `tests/test_invariant_guards.py:147, 254, 316-322` documents the storage-boundary allowlist with exactly one production caller (`librarian_executor.py`). Future contributors cannot quietly extend the exception.
- **M2 + M3 atomic commit**: `04102c4` does the rename + caller migration in one shot. This is the right answer to plan_audit C4 — three-phase batching would have left an uncompilable middle state.
- **`StagedCandidate` re-export discipline**: `application/commands/knowledge.py:7-19` imports `StagedCandidate` from `knowledge_plane` (line 10), and re-exports it in `__all__` (line 34) — preserving LTO-13 C1 fix. Web schemas continue to consume from `application/commands/knowledge`, never from `_internal_*`. The boundary chain is intact.
- **`ingestion/__init__.py` re-export removal**: `src/swallow/knowledge_retrieval/ingestion/__init__.py` lost 14 lines that previously re-exported pipeline names. Now `ingestion/` subpackage exists only for parser/filter implementations, with `pipeline.py` flattened to `_internal_ingestion_pipeline.py` at the package root. This subpackage shape is now coherent (closeout §Outcome confirms parser/filter exports remain public, which is correct because parser unit tests legitimately import them).

## Validation Replay

I did not re-run the test suite during review. Closeout records:

```text
M5: full pytest 755 passed, 8 deselected
    compileall -q src/swallow: passed
    git diff --check: passed
```

Spot-checked diff is consistent with these counts. The 755 - 745 = +10 net new tests aligns with `tests/test_knowledge_plane_facade.py` (6 new tests) + `tests/test_invariant_guards.py` (3 new fixture tests + 1 production guard test).

## Recommendation

**recommend-merge** as-is. The C1 paired-alias concern can be:

1. **Folded into the LTO-6 merge** if Codex prefers a single clean record (option a in C1, ~50-line follow-up commit).
2. **Deferred to a tiny follow-up commit on `main`** after merge (preferred — keeps LTO-6 review chain intact and is a 5-minute cleanup).
3. **Logged to `concerns_backlog.md`** if neither is convenient now.

My preference is (2) for the same reason as LTO-13 C1: single-purpose follow-up commits make merge history easier to read.

## Deferred Items Confirmed

The closeout's deferred list matches plan §Non-Goals:

- Wiki Compiler / draft-wiki / refine-wiki / source packs — out of scope, prerequisite work for LTO-1.
- Class-based `KnowledgePlane` service / DI container / repository ports — explicitly LTO-5 D2 territory.
- SQLite schema / Knowledge Truth semantic changes — preserved.
- D4 Phase B/C residual `surface_tools` relocation — touched-surface only; no broad cleanup snuck in.
- Retrieval adapter / dialect adapter implementation-test reclassification — `tests/test_retrieval_adapters.py` and `tests/unit/knowledge/test_knowledge_plane.py` keep direct imports of non-facade public modules where they are testing parser/adapter internals; this is intentional and documented in plan §Tests.
- `current_state.md` and roadmap post-merge sync — happens after merge per closeout §Deferred Follow-Ups.

All deferrals are recorded in writing; none were silently absorbed into the LTO-6 diff.
