# Active Phase

Current active phase: Phase 5 closeout checkpoint.

## Current status

- Phase 0 accepted
- Phase 1 complete
- Phase 2 baseline complete
- post-Phase-2 retrieval baseline complete
- Phase 3 baseline complete
- Phase 4 baseline complete
- Phase 5 baseline complete

## Working references

- primary runtime status:
  - `/home/rocio/projects/swallow/current_state.md`
- system tracks:
  - `/home/rocio/projects/swallow/docs/system_tracks.md`
- Phase 3 closeout:
  - `/home/rocio/projects/swallow/docs/phase3_closeout_note.md`
- Phase 4 kickoff:
  - `/home/rocio/projects/swallow/docs/phase4_kickoff_note.md`
- Phase 4 task breakdown:
  - `/home/rocio/projects/swallow/docs/phase4_task_breakdown.md`
- Phase 4 closeout:
  - `/home/rocio/projects/swallow/docs/phase4_closeout_note.md`
- Phase 5 kickoff:
  - `/home/rocio/projects/swallow/docs/phase5_kickoff_note.md`
- Phase 5 task breakdown:
  - `/home/rocio/projects/swallow/docs/phase5_task_breakdown.md`
- Phase 5 closeout:
  - `/home/rocio/projects/swallow/docs/phase5_closeout_note.md`
- retrieval closeout:
  - `/home/rocio/projects/swallow/docs/post_phase2_retrieval_closeout_note.md`

## Current implementation baseline

The repository already has:

- a runnable CLI-first task loop
- retrieval for repo files and markdown notes
- explicit harness/runtime boundaries
- multiple local executor routes
- validation artifacts and task memory
- a completed Phase 2 router baseline with:
  - route declarations
  - route provenance
  - route-policy input via `route_mode`
  - compatibility policy outputs
  - remote-ready execution-site metadata
- a completed retrieval baseline with:
  - adapter seams
  - rerank/query shaping
  - task-artifact retrieval
  - retrieval-memory reuse
  - retrieval inspection artifacts
  - retrieval regression fixtures

## Current rule

New planning work should align with `docs/system_tracks.md` first and then the active Phase 5 closeout references above.

New implementation work should not fall back to a generic MVP framing or resume open-ended Phase 5 breadth by default.
