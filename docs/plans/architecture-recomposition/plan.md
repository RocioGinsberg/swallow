---
author: codex
phase: architecture-recomposition
slice: architecture-program-plan
status: approved
depends_on:
  - docs/design/INVARIANTS.md
  - docs/design/ARCHITECTURE.md
  - docs/design/INTERACTION.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/GOF_PATTERN_ALIGNMENT.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/roadmap.md
---

TL;DR:
Architecture Recomposition turns the desired deep refactor into a multi-phase program under `LTO-3`.
It uses GoF-style responsibility language, test harness work as the first execution dependency, and named architecture subtracks.
The first implementation phase should be small: test harness foundation plus one facade-first pilot, not a big-bang rewrite.

# Architecture Recomposition Plan

## Frame

- long_term_goal: `LTO-3`
- name: `Architecture Recomposition / Deep Refactor Program`
- primary track: `Architecture / Engineering`
- intent: coordinate deeper system refactors across interface, application, domain, persistence, orchestration, provider routing, knowledge, surface, and governance boundaries.
- stance: program-level roadmap plus small implementation phases; no single PR should attempt the full recomposition.

## Current Scope And Status

This file is the current active plan, but it has two levels:

1. **Program plan**: the ordered architecture recomposition subtracks.
2. **First implementation branch plan**: the bounded Architecture Recomposition first branch.

The first branch is intentionally narrow. It may include:

- minimum test helper seed.
- Knowledge Plane facade pilot.
- one optional application query/command pilot if the test harness is stable.

As of the current branch, the helper seed and Knowledge Plane facade have been committed, and the optional Control Center query pilot has also been committed. The next step for this plan is therefore **M6 closeout and next subtrack selection**, not continuing into Provider Router, Orchestration, Surface, or Governance subtracks on the same implicit authorization.

Any Provider Router split, orchestration lifecycle decomposition, surface command split, or governance apply handler split needs a separate subtrack gate or a revised plan before implementation.

## Why This Exists

The long-term architecture goals identify real local refactor needs, but they are not independent cleanups. They interact through shared constraints:

- CLI and FastAPI must converge on application commands / queries.
- SQLite stays local-first truth behind repository facades.
- Orchestrator remains the Control Plane owner.
- Provider Router still governs Path A / C but not Path B.
- `apply_proposal` remains the only public mutation entry for canonical / route / policy truth.
- Tests need a stronger TDD harness before broad module movement.

Architecture Recomposition is the program wrapper that makes those dependencies explicit.

## Goals

1. Define the execution order for deeper refactor work:
   - test harness foundation
   - Knowledge Plane facade
   - application command/query pilot
   - Provider Router split
   - Orchestration lifecycle decomposition
   - Surface command split
   - Governance private handler split
2. Keep public behavior stable through facade-first migration.
3. Make every subtrack reviewable and reversible.
4. Ensure each subtrack has focused tests before or with implementation.
5. Prevent cross-cutting refactor drift from weakening `docs/design/INVARIANTS.md`.

## Non-Goals

- Do not rewrite CLI, Orchestrator, Provider Router, Knowledge Plane, and Governance in one phase.
- Do not change design semantics in `docs/design/*.md`.
- Do not move Control Plane authority away from Orchestrator / Operator.
- Do not make FastAPI a second business implementation or second Orchestrator.
- Do not split SQLite truth into an external service.
- Do not bypass `apply_proposal`.
- Do not perform broad file moves without a compatibility facade and focused tests.
- Do not implement Planner / DAG / Strategy Router as part of AD0.
- Do not implement LLM Wiki Compiler as part of AD0.

## Design And Engineering Anchors

- `docs/design/INVARIANTS.md`
  - Control only in Orchestrator / Operator.
  - Execution never writes Truth directly.
  - Path A/B/C boundaries remain.
  - `apply_proposal` remains the only canonical / route / policy mutation entry.
- `docs/design/INTERACTION.md`
  - CLI normal commands call application layer in-process.
  - Browser / desktop UI uses local loopback FastAPI.
  - FastAPI is an adapter.
- `docs/engineering/CODE_ORGANIZATION.md`
  - local-first clean monolith
  - interfaces -> application -> domain/governance -> repository ports -> SQLite/filesystem
  - facade-first migration discipline
- `docs/engineering/GOF_PATTERN_ALIGNMENT.md`
  - patterns are responsibility language, not decorative abstraction
  - facade, command, repository, adapter, value object, state, pipeline guide the refactor
- `docs/engineering/TEST_ARCHITECTURE.md`
  - build helpers and layer split before broad module movement
  - keep invariant guards prominent

## Program Topology

| Subtrack | Owning LTO | Main Boundary | Primary Pattern Language | Default Rule |
|---|---|---|---|---|
| Program plan / dependency order | LTO-3 | architecture recomposition sequence | Facade, Command, Repository, Adapter | docs-only, no runtime move |
| Test harness foundation | LTO-4 | test helpers and layered test seed | Builder, Fixture, CLI runner, Guard helpers | helpers first, test moves second |
| Knowledge Plane API | LTO-6 | public knowledge facade | Facade, Repository, Value Object | add facade before moving internals |
| Application command/query boundary | LTO-5 | shared application layer | Command, Query, Adapter | pilot one surface first |
| Provider Router internals | LTO-7 | provider router modules | Facade, Strategy, Registry, Adapter | keep `router.py` compatibility facade |
| Orchestration lifecycle | LTO-8 | task lifecycle and execution flow | Template Method, State, Observer | helpers cannot own Control Plane advancement |
| Surface command families / meta optimizer | LTO-9 | CLI and optimizer modules | Command, Adapter, Facade | behavior-preserving split |
| Governance private handlers | LTO-10 | internal apply handlers | Facade, Command Handler, Repository | `apply_proposal` stays public entry |

## Suggested First Implementation Phase

The first code phase should not attempt the full architecture program. Recommended first phase:

`Architecture Recomposition First Branch`

Scope:

- create minimal `tests/helpers/` foundation:
  - workspace builder
  - CLI runner
  - common JSON / event / artifact assertions
- move or add only a small number of tests to prove the helper pattern
- add a Knowledge Plane facade with backwards-compatible imports
- migrate a small number of upper-layer call sites to the facade
- optionally add one application query pilot only if the test harness is stable

Exit criteria:

- no CLI behavior change
- no Truth schema change
- invariant guards pass
- full pytest passes
- public imports remain compatible

## Milestone Plan

| Milestone | Scope | Risk | Gate |
|---|---|---|---|
| M0 | Architecture roadmap + program plan | low | docs diff review |
| M1 | Minimum helpers and CLI runner | medium | focused helper tests + current CLI focused tests |
| M2 | Move or add first focused tests into target test layers | medium | collect-only + focused pytest |
| M3 | Knowledge Plane facade skeleton | medium | import compatibility tests |
| M4 | Migrate limited Knowledge Plane callers | medium | focused knowledge / retrieval / CLI tests |
| M5 | Optional application query/command pilot | medium-high | one surface only, full regression |
| M6 | Closeout and next subtrack selection | low | full pytest + guard + diff hygiene |

## Subtrack Entry Criteria

Before starting each architecture subtrack:

- Identify the compatibility facade.
- Identify which existing callers must remain unchanged.
- Add or select focused tests that fail if the boundary is broken.
- Confirm no `docs/design/INVARIANTS.md` boundary is weakened.
- Define rollback as removing the new facade migration without data/schema loss.

## Risk Controls

| Risk | Control |
|---|---|
| Big-bang rewrite | One subtrack per phase, one facade per milestone. |
| Import churn without benefit | New modules must own a real responsibility: command, query, repository port, adapter, policy, value object, lifecycle step. |
| Hidden behavior changes | Behavior-preserving moves use old assertions first; assertion improvements are separate commits. |
| Control authority drift | Orchestration helpers cannot advance task state independently. |
| Truth boundary drift | Repositories protect writes; `apply_proposal` facade stays unique. |
| Test instability | Test helpers and collect-only checks precede broad moves. |

## Validation Baseline

Minimum checks for architecture implementation phases:

```bash
.venv/bin/python -m pytest tests/test_invariant_guards.py -q
.venv/bin/python -m compileall -q src/swallow
.venv/bin/python -m pytest -q
git diff --check
```

Additional focused checks are selected per subtrack.

## Completion Conditions For Program Plan

- `docs/roadmap.md` names the relevant `LTO-*` goals and near-term phase tickets.
- This plan records the program topology, non-goals, risk controls, and first implementation recommendation.
- No runtime code changes are required for AD0.
- The next implementation phase can be planned as a bounded first branch instead of an unbounded architecture rewrite.
