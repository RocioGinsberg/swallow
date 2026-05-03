---
author: codex
phase: lto-6-knowledge-plane-facade-solidification
slice: phase-closeout
status: final
depends_on:
  - docs/plans/lto-6-knowledge-plane-facade-solidification/plan.md
  - docs/plans/lto-6-knowledge-plane-facade-solidification/plan_audit.md
  - docs/plans/lto-6-knowledge-plane-facade-solidification/review_comments.md
  - docs/active_context.md
  - docs/concerns_backlog.md
  - src/swallow/knowledge_retrieval/knowledge_plane.py
  - src/swallow/knowledge_retrieval/_internal_canonical_registry.py
  - src/swallow/knowledge_retrieval/_internal_staged_knowledge.py
  - src/swallow/knowledge_retrieval/_internal_knowledge_store.py
  - src/swallow/knowledge_retrieval/_internal_knowledge_relations.py
  - src/swallow/knowledge_retrieval/_internal_knowledge_suggestions.py
  - src/swallow/knowledge_retrieval/_internal_ingestion_pipeline.py
  - tests/test_knowledge_plane_facade.py
  - tests/test_invariant_guards.py
---

TL;DR:
LTO-6 implementation and PR review are complete; Claude returned recommend-merge with 0 blockers / 1 non-blocking concern / 2 nits.
`knowledge_plane.py` is now the functional public facade; the six lifecycle modules are internalized, upper-layer callers are migrated, and a production import-boundary guard prevents direct bypasses.
Full validation passed with `755 passed, 8 deselected`; C1 facade naming cleanup is deferred as a small follow-up, not a merge blocker.

# LTO-6 Closeout: Knowledge Plane Facade Solidification

## Outcome

LTO-6 solidified the Knowledge Plane boundary before Wiki Compiler work expands knowledge-authoring call sites.

Delivered:

- Replaced the previous `knowledge_plane.py` barrel shape with explicit module-level facade functions.
- Added facade characterization coverage for staged knowledge, task knowledge views, ingestion, relations/suggestions, projection/review/policy, retrieval, grounding, and executor prompt data.
- Renamed six lifecycle implementation modules to same-package `_internal_*` modules:
  - `_internal_canonical_registry.py`
  - `_internal_staged_knowledge.py`
  - `_internal_knowledge_store.py`
  - `_internal_knowledge_relations.py`
  - `_internal_knowledge_suggestions.py`
  - `_internal_ingestion_pipeline.py`
- Migrated application, adapters, orchestration, provider_router, residual `surface_tools`, truth_governance, and behavior tests to import Knowledge Plane behavior through `knowledge_plane`.
- Removed pipeline re-exports from `knowledge_retrieval/ingestion/__init__.py`; parser/filter exports remain public.
- Added an invariant guard enforcing the production import boundary.

No compatibility stubs remain for the six old public module names.

## Scope Delivered

| Plan area | Result |
|---|---|
| M1 facade contract | Delivered: functional facade wrappers and `tests/test_knowledge_plane_facade.py`. |
| M2 internal module rename | Delivered: six lifecycle modules moved to `_internal_*`; no old public files remain. |
| M3 caller migration | Delivered: upper-layer runtime callers and public behavior tests now use `knowledge_plane`; `raw_material.py` remains the explicit storage-boundary exception. |
| M4 guard | Delivered: production import-boundary guard rejects `_internal_*`, old six modules, and facade-covered `knowledge_retrieval.*` behavior imports outside the package. |
| M5 validation | Delivered: compileall, full pytest, and diff hygiene passed. |

## Implementation Notes

The facade remains functional rather than class-based. This avoids coupling LTO-6 to future LTO-5 driven ports and keeps caller signatures stable.

The internal rename and caller migration were intentionally committed atomically. A rename-only commit would have left the tree uncompilable because existing upper-layer callers would still reference removed public modules.

`truth_governance/sqlite_store.py` uses lazy imports for Knowledge Plane view helpers. This preserves the facade direction while avoiding an initialization cycle:

```text
knowledge_plane -> _internal_canonical_registry -> sqlite_store -> knowledge_plane
```

Canonical promotion ownership did not change:

- `apply_proposal` remains the unique mutation entry for canonical knowledge / route metadata / policy.
- Application commands still coordinate governance.
- `knowledge_plane` exposes knowledge helper operations, not independent proposal mutation authority.

## Guard Behavior

The new guard in `tests/test_invariant_guards.py` scans production source and rejects imports outside `src/swallow/knowledge_retrieval/` from:

- `swallow.knowledge_retrieval._internal_*`
- the six old public lifecycle module names
- facade-covered behavior modules such as `retrieval`, `grounding`, `evidence_pack`, `knowledge_review`, `canonical_reuse_eval`, `knowledge_policy`, `knowledge_objects`, `knowledge_index`, `knowledge_partition`, and similar Knowledge Plane implementation modules
- any other non-`knowledge_plane` Knowledge Retrieval submodule in production source, except the explicit raw-material exception

Allowed production imports:

- `swallow.knowledge_retrieval.knowledge_plane`
- `swallow.knowledge_retrieval.raw_material` only from `src/swallow/surface_tools/librarian_executor.py`

The guard includes synthetic fixtures proving it fails on direct `_internal_knowledge_store` and `retrieval` imports while allowing the facade and raw-material exception.

## Validation

Milestone validation:

```text
M1:
- tests/test_knowledge_plane_facade.py: 6 passed
- M1 focused gate: 31 passed
- compileall -q src/swallow: passed
- git diff --check: passed

M2+M3:
- focused CLI/HTTP/orchestration/truth/provider/ingestion gate: 303 passed
- facade/knowledge/invariant gate: 58 passed
- application boundary: 11 passed
- provider_router focused gate: 40 passed
- full pytest: 751 passed, 8 deselected
- old-module import scan: clean
- external _internal import scan: clean
- git diff --check: passed

M4:
- tests/test_invariant_guards.py: 31 passed
- git diff --check: passed

M5:
- compileall -q src/swallow: passed
- full pytest: 755 passed, 8 deselected
- git diff --check: passed
```

## Plan Audit Absorption

`plan_audit.md` had 0 blockers / 7 concerns / 2 nits. The implementation absorbed them as follows:

- No omnibus `build_knowledge_projection`, `serve_knowledge_context`, or ambiguous `load_task_knowledge` function was introduced.
- Function-reference consumers kept same-signature facade wrappers.
- M2 and M3 were treated as one atomic implementation gate.
- `ingestion/__init__.py` stopped re-exporting pipeline behavior.
- Previously unclassified imports were mapped to facade functions, public test-only implementation modules, or explicit raw-material exception.
- The import-boundary guard covers non-renamed facade-covered modules, not only `_internal_*`.
- Invariant guard allowlists were updated for `_internal_knowledge_store.py` and `_internal_ingestion_pipeline.py`.

## Deferred Follow-Ups

Intentionally out of scope:

- Wiki Compiler / draft-wiki / refine-wiki / source packs.
- Class-based `KnowledgePlane` service, DI container, or repository ports.
- SQLite schema changes or Knowledge Truth semantic changes.
- Broad D4 Phase B/C file relocation.
- Retrieval adapter/config, parser/filter, and dialect adapter implementation-test reclassification.
- Facade report-name consolidation: review C1 notes that paired `render_*` / `build_*` aliases inflate the public facade surface. Preferred follow-up is to keep `render_*` for report rendering and `build_*` for object construction, then delete redundant aliases in a small post-merge cleanup before Wiki Compiler expands callers.
- `canonical_audit` lazy-import comment: review N1 notes the facade's audit functions use function-body imports to avoid a cycle; add a short comment or verify top-level import safety in the same cleanup pass.
- Explicit `__all__`: review N2 suggests declaring the facade public surface to make wildcard import and IDE behavior match the intended API.
- `current_state.md` and roadmap post-merge factual update; those happen after merge.

## Review Status

Claude PR review is complete:

```text
docs/plans/lto-6-knowledge-plane-facade-solidification/review_comments.md
verdict: recommend-merge
findings: 0 blockers / 1 concern / 2 nits
plan_audit absorption: 7 / 7 concerns + 2 / 2 nits verified
```

Disposition:

- C1 (`render_*` / `build_*` alias pairs): deferred as a non-blocking facade naming cleanup; logged to `docs/concerns_backlog.md`.
- N1 (`canonical_audit` lazy imports): deferred; add a comment or verify top-level import safety when touching facade naming.
- N2 (missing `__all__`): deferred; useful polish after the public surface stabilizes.

Final next steps:

- Human reviews and commits review / closeout / state sync materials.
- Human keeps PR body in sync from `./pr.md`.
- Human merge gate.
- After merge, Codex syncs `current_state.md`, `docs/active_context.md`, and `docs/roadmap.md`, then the next active phase can move to Wiki Compiler first stage.
