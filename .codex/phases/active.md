# Active Phase

Current active phase: Phase 2.

## Current status

- Phase 0 accepted
- Phase 1 complete
- Phase 2 in progress

## Working references

- primary runtime status:
  - `/home/rocio/projects/swallow/current_state.md`
- Phase 2 kickoff:
  - `/home/rocio/projects/swallow/docs/phase2_kickoff_note.md`
- Phase 2 closeout:
  - `/home/rocio/projects/swallow/docs/phase2_closeout_note.md`
- Phase 2 task breakdown:
  - `/home/rocio/projects/swallow/docs/phase2_task_breakdown.md`

## Current implementation baseline

The repository already has:

- a runnable CLI-first task loop
- retrieval for repo files and markdown notes
- explicit harness/runtime boundaries
- multiple local executor routes
- validation artifacts and task memory
- a Phase 2 router baseline with:
  - route declarations
  - route provenance
  - route-policy input via `route_mode`
  - compatibility policy outputs
  - remote-ready execution-site metadata

## Current rule

New planning work should align with the Phase 2 references above, and new implementation work should not continue past the completed Phase 2 baseline without a fresh planning note.
