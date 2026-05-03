---
author: claude
phase: lto-6-knowledge-plane-facade-solidification
slice: plan-audit
status: draft
depends_on:
  - docs/plans/lto-6-knowledge-plane-facade-solidification/plan.md
  - docs/design/INVARIANTS.md
  - docs/engineering/ADAPTER_DISCIPLINE.md
  - src/swallow/knowledge_retrieval/knowledge_plane.py
  - src/swallow/knowledge_retrieval/knowledge_store.py
  - src/swallow/knowledge_retrieval/canonical_registry.py
  - src/swallow/knowledge_retrieval/staged_knowledge.py
  - src/swallow/knowledge_retrieval/knowledge_suggestions.py
  - src/swallow/knowledge_retrieval/ingestion/pipeline.py
  - src/swallow/application/commands/knowledge.py
  - src/swallow/truth_governance/truth/knowledge.py
  - src/swallow/orchestration/orchestrator.py
  - src/swallow/orchestration/harness.py
  - tests/test_invariant_guards.py
---

TL;DR: has-concerns — 11 slices audited, 9 issues found (0 blockers, 7 concerns, 2 nits), 4 items confirmed strong.

## Audit Verdict

Overall: **has-concerns** — no blockers, but 7 concerns require implementation decisions before Codex starts M3. Human Plan Gate can proceed with these concerns attached.

## Issues by Slice

### M1 — Facade Contract And Characterization

**[CONCERN] `build_knowledge_projection` will become a god-function or require a mode flag.**

`build_knowledge_projection(...)` is proposed to replace `build_knowledge_objects`, `build_knowledge_index`, `build_knowledge_partition`, `apply_knowledge_decision`, four `build_*_report` helpers, and canonical reuse helpers — nine distinct operations with different outputs. These operations are called independently across `orchestrator.py` (lines 49-52), `harness.py` (line 145: only `build_knowledge_index`), `librarian_executor.py` (lines 23-32: only the partition/index/objects subset), and `knowledge_flow.py` (no index, no partition). If the facade wraps them into a single function it must accept a `kind=` or `what=` argument to select which output to produce, recreating barrel-file shape by a different mechanism. Alternatively, if the function always builds everything, it will be expensive to call in paths that need only one sub-result.

The plan acknowledges this risk ("compressed cleanly to 8-10 functions") but does not resolve it. Before M1 begins, the plan should specify whether `build_knowledge_projection` is a single omnibus call or whether it gets split (e.g. `build_knowledge_projection`, `build_knowledge_projection_report`) with explicit rationale. The current table is not implementable without that decision.

**[CONCERN] `serve_knowledge_context` mixes three consumers with different return types and injection patterns.**

The table groups `retrieve_context`, `build_evidence_pack`, `collect_prompt_data`, `build_retrieval_request`, `ClaudeXMLDialect`, and `FIMDialect` under one facade call. In actual usage:

- `retrieval_flow.py:103` uses `retrieve_context` as a `Callable[..., list[RetrievalItem]]` default argument and passes it as a function reference to `_run_retrieval`. A facade wrapper `serve_knowledge_context(...)` cannot be used as that Callable without a dedicated sub-function that matches the original signature.
- `executor.py:27-28` imports `ClaudeXMLDialect` and `FIMDialect` as class types to register in a dialect dict (`executor.py:442-444`). These are not "called" — they are instantiated as values in a module-level mapping. A facade function `serve_knowledge_context(...)` does not help here.
- `task_report.py:5` calls `build_evidence_pack` and `retrieve_context` separately with different arguments.

The facade design needs to specify how callers that use these as function references or class references will be migrated. Either the facade exposes the sub-functions (contradicting the one-omnibus-call design) or the migration matrix for `orchestration/*` needs a concrete per-file plan.

**[OK] `build_canonical_record` collapsing 3 helpers is sound.**

`build_canonical_record` in `canonical_registry.py:35-62` takes `(task_id, object_id, knowledge_object, decision_record)` and builds the full record including the key. `build_staged_canonical_key` and `build_canonical_key` are pure helpers called only inside `build_canonical_record` or `application/commands/knowledge.py:build_stage_canonical_record`. The facade collapsing these three into one operation is straightforward — no mode flag needed. Application commands can continue calling their own `build_stage_canonical_record` locally.

**[CONCERN] `load_task_knowledge(...)` collapsing 5 functions requires a disambiguation decision.**

The five underlying functions (`load_task_knowledge_view`, `load_task_evidence_entries`, `load_task_wiki_entries`, `split_task_knowledge_view`, `normalize_*`) return different types and are called in separate call sites. `knowledge_flow.py:14` imports `normalize_task_knowledge_view` and `split_task_knowledge_view` because it needs the split result. `knowledge_store.py:persist_task_knowledge_view` calls `split_task_knowledge_view` internally. If `load_task_knowledge(...)` returns an unsplit flat view, callers that need the split must either call a separate split helper or the facade must have a `split=True` kwarg. The plan does not specify the output type of `load_task_knowledge(...)`. This must be decided in M1 before M3 migration begins, or Codex will guess.

---

### M2 — Internalize Lifecycle Modules

**[CONCERN] M2 + M3 must be a single commit or compileall breaks between milestones.**

The plan describes M2 (rename six modules to `_internal_*`) and M3 (migrate 24 caller files) as separate milestones with separate commit gates. After M2 renames complete but before M3 migrations complete, all 24 external callers still import the old module names that no longer exist. `compileall` will fail. The M2 acceptance criterion specifies `compileall` pass, but if M2 and M3 are separate commits, M2 cannot satisfy its own criterion while callers remain unmigrated.

The plan should explicitly state that M2 and M3 are committed together in a single atomic commit, OR that the `compileall` gate is only checked after M3 is complete. The current milestone text implies separate commit gates, which is operationally inconsistent.

**[CONCERN] `ingestion/pipeline.py` physical location after rename is ambiguous.**

The rename table says `knowledge_retrieval/ingestion/pipeline.py` moves to `knowledge_retrieval/_internal_ingestion_pipeline.py` — that is, from a subpackage to the package root. This means the `ingestion/` subpackage shrinks to `filters.py` + `parsers.py` + `__init__.py`. The plan says these remain public for "focused parser/eval tests unless audit requires otherwise."

Two issues:

1. `ingestion/__init__.py` currently exists. After the rename, it exposes nothing from `pipeline`. Any `from swallow.knowledge_retrieval.ingestion import ...` call will silently become a different import target. Tests in `tests/test_ingestion_pipeline.py` and `tests/eval/test_eval_ingestion_quality.py` import directly from `ingestion.filters` and `ingestion.parsers` — these are fine. But `ingestion/__init__.py` may re-export names from `pipeline`; that must be audited before the rename.

2. `surface_tools/ingestion_specialist.py:6` imports `run_ingestion_pipeline` from `ingestion.pipeline`. This is not in the plan's facade surface table (`ingest_knowledge_source` only covers `ingest_local_file` and `ingest_operator_note`). `run_ingestion_pipeline` accepts `format_hint`, `submitted_by`, and `taxonomy_role` overrides that `ingest_local_file` does not accept. If `ingestion_specialist` is migrated to the facade, the facade `ingest_knowledge_source` must accept these arguments too, or `ingestion_specialist` remains a permitted direct importer of the non-internalized subpackage. This classification is missing from the plan.

---

### M3 — Upper-Layer Caller Migration

**[CONCERN] Several directly-called functions have no corresponding facade entry and no closeout rationale.**

Code survey found these active external imports of knowledge_retrieval modules that are not covered by the 11-operation facade surface, and that come from modules the plan explicitly says stay public (not renamed to `_internal_*`):

| Caller | Import | Not covered by facade because... |
|---|---|---|
| `orchestration/artifact_writer.py:14-15` | `persist_executor_side_effects`, `build_knowledge_policy_report`, `evaluate_knowledge_policy` | `knowledge_suggestions` and `knowledge_policy` are not in the six renamed modules; plan does not mention them in the migration matrix for `orchestration/*` |
| `orchestration/harness.py:18` | `persist_executor_side_effects` passed as `Callable` to `_run_execution` | Function reference injection — facade wrapper does not compose |
| `adapters/cli_commands/knowledge.py:24` | `build_relation_suggestion_application_report` from `knowledge_suggestions` | Not in the facade surface; `knowledge_suggestions` is one of the six-to-be-renamed modules, but this render function is not covered by `apply_knowledge_relation_change(...)` |
| `adapters/cli.py:54` | `build_review_queue`, `build_review_queue_report` from `knowledge_review` | `knowledge_review` stays public but these functions do not appear in any facade surface slot |
| `adapters/cli.py:12-14` | `build_canonical_reuse_evaluation_report`, `build_canonical_reuse_evaluation_summary` from `canonical_reuse_eval` | `canonical_reuse_eval` stays public; no facade coverage |
| `surface_tools/librarian_executor.py:9` | `raw_material` imports | `raw_material` stays public; no facade coverage needed but not explicitly classified |
| `truth_governance/truth/knowledge.py:10` | `persist_wiki_entry_from_record` from `knowledge_store` | This will be renamed to `_internal_knowledge_store`; the import must be migrated to the facade, but `persist_wiki_entry_from_record` does not appear in `persist_task_knowledge(...)` table entry either — the table entry only mentions `persist_task_knowledge_view` and `migrate_file_knowledge_to_sqlite`. The function also appears in `tests/test_retrieval_adapters.py:37` and is guarded by `test_canonical_write_only_via_apply_proposal`. |
| `truth_governance/sqlite_store.py:10-13` | `enforce_canonical_knowledge_write_authority`, `normalize_task_knowledge_view`, `split_task_knowledge_view` from `knowledge_store` | `sqlite_store` is a Truth-layer internal; these may be exempt, but it is not stated |

The plan's migration matrix says "Use facade for task knowledge projections, retrieval serving..." for `orchestration/*` without naming which functions in which files map to which facade calls. For M3 to be implementable without guesswork, these unclassified imports need explicit treatment in the plan: either add to facade surface, declare "direct import allowed — public non-internal module," or declare "deferred with closeout rationale."

**[OK] `apply_proposal` ownership is correctly preserved.**

Code survey confirms `promote_stage_candidate_command` in `application/commands/knowledge.py:194` is the only caller of `apply_proposal` for `CANONICAL_KNOWLEDGE` target. The facade's `decide_staged_knowledge(...)` targets only `update_staged_candidate` (status mutation), not the promotion path. INVARIANTS.md §0 rule 4 is not violated by this plan.

**[OK] `persist_task_knowledge` does NOT bypass `apply_proposal`.**

`persist_task_knowledge_view` in `knowledge_store.py:238-263` calls `_sqlite_store().replace_task_knowledge(...)` which is a task knowledge view update, not a canonical knowledge write. INVARIANTS.md §5 assigns task knowledge view writes to `Specialist (W stagedK)` and `Operator (W canonK via apply_proposal)`. The write-authority guard `enforce_canonical_knowledge_write_authority` is called inside `replace_task_knowledge`. No invariant conflict.

---

### M4 — Guards And Documentation Sync

**[CONCERN] The proposed M4 guard does not cover the non-renamed modules that are the real drift surface.**

The guard shape as described will reject imports of `swallow.knowledge_retrieval._internal_*` from outside `knowledge_retrieval/`. This is correct but insufficient. After this phase, the non-renamed public modules (`retrieval.py`, `grounding.py`, `evidence_pack.py`, `knowledge_review.py`, `canonical_reuse_eval.py`, `knowledge_policy.py`, etc.) remain importable with no guard. Wiki Compiler (LTO-1) could import `from swallow.knowledge_retrieval.retrieval import retrieve_context` and bypass the facade entirely — the guard would not catch it.

The plan says the guard also rejects imports from "old six public module names if compatibility stubs somehow remain" — but those modules will be gone. The structural problem is that 20+ non-renamed modules remain directly importable and there is no guard requiring their callers to go through `knowledge_plane`.

A complete guard would additionally enforce: for files outside `src/swallow/knowledge_retrieval/`, knowledge behavior imports should come only from `swallow.knowledge_retrieval.knowledge_plane`, not from individual modules like `swallow.knowledge_retrieval.retrieval` or `swallow.knowledge_retrieval.grounding`. Whether to enforce this for all modules or only for the ones with facade coverage is an open question the plan should decide. Without this the guard is a half-measure.

Note: `test_no_module_outside_governance_imports_store_writes` at `tests/test_invariant_guards.py:398` already allowlists `knowledge_retrieval/knowledge_store.py` for canonical writes — after the rename to `_internal_knowledge_store.py`, this allowlist path will break and must be updated in M4.

---

### M5 — Full Validation And Closeout Prep

**[NIT] 5 milestones vs 4 commit boundaries is a count mismatch.**

The plan lists 5 milestones (M1-M5) but 4 suggested code commits. M5 is described as "full validation and closeout prep" with no code change. This is fine operationally — M5 is a validation gate, not a commit — but Codex should be aware that there is no 5th commit for M5. The plan is not wrong, just slightly inconsistent in structure.

**[NIT] Deletion of old re-export shape from `knowledge_plane.py` is not an explicit milestone task.**

Current `knowledge_plane.py` is a 98-line barrel with `__all__` listing ~50 names. M1 adds real `def` implementations, but the plan does not explicitly state at which milestone the old imports and `__all__` list are removed. The M1 acceptance criterion says "`knowledge_plane.py` contains real `def` implementations and no broad `__all__` re-export list" — which implies they are removed in M1. This is the right answer but should be stated explicitly to avoid ambiguity about whether old re-exports coexist with new facade defs during M1.

---

## Questions for Codex / Human

1. **`build_knowledge_projection` decomposition**: Should this become two or three functions (e.g., `build_knowledge_projection` for data objects, `build_knowledge_projection_report` for the text reports) to avoid an omnibus call? Or should callers that need only `build_knowledge_index` call a separately-named facade function? Resolve before M1 begins.

2. **`serve_knowledge_context` and function-reference injection**: `retrieval_flow.py` passes `retrieve_context` as a `Callable[..., list[RetrievalItem]]` default argument. Should the facade expose a named sub-function (e.g., `retrieve_knowledge_context`) that has the same signature as the current `retrieve_context`, so it can be used as a function reference? Or does the migration matrix for `retrieval_flow.py` skip the facade for this particular injection point?

3. **`run_ingestion_pipeline` vs `ingest_knowledge_source`**: `ingestion_specialist.py` calls `run_ingestion_pipeline` with `format_hint`, `submitted_by`, `taxonomy_role` overrides. The plan's `ingest_knowledge_source` maps only `ingest_local_file` and `ingest_operator_note`. Is `run_ingestion_pipeline` (the session-transcript variant) included in the facade surface, or is `ingestion_specialist` a permitted direct importer of `ingestion/pipeline.py` (which stays public as `ingestion/parsers.py` and `ingestion/filters.py` siblings)?

4. **`ingestion/__init__.py` re-export audit**: Does `ingestion/__init__.py` currently re-export any names from `pipeline.py`? If yes, the M2 rename requires the `__init__.py` to be emptied or updated. This should be explicitly handled in M2.

5. **`persist_executor_side_effects` as Callable**: `harness.py:125` passes `persist_executor_side_effects` as a function reference to `_run_execution`. Should the migration map this to a facade sub-function with an identical signature, or is `knowledge_suggestions` a permitted direct import from `orchestration/` given it is in the to-be-renamed six (so it will become `_internal_knowledge_suggestions`)?

6. **`build_relation_suggestion_application_report` classification**: This render function lives in `knowledge_suggestions.py` (to be renamed `_internal_knowledge_suggestions.py`) but is not in the facade surface table. Should it be added to the `apply_knowledge_relation_change(...)` entry, or moved to a separate render function, or explicitly declared out of facade scope with a closeout note?

7. **`truth_governance/sqlite_store.py` exemption**: `sqlite_store.py` imports `enforce_canonical_knowledge_write_authority`, `normalize_task_knowledge_view`, and `split_task_knowledge_view` from `knowledge_store` (to become `_internal_knowledge_store`). Is `sqlite_store` exempt from the public-import rule as a Truth-layer peer of `knowledge_retrieval`, or must it go through the facade? If exempt, say so explicitly in the plan; if not, add it to the migration matrix.

8. **M4 guard scope for non-renamed public modules**: Should the M4 guard enforce that files outside `knowledge_retrieval/` import knowledge behavior only through `knowledge_plane` (not through `retrieval.py`, `grounding.py`, etc.)? Or is the guard scope limited to the six renamed modules only? This determines whether the guard is a full boundary or a partial one. The answer affects how much LTO-1 Wiki Compiler is constrained.

9. **`test_invariant_guards.py` allowlist update for renamed modules**: After M2 renames `knowledge_store.py` to `_internal_knowledge_store.py`, the allowlists in `test_canonical_write_only_via_apply_proposal` (line 244) and `test_no_module_outside_governance_imports_store_writes` (line 411) will reference a path that no longer exists and either silently pass (exempting nothing) or fail. Codex must update these allowlists in M4. This should be explicitly listed as an M4 acceptance criterion item.

## Confirmed Ready

- **Design decisions section**: The functional facade / one-shot / `_internal_*` naming decisions are unambiguous and implementable as stated.
- **`build_canonical_record` consolidation (Facade Surface row 6)**: Sound. No mode flag needed; three helpers cleanly collapse to one operation.
- **INVARIANTS.md alignment for `apply_proposal` boundary**: Confirmed by code survey. `persist_task_knowledge(...)` goes through `replace_task_knowledge` with write-authority enforcement; `promote_stage_candidate_command` retains sole `apply_proposal` ownership. No invariant violation risk.
- **Non-Goals section**: D4 Phase B/C scope containment, class facade deferral, and behavior-preservation constraints are clear and correctly scoped.
