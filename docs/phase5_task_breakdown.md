# Phase 5 Task Breakdown

This document turns the Phase 5 kickoff direction into concrete implementation tasks.

It is intentionally small. The goal is to make reusable capability pieces explicit and inspectable without turning the repository into a marketplace or platform too early.

Status:

- planning baseline created on 2026-04-08
- current runtime reference: `current_state.md`
- kickoff reference: `docs/phase5_kickoff_note.md`
- closeout reference: `docs/phase5_closeout_note.md`
- prior closeout references:
  - `docs/phase4_closeout_note.md`
  - `docs/phase3_closeout_note.md`
  - `docs/post_phase2_retrieval_closeout_note.md`

## Working Rule

Phase 5 should preserve the accepted loop and all current artifact contracts:

- truthful lifecycle status
- truthful phase progression
- append-only event history
- inspectable artifacts
- separate routing, topology, retrieval, validation, and workbench records
- local-first default execution

Each task below should improve capability declaration and inspection without changing where task truth lives.

## Task Order

Recommended implementation order:

1. `P5-01` Capability manifest baseline
2. `P5-02` Capability assembly record baseline
3. `P5-03` Task-level capability selection baseline
4. `P5-04` Capability inspection path baseline
5. `P5-05` Capability validation baseline
6. `P5-06` Capability closeout tightening

Current completion state:

- `P5-01` completed
- `P5-02` completed
- `P5-03` completed
- `P5-04` completed
- `P5-05` completed
- `P5-06` completed

## Closeout Judgment

The planned Phase 5 baseline is complete enough to stop open-ended `Capabilities` expansion by default.

The accepted Phase 5 outcome is a local-first capability baseline with:

- explicit requested manifests
- explicit effective assembly records
- task-level selection at create and run time
- operator-facing inspection
- clear failure for unknown capability references

Further capability breadth should begin from a fresh planning note, not from implicit continuation of the completed Phase 5 slice.

## Tasks

### P5-01 Capability Manifest Baseline

Goal:
Define a small manifest shape that can describe a task’s requested capability pieces explicitly.

Scope:

- introduce a minimal capability manifest or selection schema
- keep the initial supported pieces intentionally narrow
- persist the requested capability selection with task state

Likely affected areas:

- `src/swallow/models.py`
- `src/swallow/orchestrator.py`
- `src/swallow/cli.py`
- `tests/test_cli.py`

Validation:

- manifest shape is explicit and testable
- task creation can persist a requested capability selection
- current task loop remains unchanged when no capability selection is provided

Completion note:

- implemented with a small `CapabilityManifest` shape and a local-first default manifest
- `swl task create` now accepts repeatable `--capability kind:ref` entries and persists the requested manifest into task state and `task.created` events

Non-goals:

- plugin discovery
- remote manifests
- broad schema versioning

### P5-02 Capability Assembly Record Baseline

Goal:
Make the effective capability set for a task explicit instead of only inferring it from code and defaults.

Scope:

- build a small capability-assembly record from the requested selection
- persist it for later inspection
- keep assembly logic deterministic and local-first

Likely affected areas:

- `src/swallow/capabilities.py`
- `src/swallow/store.py`
- `src/swallow/orchestrator.py`
- `tests/test_cli.py`

Validation:

- a task has a stable assembled capability record
- default tasks still receive a valid baseline capability assembly
- assembly output is understandable without reading code

Completion note:

- implemented with a deterministic local-first capability assembly record
- tasks now persist `capability_assembly.json` alongside `state.json`
- `task.created` events and task state now distinguish requested capability manifest from effective capability assembly

Non-goals:

- dynamic runtime plugin loading
- remote dependency resolution

### P5-03 Task-Level Capability Selection Baseline

Goal:
Let an operator choose a small capability set at task creation or run time.

Scope:

- add CLI support for task-level capability selection
- define clear override or persistence behavior
- keep selection explicit and small

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/orchestrator.py`
- `tests/test_cli.py`

Validation:

- capability selection persists correctly
- repeated runs preserve or intentionally override the selection
- invalid combinations fail clearly

Completion note:

- implemented with repeatable `swl task run --capability kind:ref` overrides
- run-time overrides now update the persisted capability manifest and capability assembly before the run begins
- `task.run_started` events now carry the effective capability manifest and assembly for the current attempt

Non-goals:

- large profile grammars
- capability dependency solvers

### P5-04 Capability Inspection Path Baseline

Goal:
Add an operator-facing inspection path for the task’s effective capability assembly.

Scope:

- add a CLI command to print the capability assembly for a task
- keep output concise and inspection-oriented
- align the command with existing task inspection patterns

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Validation:

- operators can inspect capability assembly without reading raw state files
- output clearly distinguishes requested capability selection from effective assembly

Completion note:

- implemented with `swl task capabilities <task-id>` and `swl task capabilities-json <task-id>`
- operators can now inspect requested capability manifest and effective assembly separately without reading raw `state.json`

Non-goals:

- graphical capability browsers
- broad registry management flows

### P5-05 Capability Validation Baseline

Goal:
Introduce a small validation layer for capability references and capability assembly integrity.

Scope:

- fail clearly for unknown or unsupported capability references
- keep validation explicit and artifact-backed where useful
- avoid turning this into a full dependency manager

Likely affected areas:

- `src/swallow/capabilities.py`
- `src/swallow/orchestrator.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Validation:

- success and failure cases are testable
- invalid capability references produce clear operator-facing feedback
- current baseline task flow is not broken by validation checks

Completion note:

- implemented with a small known-capability allowlist for the current baseline
- unknown capability refs now fail clearly during task creation or run-time override instead of being silently accepted
- validation remains intentionally narrow and does not introduce dependency solving or external registry logic

Non-goals:

- full package management
- external registries

### P5-06 Capability Closeout Tightening

Goal:
Close the Phase 5 baseline by tightening naming, inspection flow, and documentation around capability assembly.

Scope:

- align CLI help and README wording with the accepted capability baseline
- keep capability roles distinct from routing, retrieval, and workbench roles
- confirm the capability baseline is understandable in a new session

Likely affected areas:

- `src/swallow/cli.py`
- `README.md`
- `README.zh-CN.md`
- `current_state.md`
- `tests/test_cli.py`

Validation:

- help text matches actual capability commands
- documentation matches the real operator flow
- new-session bootstrap can reach capability planning and inspection quickly

Completion note:

- CLI help and README now describe the capability manifest, assembly, override, and inspection paths coherently
- the full `P5-01` through `P5-06` baseline is now complete enough for a dedicated Phase 5 closeout judgment

Non-goals:

- capability marketplaces
- UI-heavy capability management

## Deferred Beyond This Breakdown

Keep these outside the active Phase 5 task list unless a concrete implementation need appears:

- plugin marketplaces
- remote capability registries
- broad discovery protocols
- package or version solvers
- graphical capability management interfaces

## Planning Judgment

Phase 5 should start from explicit local-first capability assembly rather than from registry breadth or marketplace ambition.

If later planning changes the primary track, this breakdown should be updated rather than half-followed.
