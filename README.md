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

At the executor layer, the system distinguishes between:

- **API executor**: better suited for planning, summarization, structured reasoning, and route judgment
- **CLI executor**: better suited for repository work, file editing, command execution, and environment-bound actions

In other words, swallow is not only about “which model to call.”  
It is about:

- how a task progresses
- how execution is constrained
- how results are recorded
- how knowledge becomes reusable
- how an operator can inspect and recover work

---

## Current Implementation Snapshot

The repository already has stable baselines for:

- Phase 0 through Phase 11
- post-Phase-2 retrieval baseline
- post-Phase-5 executor / external-input slice
- post-Phase-5 retrieval / memory-next slice

The current system already includes:

- a local-first task loop
- explicit route, topology, dispatch, handoff, and execution-fit records
- retry, stop, budget, and checkpoint policy artifacts
- operator-facing queue, control, inspect, review, resume, retry, and rerun entrypoints
- planning handoff, staged knowledge capture, and intake inspection
- retrieval over repository files and Markdown / Obsidian notes
- inspectable knowledge objects, knowledge partition, knowledge index, and knowledge policy structures

The focus is no longer to prove a minimal runnable demo.  
The focus is to keep the existing baseline stable while continuing with later phases.

---

## Documentation Structure

The repository documentation is organized into four layers.

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

Used for:
- phase goals
- phase breakdown
- phase closeout

### 4. Codex control layer
- `.codex/session_bootstrap.md`
- `.codex/rules.md`
- `.codex/templates/*`

Used for:
- Codex loading order
- Codex working rules
- phase and context templates

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

Run the test suite:

```bash id="w0d5ha"
python3 -m unittest discover -s tests
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

---

## License

TBD