# Code Organization

> **Document discipline**
> Owner: Human
> Updater: Human / Claude / Codex
> Trigger: module boundary, interface/application split, persistence layout, or long-lived import direction changes
> Anti-scope: 不维护 phase 状态、不列完整文件清单、不替代 `docs/design/INVARIANTS.md`

This document fixes Swallow's long-term code organization direction. It is a convergence standard, not a frozen final directory tree.

For GoF-style responsibility vocabulary used during system-design refactors, see `docs/engineering/GOF_PATTERN_ALIGNMENT.md`.

---

## 1. Target Shape

Swallow is a **local-first clean monolith**:

- one local Python application
- one workspace-local SQLite truth file
- multiple interface adapters
- one shared application layer
- explicit domain / governance / persistence boundaries

The target dependency direction is:

```text
interfaces/cli
interfaces/http
        ↓
application/commands
application/queries
        ↓
orchestration / knowledge / provider_router / truth_governance
        ↓
repository ports
        ↓
SQLite / filesystem / RawMaterialStore
```

No phase should introduce a second control plane or a second business implementation for a different surface.

---

## 2. Layer Duties

| Layer | Duty |
|---|---|
| `interfaces/cli` | Parse CLI arguments, format terminal output, call application commands / queries. |
| `interfaces/http` | FastAPI routes, request / response schema, HTTP error mapping, static UI serving. |
| `application/commands` | Shared user actions that may mutate task / knowledge / route / policy via Orchestrator or governance. |
| `application/queries` | Shared read models for CLI, FastAPI, Control Center, and future desktop UI. |
| `orchestration` | Control Plane workflow, task lifecycle, execution attempts, subtask flow, review / retry / recovery. |
| `knowledge` / `knowledge_retrieval` | Knowledge Truth lifecycle, raw material references, retrieval and serving projections. |
| `provider_router` | Route registry, route policy, controlled HTTP completion gateway, route selection. |
| `truth_governance` | Proposal-to-mutation boundary, repository facades, persistence ports, SQLite implementation. |
| `surface_tools` | Transitional home for current surface modules; should shrink as interfaces/application layers become explicit. |

The exact package names may evolve during implementation, but the dependency direction above should not reverse.

---

## 3. Interface Standard

CLI and UI must share behavior through the application layer:

```text
CLI command -> application command/query -> governance/orchestrator/domain -> repositories
Web/Desktop UI -> local FastAPI route -> same application command/query -> same downstream path
```

Rules:

- CLI normal commands do not call FastAPI.
- `swl serve` is the CLI exception: it starts the local FastAPI / Control Center runtime.
- Browser UI and packaged desktop UI use local loopback FastAPI.
- FastAPI is an interface adapter, not a business layer and not an Orchestrator.
- UI routes may validate request shape and map errors, but must not implement independent task state transitions, proposal mutation, or route policy logic.

See `docs/design/INTERACTION.md §4.2` for the UI runtime standard.

---

## 4. Persistence Standard

SQLite remains local-first single-file truth:

```text
<workspace_root>/.swl/swallow.db
```

Rules:

- Do not split SQLite into an external database service without phase-level design approval.
- Do not let UI / FastAPI / desktop shell read or write SQLite schema directly.
- Keep repository facades as the public persistence surface.
- Move SQLite implementation details behind persistence modules over time:

```text
truth_governance/
  store.py                  # public compatibility facade
  governance.py             # apply_proposal / mutation boundary
  repositories/
    ports.py
    default_store.py
    file_store.py
  sqlite/
    connection.py
    schema.py
    task_repository.py
    event_repository.py
    knowledge_repository.py
    route_repository.py
    policy_repository.py
```

This is a target direction. Implementation should migrate facade-first and keep backward-compatible imports where needed.

---

## 5. Domain Boundary Standards

### Knowledge Plane

Canonical is part of the Knowledge Truth lifecycle, not a separate truth plane. Upper layers should converge on a Knowledge Plane public API before internal file moves.

Target direction:

```text
knowledge_plane.py          # public facade
knowledge_model.py
knowledge_lifecycle.py
knowledge_registry.py
knowledge_graph.py
knowledge_projections.py
retrieval_eval.py
```

### Provider Router

`router.py` 已收敛为 6 个聚焦模块上的 compatibility facade(LTO-7 Step 1 已落地)。当前形态:

```text
route_registry.py
route_policy.py
route_metadata_store.py
route_selection.py
completion_gateway.py
route_reports.py
```

后续在该边界上的工作走 touched-surface caller migration,不再是 target shape 收敛。

### Orchestration

`orchestrator.py` remains the Control Plane owner. Extraction must not give helper services independent state-advancement authority.

LTO-8 Step 1 已抽出以下 6 个聚焦模块,但 `orchestrator.py` 的进一步减重和 `harness.py`(2077 行)的拆分仍是后续 step:

```text
task_lifecycle.py
execution_attempts.py
subtask_flow.py
knowledge_flow.py
retrieval_flow.py
artifact_writer.py
```

### Governance

`apply_proposal` remains the unique public mutation entry for canonical knowledge / route metadata / policy. Handler extraction is allowed only behind that facade.

Target direction:

```text
proposal_registry.py
apply_canonical.py
apply_route_metadata.py
apply_policy.py
```

---

## 6. Migration Discipline

Use these rules when implementing 簇 C subtracks(`LTO-7` / `LTO-8` / `LTO-9` / `LTO-10`)or其它 facade-first 重构:

- Prefer facade-first migration before file moves.
- Preserve current public imports until callers have migrated.
- Move one domain boundary at a time.
- Do not mix behavior changes with broad file relocation unless the behavior change requires it.
- Keep guard tests intact and strengthen them when a boundary is made more explicit.
- Avoid adding new shared imports from lower-level implementation modules when a facade exists.
- When a phase touches a module that already has a target boundary in this document, move it closer to the target rather than extending the old shape.

---

## 7. Non-Goals

- No SaaS backend by default.
- No remote database service by default.
- No UI-specific business logic fork.
- No CLI-over-HTTP requirement for local commands.
- No big-bang directory rewrite just for aesthetics.
- No weakening of `INVARIANTS.md` boundaries for organization convenience.
