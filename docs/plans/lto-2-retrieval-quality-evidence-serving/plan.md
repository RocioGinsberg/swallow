---
author: codex
phase: lto-2-retrieval-quality-evidence-serving
slice: plan-definition
status: final
depends_on:
  - docs/roadmap.md
  - docs/concerns_backlog.md
  - docs/design/INVARIANTS.md
  - docs/design/KNOWLEDGE.md
  - docs/design/DATA_MODEL.md
  - docs/design/HARNESS.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/plans/retrieval-u-t-y/plan.md
  - docs/plans/lto-1-wiki-compiler-second-stage/closeout.md
  - docs/plans/lto-1-wiki-compiler-second-stage/review_comments.md
  - docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md
  - docs/plans/lto-2-retrieval-quality-evidence-serving/review_comments.md
---

TL;DR:
This phase advances LTO-2 by turning LTO-1 stage 2 source-pack evidence into deduplicated, source-anchored retrieval support.
It keeps Knowledge Truth governed and SQLite-local, improves EvidencePack/source grounding quality, and adds deterministic eval coverage for duplicate anchors and relation expansion noise.

# LTO-2 Plan: Retrieval Quality / Evidence Serving

## Frame

- active track: `Retrieval Quality`
- active phase: `lto-2-retrieval-quality-evidence-serving`
- recommended branch after Human Plan Gate: `feat/lto-2-retrieval-quality-evidence-serving`
- current planning branch: `main`
- roadmap trigger: LTO-1 stage 2 left cross-candidate source-anchor duplication as the strongest Direction Gate signal for LTO-2.
- implementation stance: bounded retrieval/evidence quality increment; no broad schema migration or Graph RAG work.

The phase builds on the existing Retrieval U-T-Y baseline:

- retrieval trace, source policy labels, EvidencePack compatibility view, and source pointer resolution already exist.
- Wiki Compiler stage 2 now materializes `source_pack` anchors as evidence objects and persists `derived_from` edges.
- current dedup scope is still per candidate and per source-pack index, so two staged candidates citing the same source anchor can create duplicate evidence support objects.

## Goals

1. Add a stable source-anchor identity used by evidence materialization and retrieval serving:
   - normalize `source_ref`, `content_hash`, `parser_version`, `span`, and `heading_path`
   - compute a deterministic `source_anchor_key`
   - keep this identity in evidence entry metadata and serving output
2. Reuse existing evidence support objects across staged candidates when their source anchors are identical:
   - do not create duplicate evidence objects for the same resolved anchor
   - preserve the governed promotion path and current `apply_proposal` ownership
   - keep `derived_from` relations pointing to evidence object ids, not raw refs
3. Tighten relation expansion and EvidencePack serving so repeated support anchors are visible once:
   - dedupe source pointers by anchor identity
   - dedupe relation-expanded supporting evidence when multiple paths reach the same evidence object
   - preserve existing retrieval item compatibility
4. Improve operator-facing evidence quality:
   - show reused evidence counts and duplicate-anchor warnings in retrieval/source grounding reports
   - add bounded excerpts from stored evidence previews where available
   - keep unresolved/missing source pointers explicit
5. Add deterministic eval coverage for the LTO-2 quality signal:
   - duplicate source anchors across candidates
   - relation expansion dedup
   - fallback/truth source policy stability
   - bounded excerpt / source pointer status

## Non-Goals

- Do not create a new physical `know_evidence` table in this phase.
- Do not perform a DATA_MODEL §3.3 schema migration unless Human / plan audit explicitly upgrades this phase scope.
- Do not introduce object storage, MinIO, OSS, S3-compatible backend, or a new RawMaterialStore backend.
- Do not make evidence a default primary retrieval object. Evidence remains supporting material for Wiki / Canonical.
- Do not implement Graph RAG, community detection, project-level graph visualization, or multi-hop LLM retrieval.
- Do not add a durable Web background worker or change Wiki Compiler fire-and-poll semantics.
- Do not change canonical write authority or bypass `apply_proposal`.
- Do not turn eval failures into hard merge blockers; eval remains a quality signal.
- Do not backfill or rewrite existing `evidence-<candidate>-<index>` rows in this phase. Legacy evidence rows remain valid relation targets.

## Design And Engineering Anchors

- `docs/design/INVARIANTS.md`
  - P3 Truth before retrieval: vector/text/evidence serving cannot redefine Knowledge Truth.
  - `apply_proposal` remains the only canonical / route / policy mutation entry.
  - no executor or specialist gains direct Truth mutation authority.
- `docs/design/KNOWLEDGE.md`
  - Evidence is source-anchored support, not a chunk store.
  - EvidencePack prioritizes Wiki / Canonical as primary objects and marks fallback hits explicitly.
  - `Unversioned Evidence Rebuild` is the worked anti-pattern this phase must avoid.
- `docs/design/DATA_MODEL.md`
  - Physical schema mismatch remains known: design describes `know_evidence`, current implementation uses task-scoped `knowledge_evidence`.
  - This phase may add stable metadata inside existing JSON payloads; it does not add a new table without plan-gate escalation.
- `docs/design/HARNESS.md`
  - retrieval serving and artifact generation remain controlled runtime support, not task-state advancement.
- `docs/engineering/CODE_ORGANIZATION.md`
  - upper layers continue using `knowledge_plane.py` facade.
  - no new direct reach into `_internal_*` knowledge modules from application/adapters/orchestration.
- `docs/engineering/TEST_ARCHITECTURE.md`
  - new functional coverage goes to focused unit/integration files; eval lives under `tests/eval/` and stays deselected by default.
- `docs/engineering/ADAPTER_DISCIPLINE.md`
  - if HTTP/CLI output changes are needed, adapters remain thin formatters over application/domain results.

## Boundary Decision: Evidence Identity Without Schema Migration

Default decision for this plan:

- implement **semantic global evidence identity** through deterministic source-anchor keys and globally stable evidence object ids;
- continue storing evidence entries in the existing task-scoped `knowledge_evidence` implementation;
- reuse existing evidence ids across candidates by lookup, rather than duplicating entries;
- keep the `know_evidence` physical schema migration deferred.

Rationale:

- LTO-1 stage 2 duplication risk is immediate and can be resolved without a database migration.
- The current relation table references evidence by object id only, so a deterministic evidence id gives relation expansion a stable target.
- A standalone `know_evidence` table would touch DATA_MODEL, migration, store APIs, and historical backfill; that is a separate schema phase.

Plan audit validated this decision and did not upgrade the schema mismatch to blocker. If Human later expands scope into schema work, M1 becomes a schema-design milestone before implementation begins.

## Plan Audit Absorption Decisions

Claude audit verdict: `has-concerns`;0 blockers / 5 concerns / 2 nits. This plan accepts all concerns and resolves them as follows.

### C1 / C2: Source-Anchor Key Contract

`source_anchor_key` version `source-anchor-v1` is computed from all five normalized fields, in this exact order:

1. `source_ref`
2. `content_hash`
3. `parser_version`
4. `span`
5. `heading_path`

Canonical payload:

```text
["source-anchor-v1", source_ref, content_hash, parser_version, span, heading_path]
```

The key token is the first 16 hex characters of `sha256(canonical_json(payload))`, where canonical JSON uses sorted keys for nested values and compact separators. The evidence id is:

```text
evidence-src-<source_anchor_key>
```

Normalization rules:

- `source_ref`, `content_hash`, and `parser_version`: `str(value).strip()`.
- `span`: if the source value is a mapping/list, serialize as canonical JSON; otherwise `str(value).strip()`. If `span` is empty and line-range fields exist, encode as `line:<start>-<end>`.
- `heading_path`: if the source value is a list/tuple, strip non-empty segments and join with ` > `; if it is a string, split on `>` and rejoin trimmed non-empty segments with ` > `; otherwise `str(value).strip()`.

Tests must assert that changing any of the five fields changes the key, including `source_ref`.

### C3 / N1: Cross-Task Lookup And Legacy Evidence

M2 computes `evidence-src-<source_anchor_key>` first, then checks for an existing evidence object with `knowledge_object_exists(base_dir, evidence_id)`. That helper already performs a cross-task `object_id` lookup. If it returns true, materialization skips the write and reuses the id; relation creation can then pass the existing `knowledge_object_store_type()` evidence-target guard.

No new `object_id`-only SQLite index is required in this phase because evidence volume is currently small. If this becomes slow, closeout should record an index follow-up.

Existing legacy rows with ids like `evidence-<candidate>-<index>` are not rewritten and are not scanned by `entry_json` for backfill matching. New LTO-2 promotions dedupe by deterministic `evidence-src-<key>` ids going forward. Legacy rows remain valid for existing `derived_from` relations.

### C4: Relation Id Scheme

M2 changes persisted `derived_from` relation id generation from candidate/index-based ids to source/evidence pair ids. The relation id is deterministic over `(source_object_id, evidence_id)`, for example:

```text
relation-derived-from-<sha256(["derived-from-v1", source_object_id, evidence_id])[:16]>
```

This means:

- the same wiki/canonical source object and same evidence object upsert to the same relation row;
- two different wiki/canonical objects referencing the same evidence object produce two different relation rows;
- relation idempotency no longer depends on staged candidate id or source-pack index.

### C5: Source-Anchor Key Propagation

M3 uses the retrieval pipeline as the propagation path. When evidence entries become `RetrievalItem` objects, `retrieval.py` must copy `source_anchor_key` and `source_anchor_version` from stored `entry_json` into `RetrievalItem.metadata`.

`build_evidence_pack()` must dedupe from `RetrievalItem.metadata`; it must not receive `base_dir` or perform per-item store lookups.

### N2: Excerpt Source

M4 reuses stored `entry_json["preview"]` as the bounded excerpt source. It does not perform fresh raw material resolution. Existing storage-time preview caps remain authoritative, and report rendering may apply an additional display cap if the current retrieval/report surface already does so.

## Current Code Touch Map

Likely implementation surfaces:

- `src/swallow/knowledge_retrieval/_internal_knowledge_store.py`
  - source-anchor normalization and `source_anchor_key` construction
  - evidence id selection / lookup / reuse during `materialize_source_evidence_from_canonical_record`
  - preservation of parser/content/span/heading anchors
- `src/swallow/knowledge_retrieval/knowledge_plane.py`
  - public facade wrappers for any new source-anchor helper needed by tests or upper layers
- `src/swallow/truth_governance/truth/knowledge.py`
  - deterministic `derived_from` relation id based on wiki/canonical source id and evidence id
  - apply-result payload/report fields for reused evidence counts if needed
- `src/swallow/knowledge_retrieval/evidence_pack.py`
  - source pointer / fallback hit / supporting evidence dedup by source-anchor key
  - bounded excerpt fields from stored evidence previews
- `src/swallow/knowledge_retrieval/grounding.py`
  - grounding report fields for anchor key, resolution status, and stored preview excerpts
- `src/swallow/knowledge_retrieval/retrieval.py`
  - relation expansion dedup and source-policy summary preservation
- `src/swallow/orchestration/task_report.py` or harness report helpers
  - retrieval/source grounding report visibility, if this is where current report text is assembled
- tests:
  - `tests/test_governance.py`
  - `tests/test_knowledge_relations.py`
  - `tests/test_evidence_pack.py`
  - `tests/test_grounding.py`
  - `tests/test_retrieval_adapters.py`
  - `tests/eval/test_lto2_retrieval_quality.py`

## Milestones

| Milestone | Slice | Goal | Scope | Risk | Commit gate |
|---|---|---|---|---|---|
| M0 | Plan and state sync | Create this plan and align `docs/active_context.md` to the new phase. | Docs only; no implementation branch yet. | low | Human Plan Gate after plan_audit |
| M1 | Source-anchor identity contract | Add deterministic source-anchor key/value helpers and characterize current duplicate behavior. | Normalize source refs and anchors; expose helper through Knowledge Plane only if needed; tests prove same anchor -> same key and each hash input field changes the key. | medium | Standalone implementation commit; no schema migration |
| M2 | Governed evidence dedup on promotion | Reuse existing evidence objects when multiple candidates cite the same anchor. | Update materialization inside canonical apply path; deterministic evidence id; `source_evidence_ids` contains reused ids; `derived_from` relation ids use wiki/canonical source id + evidence id. | high | Separate commit; focused governance/store/relation tests |
| M3 | Retrieval / EvidencePack dedup | Avoid duplicate supporting evidence and source pointers in serving outputs. | EvidencePack grouping/dedup by anchor key; relation expansion dedup; preserve existing `RetrievalItem[]` shape and metadata compatibility. | medium-high | Separate commit; retrieval/evidence pack tests |
| M4 | Operator report quality | Surface dedup, source pointer status, and bounded excerpts in reports. | Retrieval/source grounding report additions; unresolved/missing pointers remain explicit; no broad CLI refactor. | medium | Separate surface/report commit |
| M5 | Eval, guards, closeout prep | Add deterministic LTO-2 quality eval and final validation. | New eval file; any narrow invariant guard needed for duplicate evidence id discipline; closeout/pr prep after implementation. | medium | Final milestone commit before PR review |

## Slice Details

### M1: Source-Anchor Identity Contract

Expected additions:

- a single helper that normalizes:
  - `source_ref`
  - `content_hash`
  - `parser_version`
  - `span`
  - `heading_path`
  - optional line range when no `span` exists
- deterministic `source_anchor_key` using `source-anchor-v1` canonical JSON over `[source_ref, content_hash, parser_version, span, heading_path]`
- deterministic evidence ids in the form `evidence-src-<source_anchor_key>`
- evidence entry metadata fields:
  - `source_anchor_key`
  - `source_anchor_version`

Acceptance:

- identical anchors across different staged candidates produce the same `source_anchor_key`;
- changing `source_ref`, `content_hash`, `parser_version`, `span`, or `heading_path` changes the key;
- list and string `heading_path` inputs normalize to the same canonical string when they represent the same path;
- unresolved/missing source-pack entries still do not materialize;
- helper lives behind the Knowledge Plane boundary if upper layers or tests need it.

### M2: Governed Evidence Dedup On Promotion

Expected additions:

- `materialize_source_evidence_from_canonical_record` computes `evidence-src-<source_anchor_key>` and checks `knowledge_object_exists(base_dir, evidence_id)` before creating a new evidence entry.
- evidence ids become stable by source-anchor key, for example `evidence-src-<key>`, not `evidence-<candidate>-<index>`.
- if an anchor already exists:
  - do not create another evidence entry;
  - reuse the existing evidence object id in `canonical_record["source_evidence_ids"]`;
  - still create the new wiki/canonical object's `derived_from` relation to the reused evidence id.
- relation id becomes deterministic on `(source wiki/canonical id, evidence id)`, not `(candidate_id, source_pack_index)`, so rerunning a candidate promotion is idempotent per source/evidence pair.

Acceptance:

- two different staged candidates citing the same source anchor leave exactly one evidence object id for that anchor;
- both promoted wiki/canonical records can point to that same evidence id through `derived_from`;
- two different wiki/canonical records pointing to the same evidence object produce two distinct relation ids, while rerunning the same source/evidence pair upserts one relation id;
- apply result remains truthful about created/reused evidence counts if exposed;
- canonical mutation still happens only through the existing `apply_proposal` path.
- existing `evidence-<candidate>-<index>` rows remain valid and are not rewritten.

### M3: Retrieval / EvidencePack Dedup

Expected additions:

- retrieval entry construction copies `source_anchor_key` / `source_anchor_version` from evidence `entry_json` into `RetrievalItem.metadata`;
- EvidencePack dedup by `source_anchor_key` for:
  - `supporting_evidence`
  - `source_pointers`
  - fallback hit summaries when the same physical source appears via multiple paths
- relation expansion dedup so a canonical/wiki object reached through multiple relation paths appears once with a clear `dedup_reason` or `expansion_path_count` metadata.
- existing retrieval JSON item list remains compatible; new fields are additive.
- `build_evidence_pack()` uses metadata-only dedup and does not perform store lookups.

Acceptance:

- old tests using `RetrievalItem.to_dict()` still pass;
- EvidencePack summaries make duplicate suppression visible;
- fallback hits remain marked as fallback and never become `primary_objects` because they share a source pointer with evidence.
- tests cover a retrieval evidence item carrying `source_anchor_key` metadata from stored evidence entry JSON.

### M4: Operator Report Quality

Expected additions:

- `source_grounding.md` / retrieval report include:
  - source anchor key
  - source pointer resolution status
  - reused evidence count or duplicate-anchor count
  - bounded excerpt from stored `entry_json["preview"]` when present
  - explicit unresolved/missing source pointer reason
- bounded excerpts must remain display support and must not turn raw bytes into truth.
- no fresh raw material resolution is added for excerpts in this phase.

Acceptance:

- operator can see whether repeated source refs were deduped;
- missing/unresolved source pointers are visible without implying evidence resolution succeeded;
- no new broad CLI command is required unless report output cannot express the boundary.
- report tests distinguish stored preview excerpts from unresolved source pointers.

### M5: Eval, Guards, Closeout Prep

Expected additions:

- new eval file: `tests/eval/test_lto2_retrieval_quality.py`
- deterministic fixtures with:
  - two candidates citing the same source anchor
  - same source ref but changed parser/hash/span to prove non-dedup
  - changed heading_path and changed source_ref to prove both affect the key
  - relation expansion reaching the same evidence support through two paths
  - bounded excerpt reporting from stored evidence preview
- optional guard:
  - evidence id generation remains source-anchor-key based, not candidate-index based, for Wiki Compiler source-pack materialization.

Acceptance:

- eval is deterministic and does not call live LLM / embedding / rerank endpoints;
- focused M1-M4 tests pass;
- full default pytest passes before PR review;
- closeout records whether DATA_MODEL schema migration remains deferred.

## Validation Plan

Focused default checks during implementation:

```bash
.venv/bin/python -m pytest tests/test_governance.py tests/test_knowledge_relations.py tests/test_sqlite_store.py -q
.venv/bin/python -m pytest tests/test_evidence_pack.py tests/test_grounding.py tests/test_retrieval_adapters.py -q
.venv/bin/python -m pytest tests/unit/orchestration/test_task_report_module.py tests/unit/orchestration/test_harness_facade.py -q
.venv/bin/python -m pytest tests/eval/test_lto2_retrieval_quality.py -m eval -q
git diff --check
```

Milestone / PR gate:

```bash
.venv/bin/python -m compileall -q src/swallow
.venv/bin/python -m pytest -q
git diff --check
```

No live provider, embedding API, or rerank endpoint should be required by default tests.

## Risks And Controls

| Risk | Control |
|---|---|
| Semantic evidence identity becomes an implicit schema migration | Keep `source_anchor_key` inside existing JSON payloads; no new table or DB migration in this phase. |
| Same evidence id exists in multiple task rows and confuses relation lookup | Prefer "first existing evidence id wins"; avoid writing duplicate rows when the id already exists; add tests for store lookup and relation target resolution. |
| Legacy candidate-index evidence rows remain after LTO-2 | Do not rewrite them; keep existing relations valid and dedupe only new `evidence-src-<key>` rows going forward. |
| Heading path list/string forms hash differently | Normalize list/tuple and string heading paths to the same ` > `-joined canonical string before hashing. |
| Dedup hides useful provenance | Keep per-wiki `derived_from` relations; report reused count / expansion path count instead of dropping visibility. |
| Evidence starts acting as primary retrieval truth | EvidencePack grouping keeps Evidence supporting; Wiki / Canonical remain primary objects. |
| Bounded excerpts leak too much raw content | Reuse stored evidence previews instead of fresh raw reads; preserve source pointers as references. |
| DATA_MODEL §3.3 mismatch remains unresolved | Record as deferred in closeout unless Human/audit expands this phase into schema migration. |
| Eval turns flaky or provider-dependent | Use deterministic fixtures and local scoring only; no live API calls. |

## Branch / PR / Review Gates

- Planning may happen on `main`.
- Implementation must wait for Human Plan Gate and a feature branch.
- Recommended branch:

```bash
feat/lto-2-retrieval-quality-evidence-serving
```

Commit gate proposal:

- M0: docs-only plan/state commit.
- M1: source-anchor identity contract.
- M2: governed evidence dedup on promotion.
- M3: retrieval/EvidencePack dedup.
- M4: report/CLI visibility.
- M5: eval/guards/closeout prep.

High-risk gates:

- M2 is the highest-risk milestone because it touches governed promotion and relation targets.
- Any schema migration proposal must stop implementation and return to plan audit / Human Plan Gate.

## Completion Conditions

- identical resolved source anchors across staged candidates reuse one stable evidence object id;
- changing parser/hash/span/heading produces a different evidence identity;
- `derived_from` relations still target evidence object ids only;
- EvidencePack/source grounding suppress duplicate support while reporting dedup visibility;
- retrieval reports distinguish primary truth, supporting evidence, and fallback hits;
- deterministic LTO-2 eval covers duplicate anchors and relation expansion dedup;
- no change violates Knowledge Plane facade, `apply_proposal`, or adapter boundary guards.
