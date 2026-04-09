# Active Phase

Current active phase: Phase 9 Operator Control Workbench closeout checkpoint.

## Current status

- Phase 0 accepted
- Phase 1 complete
- Phase 2 baseline complete
- post-Phase-2 retrieval baseline complete
- Phase 3 baseline complete
- Phase 4 baseline complete
- Phase 5 baseline complete
- post-Phase-5 executor / external-input slice complete
- post-Phase-5 retrieval / memory next slice complete
- Phase 6 baseline complete
- Phase 7 baseline complete
- Phase 8 baseline complete
- Phase 9 baseline complete

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
- post-Phase-2 retrieval closeout:
  - `/home/rocio/projects/swallow/docs/post_phase2_retrieval_closeout_note.md`
- post-Phase-2 retrieval phase slice:
  - `/home/rocio/projects/swallow/.codex/phases/post_phase2_retrieval.md`
- post-Phase-5 executor / external-input phase slice:
  - `/home/rocio/projects/swallow/.codex/phases/post_phase5_executor_external_input.md`
- post-Phase-5 executor / external-input closeout:
  - `/home/rocio/projects/swallow/docs/post_phase5_executor_and_external_input_closeout_note.md`
- post-Phase-5 retrieval / memory next phase slice:
  - `/home/rocio/projects/swallow/.codex/phases/post_phase5_retrieval_memory_next.md`
- post-Phase-5 retrieval / memory next kickoff:
  - `/home/rocio/projects/swallow/docs/post_phase5_retrieval_memory_next_kickoff_note.md`
- post-Phase-5 retrieval / memory next breakdown:
  - `/home/rocio/projects/swallow/docs/post_phase5_retrieval_memory_next_task_breakdown.md`
- post-Phase-5 retrieval / memory next closeout:
  - `/home/rocio/projects/swallow/docs/post_phase5_retrieval_memory_next_closeout_note.md`
- Phase 6 kickoff:
  - `/home/rocio/projects/swallow/docs/phase6_kickoff_note.md`
- Phase 6 breakdown:
  - `/home/rocio/projects/swallow/docs/phase6_task_breakdown.md`
- Phase 6 closeout:
  - `/home/rocio/projects/swallow/docs/phase6_closeout_note.md`
- Phase 6 phase slice:
  - `/home/rocio/projects/swallow/.codex/phases/phase6.md`
- Phase 7 kickoff:
  - `/home/rocio/projects/swallow/docs/phase7_kickoff_note.md`
- Phase 7 breakdown:
  - `/home/rocio/projects/swallow/docs/phase7_task_breakdown.md`
- Phase 7 closeout:
  - `/home/rocio/projects/swallow/docs/phase7_closeout_note.md`
- Phase 7 phase slice:
  - `/home/rocio/projects/swallow/.codex/phases/phase7.md`
- Phase 8 kickoff:
  - `/home/rocio/projects/swallow/docs/phase8_kickoff_note.md`
- Phase 8 breakdown:
  - `/home/rocio/projects/swallow/docs/phase8_task_breakdown.md`
- Phase 8 closeout:
  - `/home/rocio/projects/swallow/docs/phase8_closeout_note.md`
- Phase 8 phase slice:
  - `/home/rocio/projects/swallow/.codex/phases/phase8.md`
- Phase 9 kickoff:
  - `/home/rocio/projects/swallow/docs/phase9_kickoff_note.md`
- Phase 9 breakdown:
  - `/home/rocio/projects/swallow/docs/phase9_task_breakdown.md`
- Phase 9 closeout:
  - `/home/rocio/projects/swallow/docs/phase9_closeout_note.md`
- Phase 9 phase slice:
  - `/home/rocio/projects/swallow/.codex/phases/phase9.md`

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

New planning work should align with `docs/system_tracks.md` first and then the active closeout references above.

New implementation work should not fall back to a generic MVP framing, resume open-ended Phase 8 evaluation/policy breadth, or resume open-ended Phase 9 workbench breadth by default.
