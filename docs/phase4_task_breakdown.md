# Phase 4 Task Breakdown

This document turns the Phase 4 kickoff direction into concrete implementation tasks.

It is intentionally small. The goal is to make the local CLI and artifact surface operate more like a usable workbench without expanding into a full UI platform.

Status:

- planning baseline created on 2026-04-08
- current runtime reference: `current_state.md`
- kickoff reference: `docs/phase4_kickoff_note.md`
- prior closeout references:
  - `docs/phase3_closeout_note.md`
  - `docs/post_phase2_retrieval_closeout_note.md`
- closeout reference:
  - `docs/phase4_closeout_note.md`

## Working Rule

Phase 4 should preserve the accepted loop and all current artifact contracts:

- truthful lifecycle status
- truthful phase progression
- append-only event history
- inspectable artifacts
- separate route, topology, dispatch, handoff, validation, compatibility, retrieval, and memory records
- local-first default execution

Each task below should improve operator usability without changing where task truth lives.

## Task Order

Recommended implementation order:

1. `P4-01` Task list and summary baseline
2. `P4-02` Task inspect and overview baseline
3. `P4-03` Artifact index tightening
4. `P4-04` Review-focused resume path tightening
5. `P4-05` Operator filter and attention baseline
6. `P4-06` CLI workbench closeout tightening

Current completion state:

- `P4-01` completed
- `P4-02` completed
- `P4-03` completed
- `P4-04` completed
- `P4-05` completed
- `P4-06` completed

## Tasks

### P4-01 Task List And Summary Baseline

Goal:
Add a compact task-list view so operators can browse existing tasks without opening task directories manually.

Scope:

- add a CLI command that lists tasks under `.swl/tasks`
- show stable summary columns such as:
  - task id
  - status
  - phase
  - latest attempt
  - updated-at or last-activity marker
- keep output deterministic and readable in plain terminal use

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Validation:

- multiple tasks render in a stable order
- different status combinations remain easy to distinguish
- no raw task-file inspection is required for basic browsing

Completion note:

- implemented with `swl task list`
- current output is a compact, deterministic tab-separated summary ordered by most recent `updated_at`

Non-goals:

- rich text tables
- fuzzy search
- remote task browsing

### P4-02 Task Inspect And Overview Baseline

Goal:
Add a single per-task overview path that aggregates the latest meaningful state for an operator.

Scope:

- add a CLI command that summarizes one task using current state and artifact paths
- surface:
  - latest attempt identity
  - route and topology summary
  - validation / compatibility / execution-fit status
  - retrieval / grounding / memory availability
  - next-operator guidance from current artifacts

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/store.py`
- `src/swallow/models.py`
- `tests/test_cli.py`

Validation:

- overview output remains truthful after repeated runs
- failed and completed tasks both render sensibly
- operators can decide what to inspect next from the overview alone

Completion note:

- implemented with `swl task inspect <task-id>`
- current output aggregates latest attempt identity, route/topology summary, policy statuses, retrieval/memory availability, operator guidance, and key artifact paths without replacing artifact-specific commands

Non-goals:

- replacing all artifact-specific inspection commands
- UI dashboards

### P4-03 Artifact Index Tightening

Goal:
Make artifact navigation easier by providing a more intentional artifact index instead of a flat path dump.

Scope:

- group artifact references by operator concern, such as:
  - core run record
  - retrieval and grounding
  - routing and topology
  - validation and policy
  - memory and resume
- expose the grouped artifact index through CLI and persisted summaries where helpful

Likely affected areas:

- `src/swallow/harness.py`
- `src/swallow/cli.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Validation:

- grouped artifact references remain complete
- existing artifact paths stay valid
- operators can find the right artifact faster than with the current flat shape

Completion note:

- implemented with `swl task artifacts <task-id>`
- current output groups artifact paths by operator concern instead of exposing only a flat path dump

Non-goals:

- filesystem reorganization
- artifact database layers

### P4-04 Review-Focused Resume Path Tightening

Goal:
Make resume and handoff review easier by tightening the operator-facing summary of what to do next.

Scope:

- improve how overview and resume-related commands surface:
  - blocking reason
  - next operator action
  - latest handoff status
  - latest attempt outcome
- keep `resume_note.md` as the canonical artifact while improving review entrypoints

Likely affected areas:

- `src/swallow/harness.py`
- `src/swallow/cli.py`
- `tests/test_cli.py`

Validation:

- failed and warning-heavy runs produce clearer next-action guidance
- no duplication conflict appears between overview output and `resume_note.md`

Completion note:

- implemented with `swl task review <task-id>`
- current output surfaces latest attempt outcome, handoff status, blocking reason, next operator action, and review artifact paths while keeping `resume_note.md` as the canonical persisted handoff artifact

Non-goals:

- inbox systems
- notifications

### P4-05 Operator Filter And Attention Baseline

Goal:
Let operators focus on tasks that likely need review or action instead of scanning the full task list every time.

Scope:

- add simple CLI filters or modes such as:
  - active
  - failed
  - needs-review
  - recent
- keep filter logic explicit and state-driven

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Validation:

- filters are deterministic
- attention views match actual task state and recent attempts
- mixed task sets stay understandable

Completion note:

- implemented as `swl task list --focus ... [--limit N]`
- current focus modes are `all`, `active`, `failed`, `needs-review`, and `recent`
- attention views remain explicit and state-driven rather than introducing a query language or background watcher

Non-goals:

- full query languages
- background watchers

### P4-06 CLI Workbench Closeout Tightening

Goal:
Close the Phase 4 baseline by making the CLI workbench paths coherent, documented, and easy to resume in a new session.

Scope:

- tighten naming and help text for the new task-browsing commands
- align README and state references with the accepted workbench baseline
- confirm the workbench additions do not blur artifact roles or lifecycle semantics

Likely affected areas:

- `src/swallow/cli.py`
- `README.md`
- `README.zh-CN.md`
- `current_state.md`
- `tests/test_cli.py`

Validation:

- help text matches real command behavior
- documentation matches actual operator flow
- new-session bootstrap can reach list, inspect, and artifact review paths quickly

Non-goals:

- large UI redesigns
- hosted workbench deployment

## Deferred Beyond This Breakdown

Keep these outside the active Phase 4 task list unless a concrete implementation need appears:

- desktop app frameworks
- web dashboards
- remote task browsers
- broader provider expansion
- deeper remote execution infrastructure
- broad capability marketplace work

## Planning Judgment

Phase 4 should start from the existing CLI and artifact truth rather than from a GUI ambition or another execution-topology expansion.

If later planning changes the primary track, this breakdown should be updated rather than half-followed.

## Closeout Judgment

The planned Phase 4 baseline is complete.

Do not continue Phase 4 by default through open-ended Workbench / UX expansion.

Use `docs/phase4_closeout_note.md` as the decision reference before starting follow-up work.
