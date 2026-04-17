# swallow

[中文](./README.zh-CN.md) | English

**A stateful AI workflow system for real project work.**

swallow is not aimed at one-shot chat, and it is not only a wrapper around a code agent.  
It is meant to bring the following capabilities into one system that can sustain real work over time:

- task orchestration
- retrieval and context organization
- executor integration
- state, event, and artifact persistence
- review, recovery, and retry
- reusable capabilities and knowledge-object management

---

## Positioning

swallow is built for **real project workflows**, not single-turn interaction.

It is concerned with questions like:

- can a task continue across multiple steps and sessions
- can relevant context be retrieved from the workspace, not only from the current prompt
- can code work and knowledge work live in the same task flow
- can execution be recorded as state, events, and artifacts
- can external planning and external knowledge enter the system without polluting long-term memory
- can executors remain replaceable instead of being tied to one platform

So it is not:

- a generic chatbot
- a pure RAG project
- a thin wrapper around one executor
- a multi-agent demo for its own sake

It is closer to an **AI workbench / AI workflow system** for real project work.

---

## Why this project exists

Real project context is usually scattered across many places:

- code repositories and Git history
- Markdown / Obsidian notes
- task summaries, phase notes, and recovery docs
- retrieval outputs, test logs, and execution artifacts
- planning discussions and knowledge distilled from external AI tools

The problem is usually not that information does not exist. The problem is:

> **the right information is hard to retrieve, act on, and consolidate at the right moment.**

Many AI tools are already strong at single responses, but they are still weak at:

- sustaining multi-step task progress
- working across code and knowledge material
- preserving recoverable task state
- leaving inspectable execution artifacts
- turning past work into reusable future knowledge

swallow is built to address that layer.

---

## System Overview

swallow is organized around five long-running layers:

- **Orchestrator**: decides what to do and in what order
- **Harness Runtime**: runs retrieval, executor calls, recording, and artifact generation
- **Capabilities**: reusable tools, skills, profiles, workflows, and validators
- **State / Memory / Artifacts**: task truth, event history, memory, and outputs
- **Provider Routing**: route, executor family, backend, and capability fit

At the agent and execution layer, the system enforces a strict taxonomy based on system role, rather than model brand:

- **General Executor**: performs broad, substantial task work (e.g., repository edits, API planning).
- **Specialist Agent**: performs bounded, high-value subsystem work (e.g., memory curation, knowledge intake).
- **Validator / Reviewer**: audits and checks outputs without mutating main task state.
- **Orchestrator**: strictly coordinates progression and prevents any agent from becoming a hidden router.

In other words, swallow is not only about “which model to call.”  
It is about:

- how a task progresses
- how execution is constrained
- how results are recorded
- how knowledge becomes reusable
- how an operator can inspect and recover work

---

## Current Implementation Snapshot

**Current tag: `v0.2.0`**

> This section is updated only when a new tag is created. For real-time development progress, see `docs/active_context.md` and `docs/roadmap.md`.

In practice, the current system includes:

- a local-first task loop with explicit state, events, artifacts, checkpoints, resume, retry, and rerun semantics
- explicit route, topology, dispatch, execution-site, handoff, and policy records
- mock-remote dispatch gating and remote-handoff contract visibility without widening into real remote execution
- taxonomy metadata, taxonomy-aware routing guards, and operator-facing taxonomy visibility
- staged knowledge capture, review queues, promotion / rejection decisions, and capability-aware write boundaries
- an Evidence Store + Wiki Store task-knowledge split, canonical-promotion authority checks, and a rule-driven `LibrarianExecutor` with side-effect isolation (executor returns structured payload, orchestrator handles all persistence)
- canonical knowledge registry, reuse visibility, dedupe / supersede audit, and regression inspection paths
- canonical-sourced task grounding evidence artifacts, locked grounding refs, and resume-stable grounding state
- bounded 1:N `TaskCard` planning, DAG-based subtask orchestration, and parent-task artifact / event aggregation
- a ReviewGate-driven single-retry feedback loop for multi-card execution
- a capability-aware Strategy Router with `RouteRegistry`, four-tier candidate matching (exact → family+site → capability → summary fallback), and route-level binary fallback
- Claude XML and Codex FIM dialect adapters with a shared `dialect_data` prompt collection layer and FIM marker escaping
- structured executor event telemetry (`task_family`, `logical_model`, `physical_route`, `latency_ms`, `degraded`, `error_code`)
- a read-only Meta-Optimizer that scans task event logs and emits route health, failure fingerprint, and degradation trend proposals
- a read-only Web Control Center (`swl serve`): FastAPI JSON API + single-page HTML dashboard + dual-pane artifact review, zero writes to `.swl/`, no frontend build toolchain
- operator-facing inspect / review / control / intake / grounding surfaces over the same persisted task truth
- retrieval over repository files and Markdown / Obsidian notes, with reusable knowledge kept explicit and policy-gated

The current `main` should be treated as the stable baseline corresponding to the latest tag.

---

## Documentation Structure

The repository documentation is organized into five layers.

### 1. Public documentation
- `README.md`
- `README.zh-CN.md`

Used for:
- project positioning
- structure overview
- quickstart

### 2. Current execution layer
- `AGENTS.md`
- `docs/active_context.md`
- `current_state.md`

Used for:
- `AGENTS.md`: entry control surface and long-lived rules
- `docs/active_context.md`: the only high-frequency status document
- `current_state.md`: recovery entrypoint

### 3. Phase planning layer
- `docs/plans/<phase>/kickoff.md`
- `docs/plans/<phase>/breakdown.md`
- `docs/plans/<phase>/closeout.md`
- `docs/plans/<phase>/commit_summary.md` (optional)
- `docs/plans/<phase>/context_brief.md`
- `docs/plans/<phase>/design_decision.md`
- `docs/plans/<phase>/risk_assessment.md`
- `docs/plans/<phase>/review_comments.md`
- `docs/plans/<phase>/consistency_report.md` (optional)

Used for:
- phase goals
- phase breakdown
- phase closeout

### 4. Multi-agent control layer
- `.agents/shared/`
- `.agents/codex/`
- `.agents/claude/`
- `.agents/gemini/`
- `.agents/workflows/`
- `.agents/templates/`

Used for:
- shared rules, state sync, and workflow definitions
- role-specific responsibilities and write boundaries
- shared templates and collaboration flow

### 5. Tool-native entrypoints
- `CLAUDE.md`
- `.codex/session_bootstrap.md`
- `.gemini/settings.md`

Used for:
- thin pointers into the `.agents/` control layer
- tool-specific loading entrypoints rather than duplicated rules

---

## Recommended Working Style

The repository follows this default rhythm:

- **phase** defines development cadence
- **track** defines long-running system direction
- **slice** defines the current semantic goal
- **feature branch** carries the current phase
- **small commits** record slice-level progress

The default documentation and Git rhythm is:

- high-frequency state goes only into `docs/active_context.md`
- `current_state.md` is updated only when closeout or recovery semantics change
- `AGENTS.md` is updated only when entry rules or active direction change
- README files are updated only when the public structure or user-visible workflow changes

New work should no longer default to new `post-phase-*` naming.  
New work should be organized as:

- a formal phase
- a clear track
- a clear slice

---

## Quickstart

Install in editable mode:

```bash
python3 -m pip install -e .
```

Create a task:

```bash id="77sowp"
swl task create \
  --title "Design orchestrator" \
  --goal "Tighten the harness runtime boundary" \
  --workspace-root . \
  --capability profile:baseline_local \
  --capability workflow:task_loop \
  --executor local
```

Run a task:

```bash id="5e7lgb"
swl task run <task-id>
swl task run <task-id> --capability validator:strict_validation
swl task run <task-id> --executor codex
```

Inspect tasks and artifacts:

```bash id="n08n7n"
swl task list
swl task queue
swl task inspect <task-id>
swl task review <task-id>
swl task control <task-id>
swl task artifacts <task-id>
swl task summarize <task-id>
swl task resume-note <task-id>
swl task route <task-id>
swl task topology <task-id>
swl task handoff <task-id>
swl task remote-handoff <task-id>
swl task grounding <task-id>
swl task policy <task-id>
swl task memory <task-id>
```

Recovery and retry entrypoints:

```bash id="ga9xot"
swl task checkpoint <task-id>
swl task resume <task-id>
swl task retry <task-id>
swl task rerun <task-id>
```

Planning and knowledge intake:

```bash id="0iww4p"
swl task planning-handoff <task-id> --planning-source chat://session-1 --constraint "Keep task semantics explicit"
swl task knowledge-capture <task-id> --knowledge-stage candidate --knowledge-source chat://session-2 --knowledge-item "Imported knowledge should remain staged first."
swl task intake <task-id>
```

Knowledge review and promotion:

```bash id="q2m9kb"
swl task knowledge-review-queue <task-id>
swl task knowledge-promote <task-id> <object-id> --target reuse --note "Promote for retrieval reuse."
swl task knowledge-promote <task-id> <object-id> --target canonical --note "Promote to canonical after review."
swl task knowledge-reject <task-id> <object-id> --target reuse --note "Keep task-linked only."
swl task knowledge-decisions <task-id>
```

Canonical registry inspection:

```bash id="p13ckr"
swl task canonical-registry <task-id>
swl task canonical-registry-json <task-id>
swl task canonical-registry-index <task-id>
swl task canonical-reuse <task-id>
swl task canonical-reuse-json <task-id>
swl task canonical-reuse-evaluate <task-id> --citation <citation> --judgment useful
swl task canonical-reuse-eval <task-id>
swl task canonical-reuse-regression <task-id>
swl task canonical-reuse-regression-json <task-id>
```

Grounding inspection:

```bash id="gnd27a"
swl task grounding <task-id>
```

Meta-optimizer (read-only event log analysis):

```bash
swl meta-optimize
swl meta-optimize --last-n 50
```

Control Center (read-only web dashboard):

```bash
swl serve
swl serve --port 8037 --host 127.0.0.1
```

Canonical registry records are explicit persisted outputs for promoted canonical knowledge. They are not automatic global memory and do not automatically enable broad retrieval reuse.

Canonical reuse remains policy-gated. `canonical-reuse` shows which active canonical records are currently reuse-visible, while superseded canonical records stay excluded by default.

Canonical reuse evaluation also remains explicit and operator-driven. `canonical-reuse-evaluate` records a task-local judgment, `canonical-reuse-eval` shows the evaluation summary, and `canonical-reuse-regression` compares the saved regression baseline against the current evaluation summary so an operator can quickly spot drift or stale baseline state.

Canonical reuse regression control also remains operator-facing rather than automatic. Queue, control, inspect, and review now surface regression mismatch attention and point back to `canonical-reuse-regression` instead of mutating policy or blocking task flow automatically.

Execution topology now also keeps remote handoff contract truth explicit and operator-facing. `remote-handoff` shows the task-local remote handoff contract baseline, while execution-site, dispatch, handoff, control, and inspect surface the same readiness summary so an operator can see when a route has crossed into a remote-candidate boundary.

This remains a contract baseline, not real remote execution support. It does not implement cross-machine transport, remote worker dispatch, or hosted orchestration.

Run the test suite:

```bash id="w0d5ha"
.venv/bin/python -m pytest
```

---

## Current CLI Shape

The current CLI should be understood as:

* a task workbench
* an artifact inspection surface
* an operator control layer
* a recovery and comparison entrypoint set

Detailed current working boundaries are documented in:

* `AGENTS.md`
* `docs/active_context.md`
* `current_state.md`

---

## Non-Goals

Unless a phase explicitly requires them, the project does not currently prioritize:

* multi-tenant architecture
* distributed worker clusters
* large-scale hosted infrastructure
* broad plugin marketplaces
* implicit global memory
* automatic knowledge promotion
* unbounded workbench UI expansion
* platform-level complexity introduced only because it may be useful later

The immediate priority is:

> **make the single-user workflow genuinely useful while preserving clean boundaries for later expansion.**

---

## Terminology

* **task semantics**: explicit task-intent and planning-handoff objects that carry execution intent and constraints
* **knowledge objects**: staged knowledge records used for imported knowledge, reusable evidence, and later retrieval
* **resume note**: a hand-off note written after a run so the next session can continue correctly
* **handoff**: an explicit record of execution boundary, ownership, and next operator action
* **checkpoint**: a compact recovery snapshot reviewed before resume, retry, or rerun
* **general executor**: an agent role designed for broad task execution and state mutation
* **specialist agent**: an agent role designed for bounded subsystem work, strictly constrained from owning overall task progression
* **memory authority**: the explicit read/write scope granted to an agent (e.g., stateless, task-state, staged-knowledge)

---

## License

TBD
