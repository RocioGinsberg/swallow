# Phase 11 Kickoff Note

This note defines the next planned phase after the completed Phase 10 Resume And Recovery Loop baseline.

It does not reopen any earlier completed closeout judgment:

- Phase 4 remains complete
- Phase 5 remains complete
- Phase 6 remains complete
- Phase 7 remains complete
- Phase 8 remains complete
- Phase 9 remains complete
- Phase 10 remains complete
- the post-Phase-2 retrieval baseline remains complete
- the post-Phase-5 executor / external-input slice remains complete
- the post-Phase-5 retrieval / memory-next slice remains complete

## Phase Name

Phase 11: Planning And Knowledge Intake Workbench

## Why This Phase Exists

The repository now has:

- explicit task-semantics ingestion for imported planning
- staged knowledge-object ingestion for external knowledge
- operator-facing inspect, review, queue, control, checkpoint, and recovery paths

What is still missing is a tighter operator-facing intake surface.

The system can already normalize external planning and external knowledge into explicit system objects, but the current operator path is still too flag-heavy when a user wants to:

- turn an external planning handoff into task semantics
- attach external knowledge to a task after creation
- inspect what was imported without reopening raw JSON first
- keep planning input and knowledge capture explicit without collapsing them into chat residue

Phase 11 should improve those intake and inspection entrypoints without turning the repository into a chat product or a generic note app.

## What Problem It Solves

Phase 11 is intended to move the `Workbench / UX` track from:

- strong operator control around existing task runs
- explicit imported task semantics and knowledge records

toward:

- easier planning-handoff intake
- easier knowledge-capture intake
- tighter inspection of imported planning and imported knowledge
- clearer boundaries between task intent, task semantics, and reusable knowledge

The goal is not to build a broad front-end. The goal is to make the current local CLI workbench more usable for explicit planning and knowledge ingestion now that the underlying truth already exists.

## Primary Track

- `Workbench / UX`

## Secondary Tracks

- `Core Loop`
- `Retrieval / Memory`

## Scope

Phase 11 should stay focused on:

- CLI entrypoints that reduce friction around external planning handoff
- CLI entrypoints that reduce friction around staged knowledge capture
- operator-facing inspection of imported planning and imported knowledge after task creation
- preserving explicit task-semantics and knowledge-object truth instead of inventing chat-only state
- closeout-time synchronization of status-entry documentation
- a short phase-local commit summary note that is easy to reuse when creating Git commits manually

## Non-Goals

Phase 11 is not for:

- broad desktop or web UI work
- automatic ingestion from chat transcripts
- hidden promotion of knowledge into canonical memory
- background sync with note systems
- broad retrieval redesign
- open-ended workbench polish unrelated to intake and imported-input inspection

## Key Design Principles

- Imported planning should become explicit task semantics, not loose conversation history.
- Imported knowledge should remain staged, citable, and reviewable.
- Task-intake ergonomics should improve without hiding where truth lives.
- Task semantics and knowledge objects should remain visibly different system concerns.
- Phase closeout should always synchronize user-facing and agent-facing status documents.
- Phase closeout should leave a short commit-summary artifact that can be reused when committing the phase manually.

## Current Direction

The current direction is to deepen `Workbench / UX` by making planning and knowledge intake:

- easier to initiate from the CLI
- easier to inspect after import
- easier to connect to task semantics, knowledge objects, and later retrieval reuse
- easier to use in a fresh session without remembering long lists of low-level flags

without drifting into chat-interface breadth or hidden ingestion automation.

## Proposed Work Items

Possible Phase 11 slices:

1. planning-handoff intake baseline
2. staged knowledge-capture intake baseline
3. imported-input inspection tightening
4. task-semantics versus knowledge-object boundary tightening
5. intake command/help alignment
6. closeout, status sync, and commit-summary note

## Stop / Go Framing

This note is a planning entrypoint, not an implementation claim.

Go:

- if the next step should improve planning or knowledge intake in the current local workbench
- if the next step should reduce operator stitching across create, inspect, review, and imported-input artifacts
- if the next step should preserve explicit task and knowledge object boundaries while improving CLI usability

Stop:

- if the work starts drifting into generic chat intake or conversation storage
- if the work starts automatically promoting knowledge without explicit staged truth
- if the work starts broadening into generic workbench polish without a planning-intake or knowledge-intake reason
