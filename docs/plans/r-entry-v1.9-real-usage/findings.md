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

- status: resolved
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
- fix verification:
  - branch: `fix/lto2-document-path-plumbing`
  - smoke_base_dir: `/tmp/swl-r-entry-v1.9-document-path-fix`
  - smoke_task_id: `7c1e8a592ae1`
  - changed behavior: `task create --document-paths` now persists declared paths for ordinary task executors, not only `literature-specialist`.
  - operator visibility: `task intake 7c1e8a592ae1` and `task inspect 7c1e8a592ae1` show `document_paths_count: 2` and both declared absolute paths.
  - retrieval evidence: `retrieval.json` records `declared_document_priority: 1000`, `declared_document_path_status: matched`, and `declared_document_path: docs/design/KNOWLEDGE.md`; `retrieval_report.md` now surfaces `score_breakdown: ... declared_document_priority=1000`.
  - validation: `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py tests/unit/orchestration/test_retrieval_flow_module.py tests/unit/orchestration/test_task_report_module.py -q` -> `57 passed`.
- notes: Fixed as a narrow plumbing/visibility repair before broader retrieval tuning. R19-002 remains visible during the smoke: note-only/offline still reports `failed ... execution_phase=analysis_done`, but retrieval artifacts are produced and declared-document scoping applies.

## R19-002 `note-only` offline execution is classified as failed `unreachable_backend`

- status: resolved
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
- post-fix retest:
  - base_dir: `/tmp/swl-r-entry-v1.9-continue`
  - task_id: `d0a84932a9f1`
  - command: `.venv/bin/swl --base-dir /tmp/swl-r-entry-v1.9-continue task run d0a84932a9f1`
  - output: `d0a84932a9f1 failed retrieval=8 execution_phase=analysis_done`
  - notes: This remains open after R19-001. The run still produces useful retrieval and Wiki artifacts, but the operator-facing status still reads as a backend failure.
- fix verification:
  - branch: `fix/r19-002-note-only-offline-status`
  - smoke_base_dir: `/tmp/swl-r19-002-note-only-status`
  - smoke_task_id: `e3795dbb6ce5`
  - changed behavior: explicitly selected `note-only` + `route_mode=offline` now completes as a no-live-executor run record instead of reporting `failed/unreachable_backend`.
  - boundary: non-offline `note-only` fallback remains a failed backend-unavailable record, preserving the existing recovery semantics for accidental live-executor fallback.
  - artifact behavior: `executor_output.md` now uses `# Note-Only Offline Run`, records `live_executor_called: no`, and avoids backend/network repair guidance.
  - smoke output: `.venv/bin/swl --base-dir /tmp/swl-r19-002-note-only-status task run e3795dbb6ce5` -> `e3795dbb6ce5 completed retrieval=8 execution_phase=analysis_done`.
  - validation: `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py -q` -> `43 passed`; focused note-only/route override compatibility checks -> `2 passed`.

## R19-003 Truth reuse visibility works, but skipped reason semantics are confusing and warning text is stale

- status: resolved
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
- post-fix retest:
  - base_dir: `/tmp/swl-r-entry-v1.9-continue`
  - task_id: `d0a84932a9f1`
  - artifact: `/tmp/swl-r-entry-v1.9-continue/.swl/tasks/d0a84932a9f1/artifacts/retrieval_report.md`
  - report section: `Truth Reuse Visibility`
  - observed: `task_knowledge status: considered`, `considered_count: 1`, `skipped_count: 1`, and `skipped_reasons: missing_source_pointer=1, query_no_match=1, status_not_active=1`.
  - warning text: `fallback_hits_without_truth_objects: no canonical or task knowledge item is present` still appears even though task knowledge exists and was considered.
- fix verification:
  - branch: `fix/r19-003-truth-reuse-visibility`
  - smoke_base_dir: `/tmp/swl-r19-003-truth-reuse-fix`
  - smoke_task_id: `6aa7d7ed9619`
  - changed behavior: task knowledge skipped reasons are now primary/mutually exclusive for operator reporting. A candidate/source-only retrieval candidate reports `status_not_active=1` instead of also reporting `query_no_match=1` and `missing_source_pointer=1`.
  - warning behavior: fallback hits with considered task/canonical truth now report `fallback_hits_without_reused_truth_objects: canonical or task knowledge exists but did not match retrieval` instead of claiming no truth object exists.
  - evidence: `/tmp/swl-r19-003-truth-reuse-fix/.swl/tasks/6aa7d7ed9619/artifacts/retrieval_report.md`
  - validation: `.venv/bin/python -m pytest tests/unit/orchestration/test_task_report_module.py tests/unit/orchestration/test_retrieval_flow_module.py tests/test_retrieval_adapters.py -q` -> `44 passed`.

## R19-004 Wiki draft dry-run reports `prompt_artifact=-` and leaves no discoverable wiki artifact

- status: resolved
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
- post-fix retest:
  - base_dir: `/tmp/swl-r-entry-v1.9-continue`
  - task_id: `d0a84932a9f1`
  - dry-run command: `.venv/bin/swl --base-dir /tmp/swl-r-entry-v1.9-continue wiki draft --task-id d0a84932a9f1 --topic "Test Architecture" --source-ref "file://workspace/docs/engineering/TEST_ARCHITECTURE.md" --dry-run`
  - dry-run output: `wiki_draft_dry_run source_count=1 prompt_artifact=-`
  - real draft command: `source .env` then `.venv/bin/swl --base-dir /tmp/swl-r-entry-v1.9-continue wiki draft --task-id d0a84932a9f1 --topic "Test Architecture" --source-ref "file://workspace/docs/engineering/TEST_ARCHITECTURE.md"`
  - real draft output: `staged-1d1c4524 wiki_draft_staged source_count=1 prompt_artifact=/tmp/swl-r-entry-v1.9-continue/.swl/tasks/d0a84932a9f1/artifacts/wiki_compiler_prompt_pack.json result_artifact=/tmp/swl-r-entry-v1.9-continue/.swl/tasks/d0a84932a9f1/artifacts/wiki_compiler_result.json`
  - CLI review surface: `knowledge stage-inspect staged-1d1c4524` shows `source_pack_count: 1`, rationale, and text, but not the source pack anchor/preview details.
  - API review surface: `GET /api/knowledge/staged-1d1c4524` includes full `source_pack` with `resolved_path`, `span`, `content_hash`, `parser_version`, and preview.
  - refine dry-run drift: runbook command with `--topic` fails because current `wiki refine` does not accept `--topic`; current CLI also requires `--target`.
- fix verification:
  - branch: `fix/r19-004-wiki-dry-run-artifacts`
  - smoke_base_dir: `/tmp/swl-r19-004-wiki-dry-run-2`
  - smoke_task_id: `d052660f390b`
  - changed behavior: `wiki draft --dry-run` and `wiki refine --dry-run` now write `wiki_compiler_prompt_pack.json` and print its concrete `prompt_artifact` path.
  - artifact visibility: `task artifacts d052660f390b` lists `wiki_compiler_prompt_pack` and `wiki_compiler_result` under `Core Run Record`.
  - dry-run boundary: `knowledge stage-list --all` stays empty after dry-run, confirming no staged candidate is written.
  - validation: `.venv/bin/python -m pytest tests/integration/cli/test_wiki_commands.py tests/unit/orchestration/test_artifact_writer_module.py -q` -> `15 passed`.

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
- post-fix retest:
  - base_dir: `/tmp/swl-r-entry-v1.9-continue`
  - port: `8766`
  - `GET /` -> `200 text/html`
  - `GET /api/tasks` -> returned task `d0a84932a9f1`
  - `GET /api/tasks/d0a84932a9f1` -> returned `input_context.document_paths`, task knowledge, retrieval count, and action eligibility.
  - `GET /api/knowledge/staged` -> returned staged candidate `staged-1d1c4524`.
  - `GET /api/knowledge/staged-1d1c4524` -> returned staged candidate detail including source pack.
  - server stopped after smoke; follow-up health check returned `000`.

## R19-006 Post-fix declared-doc source scoping works on real design-doc flow

- status: observation
- severity: observation
- surface: retrieval
- task_id: `d0a84932a9f1`
- command: `.venv/bin/swl --base-dir /tmp/swl-r-entry-v1.9-continue task create ... --document-paths INVARIANTS.md --document-paths KNOWLEDGE.md --document-paths HARNESS.md --document-paths PROVIDER_ROUTER.md`, then `task run`.
- expected: declared docs persist into task input context, are visible through CLI/Web, and dominate retrieval when relevant.
- actual: `task inspect`, `task intake`, `state.json`, and `GET /api/tasks/d0a84932a9f1` all show four document paths. `retrieval_report.md` top references are from `docs/design/KNOWLEDGE.md` and each top hit shows `declared_document_priority=1000`.
- evidence:
  - artifact: `/tmp/swl-r-entry-v1.9-continue/.swl/tasks/d0a84932a9f1/state.json`
  - artifact: `/tmp/swl-r-entry-v1.9-continue/.swl/tasks/d0a84932a9f1/retrieval.json`
  - artifact: `/tmp/swl-r-entry-v1.9-continue/.swl/tasks/d0a84932a9f1/artifacts/retrieval_report.md`
  - report section: `Top References`
- likely next direction:
  - no phase; operator note only
- notes: This validates the R19-001 narrow fix. The remaining retrieval-quality concern is not source scoping itself, but truth reuse warning/reason wording in R19-003.

## R19-007 Runbook command drift around canonical list and wiki refine

- status: resolved
- severity: nit
- surface: docs
- task_id: `d0a84932a9f1`
- command: `.venv/bin/swl --base-dir /tmp/swl-r-entry-v1.9-continue knowledge list --status active`; `.venv/bin/swl --base-dir /tmp/swl-r-entry-v1.9-continue wiki refine ... --topic "Test Architecture" ... --dry-run`
- expected: runbook commands match the current CLI.
- actual: `knowledge list` is not a valid command in this build; `wiki refine` requires `--target` and does not accept `--topic`.
- evidence:
  - `knowledge list` error: `invalid choice: 'list'`
  - `wiki refine --help`: `--task-id`, `--mode`, `--target`, and `--source-ref` are accepted; no `--topic`.
- likely next direction:
  - docs/config hygiene
- notes: This is not runtime breakage, but it makes the runbook less copy-pasteable for future self-tests.
- fix verification:
  - branch: `fix/r19-007-runbook-command-drift`
  - changed behavior: `plan.md` now uses `knowledge canonical-audit` instead of nonexistent `knowledge list --status active`.
  - changed behavior: `wiki refine` now documents required `--target "$WIKI_TARGET"` and removes unsupported `--topic`.
  - adjacent cleanup: dry-run artifact discovery now points at `$BASE/.swl/tasks/$TASK_ID/artifacts` instead of the old `$BASE/artifacts/$TASK_ID` path.
  - validation: `.venv/bin/swl knowledge --help` confirms available knowledge subcommands; `.venv/bin/swl wiki refine --help` confirms required `--target` and no `--topic`; `rg` found no remaining stale active-runbook command pattern.

## Direction Gate Summary

Fill this after executing the runbook.

| Candidate | Evidence | Recommendation |
|---|---|---|
| Continue R-entry real usage | R19-006 verifies source scoping after the R19-001 fix; R19-002/R19-003/R19-004/R19-007 have narrow fixes verified; R19-005 Web smoke passed again. | Continue real usage with the corrected runbook; no current evidence requires broader retrieval architecture. |
| LTO-2 retrieval policy tuning | R19-001 and R19-003 are now resolved as narrow plumbing/reporting fixes. No current evidence requires broad retrieval architecture tuning. | Defer broad tuning unless later real runs show priority magnitude or filtering quality issues. |
| Wiki Compiler stage 3 | R19-004 dry-run artifact visibility is resolved; remaining Wiki ergonomics is mostly CLI stage-inspect source pack detail. | Defer broad stage 3 unless later real usage shows supersede/relation review friction. |
| D2 LTO-5 driven ports |  |  |
| Docs/config hygiene | R19-007 runbook command drift is resolved. | No open docs/config hygiene item from this findings log. |
