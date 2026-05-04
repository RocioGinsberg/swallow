---
author: claude
phase: lto-1-wiki-compiler-second-stage
slice: plan-audit
status: draft
depends_on:
  - docs/plans/lto-1-wiki-compiler-second-stage/plan.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
  - src/swallow/truth_governance/apply_canonical.py
  - src/swallow/truth_governance/proposal_registry.py
  - src/swallow/truth_governance/truth/knowledge.py
  - src/swallow/truth_governance/store.py
  - src/swallow/knowledge_retrieval/_internal_knowledge_store.py
  - src/swallow/knowledge_retrieval/_internal_staged_knowledge.py
  - src/swallow/knowledge_retrieval/_internal_knowledge_relations.py
  - src/swallow/application/commands/knowledge.py
  - src/swallow/application/commands/wiki.py
  - docs/plans/lto-1-wiki-compiler-first-stage/closeout.md
---

TL;DR: has-blockers — 5 slices audited, 3 blockers, 5 concerns, 2 nits found.

## Audit Verdict

Overall: has-blockers

Three blockers require a plan fix before implementation begins. Two are specific enough that the fix is a one-sentence plan clarification; the third (M2 evidence write boundary) needs Codex to record the explicit decision about which path governs evidence writes and verify it does not conflict with INVARIANTS §0 rule 4.

---

## Issues by Slice

### M1: Governed Supersede Apply

- [BLOCKER] **`_CanonicalProposal` dataclass has no `supersede_target_ids` field; `_promote_canonical` has no target-id flip code path.**

  The plan states: "If implementation needs to extend the in-memory canonical proposal dataclass to include `supersede_target_ids`, keep `apply_proposal(proposal_id, operator_token, target)` unchanged."

  After reading the actual code:
  - `proposal_registry.py` lines 13–21: `_CanonicalProposal` fields are `base_dir`, `canonical_record`, `write_authority`, `mirror_files`, `persist_wiki`, `persist_wiki_first`, `refresh_derived`. No `supersede_target_ids`.
  - `truth/knowledge.py` lines 15–58: `KnowledgeRepo._promote_canonical` calls `append_canonical_record` then optionally `persist_wiki_entry_from_canonical_record`. It has no loop over `supersede_target_ids` and no call to flip any old record's `canonical_status`.
  - `store.py` lines 530–561: `append_canonical_record` does same-key supersede (when a new record shares `canonical_key` with an active old record). It does not do target-id-driven supersede — that logic does not exist anywhere in the store.

  The plan says this behavior "must happen in `KnowledgeRepo._promote_canonical` / store code reached by `apply_proposal`". That is the correct constraint — but neither the dataclass extension nor the flip path has been written. The plan correctly identifies this as new work, but does not specify:
  - Whether `supersede_target_ids` goes into `_CanonicalProposal` (in-memory, cleared after apply) or into `canonical_record` dict (persisted in the JSONL registry for audit).
  - Whether `append_canonical_record` gains a new conditional branch for target-id lookup, or whether `_promote_canonical` calls a new `_flip_supersede_target` helper before or after the `append_canonical_record` call.

  Both choices are architecturally valid, but the plan must name one. Leaving this open means Codex must make a silent structural assumption at the most sensitive write boundary in the system.

  Fix needed: plan §M1 Contract must say explicitly where `supersede_target_ids` lives (proposal dataclass field vs `canonical_record` dict key) and which function gains the flip logic (`_promote_canonical` pre-append, or `append_canonical_record` new branch).

- [CONCERN] **`build_stage_promote_preflight_notices` (knowledge.py lines 119–174) already detects same-key supersede and adds a `"notice_type": "supersede"` notice, but it does NOT detect target-id-driven supersede from `relation_metadata`.**

  The current preflight reads `canonical_records` from the registry and looks for `canonical_key` collisions. A `supersedes(<target_id>)` in `relation_metadata` with a different canonical key will not generate a supersede notice. Plan §M1 Operator confirmation section implies the preflight must be extended to also scan `relation_metadata` for `relation_type == "supersedes"` entries and emit a corresponding notice. This needs to be spelled out — the existing code path will silently bypass the confirmation gate for target-id supersede candidates.

- [CONCERN] **CLI `--force` bypass skips the new `supersede` notice type at the same code point that will gate target-id supersede.**

  `promote_stage_candidate_command` (knowledge.py lines 177–214): `force=True` skips the preflight raise. Plan §M1 says "CLI may keep `--force`". This is acceptable as a transition, but if target-id supersede adds a new `"supersede"` notice type for `relation_metadata` entries, the force flag will also bypass that notice. The plan should state this explicitly to prevent a reviewer from flagging it as an oversight during PR review.

### M2: Derived-From Evidence Objectization

- [BLOCKER] **The `know_evidence` table from DATA_MODEL §3.3 does not exist in the running schema. The actual SQLite store has `knowledge_evidence` (a task-scoped key-value store for `_internal_knowledge_store.py` entries) and `knowledge_wiki` — neither matches the DATA_MODEL §3.3 standalone `know_evidence` table with `evidence_id` PK, `source_pointer` JSON, etc.**

  DATA_MODEL §3.3 defines:
  ```sql
  CREATE TABLE know_evidence (
      evidence_id TEXT PRIMARY KEY,
      content TEXT NOT NULL,
      source_pointer JSON,
      created_at TEXT NOT NULL,
      created_by TEXT NOT NULL DEFAULT 'local'
  )
  ```

  The running `sqlite_store.py` (lines 39–60) has `knowledge_evidence (task_id, object_id, sort_order, entry_json, stage, updated_at, embedding_blob)` — a different schema serving a different purpose.

  The plan says at §Implementation Decisions #11: "No new public design docs by default... If implementation discovers schema or invariant gaps, stop and revise plan." This gap is pre-implementation. The M2 evidence object ID and `source_pointer` fields assumed by the plan (`evidence-<candidate_id>-<index>`, `parser_version`, `content_hash`, `span`, `heading_path`) map to the `know_evidence.source_pointer` JSON from DATA_MODEL §3.3 — but that table is not yet created in `sqlite_store.py` and has no schema migration entry.

  Fix needed: plan §M2 must name the target table explicitly and state whether this phase creates `know_evidence` as a new table (requiring a schema migration entry per DATA_MODEL §8) or whether evidence objects are stored in the existing `knowledge_evidence` task-scoped table (requiring a schema clarification about whether standalone evidence objects with global `evidence_id` PKs are scoped to a task or not).

  This is a blocker because the entire M2 implementation path — the helper that builds and persists evidence objects, the `source_evidence_ids` update, the `derived_from` relation row — depends on which physical table is the target.

- [BLOCKER] **Evidence write boundary is not declared relative to INVARIANTS §0 rule 4.**

  INVARIANTS §0 rule 4: "canonical knowledge / route metadata / policy 三类对象的写入只有这一个函数入口 (`apply_proposal`)"

  Evidence is not listed in that three-type enumeration. The first-stage closeout confirms: `refresh_wiki_evidence_command` writes evidence via `persist_task_knowledge_view` directly (wiki.py line 139), bypassing `apply_proposal`. This is established behavior.

  Plan §M2 Contract says "Persist evidence through Knowledge Plane/store helper, not by adapter code" — this correctly prevents adapter-side writes, but it does not state whether the evidence persistence helper is called from within `apply_proposal` (inside `_promote_canonical`) or from the application command layer after `apply_proposal` returns.

  These two choices have different invariant implications:
  - Inside `apply_proposal`: evidence writes become atomic with canonical promotion; `_promote_canonical` gains a new truth-write side effect that is not currently governed by its call signature or return value.
  - After `apply_proposal` in the application command: evidence writes are a separate application-layer step; this matches the first-stage pattern for `_create_promoted_relation_records`, but means evidence objectization is not inside the governance boundary.

  The plan must explicitly record this choice and confirm it does not violate the spirit of INVARIANTS §0 rule 4 (even if evidence is not one of the three named types, it is still truth). This is a blocker because it directly shapes which module gains the new write call and whether the existing `test_only_apply_proposal_calls_private_writers` guard needs updating.

- [CONCERN] **Idempotency key for evidence objects is underspecified relative to the promote-once assumption.**

  Plan §Implementation Decisions #8: "stable evidence object id, e.g. `evidence-<candidate_id>-<index>`"

  The candidate_id is stable across re-runs only if the staged candidate is not re-created. Plan §M2 idempotency requirement says "Re-running promote for the same already-decided candidate must not duplicate evidence or relation rows." But `promote_stage_candidate_command` already raises `ValueError` when `candidate.status != "pending"` (knowledge.py line 187). So the only way to hit re-promote is if the guard is bypassed or a test re-stages the same candidate.

  This means the idempotency requirement as written in the plan is vacuously satisfied by the existing guard — unless the intent is that Operator restaging (creating a new candidate with the same source material) should reuse the same evidence object. The plan needs to clarify whether idempotency is per-candidate-id (easy, vacuous) or per-source-anchor (hard, requires content-hash dedup logic).

- [CONCERN] **`KNOWLEDGE_RELATION_TYPES` in `_internal_knowledge_relations.py` line 11 does not include `"supersedes"` or `"derived_from"` — only `("refines", "contradicts", "cites", "extends", "related_to")`.**

  Plan §M2 Contract step 4: "Persist a `derived_from` relation only from promoted wiki/canonical object id to evidence object id."

  The `create_knowledge_relation` function (lines 19–60 of `_internal_knowledge_relations.py`) validates `relation_type` against `KNOWLEDGE_RELATION_TYPES` and raises `ValueError` for unknown types. The plan requires persisting `derived_from` relation rows but the relation type enum does not include it.

  This means either: (a) `KNOWLEDGE_RELATION_TYPES` must be extended with `"derived_from"` (and possibly `"supersedes"`) before the `create_knowledge_relation` call can succeed, or (b) M2 uses a different persistence path that bypasses the type check.

  Option (a) requires updating a data model constant that has downstream effects on the relation adjacency display in queries. This is implementable but must be explicitly called out in the plan — it is not currently mentioned.

### M3: Web Wiki Compiler Fire-and-Poll API

- [CONCERN] **Job persistence storage path is unresolved; plan §Implementation Decisions #5 offers two options ("task artifacts or a task-scoped application job store") without naming the chosen one.**

  The plan says "In-memory-only job state is not acceptable as the sole status source." The two proposed options:
  - Task artifact files: path pattern not specified. Presumably `.swl/artifacts/<task_id>/wiki_jobs/<job_id>.json` or similar. Wiki Compiler already writes prompt/result artifacts; job state as another artifact is consistent with the propose-only boundary.
  - A new application job store: a new module (`application/services/wiki_jobs.py` is mentioned in the milestone table); if this writes to SQLite, it requires a new table and a schema migration entry per DATA_MODEL §8.

  The plan cannot leave this open for implementation to decide. FastAPI `BackgroundTasks` requires the job state to survive at least until the poll request arrives (seconds to minutes, not cross-restart). If the job state is in-process memory only (the exact pattern `asyncio.create_task` would produce), a server restart drops all running jobs with no way for the client to know — yet §5 forbids "in-memory-only job state as the sole status source."

  Fix needed: plan §M3 must commit to one storage mechanism and name the file path pattern or the new SQLite table name. If a new table, plan must flag it as requiring a schema migration.

- [NIT] **Plan §Implementation Decisions #3 refers to "FastAPI background task or an equivalent framework primitive" without ruling out `asyncio.create_task`.**

  `asyncio.create_task` is process-bound and does not survive worker restart (same problem as in-memory state). FastAPI `BackgroundTasks` is slightly better (it runs after response send) but also process-bound. The plan should say "best-effort in-process background execution; server restart may drop in-flight jobs" rather than implying durable job semantics. This avoids an implementer interpreting the fire-and-poll contract as requiring durable job guarantees from a single-process server.

### M4: Web Authoring and Review UX

- [OK] — No issues. M4 is bounded to `static/index.html` extension, uses the existing static HTML/JS model, and has no new architecture risk given the M3 API contract is resolved.

### M5: Guards, Eval, Closeout Prep

- [CONCERN] **Guard #1 (M5 §1) missing `application.services.wiki_compiler` from the forbidden import list.**

  The guard checks that the HTTP adapter does not import `provider_router.agent_llm`, `WikiCompilerAgent`, `apply_proposal`, `append_canonical_record`, or knowledge internals. If the fire-and-poll job runner calls `application.services.wiki_compiler` directly from the HTTP route handler (rather than through an application command), the compile call is still inline — it just moves one layer down. The guard should also forbid the HTTP adapter from importing `application.services.wiki_compiler` directly. The application boundary for Web callers is `application/commands/wiki.py` or `application/services/wiki_jobs.py` (whichever M3 defines), not the wiki_compiler service module itself.

- [NIT] **M5 eval section says "Extend `tests/eval/test_wiki_compiler_quality.py` or add a second eval file."** The first-stage closeout shows the existing eval file tests `draft`, `refine`, source_pack anchors, and relation metadata modes. The new checks (supersede target-id, evidence object count from source_pack, Web/job payload shape) are structurally different enough that a second file is cleaner — extending the existing file risks coupling the deterministic source_pack/mode checks with job/evidence checks that need different fixtures. Plan should say "add a second eval file" rather than "or".

---

## Questions for Codex / Human

1. **M1**: Where does `supersede_target_ids` live — as a new field on `_CanonicalProposal` (cleared after apply) or as a key in `canonical_record` dict (written to the JSONL registry)? And which function gains the flip branch: `append_canonical_record` (a new target-id conditional alongside the existing same-key conditional) or a new helper called from `_promote_canonical` before/after `append_canonical_record`?

2. **M2 storage**: Is `know_evidence` from DATA_MODEL §3.3 the target table for evidence objects, or does M2 store evidence objects in the existing `knowledge_evidence` task-scoped table? If it is `know_evidence`, does this phase create it (schema migration required per DATA_MODEL §8)?

3. **M2 write boundary**: Is evidence objectization called from inside `_promote_canonical` (atomic with canonical apply) or from the application command layer after `apply_proposal` returns (matching the first-stage `_create_promoted_relation_records` pattern)? Plan must record this to prevent the existing `test_only_apply_proposal_calls_private_writers` guard from flagging the new writes.

4. **M2 relation type**: Does this phase extend `KNOWLEDGE_RELATION_TYPES` in `_internal_knowledge_relations.py` to include `"derived_from"` (and possibly `"supersedes"`)? If yes, what are the downstream effects on the relation adjacency display and on `test_knowledge_relation_metadata_types_cover_design_modes` guard?

5. **M3 job storage**: Does the fire-and-poll job state write to task artifact files (path pattern?) or a new SQLite table (name + migration slug)? The answer determines whether `wiki_jobs.py` is a facade over the existing artifact writer or a new store module.

6. **M2 idempotency scope**: Is the "no duplicate evidence rows" guarantee per `candidate_id` (satisfied by existing promote-once guard) or per source anchor (requires content-hash dedup across multiple candidates citing the same source file)?

---

## Confirmed Ready

- **M4 Web Authoring and Review UX** — no issues; properly bounded to static HTML extension, clear inputs from M3, no new architecture.
- **Deferred item coverage** — all five items from the first-stage closeout §Deferred Follow-Ups are covered: Web draft/refine/refresh triggers (M3/M4), fire-and-poll runner (M3), target-id supersede flip (M1), persisted `derived_from` relation rows backed by evidence objects (M2), staged-knowledge force Web UX replacement with structured confirmation (M1). Coverage is complete.
- **INVARIANTS §0 rule 4 compliance intent** — M1 correctly routes target-id supersede through `apply_proposal`; the approach is sound. The blocker is only the missing implementation specificity.
- **propose-only boundary** — M3/M4/M5 design correctly keeps Wiki Compiler as propose-only; fire-and-poll job only wraps the existing compile path.
- **CLI sync / Web fire-and-poll asymmetry** — plan §Implementation Decisions #2 makes this explicit enough; CLI staying synchronous is correct and no guard is needed for it.
- **Path C LLM penetration** — fire-and-poll wrapper calls `WikiCompilerAgent.compile()` which already routes through Provider Router; no INVARIANTS §4 concern.
