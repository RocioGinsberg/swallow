# Phase 0 Exit Checklist

This checklist defines the minimum exit bar for the Phase 0 CLI-first MVP.

It is intentionally narrow. The point is not to declare the system finished. The point is to decide whether the current repository has proven the smallest useful end-to-end loop strongly enough to move into Phase 1 work without carrying ambiguous Phase 0 expectations forward.

Status labels used here:

- `done`: implemented and aligned with the current Phase 0 intent
- `closeout`: still belongs to Phase 0 and should be tightened before declaring the phase complete
- `defer`: explicitly postpone to Phase 1 or later

## Orchestrator

- `done`: task intake exists through `swl task create`
- `done`: task execution exists through `swl task run`
- `done`: the orchestrator advances through a small explicit step sequence instead of hiding flow in a single opaque executor call
- `done`: `status` and `phase` now have distinct semantics
- `done`: `phase` now changes only when the task actually enters `intake`, `retrieval`, `executing`, or `summarize`
- `done`: terminal `completed` or `failed` is written only after final artifacts are persisted
- `done`: repeated runs now start with a new `task.run_started` event and do not overwrite prior history
- `closeout`: run preconditions are still minimal; there is no stronger guardrail around rerunning already-completed tasks or invalid task states
- `defer`: richer orchestration policies, branching flows, and multi-agent delegation

## Harness Runtime

- `done`: the harness runtime is separated from the orchestrator
- `done`: retrieval and execution are explicit harness steps rather than being collapsed into one monolithic action
- `done`: the harness writes executor prompt/output and terminal artifacts as part of the run loop
- `done`: mock and note-only execution modes support deterministic verification and explicit non-live continuation
- `closeout`: a real operator walkthrough should still confirm that the current create -> run -> summarize -> resume-note -> rerun path feels coherent in practice
- `defer`: richer validation hooks, second executors, longer-lived runtime sessions, and remote execution mechanics

## Capabilities

- `done`: the current built-in capability surface is intentionally small and inspectable
- `done`: Codex remains the primary local executor adapter for Phase 0
- `done`: retrieval is restricted to repository files and markdown notes, which matches current phase scope
- `closeout`: the repository still describes a minimal capability registry, but the Phase 0 implementation remains more implicit than explicit here
- `defer`: broader capability packs, validators, profiles, workflows, and marketplace-style extension surfaces

## State / Memory / Artifacts

- `done`: `state.json`, `events.jsonl`, `retrieval.json`, and task-scoped artifacts are persisted under `.swl/tasks/<task-id>/`
- `done`: state, events, and artifacts are now semantically distinct instead of overlapping in meaning
- `done`: `events.jsonl` is append-only and carries explicit run-attempt boundaries plus structured payloads for retrieval, execution, artifact writing, and terminal outcomes
- `done`: `summary.md` now acts as the run record
- `done`: `resume_note.md` now acts as the hand-off artifact for the next operator or session
- `done`: executor stdout and stderr are preserved as first-class diagnostics
- `closeout`: the repository still needs one explicit operator-facing validation pass to confirm the persisted outputs are sufficient for practical resume/review use
- `defer`: richer retrieval memory, artifact indexing, and stronger resume semantics across longer-running workflows

## Provider Router

- `done`: executor boundaries are kept narrow enough that broader provider routing has not leaked into Phase 0
- `done`: the current implementation keeps Codex as the default local executor without pretending to solve multi-provider compatibility early
- `defer`: provider routing, backend capability declarations, and broader executor selection policies

## Phase 0 Exit Decision

Phase 0 should be considered complete only when these conditions are all true:

1. The current CLI loop is semantically stable: create, run, inspect artifacts, and rerun all produce truthful state and event history.
2. The current artifacts are practically usable: `summary.md` and `resume_note.md` are good enough for a human or later agent session to resume work without reinterpreting the whole run from scratch.
3. Remaining known gaps are clearly classified as either:
   - Phase 0 closeout work
   - explicit Phase 1 work

## Recommended Final Phase 0 Closeout

Before declaring Phase 0 complete, do this minimal final pass:

1. Run one realistic operator workflow end to end on a real local task, not only through unit tests.
2. Judge the produced `state.json`, `events.jsonl`, `summary.md`, and `resume_note.md` as if they were the only materials available the next day.
3. Record any findings as:
   - one last Phase 0 cleanup item, if it affects truthfulness or usability of the MVP loop
   - or a Phase 1 backlog item, if it is mainly about quality, breadth, or extensibility

## Explicitly Deferred To Phase 1

- improved retrieval quality and scoring
- second executor support
- richer capability registry behavior
- validation policies beyond the current minimal loop
- stronger backend/executor abstraction
- any broader provider router work
