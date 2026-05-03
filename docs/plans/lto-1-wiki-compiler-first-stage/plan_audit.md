---
author: claude
phase: lto-1-wiki-compiler-first-stage
slice: plan-audit
status: draft
depends_on: ["docs/plans/lto-1-wiki-compiler-first-stage/plan.md"]
---

TL;DR: has-concerns — 5 slices audited, 7 issues found (0 blockers / 5 concerns / 2 nits)

## Audit Verdict

Overall: has-concerns

The plan is implementable in its current form; M1 through M5 can proceed. No slice has a design gap that requires a plan rewrite before coding starts. However three concerns carry real implementation risk that Codex should resolve or explicitly commit to an assumption before writing the relevant code: (1) the `StagedCandidate` uses `dataclass(slots=True)`, which means extending it requires a non-trivial migration step; (2) the promotion interaction for `refines` and `supersedes` is silent about whether `promote_stage_candidate_command` will create the knowledge relation or not — the current code path does not; (3) `derived_from` relation targets in `draft` mode are raw-material `source_ref` URIs, not knowledge object ids, but `create_knowledge_relation` validates both ends against `resolve_knowledge_object_id`, which will fail for `file://...` refs. These three concerns interact: the implementer must decide which layer handles relation creation on promotion and what `derived_from` actually points to before committing M1.

---

## Issues by Slice

### Slice M1: Wiki Compiler 起草核心

- [CONCERN] **`StagedCandidate` uses `dataclass(slots=True)` — adding 6 new fields is not a simple attribute append.** `slots=True` freezes the slot layout at class definition time. Adding new fields with defaults is syntactically valid in Python 3.10+ slotted dataclasses, but `from_dict` (`_internal_staged_knowledge.py:69`) uses explicit keyword arguments, so old on-disk records that lack the new keys will map to the default values correctly. The concern is the `update_staged_candidate` function (`_internal_staged_knowledge.py:116-156`): it reconstructs a `StagedCandidate` with every field listed by name. If 6 new fields are added but `update_staged_candidate` is not updated to pass them through, they will silently be zeroed on any status update (promote/reject). The plan §Staged candidate extension says "existing staged registry records must still load" but does not name `update_staged_candidate` as a required touch point. Codex must update that function — or the compiler metadata is stripped the moment an Operator tries to promote the candidate.

- [CONCERN] **Promotion path does not create knowledge relations — plan §Promotion Interaction calls for it, but the code path has no hook.** `promote_stage_candidate_command` (`application/commands/knowledge.py:162`) calls `register_canonical_proposal` + `apply_proposal`, which in turn calls `KnowledgeRepo._promote_canonical` (`truth_governance/truth/knowledge.py:16`). None of these functions are aware of `relation_metadata`. For `refines` mode the plan says "after Operator promote and `apply_proposal`, create `refines` relation between new wiki object and target." There is no such call in the current path, and the plan does not specify which layer adds it. Two implementation paths exist: (a) `promote_stage_candidate_command` reads `candidate.relation_metadata` after successful promotion and calls `create_knowledge_relation`, or (b) the caller (CLI command) does it. Path (a) is correct per boundary rules (application layer orchestrates post-promotion side-effects) but is not mentioned in the plan. Path (b) would leak relation creation into the adapter layer. The plan must commit to one path before M1 code is written, or the `refines` relation will silently never be created. For `supersedes`, the question is more complex: the current `_promote_canonical` has no mechanism to set `canonical_status = "superseded"` on the old wiki entry — the plan acknowledges this ambiguity but defers it to "see during implementation." This is acceptable as a deferred decision only if the plan explicitly states that `supersede` promotion is out of scope for M1 (staged candidate with `supersedes` relation metadata may be promoted but the old wiki's status will not be updated until the supersede path is added). Currently the plan implies both paths will work at M1.

- [CONCERN] **`derived_from` relation type in `draft` mode points to `source_ref` URIs, not knowledge object ids — the existing `create_knowledge_relation` guard will reject this.** The plan §Specialist output contract shows `relation_metadata = [{"relation_type": "derived_from", "target_object_id": "artifact-or-evidence-id"}]`. In `draft` mode the relevant sources are raw-material `source_ref` URIs (e.g. `file://workspace/notes/foo.md` or `artifact://task-abc/result.json`). `create_knowledge_relation` (`_internal_knowledge_relations.py:19-63`) calls `resolve_knowledge_object_id` on both `source_object_id` and `target_object_id`. If the target is a `source_ref` URI and not a knowledge object id registered in the canonical/wiki/staged registry, `resolve_knowledge_object_id` will raise. Either: (a) `derived_from` in `draft` mode is stored only in `relation_metadata` on the staged candidate and is never written to the knowledge relations table (just metadata-on-staged), or (b) Wiki Compiler creates a new evidence object that it then uses as the `target_object_id`, or (c) `create_knowledge_relation` is extended to accept non-knowledge targets. The plan does not specify which path is chosen. This must be resolved before M1 or the guard test #4 (`test_knowledge_relation_types_cover_design_modes`) will require the enum to include `derived_from` while the enforcement path is broken.

- [CONCERN] **Relation type enum must be extended in M3 but is only mentioned in §Current Code Baseline — it is not listed as an M1 or M3 sub-task with acceptance criteria.** The current `KNOWLEDGE_RELATION_TYPES` tuple (`_internal_knowledge_relations.py:11-17`) contains `("refines", "contradicts", "cites", "extends", "related_to")`. The new types `supersedes`, `refers_to`, `derived_from` are completely absent from the codebase. Plan §Current Code Baseline acknowledges this but puts the fix in M3. The problem: `relation_metadata` written into staged candidates by the M1 compiler will contain `"relation_type": "supersedes"` or `"derived_from"`. If M1 relation metadata is stored as opaque `list[dict]` in the staged candidate and never validated against the enum during staging (only during actual relation creation), then M3 ordering is fine. But if M1 acceptance tests verify that the `refines` metadata triggers actual relation creation on promotion (as plan §Promotion Interaction implies), then the enum must be extended in M1. The plan is ambiguous on this cross-milestone dependency. Recommendation: explicitly state in the plan that `relation_metadata` in staged candidates is stored as raw dict data and enum validation only occurs when actual `create_knowledge_relation` calls are made (deferred to when the Operator promotes and post-promotion relation creation is added).

- [CONCERN] **`source_pack` schema in §M1 Specialist Output Contract says "with content anchors" but never pins the field names.** Plan §Implementation Decisions #7 lists the fields as `source_ref / content_hash / parser_version / span / heading_path / preview`, but §M1 Staged candidate extension shows `source_pack: list[dict[str, object]] = []` without a schema reference. The M5 guard #2 tests that refresh-evidence writes `parser_version + content_hash + (span | heading_path)`. If `source_pack` field names are not pinned in the plan, the guard is testing a schema that Codex may implement differently. `evidence_pack.py` already has `SourcePointer` with `source_ref`, `resolved_ref`, `heading_path`, `line_start`, `line_end` fields but not `content_hash` or `parser_version`. A mismatch between `source_pack` fields and the existing `SourcePointer` convention will create a second parallel anchor schema. Recommended fix: plan should explicitly state that `source_pack` entries match `SourcePointer.to_dict()` extended with `content_hash` and `parser_version`, or name a new standalone schema.

- [NIT] **Plan §Validation Plan references `tests/test_specialist_agents.py` and `tests/test_executor_protocol.py` — these files exist at the repo root test level.** Both files already exist (`tests/test_specialist_agents.py`, `tests/test_executor_protocol.py`). The plan validation command runs them as-is. Codex must decide whether to add Wiki Compiler tests to these existing files or create new ones. The plan says "specialist unit tests; executor protocol tests" in §M1 Acceptance but doesn't say where they live. If tests go into the existing files, that is fine; if they go into new files, the validation command must be updated. This is a minor ambiguity.

- [NIT] **Wiki Compiler will emit new event kinds (at minimum a `knowledge.wiki_compiler_draft_started` or similar telemetry event) — plan does not address whether any new event kind must be added to the `HARNESS_HELPER_ALLOWED_EVENT_KINDS` allowlist.** `test_harness_helper_modules_only_emit_allowlisted_event_kinds` (`tests/test_invariant_guards.py:582`) scans `HARNESS_HELPER_EVENT_MODULES` — the set of modules that are allowed to emit events — and rejects any event kind not in the allowlist. The Wiki Compiler specialist module will likely not be in `HARNESS_HELPER_EVENT_MODULES` (which covers orchestration helpers, not specialists), so it probably will not be scanned by this guard. But plan §M5 Guard #1 forbids direct `append_event` calls from the Wiki Compiler module, meaning the compiler must emit events only via `knowledge_plane.submit_staged_knowledge` (which calls the underlying append internally). If this is the intent, the plan should make it explicit. If the Wiki Compiler is added to `EXECUTION_PLANE_FILES` in the invariant guard, the guard will check that it does not call `save_state`; that check already exists. No action needed unless the specialist calls `append_event` directly — in which case the guard structure must be updated.

---

### Slice M2: Knowledge browse 路由

- [OK] — no issues. Routes are read-only; they use `application/queries/knowledge.py` (does not yet exist — must be created) and Pydantic response envelopes. ADAPTER_DISCIPLINE §1/§2 alignment is maintained. Pagination is not specified (plan says `limit=<n>` query param), which is acceptable for the first pass at the expected data volume.

### Slice M3: Knowledge detail + relations 视图

- [OK] — No issues beyond the relation type enum concern logged under M1 (cross-slice dependency). The plan correctly identifies that the enum must be extended and groups new types under M3. The M3 relations response `legacy` bucket for `cites/extends/related_to` is a clean backward-compat pattern.

### Slice M4: Web UI Knowledge panel

- [OK] — No issues. ADAPTER_DISCIPLINE §2 §4 alignment is explicit; plan prohibits state machine in JS; no new frontend dependency; "no new frontend package, build step, or asset pipeline" directly echoes Non-Goals. M4 is deliberately the lightest milestone.

### Slice M5: Guard / Eval / Closeout prep

- [OK] — Guard #1, #2, #3, #4 are all testable with concrete AST/import scan patterns matching the existing guard infrastructure. The eval marker `eval` is registered in `pyproject.toml:40` and `tests/eval/` directory exists with existing eval files. The eval test at `tests/eval/test_wiki_compiler_quality.py` follows the same pattern. "Live API smoke is optional and must be marked separately" is consistent with existing `tests/eval/test_http_executor_eval.py` pattern.

---

## Questions for Codex / Human

1. **`update_staged_candidate` pass-through**: Will `update_staged_candidate` in `_internal_staged_knowledge.py` be updated to pass all 6 new fields through when reconstructing a `StagedCandidate` during status update? If yes, this should be added to M1 acceptance criteria. If the plan intends to leave `update_staged_candidate` unmodified and rely on re-reading the staged candidate from the registry after the update, the plan should say so.

2. **Promotion path — who creates the relation record?**: After an Operator calls `promote_stage_candidate_command` on a staged candidate produced by `refine --mode refines`, which layer calls `create_knowledge_relation`? Options: (a) `promote_stage_candidate_command` itself reads `candidate.relation_metadata` and fires relation creation, (b) the CLI command handler does it after receiving `StagePromoteCommandResult`, (c) this is explicitly deferred from M1 (candidate metadata is stored but not acted on until a future phase). The plan §Promotion Interaction leans toward (a) for `refines` but is silent for `supersedes`. A one-line commitment in the plan would prevent a mid-M1 design debate.

3. **`derived_from` target type**: Does `derived_from` in staged `relation_metadata` ever result in a row in the knowledge relations table, or is it metadata-only on the staged candidate? If it results in a relations-table row, what is the `target_object_id` — an evidence id, a canonical id, or a raw `source_ref`? `create_knowledge_relation` currently rejects non-knowledge-object ids.

4. **Supersede promotion scope in M1**: Does M1 commit to (a) completing the full supersede path — new wiki in, old wiki marked `superseded` — or (b) staging the candidate with `supersedes` relation metadata only, leaving the actual `canonical_status` flip to a future plan revision? If (b), the plan should say "supersede staging is supported; supersede apply is deferred," which is consistent with Non-Goals "不自动 supersede" but should still be explicit about what `apply_proposal` does with a supersede-flagged candidate.

5. **`source_pack` schema**: Should `source_pack` entries be explicitly based on `SourcePointer.to_dict()` from `evidence_pack.py` (already has `source_ref`, `heading_path`, `line_start/end`) plus `content_hash` and `parser_version` additions, or will the Wiki Compiler define a standalone schema? The choice affects whether M5 guard #2 can reuse existing evidence field validation logic.

---

## Confirmed Ready

- **M2** — Knowledge browse routes. Read-only, Pydantic envelope, application queries boundary. No ambiguity.
- **M3** — Knowledge detail + relations view. Enum extension path is clear; legacy bucket handles backward compat.
- **M4** — Web UI Knowledge panel. Scope is tightly bounded by Non-Goals; ADAPTER_DISCIPLINE alignment explicit.
- **M5** — Guards and eval. All four guards are concrete and testable. Eval marker and directory already exist.

M1 is implementable but Codex should resolve or record explicit assumptions for concerns #1 (update_staged_candidate passthrough), #2 (promotion relation creation layer), and #3 (derived_from target type) before writing the promotion interaction code.
