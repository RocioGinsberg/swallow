# Current Agent State

## Purpose

This file tracks the implementation status of the repository itself so work can resume quickly if the terminal session is interrupted.

## Current Status

- phase: Phase 0 accepted; Phase 1 complete; Phase 2 baseline complete; Phase 3 baseline complete; Phase 4 baseline complete
- overall state: runnable, acceptance-validated, and at a Phase 4 closeout checkpoint
- last checked: 2026-04-08
- phase exit reference:
  - `docs/phase0_exit_checklist.md`
- phase 1 planning reference:
  - `docs/phase1_kickoff_plan.md`
  - `docs/phase1_task_breakdown.md`
- phase 2 planning reference:
  - `docs/phase2_kickoff_note.md`
  - `docs/phase2_closeout_note.md`
  - `docs/phase2_task_breakdown.md`
- phase 3 planning reference:
  - `docs/phase3_kickoff_note.md`
  - `docs/phase3_task_breakdown.md`
  - `docs/phase3_closeout_note.md`
- phase 4 planning reference:
  - `docs/phase4_kickoff_note.md`
  - `docs/phase4_task_breakdown.md`
  - `docs/phase4_closeout_note.md`
- system planning reference:
  - `docs/system_tracks.md`
- post-Phase-2 retrieval planning reference:
  - `docs/post_phase2_retrieval_kickoff_note.md`
  - `docs/post_phase2_retrieval_task_breakdown.md`
  - `docs/post_phase2_retrieval_closeout_note.md`
- verification:
  - `python3 -m unittest discover -s tests`
  - `PYTHONPATH=src python3 -m swallow.cli --help`
  - `AIWF_EXECUTOR_TIMEOUT_SECONDS=10 PYTHONPATH=src python3 -m swallow.cli --base-dir /tmp/aiwf-exec-real task run <task-id>`

## Completed

- Added a Python package under `src/swallow/`.
- Added a minimal CLI with:
  - `swl task create`
  - `swl task run`
  - `swl task list`
  - `swl task inspect`
  - `swl task artifacts`
  - `swl task review`
  - `swl task summarize`
  - `swl task resume-note`
  - `swl task compatibility`
  - `swl task validation`
  - `swl task grounding`
  - `swl task memory`
  - `swl task compatibility-json`
  - `swl task route`
  - `swl task route-json`
  - `swl doctor codex`
- Added explicit modules for:
  - orchestrator
  - harness runtime
  - retrieval
  - state/event/artifact storage
- Updated the main README files with quickstart and CLI shape.
- Unified the repo and package references around `swallow`.
- Switched the documented test command to `unittest` so it matches the current dependency-light setup.
- Added a narrow `codex exec` adapter with:
  - mock mode for tests
  - timeout handling
  - executor prompt/output artifacts
  - terminal failure recording when executor runs stall or fail
- Improved the live executor adapter by:
  - using `codex exec --output-last-message` for more stable result capture
  - using `--ephemeral` and `--color never` for cleaner non-interactive runs
  - preserving partial stdout/stderr on timeout for diagnosis
  - generating a structured fallback note on live executor failure without marking the task as successful
  - classifying failures into small explicit kinds such as `timeout`, `unreachable_backend`, `launch_error`, and `generic_failure`
  - giving `unreachable_backend` failures more specific recovery guidance in persisted artifacts
  - saving `executor_stdout.txt` and `executor_stderr.txt` as first-class diagnostic artifacts
  - adding `AIWF_EXECUTOR_MODE=note-only` for explicit non-live continuation-note generation

## Current Behavior

- Tasks are stored under `.swl/tasks/<task-id>/`.
- The run loop performs:
  - retrieval
  - executor prompt construction
  - explicit executor selection (`codex`, `local`, `mock`, or `note-only`)
  - validation over run outputs and artifact completeness
  - source-grounding and task-memory persistence for later review and reruns
  - summary, resume note, and validation artifact generation
- Failed executor runs now end in `status=failed` instead of leaving the task stuck in `running`.
- Task state semantics now match real execution timing:
  - `status` is lifecycle state, while `phase` is the current or last real workflow step
  - phase transitions happen only when retrieval, execution, or summarize actually start
  - final `completed` or `failed` is written only after `summary.md` and `resume_note.md` are persisted
- Event semantics are now clearer and more resume-friendly:
  - each run attempt starts with `task.run_started`
  - repeated `swl task run` calls append a new run segment to `events.jsonl`
  - retrieval, executor, artifact, and terminal task events now carry small structured payloads
- Artifact semantics are now clearer:
  - `summary.md` records what happened in the run
  - `resume_note.md` records what the next operator/session should do next
  - `route_report.md` records the selected route, route reason, and capability summary in a dedicated readable artifact
  - `compatibility_report.md` records whether the selected route matches the requested route policy baseline
  - `validation_report.md` records validator findings in a human-readable form
  - `source_grounding.md` records the retrieval-backed citations and score context that grounded the run
  - `memory.json` records a compact reusable task-memory packet for later runs
  - route records now also declare execution-site metadata such as `execution_site`, `remote_capable`, and `transport_kind` so later remote execution can be added without changing the current local behavior
- Phase 1 progress:
  - `P1-01` retrieval result shape and metadata baseline is implemented
  - `P1-02` source-aware chunking and ranking baseline is implemented for markdown notes and repo line chunks
  - `P1-03` harness retrieval boundary cleanup is implemented with explicit retrieval requests
  - `P1-04` executor selection seam baseline is implemented with explicit task-level selection and a second built-in executor path (`local`)
  - `P1-05` validator and execution-policy baseline is implemented with persisted validation results, validation events, and validator-driven terminal failure on blocking inconsistencies
  - `P1-06` artifact and memory tightening is implemented with persisted source grounding, reusable task memory, and rerun prompts that surface prior task artifacts
- Phase 2 progress:
  - `P2-01` route declaration and selection baseline is implemented with a small built-in router, declared route capabilities, and persisted route provenance in task state, events, summaries, resume notes, prompts, and task memory
  - `P2-02` richer route policy inputs are implemented with persisted `route_mode` policy selection and run-time route-mode overrides for `auto`, `live`, `deterministic`, `offline`, and `summary`
  - `P2-03` capability declaration refinement is implemented with a structured capability schema covering execution kind, tool-loop support, filesystem access, network access, determinism, and resumability
  - `P2-04` route provenance and artifact tightening is implemented with persisted `route.json`, readable `route_report.md`, route CLI inspection commands, and tighter route links inside summary, resume note, memory, and artifact indexes
  - `P2-05` backend-compatibility policy baseline is implemented with persisted `compatibility.json`, readable `compatibility_report.md`, compatibility events, route-policy fit checks, CLI inspection commands, and terminal failure on blocking compatibility mismatches
  - `P2-06` remote-ready hook baseline is implemented with explicit route execution-site metadata in route declarations, state, events, route artifacts, prompts, summaries, resume notes, and task memory while keeping all current routes local-only
  - Phase 2 closeout judgment is documented in `docs/phase2_closeout_note.md`, and no additional Phase 2 breadth should be added by default without a fresh planning note
- Post-Phase-2 retrieval planning:
  - `docs/post_phase2_retrieval_kickoff_note.md` defines the next retrieval direction: preserve the current local task loop and artifact semantics while improving retrieval quality, source coverage, and memory reuse
  - `docs/post_phase2_retrieval_task_breakdown.md` breaks that direction into `R1-01` through `R1-06`
  - `docs/post_phase2_retrieval_closeout_note.md` records the stop/go judgment for the completed retrieval baseline
  - `R1-01` retrieval adapter seam baseline is implemented with a dedicated retrieval-adapter module, explicit source-adapter selection for markdown notes and repo text, and additive `adapter_name` retrieval metadata while preserving current retrieval result and artifact semantics
  - `R1-02` query shaping and rerank baseline is implemented with explicit query preparation, stopword trimming, phrase and coverage-aware rerank signals, and additive scoring metadata while preserving current retrieval and grounding semantics
  - `R1-03` local source coverage expansion is implemented with explicit task-artifact retrieval support under `.swl/tasks/...`, a new `artifacts` source type, and additive artifact-scope metadata while keeping default retrieval behavior unchanged unless artifacts are explicitly requested
  - `R1-04` retrieval-memory reuse tightening is implemented with explicit retrieval snapshot fields in `memory.json`, persisted `retrieval.json` artifact paths in task memory, and rerun prompts that surface prior retrieval count, top references, grounding artifact, and retrieval record paths without hiding fresh retrieval behind an implicit cache
  - `R1-05` retrieval artifact indexing cleanup is implemented with a readable `retrieval_report.md`, explicit retrieval artifact links in summary/resume/memory, and CLI inspection commands for both `retrieval_report.md` and `retrieval.json`
  - `R1-06` retrieval evaluation fixture baseline is implemented with local fixture-based regression tests that cover note, repo, and task-artifact retrieval expectations without introducing a heavyweight evaluation framework
  - The post-Phase-2 retrieval closeout judgment is documented in `docs/post_phase2_retrieval_closeout_note.md`, and no additional retrieval breadth should be added by default without a fresh planning note
- System planning:
  - `docs/system_tracks.md` defines the repository’s long-running tracks so future phases can be scoped against a stable system map instead of treating each phase as a mixed bundle
  - `docs/phase3_kickoff_note.md` defines the next planned primary slice on the `Execution Topology` track
  - `docs/phase3_task_breakdown.md` breaks that direction into `P3-01` through `P3-06`
  - `docs/phase3_closeout_note.md` records the stop/go judgment for the completed Phase 3 baseline
  - `docs/phase4_kickoff_note.md` defines the next planned primary slice on the `Workbench / UX` track
  - `docs/phase4_task_breakdown.md` breaks that direction into `P4-01` through `P4-06`
  - `docs/phase4_closeout_note.md` records the stop/go judgment for the completed Phase 4 baseline
  - `P4-01` task list and summary baseline is implemented with `swl task list`, compact cross-task status summaries, stable most-recent-first ordering, and test coverage for empty and multi-task cases
  - `P4-02` task inspect and overview baseline is implemented with `swl task inspect`, a compact per-task overview of the latest attempt, route/topology, policy status, retrieval/memory availability, operator guidance, and key artifact links
  - `P4-03` artifact index tightening is implemented with `swl task artifacts`, grouped artifact-path presentation by operator concern while preserving existing artifact paths and file layout
  - `P4-04` review-focused resume path tightening is implemented with `swl task review`, a compact handoff-oriented summary of latest attempt outcome, blocking reason, next operator action, and canonical review artifacts without replacing `resume_note.md`
  - `P4-05` operator filter and attention baseline is implemented through `swl task list --focus ... [--limit N]`, with explicit state-driven views for `all`, `active`, `failed`, `needs-review`, and `recent`
  - `P4-06` CLI workbench closeout tightening is implemented with clearer help text, README quickstart alignment for the workbench commands, and test coverage for help output and list filters
  - `P3-01` execution-topology contract baseline is implemented with explicit topology fields in task state, persisted `topology.json`, readable `topology_report.md`, topology-aware event payloads, and separate route-versus-topology provenance in summaries, resume notes, and task memory
  - `P3-02` dispatch record and attempt identity baseline is implemented with stable per-run `attempt_id` sequencing, persisted `dispatch.json`, readable `dispatch_report.md`, dispatch timestamps, and attempt-aware event, summary, resume-note, state, and memory records
  - `P3-03` handoff artifact baseline is implemented with persisted `handoff.json`, readable `handoff_report.md`, explicit blocking reason and next-operator-action fields, and handoff links carried through summary, resume note, artifact paths, and task memory
  - `P3-04` topology-aware lifecycle semantics are implemented with explicit `execution_lifecycle` state, event, summary, resume-note, topology, dispatch, handoff, and memory fields so prepared, dispatched, and terminal execution states are recorded separately from task `status` and `phase`
  - `P3-05` execution-fit policy baseline is implemented with `execution_fit.json`, readable `execution_fit_report.md`, `execution_fit.completed` events, execution-fit status in terminal task payloads, and execution-fit links carried through summary, resume note, handoff, and task memory
  - `P3-06` operator inspection path tightening is implemented with dedicated CLI commands for topology, dispatch, handoff, and execution-fit artifacts and records, plus README updates so Phase 3 execution-topology outputs are inspectable without reading files manually

## Acceptance Result

- Phase 0 acceptance passed on 2026-04-07.
- Verified through:
  - unit test coverage
  - successful mock acceptance workflow
  - failed executor acceptance workflow
  - rerun validation showing append-only event history
- Acceptance confirmed that:
  - `state.json` truthfully reflects lifecycle status and real phase progression
  - `events.jsonl` truthfully reflects run boundaries and step ordering
  - `summary.md` works as the run record
  - `resume_note.md` works as the hand-off artifact

## Phase Boundary

- Phase 0 is complete enough to stop Phase 0-only cleanup work by default.
- Phase 1 is complete enough to stop Phase 1-only expansion work by default.
- The planned Phase 2 baseline is complete enough to stop open-ended Phase 2 backend expansion by default.
- The planned Phase 3 baseline is complete enough to stop open-ended execution-topology expansion by default.
- The planned Phase 4 baseline is complete enough to stop open-ended Workbench / UX expansion by default.
- New work should now begin from a fresh planning note rather than assuming more Phase 4 implementation slices exist.

## Known Issues

- A real `codex exec` run can still fail in this environment because outbound network/WebSocket connections are denied, so the adapter is structurally correct but not yet operationally reliable.
- Some deeper design and historical documents still describe earlier phases intentionally; user-facing entrypoints should stay aligned with the current post-Phase-2 baseline.

## Next Resume Step

1. Re-run the test suite.
2. Use `docs/system_tracks.md` as the system-map reference before starting new implementation.
3. Use `docs/phase3_closeout_note.md` as the execution-topology stop/go reference.
4. Use `docs/phase4_closeout_note.md` as the current Workbench / UX stop/go reference.
5. Use `docs/post_phase2_retrieval_closeout_note.md` as the current retrieval stop/go decision reference.
6. Use `docs/system_tracks.md` before writing the next planning note so the next slice is anchored to a primary track.
7. Verify the editable install exposes the `swl` entrypoint correctly.
8. Update this file after each substantial code change.

## Resume Command

Use this first after reopening the terminal:

```bash
cd /home/rocio/projects/swallow
sed -n '1,220p' current_state.md
```
