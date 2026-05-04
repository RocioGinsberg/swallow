---
author: claude
phase: lto-2-retrieval-source-scoping
slice: plan-audit
status: draft
depends_on:
  - docs/plans/lto-2-retrieval-source-scoping/plan.md
  - docs/design/INVARIANTS.md
  - docs/design/KNOWLEDGE.md
  - docs/design/ORCHESTRATION.md
  - docs/design/HARNESS.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/plans/r-entry-real-usage/findings.md
---

TL;DR: has-concerns — 4 slices audited, 0 blockers, 5 concerns, 2 nits found.

## Audit Verdict

Overall: has-concerns

The plan is well-scoped, INVARIANTS-aligned, and the causal chain from findings to milestones is clear. No blockers were found. Five concerns require explicit assumptions or pre-implementation clarifications before Codex starts each affected slice. Two nits are stylistic and do not impede progress.

---

## Issues by Slice

### Slice M1: Request Context Plumbing

- [CONCERN] `RetrievalRequest` uses `@dataclass(slots=True)`. Adding a new field `declared_document_paths` with a default value is forwards-compatible, but any call site that constructs `RetrievalRequest` positionally (rather than by keyword) will break silently on Python versions where slots ordering matters, or raise at runtime if the field is inserted before other positional fields. The plan does not mention that all construction sites must be keyword-only or that `build_retrieval_request` is the sole construction facade. In practice `build_retrieval_request` is the only factory used (confirmed by audit), but this should be stated explicitly so Codex does not add positional construction in new tests. **Assumption needed**: Codex should add the new field with a default of `()` at the end of the dataclass and confirm all `RetrievalRequest(...)` construction goes through `build_retrieval_request` — not add direct keyword construction elsewhere.

- [CONCERN] The plan says the field should be "populated from task `input_context['document_paths']`". In the codebase, `document_paths` in `input_context` is currently only consumed by `LiteratureSpecialistAgent`; it is not read by `build_task_retrieval_request` in `retrieval_flow.py`. The plan does not name the exact read site: `build_task_retrieval_request` is the place where `state.input_context` and `state.task_semantics` are already accessible and where the `RetrievalRequest` is assembled. If Codex reads `document_paths` from somewhere else (e.g., the CLI layer or `task_semantics`), it will add a second path inconsistent with the existing architecture. The plan should state that `build_task_retrieval_request` is the intended injection point.

- [READY] Non-goals around new source types, schema migration, and `apply_proposal` bypass are clearly respected in M1.

### Slice M2: Candidate Source Scoping

- [CONCERN] The plan proposes downgrading or excluding `src/*.egg-info/*` and "build/cache metadata" paths. Reviewing the existing `SOURCE_POLICY_NOISE_LABELS` set in `retrieval.py`, it currently covers `{"archive_note", "current_state", "observation_doc"}`. The label `"archive_note"` maps to paths under `docs/archive/` and `docs/archive_phases/`, but `src/*.egg-info/*` and generated build cache paths have no label and are not filtered today. This means M2 must touch `source_policy_label_for()` and possibly the `SOURCE_POLICY_NOISE_LABELS` set in `retrieval.py`. The plan's "Main Touch Points" for M2 lists `src/swallow/knowledge_retrieval/*` and "retrieval adapters/policy helpers" — this is correct but under-specified. `retrieval.py` at the `source_policy_label_for` and `SOURCE_POLICY_NOISE_LABELS` level needs to be named explicitly, because the guard test `test_harness_helper_modules_only_emit_allowlisted_event_kinds` statically checks these files and any new event kind added to `retrieval_flow.py` or `task_report.py` must be added to the allowlist in `test_invariant_guards.py`. The plan does not mention this coupling. **Assumption needed**: Codex must update the guard allowlist in `tests/test_invariant_guards.py` if any new event kind string or constant is introduced in the helper modules.

- [CONCERN] The score boost mechanism for declared docs ("strongly boosted") is mentioned in the Proposed Implementation Shape but M2's acceptance criterion is only "deterministic fixture where declared docs outrank generated/archive/code noise before rerank". Score boosts are inherently non-deterministic in magnitude relative to the lexical scoring pipeline. The plan states "If score boosts are used, they must appear in `score_breakdown`", but the acceptance criterion does not require a test that verifies `score_breakdown` contains the policy contribution. This means Codex could pass the acceptance test with an invisible mutation to sort order without surfacing the decision in metadata. **Assumption needed**: M2 acceptance should include at least one assertion that `score_breakdown` contains the declared-document priority key when a declared doc is boosted.

- [READY] The plan correctly avoids turning `document_paths` into a new `source_type` enum value, staying consistent with `KNOWLEDGE.md §3.1` and the anti-pattern "source_type 表示后端".

### Slice M3: Truth Reuse Visibility

- [NIT] The plan lists `src/swallow/orchestration/harness.py` as a "Main Touch Point" for M3 ("Truth Reuse Visibility"). Reviewing the code, `build_retrieval_report` is in `task_report.py` and is called from `harness.py` — but the actual report construction logic is entirely in `task_report.py`. If Codex treats `harness.py` as a required edit target it will unnecessarily widen scope. The canonical touch point for the new report sections is `task_report.py`; `harness.py` only wires the call.

- [READY] The proposed new report fields (`canonical_registry_status`, `task_knowledge_status`, skip reasons, counts) are read/report-only and do not touch Truth Plane writes. This is consistent with INVARIANTS §5 and the read-only constraint.

- [READY] The `task_report.py` module is already in `HARNESS_HELPER_EVENT_MODULES` in `test_invariant_guards.py`. As long as M3 adds no new `Event(...)` constructions or event kind strings in `task_report.py`, the guard test will not be triggered. The plan does not assert this explicitly, but the risk is low since report building does not emit events today.

### Slice M4: R-entry Regression Smoke

- [CONCERN] The plan specifies the eval fixture file as `tests/eval/test_lto2_retrieval_source_scoping.py`, which does not yet exist (confirmed: only `test_lto2_retrieval_quality.py` is present). According to `TEST_ARCHITECTURE.md §7`, eval tests must be marked with `pytest.mark.eval` and deselected by default. The plan's focused test command for this file is `pytest tests/eval/test_lto2_retrieval_source_scoping.py -q` — without `-m eval` this would fail the "deselected by default" rule if the marker is missing, or pass but miss the intent if the marker is present. The plan should confirm that this file will carry `@pytest.mark.eval` and that its inclusion in the default suite is explicitly gated. **Assumption needed**: Codex must mark the eval fixture with `pytest.mark.eval` and the final gate should use `pytest -m eval` not the bare module path in CI/gating contexts.

- [NIT] M4's commit gate description says "possibly `docs/plans/lto-2-retrieval-source-scoping/closeout.md` later". The plan's own "Review And Branch Flow" states closeout is produced after review concerns are handled. Adding `closeout.md` as a possible M4 artifact is out of sequence and may cause Codex to generate a premature closeout before Claude review. This is cosmetic but could cause state confusion.

---

## Questions for Codex / Human

1. **M1 injection site**: Should `build_task_retrieval_request` in `retrieval_flow.py` be the sole location that reads `state.input_context["document_paths"]` and populates `declared_document_paths` on `RetrievalRequest`? If yes, this should be stated in the plan to prevent a second read path emerging at the CLI layer or orchestrator level.

2. **M2 guard allowlist**: If any new event kind constant is added to `retrieval_flow.py` or `task_report.py` for the declared-document scoping telemetry, does the plan require a corresponding update to `HARNESS_HELPER_ALLOWED_EVENT_CONSTANTS` in `test_invariant_guards.py`? (Current answer: yes, per the guard test logic — but this coupling is not mentioned in the plan.)

3. **M2 score_breakdown acceptance**: Is it acceptable for M2's acceptance test to verify only relative ordering (declared docs outrank noise), or must it also verify that `score_breakdown` contains the policy contribution key? The plan text says boosts must appear in `score_breakdown`, but the milestone acceptance criterion does not mirror this requirement.

4. **M4 eval marker**: Will `test_lto2_retrieval_source_scoping.py` carry `@pytest.mark.eval` and be excluded from the default `pytest -q` run? The plan's final gate command `pytest -q` would include it if the marker is absent.

5. **`KNOWLEDGE.md §3` RawMaterialStore boundary**: M2 proposes matching declared `document_paths` against candidate items by path. Today, `RetrievalItem.path` contains relative paths from `workspace_root`. Is the implementation expected to normalize `declared_document_paths` relative to `workspace_root` (using `swallow.workspace.resolve_path()` per INVARIANTS §7), or is a simpler string-prefix match sufficient? The plan says "must remain relative to the workspace/base dir and must use existing path normalization rules" but does not name the normalization function or assert that `resolve_path()` is used — which matters for the §7 guard test `test_no_absolute_path_in_truth_writes`.

---

## Confirmed Ready

- M1: Request Context Plumbing — implementable after resolving the two concerns above (injection site naming and `build_retrieval_request` facade contract). No INVARIANTS conflict.
- M2: Candidate Source Scoping — implementable after resolving score_breakdown acceptance criterion gap and guard allowlist coupling.
- M3: Truth Reuse Visibility — ready with the nit noted (harness.py is wiring-only, not logic target). No INVARIANTS conflict. No truth writes introduced.
- M4: R-entry Regression Smoke — implementable after confirming `@pytest.mark.eval` marker requirement and removing the premature closeout reference.

**Recommendation**: Return to Codex for a targeted plan revision addressing the 5 concerns before Human Plan Gate. The concerns are low-cost fixes (adding a sentence to each slice's acceptance criteria or touch point list); they do not require redesign. The plan should not proceed to implementation until the injection-site question (Q1) and eval marker requirement (Q4) are resolved in writing, as both affect how Codex will structure the first and last commits.
