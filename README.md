# Project Name

[中文](./README.zh-CN.md) | English

**A stateful AI workflow system for real project work, centered on orchestration, harnessed execution, reusable capabilities, and persistent task memory.**

- **Coordinate real project tasks** through an explicit orchestrator instead of one-shot chat turns
- **Execute work through a harness runtime** that binds models, tools, permissions, hooks, and outputs
- **Reuse capabilities** as tools, skills, profiles, workflows, and validators
- **Persist state, memory, and artifacts** across code, notes, retrieval, and execution

## Why this project exists

Real project context is fragmented across many places:

- code repositories and Git history
- Obsidian / Markdown notes
- docs, summaries, handoff notes, and prior task outputs
- diffs, patches, test logs, and intermediate artifacts

The problem is usually not that information does not exist, but that it cannot be retrieved, executed against, and consolidated at the right moment. Typical AI tools are often good at isolated responses but weak at sustained task execution, local project interaction, and long-term result reuse.

This project aims to unify:

- task orchestration over real project work
- harnessed local and cloud execution
- retrieval over the workspace
- state, event, and artifact persistence
- reusable capabilities and workflow packs

## What problem it solves

This system is built to address a set of related pain points:

- **fragmented context**: useful information is spread across code, notes, docs, and history
- **one-shot AI interaction**: many AI tools respond well once, but do not sustain multi-step work over time
- **split workflows**: code work and knowledge work are often handled in separate tools
- **poor traceability**: AI execution often lacks recoverable state, event history, and artifact tracking
- **weak knowledge reuse**: prior work is hard to recover and turn into reusable task memory
- **capability sprawl**: tools, skills, and workflows are hard to standardize and reuse across tasks

The goal is to make AI not only answer, but also orchestrate, retrieve, execute, track, validate, and consolidate work around real projects.

## Why not just use Codex, Claude Code, or Gemini CLI?

Tools like Codex, Claude Code, and Gemini CLI are powerful local or semi-local code agents. They are excellent at repository reading, code editing, and command execution.

However, this project is not trying to replace them. It is trying to solve a different layer of the problem.

Those tools are primarily **executors**.
This system is intended to provide the surrounding **orchestration, harness, memory, and organization layer**.

In practice, that means:

- a task should continue across multiple steps and sessions
- relevant context should be retrieved from the whole workspace, not just the current prompt
- code work and note-based knowledge work should be connected
- progress should be recorded as state, events, and artifacts
- outputs should become reusable assets, not disappear into chat history
- capabilities should remain structured and reusable instead of being re-described ad hoc each time
- executors should remain replaceable rather than hard-wired

So the relationship is:

- **Codex / Claude Code / Gemini CLI** → strong execution engines
- **this project** → the stateful system that organizes orchestration, harnessed execution, retrieval, memory, and outputs around real work

## System positioning

Architecturally, this project is organized around five core layers:

- **Orchestrator**: decides what to do, in what order, and with which agent profile or workflow
- **Harness Runtime**: runs the task loop, assembles context, executes tools, applies permissions and hooks, and writes results back into state
- **Capabilities**: reusable tools, skills, profiles, workflows, and validators
- **State / Memory / Artifacts**: tasks, events, artifacts, Git truth, retrieval memory, and handoff outputs
- **Provider Router**: model, executor, provider, and auth-path routing

So it is not just a chatbot, not just a RAG project, and not just a multi-agent demo.

It is closer to an **AI workbench / AI workflow operating system** for real project work.

## Core principles

This system is built around five core capabilities:

- **Retrievable**: bring back the most relevant context from the workspace
- **Harnessed**: execute through an explicit runtime, not a loose prompt-only loop
- **Composable**: package reusable tools, skills, profiles, workflows, and validators as capabilities
- **Stateful**: continue work through task state instead of one-off chat turns
- **Traceable**: preserve events, artifacts, summaries, and evolution over time

## Current focus

The current phase is a **CLI-first MVP**.

Phase 0 focuses on:

- a minimal **orchestrator** for task intake and phase progression
- a minimal **harness runtime** for retrieve → execute → record → summarize
- a minimal **capability registry** with built-in tools only
- Codex as the primary local code executor adapter
- Git project files as a retrieval source
- Markdown / Obsidian notes as a retrieval source
- local-first development and inspectable architecture

The goal of this phase is to validate the core loop:

**AI should be able to work around a local project continuously through an orchestrated, harnessed task loop, not just answer once.**

## Long-term direction

The longer-term system is expected to evolve toward:

- richer workflow orchestration
- multiple replaceable executors
- improved retrieval quality and memory
- stronger state and artifact management
- reusable capability packs for coding and research work
- optional provider routing and cost-aware execution policies
- broader source adapters and a more complete workbench interface


## Runtime Shape

This project currently prioritizes **high-frequency personal workflows** and follows a **local workbench + optional remote heavy execution** model.

The default operating model is:

* The **local workbench** handles day-to-day interaction, including desktop UI, lightweight CLI usage, task initiation, result review, file access, and small-scale local processing.
* The **remote execution environment** is reserved for high-cost workloads such as long-running workflows, heavy RAG pipelines, large repository analysis, multi-step agent execution, and persistent background services.
* The architecture explicitly separates the **interaction layer** from the **execution layer**, avoiding tight coupling between the UI, orchestrator, and executors.

This means:

* Lightweight tasks can run locally.
* Heavy tasks can later be moved to a server.
* Even when the current version runs in a local-first way, the architecture remains compatible with remote expansion.

### Goals for the Current Phase

The current phase is not focused on building a full multi-user platform. Instead, it is intended to validate whether the following capabilities truly improve personal productivity:

* whether workflow orchestration creates real value;
* whether multi-agent or multi-executor collaboration is actually necessary;
* whether the RAG and memory layers reduce context switching across documents and tools;
* whether state, event, and artifact persistence create long-term reuse.

### Non-Goals for the Current Phase

The current phase does not prioritize the following:

* multi-tenant architecture and complex permission systems;
* high-concurrency distributed worker clusters;
* large-scale hosted infrastructure;
* full commercial deployment concerns.

The immediate priority is to make the system **reliably useful for a single user while preserving clean boundaries for future expansion**.

## Status

Phase 0 CLI bootstrap.

## Quickstart

This repository now includes a minimal runnable CLI for the documented Phase 0 loop.

Install in editable mode:

```bash
python3 -m pip install -e .
```

Create a task:

```bash
aiwf task create \
  --title "Design orchestrator" \
  --goal "Create a minimal Phase 0 harness runtime" \
  --workspace-root .
```

Run the task:

```bash
aiwf task run <task-id>
```

Print the generated artifacts:

```bash
aiwf task summarize <task-id>
aiwf task handoff <task-id>
```

Run the test suite:

```bash
python3 -m pytest
```

## Current CLI Shape

The Phase 0 CLI currently implements:

- `aiwf task create`
- `aiwf task run`
- `aiwf task summarize`
- `aiwf task handoff`

Task state and artifacts are written under:

```text
.aiwf/
  tasks/
    <task-id>/
      state.json
      events.jsonl
      retrieval.json
      artifacts/
        summary.md
        handoff.md
```

This is still a bootstrap. The current `run` command performs retrieval, records state and events, and writes placeholder handoff/summary artifacts. Replacing the placeholder execution step with a real executor adapter is the next implementation step.

## License

TBD
