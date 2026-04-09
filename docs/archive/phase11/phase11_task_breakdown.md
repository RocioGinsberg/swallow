# Phase 11 Task Breakdown

This document turns the planning-and-knowledge-intake direction into small executable slices.

It should preserve:

- the accepted local task loop
- the completed Phase 9 operator-control baseline
- the completed Phase 10 resume-and-recovery baseline
- explicit task-semantics and knowledge-object truth
- explicit state, event, and artifact truthfulness

Status:

- planning baseline created on 2026-04-09
- current runtime reference: `current_state.md`
- kickoff reference: `docs/phase11_kickoff_note.md`
- prior closeout references:
  - `docs/phase9_closeout_note.md`
  - `docs/phase10_closeout_note.md`

## Working Rule

Every slice in this breakdown should preserve:

- truthful task intake and lifecycle status
- append-only event history
- inspectable task-semantics and knowledge artifacts
- explicit staged knowledge boundaries
- local-first default execution

Every phase closeout in this planning direction should also leave:

- synchronized status-entry documentation
- a short phase-local commit summary note under `docs/`

This breakdown is about tightening local planning and knowledge intake.

It is not about remote ingestion pipelines, generic chat memory, or broad front-end work.

## Recommended Order

1. `P11-01` Planning-handoff intake baseline
2. `P11-02` Staged knowledge-capture intake baseline
3. `P11-03` Imported-input inspection tightening
4. `P11-04` Task-semantics versus knowledge-object boundary tightening
5. `P11-05` Intake command and help alignment
6. `P11-06` Closeout, documentation synchronization, and commit-summary note

Current completion state:

- `P11-01` complete
- `P11-02` complete
- `P11-03` complete
- `P11-04` complete
- `P11-05` complete
- `P11-06` complete

## Tasks

### P11-01 Planning-Handoff Intake Baseline

Goal:
Add a narrow operator-facing way to turn imported planning into explicit task semantics without relying on long flag lists alone.

Scope:

- add a compact CLI planning-intake path
- preserve explicit task-semantics records and reports
- avoid creating a chat-history surrogate

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/orchestrator.py`
- `src/swallow/models.py`
- `tests/test_cli.py`

Validation:

- operators can create or enrich task semantics from imported planning with less friction
- imported planning still lands in explicit task-semantics artifacts

Non-goals:

- generic conversation import
- task planning automation

### P11-02 Staged Knowledge-Capture Intake Baseline

Goal:
Add a narrow operator-facing way to attach staged knowledge to a task after creation.

Scope:

- add a compact CLI knowledge-intake path
- preserve staged knowledge-object records
- preserve explicit evidence and source metadata

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/store.py`
- `src/swallow/models.py`
- `tests/test_cli.py`

Validation:

- operators can attach staged knowledge without recreating the task
- knowledge objects remain explicit, staged, and inspectable

Non-goals:

- automatic canonicalization
- background sync with note sources

### P11-03 Imported-Input Inspection Tightening

Goal:
Make imported planning and imported knowledge easier to inspect from current workbench entrypoints.

Scope:

- tighten `inspect`, `review`, or new compact commands around imported-input visibility
- keep operator-facing output concise and artifact-backed
- preserve current task and knowledge boundaries

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/harness.py`
- `tests/test_cli.py`

Validation:

- imported-input state is visible without opening raw JSON first
- inspection remains aligned with current artifact truth

Non-goals:

- broad inspect redesign
- hidden imported-input state

### P11-04 Task-Semantics Versus Knowledge-Object Boundary Tightening

Goal:
Make the difference between imported task semantics and imported knowledge more operator-readable.

Scope:

- tighten reports or inspection output around task intent versus reusable knowledge
- preserve staged knowledge boundaries and task linkage
- avoid collapsing both into a single imported-context bucket

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/knowledge_objects.py`
- `tests/test_cli.py`

Validation:

- operators can tell what shapes task execution intent versus reusable evidence
- reports stay explicit and compact

Non-goals:

- full ontology redesign
- retrieval-policy expansion

### P11-05 Intake Command And Help Alignment

Goal:
Align command naming, help text, and README guidance with the tighter planning and knowledge intake surface.

Scope:

- align CLI help around the new intake paths
- update README references where needed
- keep intake entrypoints understandable in a fresh session

Likely affected areas:

- `src/swallow/cli.py`
- `README.md`
- `README.zh-CN.md`
- `current_state.md`
- `tests/test_cli.py`

Validation:

- intake entrypoints are discoverable without reading implementation code
- help output makes planning-handoff versus knowledge-capture boundaries clearer

Non-goals:

- broad documentation redesign
- non-CLI interfaces

### P11-06 Closeout, Documentation Synchronization, And Commit-Summary Note

Goal:
Close the phase by aligning status documents and leaving a short commit-summary artifact for manual Git submission.

Scope:

- align status-entry documents with the resulting Phase 11 baseline
- write a Phase 11 closeout note
- write `docs/phase11_commit_summary.md` as a short reusable commit-summary note
- ensure planning-entry references point to the right checkpoint

Likely affected areas:

- `docs/phase11_closeout_note.md`
- `docs/phase11_commit_summary.md`
- `current_state.md`
- `AGENTS.md`
- `README.md`
- `README.zh-CN.md`
- `.codex/`

Validation:

- status documents agree on the resulting checkpoint
- a short commit-summary note exists for manual reuse

Non-goals:

- broader repo-documentation cleanup unrelated to Phase 11

## Deferred Items

Keep these outside the active Phase 11 task list unless a concrete implementation need appears:

- remote planning-ingestion services
- generic chat transcript capture
- automatic knowledge promotion
- note-system sync daemons
- full desktop intake forms
- large workbench redesign

## Summary

Phase 11 should start from local planning-handoff and staged-knowledge intake ergonomics in the accepted CLI workbench rather than from broader chat-interface or ingestion-platform work.
