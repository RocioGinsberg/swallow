---
author: claude
phase: lto-2-retrieval-quality-evidence-serving
slice: plan-audit
status: draft
depends_on:
  - docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md
  - src/swallow/knowledge_retrieval/_internal_knowledge_store.py
  - src/swallow/knowledge_retrieval/_internal_knowledge_relations.py
  - src/swallow/knowledge_retrieval/knowledge_plane.py
  - src/swallow/knowledge_retrieval/evidence_pack.py
  - src/swallow/knowledge_retrieval/grounding.py
  - src/swallow/knowledge_retrieval/retrieval.py
  - src/swallow/truth_governance/truth/knowledge.py
  - src/swallow/truth_governance/sqlite_store.py
  - src/swallow/orchestration/task_report.py
  - docs/plans/lto-1-wiki-compiler-second-stage/review_comments.md
  - docs/plans/lto-1-wiki-compiler-second-stage/closeout.md
  - docs/concerns_backlog.md
  - docs/design/INVARIANTS.md
---

TL;DR: has-concerns — 5 slices audited, 7 issues found (0 blockers, 5 concerns, 2 nits). The plan's boundary decision is sound and implementation-side risks are generally acknowledged. Four concerns require explicit design decisions before coding starts; two are minor but will cause confusion mid-slice if not pre-resolved.

## Audit Verdict

Overall: has-concerns

No blockers. The plan's strategy (semantic identity via `source_anchor_key` in JSON payloads, no schema migration) is coherent and correctly defers DATA_MODEL §3.3. The code verification confirms all stated invariant paths hold from LTO-1 stage 2. However, four concerns carry enough implementation ambiguity that Codex will have to make silent assumptions about inputs, cross-task lookup scope, relation id collision under evidence reuse, and excerpt sourcing — each assumption-point is a future regression source unless resolved now.

---

## Issues by Slice

### M1: Source-Anchor Identity Contract

**[CONCERN] C1 — `heading_path` field type inconsistency between source and storage**

`_internal_knowledge_store.py:432` stores `heading_path` as `str(anchor.get("heading_path", "")).strip()` — converting any list to its repr string before storing. Plan §M1 says "normalize `heading_path`" but does not specify whether the input is already a string or may arrive as a list from the Wiki Compiler source_pack. The `source_anchor_key` hash stability depends on the normalization being canonical. If the Wiki Compiler ever passes `heading_path` as a list (e.g., `["Section", "Subsection"]`), `str(...)` produces `"['Section', 'Subsection']"` which is not the same as the already-stored `"Section > Subsection"` string form.

The plan needs to explicitly specify: (a) what form `heading_path` arrives in for source-pack anchors, and (b) the canonical normalization before hashing — e.g., `" > ".join(path_list) if isinstance(heading_path, list) else str(heading_path)`. This is a small but hash-stability-critical decision.

**[CONCERN] C2 — Hash input field completeness is unspecified: all 5 fields vs. a subset**

Plan §M1 lists five normalization inputs: `source_ref`, `content_hash`, `parser_version`, `span`, `heading_path`. The acceptance criterion says "changing `content_hash`, `parser_version`, `span`, or `heading_path` changes the key." This implies only 4 of the 5 inputs are tested. It is not stated whether `source_ref` is included in the hash or is the primary discriminator with the others being additional dedup axes.

From `_source_pack_evidence_entry` (line 402–444 of `_internal_knowledge_store.py`): all 5 fields are stored in entry_json but none are currently hashed anywhere. If the implementer hashes only `source_ref + content_hash` and ignores `span` and `heading_path`, two anchors at different spans of the same file would collide. The plan must specify the exact field order and concatenation scheme before M1 implementation starts.

**[OK]** The `source_anchor_key` + `source_anchor_version` fields going into `entry_json` rather than a new schema column is architecturally confirmed as safe. The `knowledge_evidence` table PK is `(task_id, object_id)` with `entry_json TEXT NOT NULL` (`sqlite_store.py:39–48`). Adding JSON payload fields requires no DDL migration.

**[OK]** The Knowledge Plane facade already exposes `materialize_source_evidence_from_canonical_record` as the single entry point (`knowledge_plane.py:250–262`). Any new anchor helper added to `_internal_knowledge_store.py` should be re-exported through this facade per `CODE_ORGANIZATION.md`. The plan correctly identifies this path.

---

### M2: Governed Evidence Dedup On Promotion

**[CONCERN] C3 — Cross-task evidence lookup requires a cross-task query that the current store API does not provide; the plan does not specify which lookup approach to use**

Plan §M2 says `materialize_source_evidence_from_canonical_record` should "check existing task-scoped knowledge evidence entries across known task ids before creating a new evidence entry."

Verification of current code:

- `knowledge_evidence` PK is `(task_id, object_id)` (`sqlite_store.py:47`). The only indexed lookup for `object_id` is `knowledge_object_exists(base_dir, object_id)` at line 670 and `knowledge_object_store_type(base_dir, object_id)` at line 698 — both do `SELECT 1 FROM knowledge_evidence WHERE object_id = ? LIMIT 1` without a `task_id` filter. This already crosses tasks.
- There is no `idx_knowledge_evidence_object_id` standalone index. The existing index is `idx_knowledge_evidence_task_id ON knowledge_evidence(task_id, sort_order)` (line 62). A `WHERE object_id = ?` lookup with no task_id filter will table-scan `knowledge_evidence`.
- `iter_knowledge_task_ids()` at line 646 does `SELECT DISTINCT task_id FROM knowledge_evidence` — also a full-table read.

The plan does not say: use `knowledge_object_exists()` as-is (cross-task scan), or add an `object_id`-only index, or use in-memory dedup within a single promotion call. For a project at near-zero evidence count today, any of these works. But the plan should pick one explicitly because:

(a) the `upsert_knowledge_relation` call in `_persist_source_evidence_relations` (`truth/knowledge.py:148`) calls `_validated_relation_payload` which calls `knowledge_object_store_type()` — a cross-task scan — to validate that the target is an evidence object. If the new evidence id `evidence-src-<key>` is not yet in the store when the relation is created, this guard will fail with `"derived_from relation target must be an evidence object."` (_internal_knowledge_relations.py:107–109).

This is a sequencing blocker within M2 itself: evidence must be written and committed to the SQLite store **before** the relation is created, otherwise `knowledge_object_store_type()` returns `""` and the guard raises. The current `_promote_canonical` in `truth/knowledge.py:55–112` does write evidence first (line 55–65) then create relations (line 102–112), so the sequencing is already correct for the same-task case. The question is whether the cross-task evidence reuse path maintains this ordering — i.e., if candidate B reuses an evidence object first created by candidate A, the reuse lookup must confirm the object is already in SQLite before skipping the write, and the relation creation will still pass the type guard.

This is implementable but the plan should explicitly state: "lookup uses `knowledge_object_exists()` which cross-scans the store by `object_id`; if found, skip write and proceed to relation creation."

**[CONCERN] C4 — Relation id collision under evidence reuse across candidates**

Current `_persist_source_evidence_relations` (`truth/knowledge.py:147`) generates:

```
relation_id = f"relation-derived-from-{_safe_id_token(candidate_id)}-{index}"
```

Where `index` is the position within `source_evidence_ids`. The plan says relation ids become "deterministic on `(source wiki/canonical id, evidence id)`." But the current relation id is based on `candidate_id + index`, not on `(wiki_id, evidence_id)`.

Under M2, two different candidates (candidate-A and candidate-B) that both promote to wiki entries and both reference the same source anchor will both try to create a relation to the same evidence id. If they use `upsert_knowledge_relation`, the id `relation-derived-from-<candidate-A>-1` and `relation-derived-from-<candidate-B>-1` are different ids pointing to the same `(wiki-A, evidence-src-X)` and `(wiki-B, evidence-src-X)` edges — which is semantically correct (two different wikis both derived_from the same evidence). This is fine.

However the plan says "relation id becomes deterministic on `(source wiki/canonical id, evidence id)`" — this means the relation id should be a function of `(wiki_id, evidence_id)`, not `(candidate_id, index)`. These are different things. The current scheme is already deterministic per `(candidate_id, index)` and is idempotent under `upsert`. The plan's phrasing implies a change to use `(wiki_id, evidence_id)` as the id basis. If implemented as described, this would generate ids like `relation-derived-from-<wiki_id_token>-<evidence_id_token>`. The plan needs to confirm which form is intended and whether the current `(candidate_id, index)` scheme is simply renamed or structurally changed.

**[NIT] N1 — Backfill strategy for existing `evidence-<candidate>-<index>` ids is unspecified but low-risk at current scale**

The plan §Non-Goals does not mention any backfill of existing evidence ids. LTO-1 stage 2 already wrote evidence entries with ids like `evidence-{candidate_id}-{index}` (`_internal_knowledge_store.py:416`). LTO-2 will write new entries with `evidence-src-<key>`. Two things follow:

- Existing `evidence-<candidate>-<index>` rows remain in the store and continue to be valid targets for existing `derived_from` relations. This is fine — they are not invalidated.
- The cross-task lookup by `object_id` will find both old-style and new-style evidence ids. If a newly promoted candidate's anchor matches an old-style evidence object's `source_anchor_key`, the lookup would need to compare anchor fields within `entry_json` rather than just compare `object_id` strings. The plan does not clarify how the lookup finds an existing evidence match: by new `object_id` form only (miss legacy entries), or by scanning `entry_json` for matching anchor fields (correct but more expensive).

Given the project is at near-zero real evidence count, this is a nit rather than a concern — but Codex should acknowledge the approach in M2 implementation.

---

### M3: Retrieval / EvidencePack Dedup

**[OK]** `build_evidence_pack` in `evidence_pack.py:66–99` iterates `retrieval_items` and builds lists in a single pass. The shape of `EvidencePack` (dataclass with five lists plus `to_dict()`) is stable. Adding dedup by `source_anchor_key` during iteration is a clean additive change with no structural break.

**[OK]** The acceptance criterion "old tests using `RetrievalItem.to_dict()` still pass" is testable. `EvidencePack.to_dict()` (line 52–54) produces a dict from `asdict(self)` plus source_pointers; adding dedup fields as new keys is additive and will not break callers that iterate existing keys.

**[CONCERN] C5 — `source_anchor_key` is not on `RetrievalItem` or its metadata today; dedup in `build_evidence_pack` must either pull from metadata or retrieve from store**

The current `_evidence_entry` builder (`evidence_pack.py:102–116`) reads `canonical_id`, `knowledge_object_id`, `evidence_status`, `source_ref`, `artifact_ref` from `item.metadata`. It does not read `source_anchor_key`. The dedup in M3 would need `source_anchor_key` in `item.metadata` to group entries. There are two paths to get it there:

(a) The retrieval pipeline (`retrieval.py`) enriches `RetrievalItem.metadata` with `source_anchor_key` from the stored `entry_json` when loading evidence entries from `knowledge_evidence`.
(b) `build_evidence_pack` receives `base_dir` and does a secondary lookup per item to fetch `entry_json` and extract `source_anchor_key`.

Path (a) is cleaner and consistent with how `canonical_id`, `evidence_status`, etc. are already in metadata. Path (b) adds per-item store round-trips. The plan says dedup happens "by `source_anchor_key`" but does not specify which path populates the key in `RetrievalItem.metadata`. This should be resolved before M3 starts to avoid a mid-implementation pivot.

---

### M4: Operator Report Quality

**[OK]** `task_report.py` already calls `build_evidence_pack` and `build_source_grounding` through the Knowledge Plane facade (lines 5–12 of `task_report.py`). The `ADAPTER_DISCIPLINE` concern about orchestration-layer report assembly is already respected — `task_report.py` renders a string from results returned by the facade; it does not call any `_internal_*` module directly. M4 additions (anchor key, dedup count, bounded excerpt) extend the same pattern.

**[NIT] N2 — Bounded excerpt sourcing: three competing preview constants already exist; M4 must pick one or add a fourth**

The codebase has three different preview/excerpt length caps:
- `wiki_compiler.py:38` `PREVIEW_LIMIT = 320` (WikiCompilerSourceAnchor output)
- `_internal_knowledge_store.py:19` `SOURCE_EVIDENCE_PREVIEW_LIMIT = 1000` (evidence entry preview stored in entry_json)
- `retrieval_config.py:8` `RETRIEVAL_PREVIEW_LIMIT = 220` (retrieval item preview in display)

Plan §M4 says "bounded excerpts must be capped" and §M4 acceptance says excerpts come from "raw source resolution." The WikiCompilerSourceAnchor already produces a `preview` field capped at 320 chars (wiki_compiler.py:216–218), which `_source_pack_evidence_entry` stores in `entry_json["preview"]` (`_internal_knowledge_store.py:412–443`). If M4 reads `entry_json["preview"]` this is already bounded by 320. If M4 attempts fresh resolution from the raw material store, it needs its own cap constant.

The plan should state explicitly whether M4 excerpts reuse the stored `entry_json["preview"]` (320-char limit already applied by WikiCompiler) or perform fresh resolution with a new cap. Reuse is far simpler and avoids a new raw_material read path; fresh resolution provides dynamic content but is more complex. Either is fine, but the choice determines which of `grounding.py` or `task_report.py` needs to change and by how much.

---

### M5: Eval, Guards, Closeout Prep

**[OK]** The eval design is deterministic — local fixtures only, `@pytest.mark.eval` deselected by default, no live endpoints. LTO-1 stage 2 set the pattern with `test_wiki_compiler_second_stage_quality.py` (8 passed); the new `test_lto2_retrieval_quality.py` follows the same structure.

**[OK]** The optional guard (evidence id remains source-anchor-key based) is appropriate for M5 position — it guards the output of M1+M2 after the fact rather than constraining M1 design mid-implementation.

---

## Questions for Codex / Human

1. **C1: `heading_path` type** — Does the source_pack anchor always deliver `heading_path` as a string by the time it reaches `materialize_source_evidence_from_canonical_record`? If it can arrive as a list, what is the canonical join separator for hashing? This must be fixed in M1 before the hash function is written.

2. **C2: Hash input spec** — What are the exact fields and concatenation order used to compute `source_anchor_key`? Is `source_ref` part of the hash or does it serve as a partition prefix? Recommend explicit spec like: `sha256("|".join([source_ref, content_hash, parser_version, span, heading_path_normalized]))[:16]`.

3. **C3: Cross-task lookup mechanism** — Confirm that M2 will use `knowledge_object_exists(base_dir, new_evidence_id)` (which does `WHERE object_id = ? LIMIT 1` across all tasks) to check for an existing evidence entry before writing, and that this is sufficient without an additional `object_id`-only index. Also confirm: the deterministic `evidence-src-<key>` id is computed first, then existence is checked by that id, so the lookup does not need to scan `entry_json`.

4. **C4: Relation id scheme** — Is the intent to change the relation id from `relation-derived-from-<candidate_id>-<index>` to `relation-derived-from-<wiki_id_token>-<evidence_key_token>`, or to keep the current per-candidate id and rely on `upsert` idempotency? The plan says "deterministic on `(source wiki/canonical id, evidence id)`" — this implies a schema change to the id string, not just upsert behavior. Clarify before M2.

5. **C5: `source_anchor_key` propagation path** — Will `source_anchor_key` be loaded into `RetrievalItem.metadata` by the retrieval pipeline (path A: preferred), or will `build_evidence_pack` receive `base_dir` and perform per-item lookups (path B)? This decision determines which file changes are needed for M3.

6. **N2: Excerpt source** — Does M4 reuse `entry_json["preview"]` (already bounded at 320 by `wiki_compiler.py PREVIEW_LIMIT`) or attempt fresh raw material resolution? If fresh resolution, what is the cap and where does the new constant live?

---

## Confirmed Ready

- **M1 scope and location**: adding a deterministic hash helper to `_internal_knowledge_store.py` and re-exporting via `knowledge_plane.py` is fully clear and implementable once C1 and C2 are resolved.
- **M2 apply-path ownership**: `_promote_canonical` in `truth/knowledge.py` is the correct and already-confirmed site for evidence dedup. INVARIANTS §0 fourth rule is respected. Evidence write precedes relation creation in the existing flow; M2 extends this correctly.
- **M2 `derived_from` type guard interaction**: the `knowledge_object_store_type()` cross-task lookup (`sqlite_store.py:698`) will correctly validate new `evidence-src-<key>` ids as type `"evidence"` provided evidence is written to SQLite before the relation is created — which the current `_promote_canonical` ordering already ensures.
- **M3 EvidencePack structural compatibility**: additive changes to `build_evidence_pack` will not break existing `to_dict()` callers.
- **M4 task_report.py layer ownership**: confirmed that `task_report.py` calls Knowledge Plane facade only, not `_internal_*` modules. M4 additions follow the same pattern with no layer violation.
- **M5 eval pattern**: follows established `tests/eval/` discipline from LTO-1 stage 2.
- **INVARIANTS §0 fourth rule**: `apply_proposal` ownership is fully intact through `_promote_canonical`. No plan action touches this boundary.
- **LTO-1 stage 2 review C1 decision matrix**: confirmed documented in `docs/plans/lto-1-wiki-compiler-second-stage/closeout.md:81–88`. `derived_from` layer attribution (governance apply path) is the established decision; LTO-2 M2 extends evidence id scheme within that same path without changing layer ownership.
- **Boundary Decision (no DATA_MODEL §3.3 migration)**: confirmed technically correct. `knowledge_evidence` PK `(task_id, object_id)` with `entry_json` is sufficient to store `source_anchor_key` as a JSON payload field. No DDL change required.
