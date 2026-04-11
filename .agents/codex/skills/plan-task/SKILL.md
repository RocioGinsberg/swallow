---
name: plan-task
description: Use this skill when a task needs to be broken into a small, executable plan aligned with the current system tracks and active phase slice, with clear scope, affected modules, validation steps, and non-goals.
---

# Plan Task

## Purpose

Use this skill to convert a request into a compact implementation plan aligned with the current system tracks and active phase slice.

## When to use

Use this skill when:
- a task spans multiple modules
- the next implementation steps are not yet concrete
- phase scope needs to be enforced explicitly
- the work risks drifting into later-phase abstractions

## Workflow

1. Read `docs/system_tracks.md`.
2. Read the active phase document in `.codex/phases/`.
3. Read the current execution status in `current_state.md`.
4. Restate the task in repository terms.
5. Identify the minimum useful outcome.
6. Identify likely affected files or modules.
7. Write a short step sequence.
8. Include validation steps.
9. State what is explicitly deferred.

## Output shape

Prefer this structure:
- goal
- scope
- affected areas
- implementation steps
- validation
- deferred items / non-goals

## Constraints

- Keep the plan small enough to execute incrementally.
- Prefer a working baseline over broad abstraction.
- Respect the current track priority and current phase boundary.
