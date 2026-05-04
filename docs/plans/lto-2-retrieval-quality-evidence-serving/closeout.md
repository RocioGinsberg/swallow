---
author: codex
phase: lto-2-retrieval-quality-evidence-serving
slice: closeout
status: final
depends_on:
  - docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md
  - docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md
  - docs/plans/lto-2-retrieval-quality-evidence-serving/review_comments.md
  - docs/active_context.md
  - current_state.md
---

TL;DR:
LTO-2 is complete and review passed with `recommend-merge`.
The phase delivered source-anchor evidence identity, promotion-time evidence reuse, retrieval/EvidencePack dedup, operator report visibility, and deterministic eval/guard coverage.
No schema migration, legacy evidence backfill, Graph RAG, object storage, or Web worker expansion was included.

# LTO-2 Closeout: Retrieval Quality / Evidence Serving

## Phase Outcome

Status: `recommend-merge` after Claude PR review.

This phase converted LTO-1 stage 2 source-pack evidence from candidate/index-scoped support rows into source-anchored retrieval support with stable identity and serving-time dedup. The implementation keeps Evidence as supporting material, keeps canonical mutation behind `apply_proposal`, and stays within the existing task-scoped `knowledge_evidence` store.

Delivered commits:

- `f9b683a feat(wiki): add source anchor evidence identity`
- `9b0a381 feat(wiki): dedupe source evidence on promotion`
- `1590e62 feat(retrieval): dedupe evidence serving by source anchor`
- `62a2a7d feat(retrieval): surface source-anchor evidence quality`
- `d6967f3 test(retrieval): add lto2 evidence quality eval`

## Delivered Scope

M1 Source-anchor identity contract:

- Added `source-anchor-v1` source-anchor identity over `source_ref`, `content_hash`, `parser_version`, `span`, and `heading_path`.
- Standardized evidence ids as `evidence-src-<source_anchor_key>`.
- Exposed `build_source_anchor_identity()` through the Knowledge Plane facade.

M2 Governed evidence dedup on promotion:

- Reused existing evidence objects with `knowledge_object_exists(base_dir, evidence_id)`.
- Skipped duplicate evidence writes while preserving `source_evidence_ids`.
- Changed `derived_from` relation ids to deterministic `derived-from-v1` source object + evidence id pairs.

M3 Retrieval / EvidencePack dedup:

- Propagated source-anchor metadata into `RetrievalItem.metadata`.
- Deduped supporting evidence, fallback hits, and source pointers from retrieval metadata only.
- Preserved duplicate-path observability with `expansion_path_count` / `dedup_reason`.

M4 Operator report quality:

- Surfaced source-anchor keys, source pointer status/reason, dedup counts, and stored preview excerpts in retrieval/source grounding reports.
- Reused stored `entry_json["preview"]`; no fresh raw material resolution was added.

M5 Eval and guards:

- Added `tests/eval/test_lto2_retrieval_quality.py` for duplicate source anchors, five-field hash discrimination, relation expansion dedup, and stored preview reporting.
- Added invariant guard coverage for `evidence-src-<source_anchor_key>` id discipline.

## Plan Audit Absorption

Plan audit verdict: `has-concerns`; 0 blockers / 5 concerns / 2 nits. All items were accepted before implementation.

| Audit item | Closeout disposition |
|---|---|
| C1 heading path normalization | Implemented list/string normalization to ` > ` joined canonical form. |
| C2 hash input completeness | Fixed exact `source-anchor-v1` canonical JSON payload order: version, `source_ref`, `content_hash`, `parser_version`, `span`, `heading_path`. |
| C3 cross-task lookup scope | Selected existing `knowledge_object_exists(base_dir, evidence_id)` cross-task object-id lookup; no new SQLite index in this phase. |
| C4 relation id scheme | Implemented deterministic `derived-from-v1` source object + evidence id relation ids. |
| C5 source anchor propagation | Chose retrieval pipeline path A: retrieval enriches `RetrievalItem.metadata`; EvidencePack remains a metadata consumer. |
| N1 eval placement | Added a dedicated LTO-2 eval file under `tests/eval/`. |
| N2 excerpt source | Reused stored evidence preview from `entry_json["preview"]`; no new raw material resolution path. |

## Review Disposition

Review artifact: `docs/plans/lto-2-retrieval-quality-evidence-serving/review_comments.md`.

Verdict: `recommend-merge`; 0 blockers / 1 concern / 1 nit.

- C1 closeout missing: resolved by this file.
- N1 active_context `latest_completed_slice` wording: acknowledged as cosmetic; not changed in this closeout because it is historical snapshot wording and does not affect merge readiness.

Review also recommended not cutting a standalone tag for LTO-2. The suggested release posture is to accumulate this retrieval-quality increment with a later capability phase, then consider `v1.9.0`. Final tag decision remains Human-owned.

## Final Validation

Final closeout validation:

```text
.venv/bin/python -m pytest tests/eval/test_lto2_retrieval_quality.py -m eval -q
3 passed

.venv/bin/python -m pytest tests/test_invariant_guards.py -q -k "source_pack_evidence_id or evidence_objectization"
2 passed, 39 deselected

.venv/bin/python -m pytest tests/test_governance.py tests/test_knowledge_relations.py tests/test_sqlite_store.py -q
39 passed

.venv/bin/python -m pytest tests/test_evidence_pack.py tests/test_grounding.py tests/test_retrieval_adapters.py -q
39 passed

.venv/bin/python -m pytest tests/unit/orchestration/test_task_report_module.py tests/unit/orchestration/test_harness_facade.py -q
9 passed

.venv/bin/python -m pytest tests/test_invariant_guards.py -q
41 passed

.venv/bin/python -m compileall -q src/swallow
passed

.venv/bin/python -m pytest -q
802 passed, 19 deselected in 131.59s

git diff --check
passed
```

## Deferred Follow-Ups

Deferred by phase boundary:

- `know_evidence` physical table / DATA_MODEL schema migration remains deferred.
- Legacy `evidence-<candidate>-<index>` rows are not backfilled or rewritten.
- No object storage / MinIO / OSS / S3-compatible evidence backend.
- No Graph RAG, community detection, project-level graph visualization, or multi-hop LLM retrieval.
- No durable Web background worker or change to Wiki Compiler fire-and-poll semantics.
- No new SQLite object-id index for evidence lookup; revisit only if real evidence volume makes `knowledge_object_exists(base_dir, evidence_id)` slow.

Post-merge state work:

- Update `current_state.md` and `docs/active_context.md` to the merge checkpoint.
- Let roadmap update mark LTO-2 complete.
- Move the LTO-2 Roadmap-Bound cross-candidate evidence dedup concern to Resolved in `docs/concerns_backlog.md`.

## Merge Readiness

Ready for Human closeout commit and merge after final validation passes.
