---
author: codex
phase: architecture-recomposition
slice: ad0-program-plan
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
Candidate AD turns the desired deep refactor into a multi-phase architecture recomposition program.
It uses AC's GoF-style responsibility language, AA's test harness as the first execution dependency, and V/AB/W/X/Y/Z as ordered subtracks.
The first implementation phase should be small: test harness foundation plus one facade-first pilot, not a big-bang rewrite.

# Architecture Recomposition Plan

## Frame

- candidate: `AD`
- name: `Architecture Recomposition / Deep Refactor Program`
- primary track: `Architecture / Engineering`
- intent: coordinate deeper system refactors across interface, application, domain, persistence, orchestration, provider routing, knowledge, surface, and governance boundaries.
- stance: program-level roadmap plus small implementation phases; no single PR should attempt the full recomposition.

## Why This Exists

The existing roadmap candidates `AB/V/W/X/Y/Z` identify real local refactor needs, but they are not independent cleanups. They interact through shared constraints:

- CLI and FastAPI must converge on application commands / queries.
- SQLite stays local-first truth behind repository facades.
- Orchestrator remains the Control Plane owner.
- Provider Router still governs Path A / C but not Path B.
- `apply_proposal` remains the only public mutation entry for canonical / route / policy truth.
- Tests need a stronger TDD harness before broad module movement.

Candidate AD is the program wrapper that makes those dependencies explicit.

## Goals

1. Define the execution order for deeper refactor work:
   - AA test harness foundation
   - V Knowledge Plane facade
   - AB application command/query pilot
   - W Provider Router split
   - X Orchestration lifecycle decomposition
   - Y Surface command split
   - Z Governance private handler split
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

| Subtrack | Existing Candidate | Main Boundary | Primary Pattern Language | Default Rule |
|---|---|---|---|---|
| AD0 | AD | program plan / dependency order | Facade, Command, Repository, Adapter | docs-only, no runtime move |
| AD1 | AA | test harness foundation | Builder, Fixture, CLI runner, Guard helpers | helpers first, test moves second |
| AD2 | V | Knowledge Plane API | Facade, Repository, Value Object | add facade before moving internals |
| AD3 | AB | application command/query boundary | Command, Query, Adapter | pilot one surface first |
| AD4 | W | Provider Router internals | Facade, Strategy, Registry, Adapter | keep `router.py` compatibility facade |
| AD5 | X | orchestration lifecycle | Template Method, State, Observer | helpers cannot own Control Plane advancement |
| AD6 | Y | surface command families / meta optimizer | Command, Adapter, Facade | behavior-preserving split |
| AD7 | Z | governance private handlers | Facade, Command Handler, Repository | `apply_proposal` stays public entry |

## Suggested First Implementation Phase

The first code phase after AD0 should not attempt all of AD. Recommended first phase:

`Architecture Recomposition AD1/V Pilot`

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
| M0 | AD roadmap + program plan | low | docs diff review |
| M1 | AA minimum helpers and CLI runner | medium | focused helper tests + current CLI focused tests |
| M2 | Move or add first focused tests into target test layers | medium | collect-only + focused pytest |
| M3 | V Knowledge Plane facade skeleton | medium | import compatibility tests |
| M4 | Migrate limited Knowledge Plane callers | medium | focused knowledge / retrieval / CLI tests |
| M5 | Optional AB query/command pilot | medium-high | one surface only, full regression |
| M6 | Closeout and next subtrack selection | low | full pytest + guard + diff hygiene |

## Subtrack Entry Criteria

Before starting each AD subtrack:

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
| Test instability | AA helpers and collect-only checks precede broad moves. |

## Validation Baseline

Minimum checks for AD implementation phases:

```bash
.venv/bin/python -m pytest tests/test_invariant_guards.py -q
.venv/bin/python -m compileall -q src/swallow
.venv/bin/python -m pytest -q
git diff --check
```

Additional focused checks are selected per subtrack.

## Completion Conditions For AD0

- `docs/roadmap.md` names Candidate AD and its subtracks.
- This plan records the program topology, non-goals, risk controls, and first implementation recommendation.
- No runtime code changes are required for AD0.
- The next implementation phase can be planned as a bounded AA/V pilot instead of an unbounded architecture rewrite.
