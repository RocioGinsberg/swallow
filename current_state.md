# Current Agent State

## Purpose

This file tracks the implementation status of the repository itself so work can resume quickly if the terminal session is interrupted.

## Current Status

- phase: Phase 0 accepted; Phase 1 in progress
- overall state: runnable, acceptance-validated, and partway through the Phase 1 execution plan
- last checked: 2026-04-08
- phase exit reference:
  - `docs/phase0_exit_checklist.md`
- phase 1 planning reference:
  - `docs/phase1_kickoff_plan.md`
  - `docs/phase1_task_breakdown.md`
- verification:
  - `python3 -m unittest discover -s tests`
  - `PYTHONPATH=src python3 -m swallow.cli --help`
  - `AIWF_EXECUTOR_TIMEOUT_SECONDS=10 PYTHONPATH=src python3 -m swallow.cli --base-dir /tmp/aiwf-exec-real task run <task-id>`

## Completed

- Added a Python package under `src/swallow/`.
- Added a minimal CLI with:
  - `swl task create`
  - `swl task run`
  - `swl task summarize`
  - `swl task resume-note`
  - `swl task validation`
  - `swl task grounding`
  - `swl task memory`
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
  - `validation_report.md` records validator findings in a human-readable form
  - `source_grounding.md` records the retrieval-backed citations and score context that grounded the run
  - `memory.json` records a compact reusable task-memory packet for later runs
- Phase 1 progress:
  - `P1-01` retrieval result shape and metadata baseline is implemented
  - `P1-02` source-aware chunking and ranking baseline is implemented for markdown notes and repo line chunks
  - `P1-03` harness retrieval boundary cleanup is implemented with explicit retrieval requests
  - `P1-04` executor selection seam baseline is implemented with explicit task-level selection and a second built-in executor path (`local`)
  - `P1-05` validator and execution-policy baseline is implemented with persisted validation results, validation events, and validator-driven terminal failure on blocking inconsistencies
  - `P1-06` artifact and memory tightening is implemented with persisted source grounding, reusable task memory, and rerun prompts that surface prior task artifacts

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
- New work should now be evaluated against Phase 1 goals unless it fixes a clear regression in the accepted Phase 0 loop.

## Known Issues

- A real `codex exec` run can still fail in this environment because outbound network/WebSocket connections are denied, so the adapter is structurally correct but not yet operationally reliable.
- The package metadata and CLI help text still describe the project as a Phase 0 bootstrap, which is correct for now but should be revised once the first real executor is integrated.

## Next Resume Step

1. Re-run the test suite.
2. Use `docs/phase1_kickoff_plan.md` and `docs/phase1_task_breakdown.md` as the active planning references for Phase 1.
3. Revisit Phase 1 scope and decide whether to harden current slices or define the first Phase 2 planning note.
4. Verify the editable install exposes the `swl` entrypoint correctly.
5. Update this file after each substantial code change.

## Resume Command

Use this first after reopening the terminal:

```bash
cd /home/rocio/projects/swallow
sed -n '1,220p' current_state.md
```
