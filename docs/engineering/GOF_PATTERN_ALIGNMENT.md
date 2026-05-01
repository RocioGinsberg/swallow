---
author: codex
phase: candidate-r
slice: system-design-refactor-planning
status: draft
depends_on:
  - docs/design/INVARIANTS.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/roadmap.md
---

TL;DR:
Swallow should use GoF-style patterns as responsibility language, not as decorative abstraction.
The immediate use is Candidate U retrieval observability; the broader system-design refactor is Candidate AC.
Every pattern boundary remains subordinate to `docs/design/INVARIANTS.md`.

# GoF Pattern Alignment

> **Document discipline**
> Owner: Human
> Updater: Human / Claude / Codex
> Trigger: system-design refactor planning, module boundary redesign, or long-lived responsibility split decisions
> Anti-scope: 不维护 phase 状态、不要求为了模式而模式化、不替代 `docs/design/INVARIANTS.md` 或 `docs/engineering/CODE_ORGANIZATION.md`

This document explains how Swallow may use GoF-style design pattern thinking during system-design refactors.

The goal is not to decorate code with pattern names. The goal is to make object responsibilities, collaboration boundaries, and extension points explicit while preserving Swallow's constitutional invariants.

---

## 1. First Principles

GoF patterns are allowed as a **design vocabulary**:

- to identify which object owns a decision
- to separate stable facade from replaceable internals
- to make policies and workflows observable
- to reduce hidden coupling between CLI, orchestration, retrieval, governance, and persistence

GoF patterns are not allowed as an excuse to:

- add indirection without a real change pressure
- move Control Plane authority away from Orchestrator / Operator
- bypass `apply_proposal`
- turn helper services into silent state-advancing actors
- hide SQLite Truth writes behind vague "manager" objects
- create generic frameworks disconnected from current Swallow workflows

When in doubt, `docs/design/INVARIANTS.md` wins over any pattern.

---

## 2. Pattern Mapping

| Pattern / idea | Swallow use | Boundary |
|---|---|---|
| **Facade** | Keep stable public entry points while internals split: `router.py`, `orchestrator.py`, `knowledge_plane.py`, `governance.apply_proposal` | Facade preserves behavior; it must not become a second implementation. |
| **Strategy** | Route selection, retrieval source policy, fallback policy, rerank labeling, retry / stop / budget policy | Strategies choose behavior inside an authorized owner; they do not own Control Plane advancement. |
| **Command** | CLI / FastAPI / application user actions such as task run, knowledge promote, proposal apply | Commands model operator intent; mutation still goes through Orchestrator or governance. |
| **Repository** | Task / event / knowledge / route / policy persistence ports | Repositories protect Truth writes; no caller gets raw SQL as a shortcut. |
| **Adapter** | CLI, FastAPI, New API OpenAI-compatible endpoint, RawMaterialStore backend, future desktop shell | Adapters translate protocols; they do not encode domain policy. |
| **Template Method / Pipeline** | Task run lifecycle, retrieval serving lifecycle, ingestion review flow | Pipeline steps must expose trace data; hidden side effects are unacceptable. |
| **Chain of Responsibility** | Retrieval source stages, validation / policy checks, routing fallback chain | Each link must be observable and bounded; no link silently escalates authority. |
| **Observer / Event Log** | `event_log`, routing hints, checkpoints, handoff records | Events make state changes auditable; event consumers do not gain mutation rights by subscribing. |
| **Factory / Registry** | Executor registry, route registry, provider registry | Registry binds taxonomy to concrete implementation without leaking brand logic into design docs. |
| **Value Object** | `TaskSemantics`, `RouteSpec`, `RetrievalRequest`, `RetrievalTrace`, `EvidencePack`, `SourcePointer`, `FallbackReason` | Value objects make boundaries explicit; they should be immutable or treated as immutable across layers. |
| **State** | Task lifecycle, attempt lifecycle, staged knowledge lifecycle, proposal lifecycle | State transitions must be explicit and guarded; avoid scattered boolean flags as lifecycle authority. |

---

## 3. Candidate-Specific Guidance

### Candidate U: Retrieval Observability

Candidate U should be the first practical application of this pattern language.

Recommended pattern usage:

- **Value Object**: `RetrievalTrace`, `RetrievalMode`, `FallbackReason`, `RerankTrace`
- **Strategy**: source policy labels and fallback classification
- **Adapter**: embedding provider / `sqlite-vec` availability reporting
- **Facade**: keep `swl task retrieval` and `retrieval-json` stable while report internals improve

Do not turn Candidate U into a platform rewrite. It should clarify existing retrieval behavior before changing retrieval architecture.

### Candidate T: EvidencePack / Source Resolution

Recommended pattern usage:

- **Value Object**: `EvidencePack`, `SourcePointer`, `ResolvedEvidence`
- **Adapter**: `RawMaterialStore` source resolution
- **Pipeline**: primary object selection -> evidence resolution -> fallback labeling -> report assembly

Do not embed raw bytes as Knowledge Truth. EvidencePack carries references and bounded excerpts, not a second truth store.

### Candidate Y: Summary Route / Surface Ergonomics

Recommended pattern usage:

- **Command**: distinguish inspection commands from answer-producing commands
- **Adapter**: CLI output formatting stays separate from execution semantics
- **Facade**: keep current CLI entry points stable while clarifying behavior

The narrow Y follow-up should clarify whether `summary` mode is inspection-only or whether a separate QA route is needed.

### Candidate AC: System Design Refactor

Candidate AC should not be a big-bang rewrite. It should be a design refactor plan that coordinates AB / V / W / X / Y / Z using the pattern language above.

Recommended lanes:

| Lane | Main patterns | Existing candidate alignment |
|---|---|---|
| Application command boundary | Command, Facade, Adapter | AB |
| Retrieval serving boundary | Pipeline, Strategy, Value Object | U -> T |
| Provider Router boundary | Facade, Strategy, Registry, Adapter | W |
| Orchestration lifecycle boundary | Template Method, State, Observer | X / D |
| Knowledge Plane boundary | Facade, Repository, Value Object | V |
| Governance apply boundary | Facade, Command Handler, Repository | Z |

Candidate AC should produce or update plans; it should not move multiple major subsystems in one commit.

---

## 4. Refactor Rules

1. **Facade first**
   Keep existing imports and CLI/API entry points stable, then migrate internals behind the facade.

2. **One authority per decision**
   If a function chooses a route, writes Truth, advances task state, and formats output, split responsibilities before adding features.

3. **Make policy objects explicit**
   Retrieval source selection, fallback classification, retry/stop decisions, and route choice should be testable without running the full task loop when feasible.

4. **Prefer value objects at layer boundaries**
   Replace ad hoc dicts when the data crosses interface/application/domain/persistence boundaries or appears in reports.

5. **Do not extract powerless wrappers**
   A new class or module should own a real concept: policy, command, trace, repository port, adapter, lifecycle step, or value object.

6. **Keep invariants executable**
   Every refactor near Control / Truth / Provider Router / `apply_proposal` must preserve or strengthen guard tests.

7. **Slice by behavior surface**
   Use small reviewable slices: report clarity, source policy labeling, command/query extraction, provider route selection, repository port, lifecycle helper.

8. **No big-bang pattern rewrite**
   If a refactor cannot be verified by focused tests and a stable facade, it is too broad for one phase.

---

## 5. Naming Guidance

Avoid vague names:

- `Manager`
- `Helper`
- `Processor`
- `Service` without a domain noun
- `Util`

Prefer names that reveal the responsibility:

- `RouteSelectionPolicy`
- `RetrievalTrace`
- `FallbackReason`
- `SourcePolicyLabel`
- `TaskRunCommand`
- `CanonicalRepository`
- `RawMaterialResolver`
- `EvidencePackAssembler`
- `AttemptLifecycle`

Existing compatibility facades may keep historical names while internals converge.

---

## 6. Review Checklist

Use this checklist for system-design refactor PRs:

- Does the change preserve `docs/design/INVARIANTS.md`?
- Is there a stable facade for existing callers?
- Which object owns the decision being changed?
- Which pattern idea is being used, and what concrete coupling does it remove?
- Are Truth writes still behind repository / governance boundaries?
- Are task state transitions still controlled by Orchestrator / Operator?
- Are policy decisions visible in reports or traces?
- Are new value objects documented through tests?
- Does the change avoid moving unrelated subsystems?
- Are guard tests preserved or strengthened?
