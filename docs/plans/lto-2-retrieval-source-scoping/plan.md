---
author: codex
phase: lto-2-retrieval-source-scoping
slice: retrieval-source-scoping-and-truth-reuse-visibility
status: draft
depends_on:
  - docs/design/INVARIANTS.md
  - docs/design/KNOWLEDGE.md
  - docs/design/ORCHESTRATION.md
  - docs/design/HARNESS.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/roadmap.md
  - docs/active_context.md
  - docs/plans/r-entry-real-usage/findings.md
  - docs/plans/lto-2-retrieval-source-scoping/plan_audit.md
---

TL;DR:
This phase makes retrieval respect task-declared source documents before rerank, and makes truth reuse explainable when canonical/task knowledge exists but is not reused.
It is an LTO-2 product-quality increment, not a Graph RAG, vector-index, chunking, or schema-migration phase.
Implementation should proceed after plan audit / Human gate on a feature branch, with milestone commits split by request shape, candidate policy, and reporting/eval.
Plan audit found no blockers; this revision absorbs its 5 concerns as explicit pre-implementation constraints.

# LTO-2 Retrieval Source Scoping And Truth Reuse Visibility Plan

## Current Phase

- active_track: `LTO-2 Retrieval Quality / Evidence Serving`
- active_phase: `lto-2-retrieval-source-scoping`
- active_slice: `retrieval-source-scoping-and-truth-reuse-visibility`
- recommended_branch: `feat/lto-2-retrieval-source-scoping`
- gate_required_before_implementation: `plan_audit.md` + Human Plan Gate + branch switch

## Problem Statement

R-entry real usage showed a concrete retrieval quality gap after connectivity was no longer the issue. Wiki LLM calls worked after sourcing `.env`, and OpenRouter `cohere/rerank-v3.5` returned 200 with `rerank_applied: True`. Despite that, a task that declared specific design and engineering `document_paths` still produced top retrieval hits from broad workspace material: repo code, generated metadata, tests, and archived phase docs.

That means rerank was ordering a poor candidate pool. The next useful increment is to make task-declared source documents shape candidate selection before rerank, and to explain whether canonical/task knowledge was considered, matched, skipped, or absent. Chunk tuning may still be useful later, but the R-entry evidence points first to source scoping and operator-visible reuse reasoning.

## Goals

1. Make task-declared `document_paths` influence retrieval request shape and candidate selection.
2. Keep `source_types` semantic, per `KNOWLEDGE.md`: do not turn source types into file-extension or backend filters.
3. Add a source policy that downgrades or excludes generated/archive/noise paths unless explicitly requested.
4. Preserve truth-first retrieval: Wiki / Canonical / task knowledge remain primary semantic surfaces; raw notes/repo chunks stay fallback or scoped context.
5. Add retrieval report sections that show:
   - declared source documents considered / matched / missed
   - canonical registry objects considered / matched / skipped / absent
   - task knowledge objects considered / matched / skipped / absent
   - final ordering basis after scoping and rerank
6. Add deterministic tests and at least one eval fixture that reproduces the R-entry failure shape without external API calls.

## Non-Goals

- No Graph RAG or project-level relation graph UI.
- No `know_evidence` schema migration.
- No vector index backend overhaul or new external vector store.
- No broad chunking rewrite. Existing Markdown heading chunks and 40-line non-Markdown chunks can be adjusted only if a narrow test proves an immediate blocker.
- No new retrieval source type for `document_paths`; `document_paths` are task input/context, not a semantic source type.
- No automatic canonical promotion, truth mutation, or bypass around `apply_proposal`.
- No new provider/rerank integration work. OpenRouter rerank is treated as already operational.
- No Web UI expansion beyond surfacing already-produced retrieval report data through existing artifact views.

## Design Anchors

- `docs/design/INVARIANTS.md`
  - Control remains Orchestrator / Operator only.
  - Retrieval may emit hints or reports, but must not mutate task truth or canonical truth.
  - Canonical writes still only go through `apply_proposal`.
- `docs/design/KNOWLEDGE.md`
  - Knowledge truth is Wiki / Canonical / Evidence / Staged, not anonymous chunks.
  - `RetrievalRequest.source_types` are semantic sources, not physical backend switches.
  - Default retrieval is wiki-first / canonical-first / evidence-backed / vector-assisted.
- `docs/design/ORCHESTRATION.md`
  - Retrieval observability can inform Review Gate or Operator, but cannot silently advance or reroute task state.
- `docs/design/HARNESS.md`
  - Artifacts and reports are the audit surface for operator review.
- `docs/engineering/TEST_ARCHITECTURE.md`
  - New tests should use focused unit/integration/eval locations; no new monolithic CLI test file.
- `docs/plans/r-entry-real-usage/findings.md`
  - This phase is justified by the R-entry evidence: source scoping and truth reuse visibility are the highest-value next gate.

## Proposed Implementation Shape

### Request Shape

Introduce an explicit retrieval request field for task-declared document context, tentatively:

```python
declared_document_paths: tuple[str, ...] | list[str]
```

The field must be added at the end of the `RetrievalRequest` dataclass with default `()`, preserving forwards compatibility for existing construction sites. M1 must confirm construction sites and keep request assembly behind the existing retrieval request factory path; new tests should avoid positional `RetrievalRequest(...)` construction.

The sole task-state injection point is `build_task_retrieval_request` in `src/swallow/orchestration/retrieval_flow.py`. That function already has access to `TaskState.input_context` and `TaskState.task_semantics`; it should read `state.input_context["document_paths"]`, normalize it, and populate `declared_document_paths`. Do not add a second read path in CLI commands or Orchestrator call sites.

Declared paths must remain workspace-relative. Validation / normalization should use the existing workspace path boundary, including `swallow.workspace.resolve_path()` where path resolution is needed, and must not persist absolute paths into task truth or retrieval metadata. It should not replace `source_types`; it constrains or prioritizes candidates within the selected semantic sources.

### Candidate Scoping Policy

Add a small, deterministic source scope policy before rerank:

- Exact declared `document_paths` are included or strongly boosted when their source type is requested.
- Markdown declared paths should be eligible under `notes`.
- Non-Markdown declared paths should be eligible under `repo` if `repo` is requested explicitly.
- Generated paths are downgraded or excluded by default:
  - `src/*.egg-info/*`
  - build/cache metadata
  - generated artifacts outside the current task unless `artifacts` was requested with a task/artifact pointer
- Archive paths are downgraded or excluded by default:
  - `docs/archive_phases/*`
  - `docs/archive/*`
- Explicit operator source override should be able to request broad `repo` / `artifacts`, but report must still label noisy paths.

The policy should prefer clear, testable metadata over hidden score magic. Implementation is expected to touch `src/swallow/knowledge_retrieval/retrieval.py`, especially `source_policy_label_for()` and `SOURCE_POLICY_NOISE_LABELS`, so generated metadata and build/cache paths have explicit labels instead of falling through as ordinary repo hits.

If score boosts are used, they must appear in `score_breakdown` under an explicit key such as `declared_document_priority`. M2 tests must assert both relative ordering and the presence of that score/policy contribution.

If any new event kind string or event kind constant is introduced in `retrieval_flow.py`, `task_report.py`, or another harness helper module, the implementation must update the narrow guard allowlist in `tests/test_invariant_guards.py`. Prefer report metadata over new event kinds unless an event is genuinely needed.

### Truth Reuse Visibility

Extend retrieval summary/report metadata so a zero reuse count is not opaque:

- `canonical_registry_status`: `absent | considered | matched | skipped`
- `task_knowledge_status`: `absent | considered | matched | skipped`
- skipped reasons such as:
  - `query_no_match`
  - `source_type_not_requested`
  - `policy_excluded`
  - `status_not_active`
  - `missing_source_pointer`
- counts for considered/matched/skipped/absent states

This is report and artifact visibility. It should not change canonical truth or task knowledge lifecycle semantics.

### Report Contract

`retrieval_report.md` should gain compact sections:

- `## Declared Source Documents`
- `## Truth Reuse Visibility`
- existing `EvidencePack Summary`, source policy warnings, top references, and source pointers remain compatible.

The report should make the R-entry failure impossible to miss:

- declared docs listed as `matched` or `missed`
- generated/archive hits labeled as downgraded/excluded or warnings
- canonical/task knowledge existence and skip reasons visible when reuse counts are zero

## Slice / Milestone Plan

| Milestone | Slice | Goal | Main Touch Points | Acceptance | Risk | Commit Gate |
|---|---|---|---|---|---|---|
| M1 | Request Context Plumbing | Carry task-declared document paths into `RetrievalRequest` and retrieval telemetry without changing candidate ranking yet. | `src/swallow/orchestration/retrieval_flow.py`, retrieval request model, focused unit tests. | `build_task_retrieval_request` is the sole task-state injection point; a task with `input_context["document_paths"]` produces a retrieval request containing normalized workspace-relative declared paths; the new dataclass field is appended with default `()`; existing source type defaults remain unchanged. | Low | Separate commit: request shape + tests. |
| M2 | Candidate Source Scoping | Apply declared-document priority and generated/archive noise policy before rerank. | `src/swallow/knowledge_retrieval/retrieval.py` (`source_policy_label_for`, `SOURCE_POLICY_NOISE_LABELS`), retrieval adapters/policy helpers, score metadata, source policy tests. | Deterministic fixture where declared docs outrank generated/archive/code noise before rerank; `score_breakdown` exposes the declared-document priority contribution when used; explicit overrides remain possible and labeled; guard allowlists are updated only if new event kinds are introduced. | Medium | Separate commit: candidate policy + tests/eval. |
| M3 | Truth Reuse Visibility | Explain canonical/task knowledge considered/matched/skipped/absent in report and memory metadata. | `src/swallow/orchestration/task_report.py`, `retrieval_flow.py`, CLI/report tests; `harness.py` is wiring-only unless call signatures force a narrow update. | A zero reuse report distinguishes no truth objects from existing-but-skipped truth objects, with reason counts; report building remains read-only and emits no new events unless explicitly justified and guard-covered. | Medium | Separate commit: report contract + tests. |
| M4 | R-entry Regression Smoke | Re-run a local no-network scenario based on the R-entry docs and verify report shape. | `tests/eval/`, deterministic fixtures. | Eval/smoke fixture is marked `pytest.mark.eval`, proves declared design docs are considered, and shows archive/generated noise is not silently dominant. Focused tests and explicit eval gate pass. | Low | Final milestone gate before review. |

## Test Plan

Focused commands during implementation:

```bash
.venv/bin/python -m pytest tests/unit/orchestration/test_retrieval_flow_module.py -q
.venv/bin/python -m pytest tests/integration/cli/test_retrieval_commands.py -q
.venv/bin/python -m pytest tests/unit/orchestration/test_task_report_module.py -q
```

Eval / quality signal:

```bash
.venv/bin/python -m pytest -m eval tests/eval/test_lto2_retrieval_source_scoping.py -q
```

Milestone / final gates:

```bash
.venv/bin/python -m compileall -q src/swallow tests
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -m eval tests/eval/test_lto2_retrieval_source_scoping.py -q
git diff --check
```

If external rerank is used for manual smoke only, it must be explicitly marked as non-gating and run after:

```bash
set -a
source .env
set +a
```

No test in this phase should require OpenRouter, BGE, New API, or any live LLM/rerank endpoint.

## Review And Branch Flow

1. Codex produces this `plan.md`.
2. Human requests/obtains `plan_audit.md` from design-auditor.
3. Human approves the plan gate.
4. Human creates/switches to `feat/lto-2-retrieval-source-scoping`.
5. Codex implements M1-M4 with milestone commits suggested after each gate.
6. Claude review happens after implementation milestone(s), with `review_comments.md`.
7. Codex prepares `closeout.md` / `pr.md` after review concerns are handled.

Implementation should not begin on `main`.

## Risks And Mitigations

- Risk: source scoping silently hides useful context.
  - Mitigation: preserve explicit source override and report excluded/downgraded policy decisions.
- Risk: `document_paths` become a hidden physical source type.
  - Mitigation: model them as request constraints/priority inputs, not as new `source_types`.
- Risk: score tuning becomes opaque.
  - Mitigation: expose score/policy contributions in `score_breakdown` and `retrieval_report.md`, and assert the contribution key in M2 tests.
- Risk: path normalization leaks absolute paths into truth or retrieval metadata.
  - Mitigation: normalize declared paths at `build_task_retrieval_request`, use the workspace path boundary for resolution, and persist only relative paths.
- Risk: truth reuse visibility accidentally changes truth lifecycle.
  - Mitigation: keep this slice read/report-only; no canonical/task knowledge writes.
- Risk: eval becomes brittle.
  - Mitigation: use small deterministic fixture documents, mark the test with `pytest.mark.eval`, and keep it free of network/rerank dependency.

## Completion Conditions

- `RetrievalRequest` carries declared document paths from task context.
- Declared docs can influence candidate scope/priority before rerank.
- Generated/archive noise is downgraded/excluded by default and labeled when present.
- Declared-document priority appears in `score_breakdown` when it affects ranking.
- Retrieval report shows declared source document status and truth reuse visibility.
- Deterministic tests cover source scoping, noisy path policy, and reuse visibility.
- Eval fixture is marked `pytest.mark.eval` and reproduces the R-entry failure mode without network access.
- Focused tests, compileall, full default pytest, and `git diff --check` pass at final gate.
- `docs/active_context.md` and closeout/PR docs are updated after implementation and review, not before.
