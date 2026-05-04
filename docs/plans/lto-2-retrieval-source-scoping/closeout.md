---
author: codex
phase: lto-2-retrieval-source-scoping
slice: closeout
status: final
depends_on:
  - docs/plans/lto-2-retrieval-source-scoping/plan.md
  - docs/plans/lto-2-retrieval-source-scoping/plan_audit.md
  - docs/plans/lto-2-retrieval-source-scoping/review_comments.md
  - docs/concerns_backlog.md
  - docs/active_context.md
  - pr.md
---

TL;DR:
LTO-2 Retrieval Source Scoping And Truth Reuse Visibility is complete and review says acceptable to merge with 3 tracked concerns.
The phase makes task-declared `document_paths` shape retrieval before rerank, downgrades generated/archive noise, and adds truth reuse visibility to retrieval reports and memory surfaces.
No Graph RAG, schema migration, vector-index overhaul, chunk rewrite, new source type, provider/rerank integration, or truth mutation was included.

# LTO-2 Closeout: Retrieval Source Scoping And Truth Reuse Visibility

## Phase Outcome

Status: `acceptable-to-merge` after Claude PR review.

This phase consumed the highest-priority R-entry finding: retrieval ignored task-declared source documents even after OpenRouter rerank was working, and truth reuse counts were opaque when canonical/task knowledge existed but was not reused.

Delivered commits:

- `6cda76c docs(plans)lto-2-retrieval-source-scoping`
- `03ef358 feat(retrieval): scope sources from declared documents`

## Delivered Scope

M1 Request Context Plumbing:

- Added `RetrievalRequest.declared_document_paths` at the end of the dataclass with default `()`.
- `build_task_retrieval_request` is the only task-state injection point for `state.input_context["document_paths"]`.
- Declared paths are normalized through the workspace path boundary and stored as workspace-relative POSIX strings.
- Retrieval completion telemetry now includes `declared_document_paths`.

M2 Candidate Source Scoping:

- Added `apply_source_scoping_policy` before final score sort and rerank.
- Declared source documents receive a deterministic `declared_document_priority` score contribution.
- Generated/archive/build-cache noise gets explicit labels and a deterministic `source_noise_penalty`.
- Source policy labels now cover:
  - `generated_metadata`
  - `build_cache`
  - `generated_artifact`
  - existing `archive_note`, `current_state`, and `observation_doc`
- EvidencePack policy labeling was kept consistent with retrieval policy labeling.

M3 Truth Reuse Visibility:

- Added `summarize_truth_reuse_visibility`.
- `retrieval_report.md` now includes `## Truth Reuse Visibility`.
- Task memory and summary surfaces include truth reuse visibility status.
- The implementation is read/report-only: no canonical registry, task knowledge, `know_evidence`, or `apply_proposal` write path was added.

M4 R-entry Regression Smoke:

- Added `tests/eval/test_lto2_retrieval_source_scoping.py`.
- The eval fixture is marked `pytest.mark.eval`, disabled in default pytest, and uses only local temporary files.
- The fixture reproduces the R-entry failure shape: declared `docs/design/KNOWLEDGE.md` outranks noisy `docs/archive_phases/*` and `src/*.egg-info/*` hits without live LLM or rerank calls.

## Plan Audit Absorption

Plan audit verdict: `has-concerns`; 0 blockers / 5 concerns / 2 nits.

All audit concerns were absorbed before implementation:

| Audit item | Closeout disposition |
|---|---|
| M1 dataclass compatibility / construction path | Added the field at the end with default `()`; tests use the request factory rather than new direct positional construction. |
| M1 injection site | `build_task_retrieval_request` is the only reader of task-state `document_paths`. |
| M2 source policy touch points / guard coupling | Updated `source_policy_label_for` and `SOURCE_POLICY_NOISE_LABELS`; no new event kinds were introduced, so no guard allowlist update was needed. |
| M2 score_breakdown acceptance | Tests assert `declared_document_priority` and `source_noise_penalty` in `score_breakdown`. |
| M4 eval marker | New eval fixture uses module-level `pytestmark = pytest.mark.eval` and is run through explicit `-m eval`. |
| NIT premature closeout | No closeout was generated before PR review. |
| NIT `harness.py` as main touch point | Logic stayed in `task_report.py` / retrieval helpers; `harness.py` only carries visibility into memory/summary surfaces. |

## Review Disposition

Review artifact: `docs/plans/lto-2-retrieval-source-scoping/review_comments.md`.

Verdict: acceptable to merge; 0 blocks / 3 concerns / 3 nits.

The 3 concerns were accepted as non-blocking follow-ups and are tracked in `docs/concerns_backlog.md` under `LTO-2 Source Scoping review follow-ups`:

| Review concern | Disposition |
|---|---|
| C1 score magnitudes are hardcoded and undocumented (`DECLARED_DOCUMENT_PRIORITY_BONUS = 1000`, `SOURCE_POLICY_NOISE_PENALTY = 250`) | Tracked as a future retrieval policy tuning concern. No code change before merge because current behavior matches the plan's "strongly boosted" operator-intent choice and tests verify it. |
| C2 task knowledge `reason_counts` can double-count because reasons are signal counts, not a partition | Tracked as report semantics follow-up. Current report remains useful for visibility but should be clarified or made mutually exclusive if real operators find the counts confusing. |
| C3 canonical registry visibility only reports `query_no_match`; policy/status excluded canonical records are not surfaced | Tracked as future canonical visibility refinement. Current implementation remains internally consistent by considering only reuse-visible canonical records. |

Review nits were acknowledged:

- `source_policy_label_for(replace(item, metadata=metadata))` can be simplified later.
- `absent_count` is a 0/1 sentinel next to real counts; future report semantics may prefer `is_absent`.
- `SOURCE_POLICY_NOISE_LABELS` is duplicated between retrieval and EvidencePack; future hygiene can centralize it.

## Final Validation

Codex validation:

```text
.venv/bin/python -m pytest tests/unit/orchestration/test_retrieval_flow_module.py -q
12 passed in 0.19s

.venv/bin/python -m pytest tests/unit/orchestration/test_task_report_module.py -q
3 passed in 0.04s

.venv/bin/python -m pytest -m eval tests/eval/test_lto2_retrieval_source_scoping.py -q
1 passed in 0.03s

.venv/bin/python -m pytest tests/integration/cli/test_retrieval_commands.py -q
44 passed in 7.53s

.venv/bin/python -m compileall -q src/swallow tests
passed

.venv/bin/python -m pytest -q
812 passed, 20 deselected in 110.51s

git diff --check
passed
```

Claude independent validation:

```text
.venv/bin/python -m pytest tests/unit/orchestration/test_retrieval_flow_module.py tests/unit/orchestration/test_task_report_module.py tests/integration/cli/test_retrieval_commands.py -q
59 passed in 7.70s

.venv/bin/python -m pytest -m eval tests/eval/test_lto2_retrieval_source_scoping.py -q
1 passed in 0.02s

.venv/bin/python -m pytest -q
812 passed, 20 deselected in 139.11s
```

## Deferred Follow-Ups

Deferred by phase boundary or review disposition:

- Tuning / documenting the source-scope score magnitudes.
- Clarifying whether truth reuse `reason_counts` are signal counts or mutually exclusive buckets.
- Surfacing canonical `policy_excluded` / `status_not_active` reasons when canonical records are filtered before reuse visibility.
- Centralizing source policy labels between retrieval and EvidencePack to avoid drift.
- `know_evidence` physical schema migration remains deferred.
- Graph RAG, vector-index overhaul, chunk strategy rewrite, object storage, and new rerank/provider integrations remain out of scope.

## Merge Readiness

Ready for Human closeout commit and merge decision.

Recommended closeout commit scope:

- `docs/plans/lto-2-retrieval-source-scoping/review_comments.md`
- `docs/plans/lto-2-retrieval-source-scoping/closeout.md`
- `docs/concerns_backlog.md`
- `docs/active_context.md`
- `current_state.md`
- `pr.md`
