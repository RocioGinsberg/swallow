---
author: codex
phase: lto-6-knowledge-plane-facade-solidification
slice: phase-plan
status: final
depends_on:
  - docs/roadmap.md
  - docs/active_context.md
  - docs/design/INVARIANTS.md
  - docs/design/KNOWLEDGE.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/ARCHITECTURE_DECISIONS.md
  - docs/engineering/ADAPTER_DISCIPLINE.md
  - src/swallow/knowledge_retrieval/knowledge_plane.py
  - src/swallow/application/commands/knowledge.py
  - src/swallow/application/commands/synthesis.py
  - src/swallow/orchestration/orchestrator.py
  - src/swallow/orchestration/harness.py
  - src/swallow/surface_tools/librarian_executor.py
  - src/swallow/truth_governance/truth/knowledge.py
  - tests/test_invariant_guards.py
  - docs/plans/lto-6-knowledge-plane-facade-solidification/plan_audit.md
---

TL;DR:
LTO-6 turns `knowledge_retrieval/knowledge_plane.py` from a 50-name barrel file into the public functional facade for Knowledge Truth / Retrieval / Serving.
This phase uses a **Functional facade + 一次清** shape: no class facade, no DI container, no driven-port rollout, and no behavior changes.
The implementation migrates every upper-layer `knowledge_retrieval.*` import to `knowledge_plane`, renames the six lifecycle modules to internal names, and adds guard coverage so new upper layers cannot bypass the facade again.

# LTO-6 Plan: Knowledge Plane Facade Solidification

## Frame

- track: `Architecture / Knowledge Plane`
- phase: `LTO-6 — Knowledge Plane Facade Solidification`
- roadmap ticket: `LTO-6 Knowledge Plane Facade Solidification (D1 active 化)`
- long-term goal: `LTO-6 Knowledge Plane API Simplification`
- recommended implementation branch: `feat/lto-6-knowledge-plane-facade-solidification`
- planning branch: `main`
- implementation mode: functional facade / one-shot caller migration / behavior-preserving internalization
- context brief: not produced this round; this plan is based on the updated roadmap, active context, design anchors, and direct code survey.
- plan audit: `has-concerns`; 0 blockers / 7 concerns / 2 nits. This revision absorbs all concerns into concrete facade decomposition, atomic migration, ingestion handling, guard scope, and invariant allowlist requirements.

This is a prerequisite phase for Wiki Compiler. Its purpose is to make the Knowledge Plane public API explicit before LTO-1 expands knowledge-authoring call sites.

## Current Code Context

| Area | Current shape |
|---|---|
| `src/swallow/knowledge_retrieval/knowledge_plane.py` | 98-line migration shim with no `def` / `class`; it imports and re-exports about 50 names from lower modules. |
| Direct upper-layer imports | Current grep finds 24 source files outside `knowledge_retrieval/` importing `swallow.knowledge_retrieval.*`: adapters 2, application 3, orchestration 7, provider_router 2, residual `surface_tools` 4, truth_governance 4, plus direct tests. |
| Existing healthy users | `truth_governance/store.py` and `truth_governance/truth/knowledge.py` already import some names from `knowledge_plane`, but still mix in direct `knowledge_store` imports. |
| Target pressure | Wiki Compiler will need staged knowledge, canonical record construction, source/evidence projections, and retrieval serving. If LTO-6 is not done first, LTO-1 will add more direct imports and make the migration harder. |

Representative bypasses observed during planning:

| Layer | Files |
|---|---|
| Adapters | `adapters/cli.py`, `adapters/cli_commands/knowledge.py` |
| Application | `application/commands/knowledge.py`, `application/commands/synthesis.py`, `application/commands/tasks.py` |
| Orchestration | `artifact_writer.py`, `executor.py`, `harness.py`, `knowledge_flow.py`, `orchestrator.py`, `planner.py`, `retrieval_flow.py`, `task_report.py` |
| Provider Router | `route_registry.py`, `route_selection.py` |
| Residual `surface_tools` | `doctor.py`, `ingestion_specialist.py`, `librarian_executor.py`, `literature_specialist.py` |
| Truth Governance | `proposal_registry.py`, `sqlite_store.py`, `store.py`, `truth/knowledge.py` |

## Goals

1. Replace `knowledge_plane.py` re-export barrel behavior with explicit functional facade operations.
2. Move upper layers to `from swallow.knowledge_retrieval.knowledge_plane import ...` for all Knowledge Plane access.
3. Rename the six lifecycle implementation modules to internal names so direct imports become visibly wrong.
4. Preserve behavior and public CLI / HTTP outputs.
5. Add guard tests preventing future upper-layer imports from internal Knowledge Plane modules.
6. Add focused unit coverage for each facade operation before broad caller migration.
7. Keep the phase narrow enough that Wiki Compiler can start immediately after it lands.

## Non-Goals

- Do not implement Wiki Compiler, draft-wiki, refine-wiki, source packs, rationale, or conflict flags.
- Do not introduce class-based facades, service objects, dependency injection containers, or application ports; those belong to future LTO-5 / D2.
- Do not change SQLite schema, Knowledge Truth semantics, canonical promotion policy, raw material storage, vector retrieval behavior, or evidence-pack structure.
- Do not move `surface_tools/{paths,workspace}.py` or application-service remnants as a broad D4 Phase B/C cleanup. Only do touched-path import updates if required by LTO-6.
- Do not make tests depend on private `_internal_*` modules unless the test is explicitly a knowledge-retrieval internal unit test. Behavior tests should use the facade.
- Do not weaken existing invariants around canonical writes, `apply_proposal`, Orchestrator control, or task truth writes.

## Design Decisions

| Decision point | Decision |
|---|---|
| Facade style | Use module-level functions in `knowledge_plane.py`. No `KnowledgePlane` class, no injected service object, and no DI context in this phase. |
| Migration rhythm | One-shot migration. The old direct import shape and the new facade shape should not coexist across multiple phases. |
| API granularity | Use domain operations, not every lower-level helper name. `knowledge_plane.py` may export stable value types / constants, but behavior exports must be a small named set with Knowledge Plane vocabulary. |
| Internal module naming | Use same-package `_internal_*` filenames for the six lifecycle modules. This keeps import rewrites mechanical and avoids a nested `internals/` package churn. |
| Public import rule | Outside `src/swallow/knowledge_retrieval/`, code should import Knowledge Plane behavior from `swallow.knowledge_retrieval.knowledge_plane`. |
| Internal import rule | Modules inside `knowledge_retrieval/` may use relative imports among internal modules. Upper layers must not import `_internal_*`. |
| Tests | Facade tests prove the public API. Internal module tests are allowed only where they validate implementation-specific parser / retrieval behavior that is not part of facade semantics. |
| Compatibility | No compatibility modules named `canonical_registry.py`, `staged_knowledge.py`, etc. after this phase. If an import should remain public, it must be expressed through `knowledge_plane.py` or explicitly declared out of LTO-6 scope in closeout. |

## Plan Audit Absorption

`plan_audit.md` raised 7 concerns and 2 nits. This revision resolves them as follows:

- Removed omnibus facade ideas. `build_knowledge_projection(...)`, `serve_knowledge_context(...)`, and a single ambiguous `load_task_knowledge(...)` are replaced by explicit named facade functions grouped by domain family.
- Function-reference call sites get same-signature facade wrappers where needed: retrieval context, executor side-effect persistence, and ingestion pipeline orchestration.
- M2 internal renames and M3 caller migration are now an **atomic implementation gate**. There is no standalone compileall gate after renaming but before caller migration.
- `ingestion/__init__.py` is explicitly in scope: pipeline re-exports move behind the facade; parser/filter exports remain public.
- Unclassified imports are now assigned to one of three buckets: facade function, public non-internal implementation module, or test-only/internal-unit exemption.
- The guard is broadened from "no `_internal_*` imports" to an explicit Knowledge Plane import-boundary guard with a small allowlist for public implementation modules and tests.
- Existing invariant guard allowlists for `knowledge_store.py` are explicitly updated to `_internal_knowledge_store.py`.

## Proposed Facade Surface

The facade surface is grouped by domain family. It must not use `kind=`, `mode=`, `what=`, or equivalent selector flags to hide many behaviors behind one function. The exact signatures may be refined in M1, but the names and output distinctions below are the implementation target.

### Staged Knowledge And Canonical Promotion Support

| Facade name | Purpose | Replaces |
|---|---|---|
| `list_staged_knowledge(...)` | Read staged candidates. | `load_staged_candidates` |
| `submit_staged_knowledge(...)` | Persist a staged candidate. | `submit_staged_candidate` |
| `decide_staged_knowledge(...)` | Update staged status / decision metadata only. | `update_staged_candidate` |
| `build_task_canonical_record(...)` | Build canonical record from a task knowledge object + decision. | `canonical_registry.build_canonical_record` |
| `build_staged_canonical_record(...)` | Build canonical record from a staged candidate. | `build_staged_canonical_key` plus application-local record assembly |

Application commands still own canonical promotion orchestration: `register_canonical_proposal(...)` and `apply_proposal(...)` stay outside the Knowledge Plane facade.

### Task Knowledge View Persistence

| Facade name | Output / purpose | Replaces |
|---|---|---|
| `normalize_task_knowledge_view(...)` | Flat normalized view. | `normalize_task_knowledge_view` |
| `split_task_knowledge_view(...)` | `(evidence_entries, wiki_entries)` split. | `split_task_knowledge_view` |
| `load_task_knowledge_view(...)` | Flat task knowledge view. | `load_task_knowledge_view` |
| `load_task_evidence_entries(...)` | Evidence-only view. | `load_task_evidence_entries` |
| `load_task_wiki_entries(...)` | Wiki-only view. | `load_task_wiki_entries` |
| `enforce_canonical_knowledge_write_authority(...)` | Shared authority check for task knowledge views that include canonical wiki entries. | `enforce_canonical_knowledge_write_authority` |
| `persist_task_knowledge_view(...)` | Persist full task knowledge view with explicit authority. | `persist_task_knowledge_view` |
| `persist_wiki_entry_from_canonical_record(...)` | Persist wiki entry derived from canonical record. | `persist_wiki_entry_from_record` |
| `iter_file_knowledge_task_ids(...)` | File-store scan used by doctor / migration paths. | `iter_file_knowledge_task_ids` |
| `migrate_file_knowledge_to_sqlite(...)` | File-to-SQLite migration command helper. | `migrate_file_knowledge_to_sqlite` |

No single `load_task_knowledge(...)` function exists in this plan; call sites choose the exact output shape they need.

### Ingestion

| Facade name | Purpose | Replaces |
|---|---|---|
| `ingest_operator_note(...)` | Stage a note from CLI/operator text. | `ingest_operator_note` |
| `ingest_local_file(...)` | Stage a local file with `dry_run`. | `ingest_local_file` |
| `run_knowledge_ingestion_pipeline(...)` | Full ingestion pipeline with `format_hint`, `submitted_by`, taxonomy role, and memory authority overrides for specialist flows. | `run_ingestion_pipeline` |
| `run_knowledge_ingestion_bytes_pipeline(...)` | Clipboard/bytes ingestion pipeline. | `run_ingestion_bytes_pipeline` |
| `render_ingestion_report(...)` | Full ingestion report. | `build_ingestion_report` |
| `render_ingestion_summary(...)` | Short ingestion summary. | `build_ingestion_summary` |

`knowledge_retrieval/ingestion/parsers.py` and `ingestion/filters.py` remain public implementation modules for parser/filter unit tests and evals. `ingestion/__init__.py` must stop re-exporting pipeline functions after `pipeline.py` is internalized.

### Knowledge Relations And Executor Suggestions

| Facade name | Purpose | Replaces |
|---|---|---|
| `create_knowledge_relation(...)` | Create relation with resolution / validation. | `create_knowledge_relation` |
| `list_knowledge_relations(...)` | List relation neighborhood. | `list_knowledge_relations` |
| `delete_knowledge_relation(...)` | Delete relation by id. | `delete_knowledge_relation` |
| `render_knowledge_relation_report(...)` | Single relation text report. | `build_knowledge_relation_report` |
| `render_knowledge_relations_report(...)` | Relation list text report. | `build_knowledge_relations_report` |
| `persist_executor_side_effects(...)` | Same-signature function reference for execution pipeline side effects. | `persist_executor_side_effects` |
| `apply_relation_suggestions(...)` | Apply executor-side relation suggestions. | `apply_relation_suggestions` |
| `render_relation_suggestion_application_report(...)` | CLI report for suggestion application. | `build_relation_suggestion_application_report` |

### Knowledge Projections, Review, Reuse, And Policy

| Facade name | Purpose | Replaces |
|---|---|---|
| `build_knowledge_objects(...)` | Build task knowledge objects. | `knowledge_objects.build_knowledge_objects` |
| `build_knowledge_index(...)` / `render_knowledge_index_report(...)` | Build/render knowledge index. | `build_knowledge_index`, `build_knowledge_index_report` |
| `build_knowledge_partition(...)` / `render_knowledge_partition_report(...)` | Build/render knowledge partition. | `build_knowledge_partition`, `build_knowledge_partition_report` |
| `apply_knowledge_review_decision(...)` / `render_knowledge_decisions_report(...)` | Apply/render knowledge review decisions. | `apply_knowledge_decision`, `build_knowledge_decisions_report` |
| `build_review_queue(...)` / `render_review_queue_report(...)` | CLI review queue. | `build_review_queue`, `build_review_queue_report` |
| `audit_canonical_registry(...)` / `render_canonical_audit_report(...)` | Canonical registry audit CLI path. | `audit_canonical_registry`, `build_canonical_audit_report` |
| `build_canonical_reuse_summary(...)` / `render_canonical_reuse_report(...)` | Canonical reuse policy and report. | canonical reuse helpers |
| `build_canonical_reuse_evaluation_*` wrappers | Canonical reuse eval and regression CLI paths. | `canonical_reuse_eval` helpers |
| `evaluate_knowledge_policy(...)` / `render_knowledge_policy_report(...)` | Knowledge policy artifacts. | `evaluate_knowledge_policy`, `build_knowledge_policy_report` |
| `summarize_*` helpers | Text summaries currently consumed by CLI / harness reports. | `summarize_canonicalization`, `summarize_knowledge_*` |

There is no `build_knowledge_projection(...)` omnibus function.

### Retrieval, Evidence, Grounding, And Executor Prompt Data

| Facade name | Purpose | Replaces |
|---|---|---|
| `build_retrieval_request(...)` | Retrieval request factory. | `retrieval.build_retrieval_request` |
| `retrieve_knowledge_context(...)` | Same-signature callable wrapper for retrieval flow injection. | `retrieve_context` |
| `summarize_reused_knowledge(...)` | Retrieval reuse summary. | `summarize_reused_knowledge` |
| `build_evidence_pack(...)` | Structured EvidencePack. | `evidence_pack.build_evidence_pack` |
| `build_grounding_evidence(...)`, `extract_grounding_entries(...)`, `render_grounding_evidence_report(...)` | Grounding artifacts. | grounding helpers |
| `collect_executor_prompt_data(...)` | Executor prompt data. | `dialect_data.collect_prompt_data` |
| `DEFAULT_EXECUTOR`, `normalize_executor_name(...)`, `resolve_executor_name(...)` | Executor/dialect defaults currently housed under `knowledge_retrieval`. | `dialect_data` helpers |
| `ClaudeXMLDialect`, `FIMDialect` | Class references used by executor dialect registry. | `dialect_adapters` classes |

`retrieval_adapters.py`, `retrieval_config.py`, and `dialect_adapters/*` remain public implementation modules for their own unit tests and patch points. Upper runtime callers should use the facade unless a test is explicitly exercising the implementation module.

Stable value objects and constants that may remain exported from the facade:

- `StagedCandidate`
- `IngestionPipelineResult`
- `KNOWLEDGE_RELATION_TYPES`
- canonical write-authority constants (`LIBRARIAN_AGENT_WRITE_AUTHORITY`, `OPERATOR_CANONICAL_WRITE_AUTHORITY`, `KNOWLEDGE_MIGRATION_WRITE_AUTHORITY`, `TEST_FIXTURE_CANONICAL_WRITE_AUTHORITY`)
- retrieval source type constants if required by existing call sites

The facade may contain more than 10 public names because Python callers use function and class references directly. The quality bar is not the raw export count; it is that each exported name is explicit, typed by purpose, and not a transparent import-only barrel.

## Internal Module Rename Plan

| Current module | Target module | Notes |
|---|---|---|
| `knowledge_retrieval/canonical_registry.py` | `knowledge_retrieval/_internal_canonical_registry.py` | Canonical keys, record construction, registry index/report internals. |
| `knowledge_retrieval/staged_knowledge.py` | `knowledge_retrieval/_internal_staged_knowledge.py` | `StagedCandidate` storage and status mutation. `StagedCandidate` may be re-exported by facade. |
| `knowledge_retrieval/knowledge_store.py` | `knowledge_retrieval/_internal_knowledge_store.py` | Task knowledge view persistence and canonical write authorities. |
| `knowledge_retrieval/knowledge_relations.py` | `knowledge_retrieval/_internal_knowledge_relations.py` | Relation create/list/delete internals and relation report helpers. |
| `knowledge_retrieval/knowledge_suggestions.py` | `knowledge_retrieval/_internal_knowledge_suggestions.py` | Executor side-effect relation suggestion loading / application. |
| `knowledge_retrieval/ingestion/pipeline.py` | `knowledge_retrieval/_internal_ingestion_pipeline.py` | Ingestion orchestration. Keep `ingestion/filters.py` and `ingestion/parsers.py` public for focused parser/eval tests unless audit requires otherwise. |

`knowledge_retrieval/ingestion/__init__.py` is part of the rename work. After `pipeline.py` is internalized, `ingestion/__init__.py` must stop re-exporting pipeline names (`run_ingestion_pipeline`, `ingest_local_file`, `ingest_operator_note`, report builders, and pipeline result types). It should expose only parser/filter symbols, or become empty if that is cleaner. Runtime callers of pipeline behavior must import through `knowledge_plane.py`.

### Public / Internal Classification For Non-Renamed Modules

Not every module is renamed in this phase. The classification below decides what the import guard should allow:

| Module family | Classification | Rule |
|---|---|---|
| `retrieval.py`, `grounding.py`, `evidence_pack.py`, `dialect_data.py`, `canonical_reuse.py`, `canonical_reuse_eval.py`, `knowledge_index.py`, `knowledge_objects.py`, `knowledge_partition.py`, `knowledge_policy.py`, `knowledge_review.py`, `canonical_audit.py` | Facade-covered implementation modules | Keep physical filenames, but production callers outside `knowledge_retrieval/` must use `knowledge_plane.py`. Unit tests may import them directly only when testing that implementation module. |
| `retrieval_adapters.py`, `retrieval_config.py`, `dialect_adapters/*` | Public implementation / patch-point modules | Direct imports remain allowed for implementation tests, evals, and adapter patch points. Runtime orchestration/provider callers should still use facade wrappers for executor defaults, dialect classes, retrieval requests, and retrieval context. |
| `ingestion/parsers.py`, `ingestion/filters.py` | Public parser/filter implementation modules | Direct imports remain allowed for parser/filter tests and ingestion evals. Pipeline orchestration is not public after this phase. |
| `raw_material.py` | Public storage-boundary module | `surface_tools/librarian_executor.py` may keep direct raw-material storage imports because this is raw material persistence, not Knowledge Plane behavior. Other runtime callers need an explicit closeout rationale if they bypass the facade. |

## Caller Migration Matrix

| Caller group | Migration target |
|---|---|
| `application/commands/knowledge.py` | Use staged lifecycle, canonical-record, relation, ingestion, and migration facade operations. Keep `apply_proposal` / `register_canonical_proposal` ownership unchanged. |
| `application/commands/synthesis.py` | Use staged lifecycle facade operations for duplicate detection and candidate submission. |
| `application/commands/tasks.py` | Import canonical write-authority constant from facade. |
| `adapters/cli.py` | Use facade for ingestion, staged listing, canonical registry/reuse/eval reports, relation type constants, review queue builders, and canonicalization summaries. |
| `adapters/cli_commands/knowledge.py` | Use facade for staged listing, relation reports, ingestion rendering, canonical audit/report access, and `render_relation_suggestion_application_report(...)`. |
| `orchestration/artifact_writer.py` | Use facade for `persist_executor_side_effects(...)`, `evaluate_knowledge_policy(...)`, and `render_knowledge_policy_report(...)`. |
| `orchestration/harness.py` | Use same-signature facade callables for `persist_executor_side_effects(...)`, grounding helpers, knowledge index/object builders, and retrieval context. |
| `orchestration/retrieval_flow.py` | Use `build_retrieval_request(...)`, `retrieve_knowledge_context(...)`, and `summarize_reused_knowledge(...)` from facade; callable injection must keep the current `retrieve_context` signature. |
| `orchestration/task_report.py` | Use facade for `build_evidence_pack(...)`, retrieval context, and reused-knowledge summaries. |
| `orchestration/executor.py` | Use facade exports for `DEFAULT_EXECUTOR`, executor-name normalization/resolution, `collect_executor_prompt_data(...)`, `ClaudeXMLDialect`, and `FIMDialect`. |
| `orchestration/knowledge_flow.py`, `planner.py`, `orchestrator.py` | Use facade for knowledge objects, task view normalization/splitting, canonical registry/reuse/eval, grounding, partition/index/review, and task knowledge persistence. |
| `provider_router/route_registry.py`, `provider_router/route_selection.py` | Use facade for executor defaults and normalization currently sourced through `dialect_data`. |
| `surface_tools/doctor.py` | Use facade for `iter_file_knowledge_task_ids(...)`. |
| `surface_tools/ingestion_specialist.py` | Use facade for `run_knowledge_ingestion_pipeline(...)`, `render_ingestion_report(...)`, and `render_ingestion_summary(...)`. |
| `surface_tools/literature_specialist.py` | Use facade for `KNOWLEDGE_RELATION_TYPES`. |
| `surface_tools/librarian_executor.py` | Use facade for canonical registry/reuse, object/index/partition/review helpers; keep direct `raw_material.py` imports as the explicit public storage-boundary exception. |
| `truth_governance/truth/knowledge.py` | Use facade for `persist_wiki_entry_from_canonical_record(...)` and canonical write authorities. |
| `truth_governance/sqlite_store.py` | Not exempt. Use facade for `enforce_canonical_knowledge_write_authority(...)`, `normalize_task_knowledge_view(...)`, and `split_task_knowledge_view(...)`. |
| `truth_governance/store.py`, `truth_governance/proposal_registry.py` | Already use facade for current knowledge accesses; preserve that shape. |
| Tests | Public behavior tests migrate to facade imports. Direct imports remain allowed for parser/filter, retrieval adapter/config, dialect adapter, raw-material, and explicitly internal `knowledge_retrieval` unit tests. |

## Milestones

### M1 — Facade Contract And Characterization

Scope:

- Add focused tests for the proposed facade operations without moving callers yet.
- Use existing fixtures / tmp workspaces to characterize staged lifecycle, task knowledge view persistence, relation operations, ingestion report rendering, canonical record construction, and retrieval serving.
- Finalize function names and signatures in `knowledge_plane.py`.
- Replace the old import-only barrel body in `knowledge_plane.py` with real wrappers / cohesive facade definitions. Remove the broad legacy `__all__` list in this milestone rather than letting old re-exports coexist with the new API.

Acceptance:

- New facade tests fail before implementation and pass after the facade functions are added.
- `knowledge_plane.py` contains real `def` implementations and no broad `__all__` re-export list of lower-level helper names.
- Existing behavior is unchanged; no file renames yet.

Suggested focused tests:

```bash
.venv/bin/python -m pytest tests/test_knowledge_store.py tests/test_staged_knowledge.py tests/test_knowledge_relations.py tests/test_ingestion_pipeline.py -q
```

### M2 — Internalize Lifecycle Modules

Scope:

- Rename the six selected lifecycle modules to `_internal_*`.
- Update imports inside `knowledge_retrieval/` to use relative internal imports.
- Keep `knowledge_plane.py` as the only public bridge for these modules.
- Treat M2 and M3 as one atomic implementation gate. M2 is not a standalone commit and does not need to pass `compileall` before caller migration is complete.
- Update `knowledge_retrieval/ingestion/__init__.py` so it no longer re-exports internalized pipeline behavior.

Acceptance:

- No source file outside `src/swallow/knowledge_retrieval/` imports any of:
  - `swallow.knowledge_retrieval._internal_canonical_registry`
  - `swallow.knowledge_retrieval._internal_staged_knowledge`
  - `swallow.knowledge_retrieval._internal_knowledge_store`
  - `swallow.knowledge_retrieval._internal_knowledge_relations`
  - `swallow.knowledge_retrieval._internal_knowledge_suggestions`
  - `swallow.knowledge_retrieval._internal_ingestion_pipeline`
- Old public module names for the six internalized modules do not remain as compatibility stubs.
- Final acceptance for this milestone is checked after M3 caller migration in the same commit.

### M3 — Upper-Layer Caller Migration

Scope:

- Migrate application, adapters, orchestration, provider_router, residual `surface_tools`, and truth_governance callers according to the migration matrix.
- Keep application command ownership unchanged: application commands may still coordinate governance / `apply_proposal`; they simply stop importing knowledge internals directly.
- Preserve public CLI / HTTP outputs.
- Commit M2 + M3 together as one atomic refactor once renames and caller migration are both complete.

Acceptance:

- Runtime scan has no direct facade-covered `swallow.knowledge_retrieval.<module>` import outside the package, except the explicit public implementation/storage exceptions listed above.
- Runtime scan has no imports from the six old public module names or from `_internal_*` modules outside `src/swallow/knowledge_retrieval/`.
- `compileall` passes after the rename and caller migration are both complete.
- Existing CLI, HTTP, orchestration, truth_governance, provider_router, and ingestion tests pass.
- No unrelated D4 Phase B/C file relocation is included.

Suggested focused gate:

```bash
.venv/bin/python -m compileall -q src/swallow
.venv/bin/python -m pytest \
  tests/test_cli.py \
  tests/integration/cli/test_knowledge_commands.py \
  tests/integration/cli/test_synthesis_commands.py \
  tests/integration/http/test_web_write_routes.py \
  tests/test_librarian_executor.py \
  tests/test_sqlite_store.py \
  tests/test_retrieval_adapters.py \
  -q
```

### M4 — Guards And Documentation Sync

Scope:

- Add a guard to `tests/test_invariant_guards.py` enforcing Knowledge Plane public-boundary imports.
- Update `docs/active_context.md` for implementation status.
- Update this plan only if plan-audit changes the target API shape.

Guard shape:

- Parse `src/**/*.py` for the production boundary. Test/eval imports follow the classification table above, but M4 does not need to block every test import that intentionally targets an implementation module.
- For files outside `src/swallow/knowledge_retrieval/`, reject imports of `swallow.knowledge_retrieval._internal_*`.
- For files outside `src/swallow/knowledge_retrieval/`, reject imports from the old six public module names even if compatibility stubs somehow remain.
- For production files outside `src/swallow/knowledge_retrieval/`, reject direct imports from facade-covered modules such as `retrieval`, `grounding`, `evidence_pack`, `knowledge_review`, `canonical_reuse_eval`, `knowledge_policy`, `knowledge_objects`, `knowledge_index`, `knowledge_partition`, `canonical_registry`, `knowledge_store`, `knowledge_relations`, `knowledge_suggestions`, and `ingestion.pipeline`.
- Allow imports from `swallow.knowledge_retrieval.knowledge_plane`.
- In production source, allow only the explicit `raw_material.py` storage-boundary exception for `surface_tools/librarian_executor.py`. Parser/filter modules, retrieval adapter/config modules, and dialect adapter modules remain direct-importable only for implementation tests/evals/patch points.
- Update existing invariant guard allowlists from `src/swallow/knowledge_retrieval/knowledge_store.py` to `src/swallow/knowledge_retrieval/_internal_knowledge_store.py` in `test_canonical_write_only_via_apply_proposal`, `test_only_apply_proposal_calls_private_writers`, and `test_no_module_outside_governance_imports_store_writes`.

Acceptance:

- Guard fails on a deliberate direct internal import and passes on the final tree.
- Guard fails on a deliberate direct import from a facade-covered non-renamed behavior module outside `knowledge_retrieval/`.
- Existing canonical writer invariant guards still pass after the `knowledge_store.py` rename.
- `tests/test_invariant_guards.py -q` passes.

### M5 — Full Validation And Closeout Prep

Scope:

- Run full validation.
- Prepare implementation summary and suggested commit scope.
- Leave `closeout.md` for post-implementation review / final closeout, not for plan stage.

Validation:

```bash
.venv/bin/python -m compileall -q src/swallow
.venv/bin/python -m pytest -q
git diff --check
```

## Acceptance Criteria

1. `knowledge_plane.py` is a functional facade with named domain operations, not a re-export list.
2. The six lifecycle modules are renamed to internal modules and are not imported by upper layers.
3. All current upper-layer direct imports from facade-covered Knowledge Plane behavior modules are migrated to `knowledge_plane`.
4. Existing CLI / HTTP / orchestration / truth_governance behavior remains compatible.
5. Tests cover the facade operations and the import-boundary guard.
6. Full pytest, compileall, and diff hygiene pass.

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Facade becomes a new barrel file | Require domain-operation tests in M1 and reject a broad re-export `__all__`. |
| One-shot migration diff is large | Keep changes mechanical, but make internal rename + caller migration one atomic commit so the tree never contains broken imports at a commit boundary. |
| Retrieval / dialect imports do not fit the first API shape | Let M1 refine names, but require every upper-layer dependency to be intentionally classified as facade, public non-internal module, or deferred with closeout rationale. |
| Tests become coupled to private internals | Move behavior tests to facade imports; keep internal imports only for parser / retrieval adapter unit tests that are explicitly implementation-level. |
| Accidental behavior change in canonical promotion | Keep `apply_proposal`, `register_canonical_proposal`, and application command orchestration unchanged; only move knowledge helper access behind facade. |
| D4 Phase B/C sneaks in | Do not move residual `surface_tools` files except touched imports. Any service/infrastructure relocation needs a separate phase or a touched-surface justification. |

## Suggested Commit Boundaries

1. `refactor(knowledge): add functional knowledge plane facade`
2. `refactor(knowledge): internalize modules and migrate callers`
3. `test(knowledge): guard knowledge plane import boundary`
4. Optional docs/status commit if Human wants plan/closeout materials separate from code.

M5 is a validation gate, not a code commit.

## Plan Gate Checklist

- [x] Claude / design-auditor reviews the facade API names and verifies they are not just old helper names with a new import path.
- [x] Human confirms the internal module naming choice (`_internal_*` same-package) before implementation.
- [x] Human confirms one-shot migration is acceptable for this phase.
- [x] Implementation branch is cut from `main` after plan gate.
