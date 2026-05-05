---
author: codex
phase: r-entry-v1.9-real-usage
slice: findings-log
status: draft
depends_on:
  - docs/plans/r-entry-v1.9-real-usage/plan.md
  - docs/roadmap.md
  - docs/concerns_backlog.md
---

TL;DR:
Findings log for post-v1.9.0 real usage with Swallow design documents.
Use this file to record real operator friction and decide whether the next phase should be LTO-2 retrieval policy tuning, Wiki Compiler stage 3, D2 driven ports, docs/config hygiene, or no phase.

# R-entry v1.9 Findings

## Run Metadata

- base_dir: `/tmp/swl-r-entry-v1.9-real-usage`
- repository_tag: `v1.9.0`
- release_commit: `d598e58 docs(release): sync v1.9.0 release docs`
- source_docs:
  - `docs/design/INVARIANTS.md`
  - `docs/design/KNOWLEDGE.md`
  - `docs/design/HARNESS.md`
  - `docs/design/PROVIDER_ROUTER.md`
  - `docs/engineering/TEST_ARCHITECTURE.md`
  - `docs/engineering/ADAPTER_DISCIPLINE.md`
- operator:
- date:

## Finding Template

```markdown
## R19-001 Short Title

- status: open | resolved | deferred | observation
- severity: blocker | concern | nit | observation
- surface: retrieval | truth-reuse | wiki | cli | web | nginx | config | docs
- task_id:
- command:
- expected:
- actual:
- evidence:
  - artifact:
  - report section:
  - log excerpt:
- likely next direction:
  - LTO-2 retrieval policy tuning
  - Wiki Compiler stage 3
  - D2 LTO-5 driven ports
  - docs/config hygiene
  - no phase; operator note only
- notes:
```

## Findings

## R19-001 Declared `document_paths` are not visible in task truth and source scoping did not apply

- status: open
- severity: blocker
- surface: retrieval
- task_id: `10b2890bab71`
- command: `.venv/bin/swl --base-dir /tmp/swl-r-entry-v1.9-real-usage task create ... --document-paths docs/design/INVARIANTS.md --document-paths docs/design/KNOWLEDGE.md --document-paths docs/design/HARNESS.md --document-paths docs/design/PROVIDER_ROUTER.md`
- expected: declared design docs are persisted in task input context, visible through an operator-auditable surface, and retrieval applies `declared_document_priority` to those paths.
- actual: `task inspect`, `task intake`, `task_semantics_report.md`, `task_semantics.json`, and `state.json` do not show the declared document paths; `retrieval_report.md` top hits are code/runbook files, not the declared design docs; no `declared_document_priority` or `source_noise_penalty` appears in retrieval output.
- evidence:
  - artifact: `/tmp/swl-r-entry-v1.9-real-usage/.swl/tasks/10b2890bab71/artifacts/task_semantics_report.md`
  - artifact: `/tmp/swl-r-entry-v1.9-real-usage/.swl/tasks/10b2890bab71/task_semantics.json`
  - artifact: `/tmp/swl-r-entry-v1.9-real-usage/.swl/tasks/10b2890bab71/artifacts/retrieval_report.md`
  - report section: `Top References` shows `src/swallow/knowledge_retrieval/knowledge_plane.py`, `docs/plans/r-entry-v1.9-real-usage/plan.md`, `src/swallow/knowledge_retrieval/retrieval.py`, and `src/swallow/orchestration/retrieval_flow.py` as the first four hits.
  - Web API evidence: `GET /api/tasks/10b2890bab71` returned `"input_context": {}` after task creation with `--document-paths`.
  - command evidence: `rg -n "declared_document_priority|source_noise_penalty|document_paths|INVARIANTS|KNOWLEDGE|PROVIDER_ROUTER|HARNESS" ...` returned no matches across task semantics, state, retrieval JSON, and retrieval report.
- likely next direction:
  - LTO-2 retrieval policy tuning
- notes: This is stronger than the review follow-up about score magnitudes. The operator-facing CLI accepted `--document-paths`, but the paths were not recoverable in task truth and did not influence retrieval. Before tuning score weights, the create/intake/run plumbing for declared document paths needs to be verified.

## R19-002 `note-only` offline execution is classified as failed `unreachable_backend`

- status: open
- severity: concern
- surface: cli
- task_id: `10b2890bab71`
- command: `.venv/bin/swl --base-dir /tmp/swl-r-entry-v1.9-real-usage task run 10b2890bab71`
- expected: a task explicitly created with `--executor note-only --route-mode offline` should either complete as a no-live-executor note-only run or use an operator-facing status that explains "skipped by design" without suggesting backend/network repair.
- actual: run output was `10b2890bab71 failed retrieval=8 execution_phase=analysis_done`; `executor_output.md` says `status: failed`, `failure_kind: unreachable_backend`, and recommends verifying outbound network/process execution, even though the selected route is offline/local-note.
- evidence:
  - artifact: `/tmp/swl-r-entry-v1.9-real-usage/.swl/tasks/10b2890bab71/artifacts/executor_output.md`
  - artifact: `/tmp/swl-r-entry-v1.9-real-usage/.swl/tasks/10b2890bab71/artifacts/resume_note.md`
  - artifact: `/tmp/swl-r-entry-v1.9-real-usage/.swl/tasks/10b2890bab71/artifacts/validation_report.md`
  - log excerpt: `Operator selected note-only non-live mode; live executor execution was skipped.`
- likely next direction:
  - docs/config hygiene
  - LTO-2 retrieval policy tuning
- notes: Retrieval and validation artifacts were produced, so the run is useful for R-entry, but the failure classification creates false operator work. This may be a local runtime semantics issue rather than retrieval itself.

## R19-003 Truth reuse visibility works, but skipped reason semantics are confusing and warning text is stale

- status: open
- severity: concern
- surface: truth-reuse
- task_id: `10b2890bab71`
- command: `.venv/bin/swl --base-dir /tmp/swl-r-entry-v1.9-real-usage task knowledge-capture 10b2890bab71 ...` followed by `.venv/bin/swl --base-dir /tmp/swl-r-entry-v1.9-real-usage task rerun 10b2890bab71`
- expected: after task-scoped retrieval-eligible knowledge is captured, the retrieval report should clearly explain whether that knowledge was considered, matched, or skipped; warning text should not claim task knowledge is absent once task knowledge exists.
- actual: `Truth Reuse Visibility` correctly says task knowledge was considered and skipped, but the single captured item contributes to three skipped reasons (`missing_source_pointer=1`, `query_no_match=1`, `status_not_active=1`), making the counts look like a partition when they are overlapping signals. The `Source Policy Warnings` section still says `fallback_hits_without_truth_objects: no canonical or task knowledge item is present` even though task knowledge exists and was considered.
- evidence:
  - artifact: `/tmp/swl-r-entry-v1.9-real-usage/.swl/tasks/10b2890bab71/artifacts/retrieval_report.md`
  - artifact: `/tmp/swl-r-entry-v1.9-real-usage/.swl/tasks/10b2890bab71/memory.json`
  - report section: `Truth Reuse Visibility`
  - report section: `Source Policy Warnings`
- likely next direction:
  - LTO-2 retrieval policy tuning
- notes: This directly reproduces the review concern about task-knowledge reason counts. The stale source-policy warning is a separate operator-facing wording issue: fallback hits can be present without reusable truth objects, but the message should distinguish "no active reusable truth" from "no task knowledge item exists."

## R19-004 Wiki draft dry-run reports `prompt_artifact=-` and leaves no discoverable wiki artifact

- status: open
- severity: concern
- surface: wiki
- task_id: `10b2890bab71`
- command: `.venv/bin/swl --base-dir /tmp/swl-r-entry-v1.9-real-usage wiki draft --task-id 10b2890bab71 --topic "Test Architecture" --source-ref "file://workspace/docs/engineering/TEST_ARCHITECTURE.md" --dry-run`
- expected: dry-run produces an inspectable prompt/source-pack artifact or prints a concrete path, so the operator can review what a real Wiki Compiler call would use.
- actual: command succeeded with `wiki_draft_dry_run source_count=1 prompt_artifact=-`; `task artifacts` and file search only show generic `executor_prompt.md` / `source_grounding.md`, with no obvious wiki draft dry-run prompt or source-pack artifact.
- evidence:
  - command output: `wiki_draft_dry_run source_count=1 prompt_artifact=-`
  - command evidence: `find /tmp/swl-r-entry-v1.9-real-usage/.swl -maxdepth 5 -type f | sort | rg "wiki|draft|prompt|source|compiler"` only found `executor_prompt.md` and `source_grounding.md`.
- likely next direction:
  - Wiki Compiler stage 3
  - docs/config hygiene
- notes: This does not prove Wiki Compiler real draft is broken. It does show dry-run is not yet a strong operator review surface.

## R19-005 Web Control Center loopback smoke passed for task list/detail

- status: observation
- severity: observation
- surface: web
- task_id: `10b2890bab71`
- command: `.venv/bin/swl --base-dir /tmp/swl-r-entry-v1.9-real-usage serve --host 127.0.0.1 --port 8765`
- expected: loopback Web UI serves HTML and API exposes the same task truth as CLI.
- actual: `GET /` returned HTML; `GET /api/tasks` returned the failed task with `retrieval_count=8`; `GET /api/tasks/10b2890bab71` returned task detail including failed status, task semantics, and captured task knowledge.
- evidence:
  - `curl -s http://127.0.0.1:8765/ | head -c 500` returned the Control Center HTML.
  - `curl -s http://127.0.0.1:8765/api/tasks` returned `count: 1` and task `10b2890bab71`.
  - `curl -s http://127.0.0.1:8765/api/tasks/10b2890bab71` returned task detail.
- likely next direction:
  - no phase; operator note only
- notes: `HEAD /` returns 405 while `GET /` works; not a blocker for browser use. The temporary server was stopped after the smoke test.

## Direction Gate Summary

Fill this after executing the runbook.

| Candidate | Evidence | Recommendation |
|---|---|---|
| Continue R-entry real usage | R19-001 blocks the source-scoping validation path, but R4-R10 can still test truth visibility absence, Wiki dry-run, and Web smoke. | Continue only for non-source-scoping surfaces unless a workaround is found. |
| LTO-2 retrieval policy tuning | R19-001 shows declared docs were not persisted/applied; R19-003 reproduces confusing truth reuse reason counts and stale source-policy warning text. | Strong candidate for next phase if no simpler CLI plumbing bugfix is split first. |
| Wiki Compiler stage 3 | R19-004 shows wiki draft dry-run is not inspectable enough for source-pack/prompt review. | Candidate only if real draft/refine also shows review friction; otherwise treat as CLI/docs hygiene. |
| D2 LTO-5 driven ports |  |  |
| Docs/config hygiene | R19-002 may need operator guidance if note-only failure semantics are intentional; R19-004 may need dry-run docs or artifact surfacing. | Defer until code semantics are confirmed. |
