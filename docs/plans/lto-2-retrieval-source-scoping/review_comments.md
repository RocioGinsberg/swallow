---
author: claude
phase: lto-2-retrieval-source-scoping
slice: pr-review
status: review
depends_on:
  - docs/plans/lto-2-retrieval-source-scoping/plan.md
  - docs/plans/lto-2-retrieval-source-scoping/plan_audit.md
  - docs/design/INVARIANTS.md
  - docs/design/KNOWLEDGE.md
  - docs/engineering/TEST_ARCHITECTURE.md
---

TL;DR: Acceptable to merge with 3 [CONCERN]s. M1–M4 implementation matches the revised plan, all 5 audit concerns are absorbed and verified by tests, INVARIANTS held (no truth writes, paths workspace-relative, no new event kinds requiring guard allowlist). Concerns are about score-magnitude justification, truth-reuse reason-count semantics, and parallel `SOURCE_POLICY_NOISE_LABELS` duplication; none block merge.

## Test Verification (Independent)

Run on `feat/lto-2-retrieval-source-scoping` at `03ef358`:

- `.venv/bin/python -m pytest tests/unit/orchestration/test_retrieval_flow_module.py tests/unit/orchestration/test_task_report_module.py tests/integration/cli/test_retrieval_commands.py -q` → `59 passed in 7.70s`
- `.venv/bin/python -m pytest -m eval tests/eval/test_lto2_retrieval_source_scoping.py -q` → `1 passed in 0.02s`
- `.venv/bin/python -m pytest -q` → `812 passed, 20 deselected in 139.11s`
- Numbers match Codex's reported `812 passed, 20 deselected` baseline.

## Plan Conformance Checklist

### M1 — Request Context Plumbing

- `[PASS]` `RetrievalRequest.declared_document_paths` appended at the end of the dataclass with default `()` (`src/swallow/orchestration/models.py:601`). Existing positional construction and `to_dict()` remain compatible.
- `[PASS]` `build_task_retrieval_request` is the sole task-state injection point (`src/swallow/orchestration/retrieval_flow.py:108`); `_declared_document_paths(state)` reads `state.input_context["document_paths"]` and is not called from CLI / orchestrator surface.
- `[PASS]` Path normalization uses `swallow.application.infrastructure.workspace.resolve_path` against the workspace root and stores only `relative_to(workspace_root).as_posix()`; outside-workspace paths and unresolved entries are silently dropped. Verified by `test_retrieval_request_carries_workspace_relative_declared_document_paths` covering absolute, relative, duplicate, and outside cases.
- `[PASS]` Default-empty path verified by `test_retrieval_request_defaults_declared_document_paths_to_empty_tuple`.
- `[PASS]` Retrieval telemetry (`save_retrieval` payload at `retrieval_flow.py:149`) records `declared_document_paths` as a list, preserving offline auditability.

### M2 — Candidate Source Scoping

- `[PASS]` `SOURCE_POLICY_NOISE_LABELS` extended with `build_cache`, `generated_artifact`, `generated_metadata` and the matching detectors (`_is_generated_metadata_path`, `_is_build_cache_path`, `_is_generated_artifact_path`) cover `*.egg-info`, `__pycache__`, `build/`, `dist/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, and `.swl/tasks/<id>/artifacts/*` — directly addressing the audit Q2 gap.
- `[PASS]` `apply_source_scoping_policy` is invoked on the candidate list before the score sort and before rerank in `retrieve_context` (`retrieval.py:1355–1360`). Order matches the plan ("before rerank").
- `[PASS]` `score_breakdown` exposes `declared_document_priority` and `source_noise_penalty` keys; both unit and eval tests assert their presence and sign. Audit Q3 satisfied.
- `[PASS]` No new event kind constants were introduced in `retrieval_flow.py` or `task_report.py`; guard allowlist update was therefore not required, matching audit Q2's contingent ask.
- `[CONCERN]` Score magnitudes `DECLARED_DOCUMENT_PRIORITY_BONUS = 1000` and `SOURCE_POLICY_NOISE_PENALTY = 250` (`retrieval.py:99–100`) are hardcoded constants without a comment justifying the magnitudes. The eval fixture has lexical scores in single digits to ~60, so +1000 effectively makes declared-doc priority dominate any rerank or relevance signal. That matches the operator-intent reading of "strongly boosted", but the bonus magnitude makes downstream rerank irrelevant on the priority axis. Suggest either (a) a one-line comment explaining the magnitude is intentionally dominant, (b) routing through an env var so operators can tune, or (c) using a multiplicative boost so the bonus stays proportional to the lexical score scale. Not a blocker.

### M3 — Truth Reuse Visibility

- `[PASS]` `summarize_truth_reuse_visibility` returns `{task_knowledge: {...}, canonical_registry: {...}}` with `status / considered_count / matched_count / skipped_count / absent_count / reason_counts` per the plan contract (`retrieval.py:418–467`).
- `[PASS]` `task_report.build_retrieval_report` adds a `## Truth Reuse Visibility` section (`task_report.py:148–161`); `harness.build_task_memory` and `harness.build_summary` wire the same visibility into `task_memory.json` and the summary lines.
- `[PASS]` Read-only on truth plane: `_load_visible_canonical_records` only reads `canonical_reuse_policy_path`; no writes to canonical registry, task knowledge, or `know_evidence`. INVARIANTS §0 / §5 respected.
- `[PASS]` Test `test_retrieval_report_explains_zero_truth_reuse_when_truth_objects_exist` verifies the section is present, distinguishes `considered` vs `absent`, and surfaces `skipped_reasons: query_no_match=1`.
- `[CONCERN]` `task_knowledge.reason_counts` is computed by mixing three independent aggregations (`summarize_knowledge_reuse`, `summarize_knowledge_stages`, `summarize_knowledge_evidence`) — these classify objects on different dimensions and can double-count: a `stage: candidate` + `evidence_status: unbacked` object will contribute to both `status_not_active` and `missing_source_pointer`. The sum of the four reason buckets is not guaranteed to equal `skipped_count`. Operators reading the report may interpret these as a partition. Suggest either (a) document them as "signal counts, not a partition" in the report header, (b) compute mutually exclusive buckets per knowledge object, or (c) drop counts and surface only the dominant reason. Not a blocker; the plan asked for "reason counts" without specifying partitioning.
- `[CONCERN]` `canonical_registry.reason_counts` only emits `query_no_match`, with the implicit assumption that every skipped canonical record was skipped for that reason (`retrieval.py:457–459`). The plan listed `policy_excluded`, `status_not_active`, `missing_source_pointer` as candidate reasons. A canonical record filtered by `is_canonical_reuse_visible` returning false (status / policy) is currently invisible to the visibility report — those records will never appear in `considered_count` either, which is internally consistent but means policy-excluded canonical records are lost entirely from the visibility surface. Suggest a follow-up slice (or log a Roadmap-Bound entry) to surface `policy_excluded` and `status_not_active` causes for canonical records when their existence matters to operator review.

### M4 — R-entry Regression Smoke

- `[PASS]` `tests/eval/test_lto2_retrieval_source_scoping.py` carries `pytestmark = pytest.mark.eval` at module scope, so it is excluded from default `pytest -q` and only runs under `-m eval`. Audit Q4 satisfied.
- `[PASS]` Eval is offline: scenario uses `tmp_path` only; `with patch.dict("os.environ", {"SWL_RETRIEVAL_RERANK_ENABLED": "false"}, clear=False)` disables rerank; no LLM or external API calls.
- `[PASS]` Reproduces the R-entry shape: declared `docs/design/KNOWLEDGE.md` outranks `docs/archive_phases/old/closeout.md` and `src/swallow.egg-info/SOURCES.txt`, with the latter labeled `generated_metadata` and carrying a negative `source_noise_penalty`.
- `[PASS]` Eval gate command `pytest -m eval tests/eval/test_lto2_retrieval_source_scoping.py -q` passes locally (1 passed in 0.02s).

## Cross-Cutting Checks

### INVARIANTS Conformance

- `[PASS]` §0 Control boundary: `apply_source_scoping_policy` mutates only retrieval-side scoring metadata, never canonical or task knowledge. `summarize_truth_reuse_visibility` is read-only.
- `[PASS]` §2 Knowledge truth: `document_paths` is treated as a request-time priority constraint, not a new `source_types` enum value, per `KNOWLEDGE.md §3.1`.
- `[PASS]` §5 Write permissions: no new write paths to `canonical_reuse_policy.json`, `know_evidence`, `task_knowledge`, or `apply_proposal`.
- `[PASS]` §7 Path discipline: declared paths are normalized to workspace-relative posix form before storage in `RetrievalRequest`; absolute paths outside workspace are filtered. No new absolute-path leak surfaces.

### Test Coverage

- `[PASS]` New unit tests cover injection (M1), scoping policy + score breakdown (M2), report contract (M3).
- `[PASS]` Eval covers the R-entry failure mode end-to-end (M4) and is correctly gated.
- `[PASS]` Integration `test_retrieval_commands.py` (44 tests) still passes — no regression on existing CLI surface.
- `[PASS]` Full default suite: 812 passed, 20 deselected (was 806/19 pre-PR; +6 default and +1 eval matches the 4 new default tests + 1 eval test plus parametric expansion in adjacent assertions).

### Scope Discipline

- `[PASS]` No Graph RAG, schema migration, vector index overhaul, chunk rewrite, new source type, or provider integration — all non-goals respected.
- `[PASS]` `harness.py` change is wiring-only (3 small additions to `build_task_memory` / `build_summary`); audit nit about treating it as a logic touch point did not materialize.
- `[PASS]` No premature `closeout.md` was added; that audit nit was honored.

## Nits

- `[NIT]` `apply_source_scoping_policy` calls `source_policy_label_for(replace(item, metadata=metadata))` (`retrieval.py:723`). `source_policy_label_for` reads only `item.path` and `item.source_type`, so the `replace(...)` is a no-op for label resolution; `source_policy_label_for(item)` would be equivalent and cheaper. Cosmetic.
- `[NIT]` `task_knowledge.absent_count: 0 if task_considered_count else 1` uses 0/1 as a boolean sentinel but neighboring fields are real counts. Either rename to `is_absent: bool` or compute `absent_count` consistently (e.g., always 0 since absence is a status, not a count). Cosmetic.
- `[NIT]` `SOURCE_POLICY_NOISE_LABELS` and the path-detector helpers are now defined in parallel in `src/swallow/knowledge_retrieval/retrieval.py` and `src/swallow/knowledge_retrieval/evidence_pack.py`, identical post-PR. This duplication pre-exists, but the PR doubles the surface area for future drift. Out-of-scope to fix here; worth a follow-up code-hygiene slice.

## Verdict

Acceptable to merge with the 3 `[CONCERN]` items tracked. No `[BLOCK]`. Merge prerequisites:

- All audit concerns absorbed and verified ✓
- INVARIANTS respected ✓
- Tests pass independently ✓
- Scope discipline held ✓

Concerns C1–C3 will be appended to `docs/concerns_backlog.md` Active Open as LTO-2 follow-ups; none require modification before merge.
