---
name: plan-task
description: Use this skill when a task needs to be broken into a small, executable Phase 0 plan with clear scope, affected modules, validation steps, and non-goals.
---

# Plan Task

## Purpose

Use this skill to convert a request into a compact implementation plan aligned with the current active phase.

## When to use

Use this skill when:
- a task spans multiple modules
- the next implementation steps are not yet concrete
- phase scope needs to be enforced explicitly
- the work risks drifting into later-phase abstractions

## Workflow

1. Read the active phase document in `.codex/phases/`.
2. Restate the task in repository terms.
3. Identify the minimum useful outcome.
4. Identify likely affected files or modules.
5. Write a short step sequence.
6. Include validation steps.
7. State what is explicitly deferred.

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
- Respect the current phase boundary.
