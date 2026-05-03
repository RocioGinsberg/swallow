---
author: claude
phase: lto-13-fastapi-local-web-ui-write-surface
slice: architecture-identity
status: draft
depends_on:
  - docs/design/INVARIANTS.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/GOF_PATTERN_ALIGNMENT.md
---

TL;DR:
Swallow follows **Hexagonal Architecture (Ports & Adapters)**, adapted to a local-first single-user monolith.
This document is the project's architectural identity: it names the chosen style, names the patterns actually in use, and tracks the known deviations from the target with their repair directions.
It is not a rule book. `INVARIANTS.md` remains the constitution; `CODE_ORGANIZATION.md` remains the target shape; this file explains *what kind of architecture* both documents describe and where today's code stands relative to it.

# Architecture Decisions

> **Document discipline**
> Owner: Human
> Updater: Human / Claude / Codex
> Trigger: architectural style change, structural deviation discovered, deviation closed, or new design pattern adopted at a system boundary
> Anti-scope: 不维护 phase 状态、不替代 `INVARIANTS.md`、不重复 `CODE_ORGANIZATION.md` 的目标分层、不替 `GOF_PATTERN_ALIGNMENT.md` 列模式词汇表

This document answers three standing questions:

1. *What architectural style does Swallow follow?* — section §1
2. *Which standard design patterns are actually in use, and how healthy is each instance?* — section §2
3. *Where does today's code deviate from the target, and how should each deviation be repaired?* — section §3

Phase plans should consult §3 before adding new code at any of the listed deviations, so each phase moves the deviation toward repair rather than enlarging it.

---

## 1. Architectural Style

### 1.1 The Choice

Swallow follows **Hexagonal Architecture** (Alistair Cockburn's *Ports & Adapters*).

Layout, in Hexagonal vocabulary:

```text
            ┌─────────────────────────────────────────────────┐
            │  Driving adapters                               │
            │      adapters/cli       adapters/http       │
            │    (future) MCP server, desktop shell           │
            └────────────────────────┬────────────────────────┘
                                     │ calls driving ports
                                     ▼
            ┌─────────────────────────────────────────────────┐
            │  Application layer                              │
            │    application/commands/   (write use cases)    │
            │    application/queries/    (read use cases)     │
            └────────────────────────┬────────────────────────┘
                                     │ calls domain / driven ports
                                     ▼
            ┌─────────────────────────────────────────────────┐
            │  Domain & control plane                         │
            │    orchestration/    knowledge_retrieval/       │
            │    truth_governance/ provider_router/           │
            └────────────────────────┬────────────────────────┘
                                     │ calls driven adapters
                                     ▼
            ┌─────────────────────────────────────────────────┐
            │  Driven adapters / infrastructure               │
            │    truth_governance/sqlite_store.py             │
            │    truth_governance/repositories/file_store.py  │
            │    provider_router/ HTTP completion gateway     │
            │    knowledge_retrieval/ raw_material storage    │
            │    _io_helpers.py, surface_tools/paths.py       │
            └─────────────────────────────────────────────────┘
```

Hexagonal vocabulary used in this repo:

| Term | Meaning here |
|---|---|
| **Driving port** | A function in `application/commands/*` or `application/queries/*` that an adapter invokes |
| **Driving adapter** | A package in `surface_tools/{cli,web}/` that translates an external request (argv, HTTP) into a driving-port call |
| **Driven port** | A `Protocol` (or facade contract) the application layer depends on, e.g. `TaskStoreProtocol` in `truth_governance/store.py:151` |
| **Driven adapter** | A concrete implementation that fulfils a driven port, e.g. `DefaultTaskStore` (SQLite) and `FileTaskStore` (filesystem) |
| **Domain / control plane** | Layers between application and driven adapters that own task state, knowledge state, route state, and governance |

### 1.2 Why Hexagonal (and not the alternatives)

| Style | Fit | Reason |
|---|---|---|
| **Hexagonal / Ports & Adapters** | ★★★★★ | Local-first monolith with multiple surfaces sharing one core is the canonical use case. Multiple adapters (CLI today, web shipping in LTO-13, MCP / desktop later) all need the same `application/commands` / `application/queries`. |
| Clean Architecture | ★★★ | A superset of Hexagonal with explicit Use Case + Entity layers. Use cases are already implicit in `application/commands/*`; an Entity layer adds little for a metadata-driven LLM orchestration system. |
| Tactical DDD (Aggregate / Entity / VO / Domain Service / Repository) | ★★ | Swallow's domain is workflow orchestration — heavy on policy and state transitions, light on aggregate roots. Forcing tactical DDD vocabulary fights the codebase. |
| Vertical Slice Architecture | ★★ | Conflicts with the existing horizontal application/orchestration shape; would force per-use-case duplication of orchestration logic that is genuinely cross-cutting. |

**Hexagonal won by alignment with the existing shape**, not by aspirational rewrite. `CODE_ORGANIZATION.md §1 Target Shape` already drew the Hexagonal layout; this document makes the choice explicit and names it.

### 1.3 Constraints inherited from the choice

These are direct consequences of choosing Hexagonal; they apply without further argument:

- **Application layer stays framework-free.** No FastAPI, Pydantic, or click types appear in `application/commands` or `application/queries` signatures. Adapters do their own validation in their own dialect (Pydantic for web, click for CLI, Protocol-buffer types for future MCP).
- **Adapters do not implement business logic.** A driving adapter's only legitimate work is request parsing, response serialization, error mapping, and dependency resolution. It must not encode state-machine rules, proposal policy, or canonical knowledge logic.
- **Domain calls go through ports.** Application code depends on `Protocol` types or facade contracts, not on concrete persistence / IO modules. (This is the hardest constraint to honor today; see §3.2.)
- **Driven adapters are the only place where IO technology choices live.** SQLite knowledge does not leak into `application/commands`; HTTP-client knowledge does not leak into `provider_router/router.py`'s public surface.

---

## 2. Pattern Inventory

This section catalogs the standard design patterns actually used in Swallow today, distinguishing healthy from over-grown / mis-named instances. Patterns not listed are not currently in use; do not add them without a real change pressure (see `GOF_PATTERN_ALIGNMENT.md §1`).

### 2.1 Healthy instances

| Pattern | Where | Health note |
|---|---|---|
| **Facade** | `truth_governance/store.py` | Hides SQLite vs filesystem choice and atomic-write mechanics behind `save_state` / `load_state` / `append_event`. ~700 lines of internal logic; ~10-line public surface. Genuine facade. |
| **Facade** | `provider_router/router.py` | Hides 6 focused submodules (`route_registry`, `route_policy`, `route_metadata_store`, `route_selection`, `completion_gateway`, `route_reports`) behind a stable public API. Size and shape are healthy. |
| **Facade** | `truth_governance/governance.py` `apply_proposal` | The unique mutation entry for canonical knowledge / route metadata / policy. Behavior of the facade is locked by INVARIANTS §0; this is the strongest facade in the repo. |
| **Strategy** | `orchestration/executor.py` `run_executor` | Selects `ClaudeXMLDialect` or `FIMDialect` per task; algorithm is replaceable without touching callers. Healthy. |
| **Strategy** | `provider_router/route_selection.py` | Route decisions are pluggable; policy lookup is data-driven. Healthy. |
| **Repository (Protocol-based)** | `truth_governance/store.py:151` `TaskStoreProtocol` + `DefaultTaskStore` / `FileTaskStore` | Driven port + two implementations. The pattern exists at the type level but is not yet used uniformly by application code (see §3.2). |
| **Command (function form)** | `application/commands/*` | Each public function is a command; result dataclasses are outbound DTOs. The function-based form is intentional and works for synchronous local execution. Limitation noted in §3.4. |
| **Observer / Outbox** | `truth_governance/apply_outbox.py` + `append_event` | Decouples governance events from downstream consumers. Working but not yet durable (LTO-10 deferred). |

### 2.2 Mis-named / over-grown instances

These are recorded so future contributors do not mistake the existing code for healthy implementations of these patterns.

| Pattern | Where | What's wrong |
|---|---|---|
| **"Facade"** in name only | `knowledge_retrieval/knowledge_plane.py` | 98 lines, ~50 names, all of them direct re-exports from 7+ underlying modules. Hides nothing, defines no domain language, and is bypassed by application/commands/{knowledge,synthesis}.py which import the underlying modules directly. This is a **barrel file**, not a facade. See §3.1. |
| **Mediator** over-grown to **God Object** | `orchestration/orchestrator.py` | 3000+ lines mixing domain rules (state-machine decisions, retry policy evaluation), application service responsibilities (coordinating command execution), and infrastructure calls (SQLite writes, artifact serialization). LTO-8 has extracted 6 focused submodules but `orchestrator.py` itself remains a fused mass. See §3.3. |

### 2.3 Patterns deliberately not used

The patterns below have been considered and **rejected** for Swallow. Each rejection has a stated reason; do not re-introduce these patterns without first invalidating the reason.

| Pattern | Reason for rejection |
|---|---|
| **Singleton** | Conflicts with the project's dependency-injection style. `base_dir`, `OperatorToken`, and (per D6) `HttpClient` are all passed explicitly. Singleton would silently break test isolation and introduce monkey-patch points. Where "global uniqueness" is genuinely needed (e.g., loaded configuration), Python module-level functions plus `functools.cache` already provide it. |
| **Builder (GoF object form)** | Python's `dataclass` + keyword arguments + `__post_init__` validation already cover the cases GoF Builder solves in Java/C++ (many parameters, partial-fill, optional vs required). Existing `build_*` functions in the repo are factory functions, not GoF Builders — the naming should not be confused. Only consider GoF Builder if a genuine "construct in stages with observable intermediate state" requirement appears, which currently does not exist. |
| **GoF State Pattern (object-per-state)** | `TaskState` is a dataclass that is serialized to SQLite; `status` and `phase` are plain strings. Object-per-state would force either persisting full state objects (complex) or rebuilding them from strings on every read (no benefit). State-action matrix is also sparse and condition-driven (`status` × `phase` × `checkpoint_kind`), which makes object dispatch awkward. The right replacement is a **functional state machine** — pure functions like `can_run(state)`, `can_retry(state) -> (bool, reason)`, `next_phase_after(state, event)` — which is the natural target shape for D3's domain sub-layer and also satisfies LTO-13 R2-2 (eligibility flags exposed to UI). |
| **GoF Decorator (object-wrapping chains)** | Python function decorators (`@app.post`, `@dataclass`, `@functools.cache`) cover the practical use cases. Object-wrapping decorator chains (`LoggingExecutor(MetricsExecutor(BaseExecutor()))`) would duplicate concerns already addressed by the logging module, the Observer/Outbox event system, and `retry_policy.py`'s data-driven Strategy. Reconsider only if a real cross-cutting need emerges that cannot be satisfied by those mechanisms. |
| **Abstract Factory** | Construction is straightforward; dataclasses suffice. |
| **Visitor** | Domain objects are stable; visitor adds indirection without payoff. |

If a future phase needs one of these, it must invalidate the rejection reason in writing (not just claim necessity).

---

## 3. Known Deviations from the Hexagonal Target

Each deviation lists: **what is wrong**, **why it persists**, **what the repair looks like**, **trigger to start the repair**, and **rough size**. Phases should reference the deviation ID when work touches the affected area.

### 3.1 D1 — `knowledge_plane.py` is a barrel file masquerading as a facade

**What's wrong**: 50 transparent re-exports, no domain language of its own, bypassed in practice by `application/commands/{knowledge,synthesis}.py` which import from `canonical_registry`, `staged_knowledge`, `knowledge_store`, `knowledge_relations`, `ingestion.pipeline`, and `knowledge_suggestions` directly.

**Why it persists**: Originally introduced as a *migration shim* during knowledge layer extraction. Phase pressure has favored "ship the feature, migrate later"; LTO-13 added a new bypass (the staged-knowledge promote/reject routes go through `application/commands/knowledge.py` which is itself a bypass).

**Repair direction**:

- Replace 50 re-exports with 6–10 domain methods (`submit_staged`, `promote`, `reject`, `load_task_view`, `persist_task_view`, `search`, `record_decision`, ...).
- Rename underlying modules to `_internal_*` or move into a `knowledge_retrieval/internals/` subpackage.
- Migrate application + truth_governance imports to the new facade in one phase, not piecemeal.

**Trigger to start**: After LTO-13 closeout. Doing it concurrently with LTO-13 doubles the diff surface.

**Rough size**: Medium. ~10 import sites in `application/`; ~3 in `truth_governance/`; ~6 internal modules to relabel. One focused phase, ~3 commits.

**Roadmap home**: This is the new shape of LTO-6 (currently described as "touched-surface 慢推"). Recommend renaming LTO-6 to **"Knowledge Plane Facade Solidification"** and reclassifying it from passive ("migrate when touched") to active ("close the bypass").

### 3.2 D2 — Application layer reaches past driven ports

**What's wrong**: `application/commands/tasks.py` directly imports `swallow.orchestration.orchestrator.run_task`. `application/commands/knowledge.py` directly imports `knowledge_retrieval.knowledge_store.*`. There are no `Protocol` types between application and orchestration / knowledge layers, so application code is bound to concrete implementations.

**Why it persists**: Driven ports require explicit `Protocol` definitions and a place to put them. The codebase grew organically; ports were not the bottleneck while there was only one CLI surface.

**Repair direction**:

- Define driven ports under `application/ports/`:
  - `OrchestratorPort` — `run_task`, `create_task`, `acknowledge_task`, `retry_task`, `resume_task`
  - `KnowledgePort` — staged candidate lifecycle + canonical view operations
  - `ProposalPort` — review / apply proposal flow
  - `ProviderRouterPort` — route selection + completion
- Application functions accept the port as a parameter (or via a thin context object), rather than importing concretes.
- Concrete classes in `orchestration/`, `knowledge_retrieval/`, `truth_governance/`, `provider_router/` declare they implement the corresponding port.

**Trigger to start**: When a real second adapter (test double, alternative orchestrator implementation, or mock-based unit test of a command) is needed. LTO-13's HTTP adapter does not by itself create the trigger because it calls the same concretes the CLI calls.

**Rough size**: Large. ~30 application command functions × parameter signature change + adapter wiring. Best done as a sequence of 4–6 phases, one port at a time, in deliberate touched-surface fashion.

**Roadmap home**: This is LTO-5 ("repository ports") expanded. Recommend reframing LTO-5 from "repository ports only" to **"driven ports, in N phases, starting with TaskStoreProtocol"**.

### 3.3 D3 — `orchestrator.py` is a Mediator that has become a God Object

**What's wrong**: 3000+ lines containing domain rules (`_resolved_path_string`, retry-policy evaluation, checkpoint decisions), application coordination (`run_task`, `create_task`), and infrastructure calls (SQLite writes, artifact serialization). LTO-8 extracted 6 focused submodules, but the entry-point file still fuses all three concerns.

**Why it persists**: Each extraction has paid for itself, but the residual `orchestrator.py` is what binds them together; pulling it apart further requires deciding which residual responsibility lives where.

**Repair direction**:

- Split into three layers within `orchestration/`:
  - `domain/` — pure functions over `TaskState` (state-machine transitions, retry/resume eligibility, checkpoint snapshot evaluation). No IO.
  - `service/` — application service that composes domain rules + driven ports (`OrchestratorService.run_task` calling `domain.advance(state)` then `task_store.save(state)`).
  - `compatibility.py` — keep current public function names (`run_task`, `create_task`) as thin wrappers calling the service, until callers migrate.
- Pre-condition: D2 (driven ports) at least partially in place, otherwise the service layer ends up with the same import shape as today.

**Trigger to start**: When a second use case requires reusing domain rules without IO (e.g., a dry-run / preview API that evaluates eligibility without persisting; or a unit test of retry policy without a SQLite fixture).

**Rough size**: Very large. Multiple phases. Should not be attempted before D2 is partially complete.

**Roadmap home**: Successor to LTO-8 cluster. Defer until D1 + D2 first phase land.

### 3.4 D4 — `surface_tools/` mixes three layer-distinct kinds of code

**What's wrong**: `surface_tools/` currently houses three different things at once:

| File / package | Hexagonal classification |
|---|---|
| `adapters/cli.py` + `adapters/cli_commands/` | Driving adapter |
| `adapters/http/` | Driving adapter |
| `surface_tools/consistency_audit.py` | Application service (a use case) |
| `surface_tools/meta_optimizer.py` | Application service (a use case) |
| `surface_tools/paths.py`, `surface_tools/workspace.py` | Application infrastructure (workspace conventions) |

The name "surface_tools" predates the Hexagonal vocabulary and groups by "things that touch the user surface" — but driving adapters, application services, and application infrastructure are three different layers with three different rules. Mixing them invites the kind of boundary drift LTO-13 audit Round 3 surfaced (`globals().update`, web schema defaults encoding `planning_source="web"`).

**Why it persists**: `CODE_ORGANIZATION.md §2` already calls `surface_tools` a *transitional home* but provides no owner, no trigger, and no schedule for the shrink. Each phase adds new files to it because that is the shortest path.

**Repair direction**: Three independent renames, each a small pure-structural phase:

1. **Phase A (easy)**: `surface_tools/cli.py` + `surface_tools/cli_commands/` → `adapters/cli.py` + `adapters/cli_commands/`; `surface_tools/web/` → `adapters/http/`. Pure import-path update.
2. **Phase B (medium)**: `surface_tools/{consistency_audit,meta_optimizer}.py` → `application/services/` (or absorb into existing `application/commands/` if they have a single entry point each).
3. **Phase C (medium)**: `surface_tools/{paths,workspace}.py` → `application/infrastructure/` (or top-level `infrastructure/` if more driven adapters move there in D2 / D3).

After all three, `surface_tools/` package can be deleted entirely.

**Trigger to start**: After LTO-13 closeout; Phase A first, since LTO-13 just finished settling the web adapter shape and a fresh rename now is cheap.

**Rough size**: Three small phases of ~50–150 line diffs each, all pure structural moves.

**Roadmap home**: New cluster (post-LTO-13). Suggest naming **"Adapter / Service Boundary Cleanup"** with three sequenced sub-phases.

### 3.5 D5 — Adapter discipline is not codified

**What's wrong**: There is no standing rule preventing a driving adapter from doing application work. LTO-13 audit Round 3 found 6 instances where the web adapter implemented logic FastAPI / Pydantic should own (`http_models.py` hand-rolled response converters, `_status_for_value_error` string-matching error classification, `WebRequestError` reinventing `HTTPException`, `globals().update` ABI surgery, closure-captured `base_dir` instead of `Depends`, no `response_model=` or `@app.exception_handler`). Each instance was reasonable in isolation; collectively they re-implemented ~80% of what FastAPI already provides.

**Why it persists**: The plan-stage instinct treats every framework feature as "extra dependency surface" rather than as "the cheapest option". There is no document saying "use the framework primitive by default".

**Repair direction**: Add a document `docs/engineering/ADAPTER_DISCIPLINE.md` (separate from this one) that codifies:

- **Framework-Default Principle** — for any capability provided by FastAPI / Pydantic / click / uvicorn / future MCP framework, use the framework primitive by default. A documented reason is required to write a hand-rolled equivalent.
- **Adapter forbidden zone** — adapters do not encode state-machine rules, do not modify module globals, do not encode "I am which surface" in schema defaults, do not implement domain validation.
- **Adapter module layout** — for each adapter, a fixed file convention (e.g. for `adapters/http/`: `api.py` for routes, `schemas.py` for Pydantic request+response models, `dependencies.py` for `Depends` factories, `errors.py` for `@app.exception_handler` definitions).
- **Surface-identity rule** — "I am web / cli / mcp" lives in the adapter's `OperatorToken` construction, not in schema defaults or application logic.

**Trigger to start**: LTO-13 closeout — write the document with the 14 audit concerns from LTO-13 plan_audit as the worked examples, while the lessons are concrete.

**Rough size**: Single small phase, ~150 line document, no code change.

**Roadmap home**: Document-only phase between LTO-13 and the D4 sub-phases. Recommended name: **"Adapter Discipline Codification"**.

### 3.6 D6 — Outbound HTTP calls are scattered, with no client reuse

**What's wrong**: `httpx` is used as a module-level call site at five locations across three packages, with **no `httpx.Client` reuse**:

| Site | Style |
|---|---|
| `orchestration/executor.py:1180` | `httpx.post(...)` (sync, per-call) |
| `orchestration/executor.py:1302` | `async with httpx.AsyncClient(...) as client:` (per-call construct + teardown) |
| `provider_router/completion_gateway.py:41` | `httpx.post(...)` |
| `knowledge_retrieval/retrieval_adapters.py:219` | `httpx.post(...)` |
| `knowledge_retrieval/retrieval_adapters.py:519` | `httpx.post(...)` |

Every LLM call pays a fresh TCP + TLS handshake. There is no place to attach uniform retry, cost accounting, request logging, or timeouts. Configuration (timeout, headers, endpoint) is duplicated and read from environment variables at call time.

**Why it persists**: Each site grew with the feature it serves. There has been no second use case for HTTP-call configuration that would create the pressure to consolidate.

**Repair direction**:

- Define `HttpClientPort` as a driven port in `application/ports/http_client_port.py` (or co-located with D2's other ports).
- Implement a single driven adapter that holds an `httpx.Client` (or `httpx.AsyncClient`) plus its configuration (timeout / headers / retry policy / cost-attribution hook).
- Inject the port into `executor.run_http_executor` / `provider_router.completion_gateway` / `knowledge_retrieval.retrieval_adapters` rather than calling `httpx.post` at module level.
- Cost accounting (per §5 Q5) becomes a hook on the adapter, not a new module.
- Set the design rule "no module-level `httpx.*` calls outside `adapters/http_client/`" and add a guard test analogous to `test_ui_backend_only_calls_governance_functions`.

**Trigger to start**: After D2's first port (likely `TaskStorePort`) lands, since this is the same DI shape applied to a different driven adapter — the patterns reinforce each other and the second instance is much cheaper.

**Rough size**: Medium. ~5 call-site rewrites + 1 port + 1 adapter + 1 guard test. One focused phase, ~3 commits. The bulk of the diff is mechanical signature change at the call sites.

**Roadmap home**: Sub-phase of D2's port rollout, or independent if D2 is sequenced as multiple smaller phases. Anti-pattern: doing D6 *before* D2 means inventing a one-off DI scheme for HTTP that does not match the rest of the codebase — wait for D2's first port to set the convention.

---

## 4. How to Use This Document

- **In phase plans**: when a phase touches an area listed in §3, the plan must say whether it advances the deviation toward repair, holds the line, or temporarily enlarges it (with a written reason).
- **In `plan_audit`**: deviations are reviewable categories. A finding can be tagged "D2-relevant" rather than re-explained from scratch each time.
- **In `closeout`**: if a phase closed all or part of a deviation, the closeout updates §3 directly. If a deviation widened, the closeout records why.
- **Not a rule book**: this document does not add new rules. `INVARIANTS.md` is the constitution; `CODE_ORGANIZATION.md` is the target shape; `GOF_PATTERN_ALIGNMENT.md` is the pattern vocabulary; this document is the *mapping* between them and today's code.

---

## 5. Open Questions

These are items the document explicitly does not yet answer. Recording them prevents silent drift.

- **Q1**: When `application/commands/*` is migrated to driven ports (D2), do commands stay as functions or upgrade to objects? Object form would enable LTO-13 R2-1 fire-and-poll for long-running tasks (a `Command.execute_in_background()` pattern). Function form keeps the layer simpler. Defer until D2 first phase has data on call-site complexity.
- **Q2**: Where does `_io_helpers.py` belong in the Hexagonal layout? It currently sits at `src/swallow/_io_helpers.py` — neither application nor infrastructure. Likely target: `infrastructure/io.py` or absorbed into per-adapter helpers. Defer until D4 Phase C.
- **Q3**: Does `orchestration/harness.py` (the LLM execution harness) belong in `orchestration/` (control plane) or in a separate `harness/` peer package? It is large (1000+ lines after LTO-8) and has a different concept of state from task lifecycle. Defer until D3.
- **Q4**: The `provider_router/` package is well-encapsulated as a facade today (§2.1) but its public surface mixes "select a route" and "perform a completion call". Do these belong in one package or two? Defer pending real coupling pain.
- **Q5**: Cost / budget tracking lives in two places today — `orchestration/execution_budget_policy.py` (per-call token-cost evaluation) and `provider_router/route_policy.py` (per-route limits). When D6 lands and call-site cost data becomes uniform, should these merge into one "cost & budget policy" module, or stay separated by concern (per-call cost vs lifetime budget)? Defer until D6's `HttpClientPort` adapter exposes a uniform cost-attribution hook.
