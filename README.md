# swallow

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
- docs, summaries, resume notes, and prior task outputs
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
- **State / Memory / Artifacts**: tasks, events, artifacts, Git truth, retrieval memory, and resume note outputs
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

## Retrieval and Context Direction

Retrieval in this project is a system-level capability, not a helper attached to a single executor. The retrieval and context layer should remain external, traceable, and orchestrator-controlled even when vendor built-in retrieval from tools like Codex, Claude, or Gemini can be reused as a shortcut.

The intended direction is to strengthen enhanced retrieval first, then add light agentic retrieval where orchestration benefits from dynamic retrieval decisions. GraphRAG is optional and should be introduced only when multi-hop relationships or broader document structure clearly justify it.

This also means context should not be reduced to only the current prompt. The system should continue to distinguish session context, workspace context, task context, and historical context, while keeping retrieval results reusable across state, memory, and artifacts instead of consuming them only once inside a single run.

Domain-specific behavior should live in domain packs or capability packs rather than being hard-coded into one-off prompts. That applies to retrieval behavior as much as to tools, workflows, or validators.

## Current focus

The repository is currently at a **Phase 3 closeout checkpoint**.

The implemented baseline now includes:

- an explicit **orchestrator** for task intake, phase progression, and route selection
- a **harness runtime** for retrieve → execute → record → summarize
- structured route and capability declarations
- compatibility checks and route provenance artifacts
- explicit local-first execution with route, topology, dispatch, handoff, and execution-fit artifacts
- Git project files and Markdown / Obsidian notes as retrieval sources

The current goal is no longer to prove a bare bootstrap loop. The current goal is to preserve a clean, inspectable baseline before writing the next planning note.

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

### Backend Compatibility Principle

This project may allow multiple harness backends in the future, but **multiple backends do not imply universal compatibility**.

A backend is not the same thing as a model, and it is not the same thing as an executor.

The system should distinguish between three layers:

* **Model**: the underlying reasoning provider, such as OpenAI, Anthropic, Gemini, or routed providers
* **Runtime backend**: the agent or workflow runtime used inside the harness
* **Executor**: the concrete execution unit used for code, commands, or other task actions

Because of that, the project should not assume that:

* every model supports the same agent capabilities
* every runtime backend supports the same handoff semantics
* every executor can participate in every workflow step
* every backend can support code execution, tool loops, structured handoff, or resumable runs equally

Instead, the system should follow this rule:

> **The harness may expose a unified backend interface, but each backend must declare its own capability level.**

For example, a backend may or may not support:

* structured handoff packets
* tool loops
* multi-step runtime sessions
* code execution
* resumable execution after failure
* tracing or richer runtime metadata

This means the architecture should aim for **routable compatibility**, not universal compatibility.

In practice:

* the **Orchestrator** chooses a backend or executor according to task needs
* the **Harness Runtime** provides a stable integration boundary
* each backend declares what it can actually do
* workflow design should target role and capability, not hard-code specific model vendors

This principle matters because the project is not trying to become a thin wrapper around a single agent framework. Its core value lies in its own orchestration, retrieval, state, artifact, and execution design 

So the intended direction is:

* keep the project’s own orchestration and persistence semantics stable
* allow multiple backends later where useful
* avoid assuming that “supporting many models” automatically means “supporting all agent behaviors”

A practical interpretation is:

> **Unified interface at the harness boundary, capability-based routing underneath.**

## Status

Phase 0 accepted, Phase 1 complete, and the planned Phase 2 baseline complete.

Implementation checkpoint for interrupted sessions:

- [current_state.md](./current_state.md)
- [docs/phase2_closeout_note.md](./docs/phase2_closeout_note.md)
- [CHANGELOG.md](./CHANGELOG.md)

## Terminology

- `agent handoff`: a future runtime delegation step where the orchestrator or harness runtime passes work to another agent or backend
- `resume note`: a persisted continuation artifact written after a run so a later agent or human can recover, continue, or inspect the task state

## Quickstart

This repository includes a runnable CLI for the current local-first workflow baseline.

Install in editable mode:

```bash
python3 -m pip install -e .
```

Create a task:

```bash
swl task create \
  --title "Design orchestrator" \
  --goal "Tighten the harness runtime boundary" \
  --workspace-root . \
  --executor local
```

Run the task:

```bash
swl task run <task-id>
swl task run <task-id> --executor codex
```

Print the generated artifacts:

```bash
swl task summarize <task-id>
swl task resume-note <task-id>
swl task compatibility <task-id>
swl task validation <task-id>
swl task grounding <task-id>
swl task topology <task-id>
swl task dispatch <task-id>
swl task handoff <task-id>
swl task execution-fit <task-id>
swl task memory <task-id>
swl task route <task-id>
```

Run a minimal Codex preflight:

```bash
swl doctor codex
```

Run the test suite:

```bash
python3 -m unittest discover -s tests
```

## Current CLI Shape

The current CLI implements:

- `swl task create`
- `swl task run`
- `swl task summarize`
- `swl task resume-note`
- `swl task compatibility`
- `swl task validation`
- `swl task grounding`
- `swl task topology`
- `swl task dispatch`
- `swl task handoff`
- `swl task execution-fit`
- `swl task memory`
- `swl task compatibility-json`
- `swl task route`
- `swl task route-json`
- `swl task topology-json`
- `swl task dispatch-json`
- `swl task handoff-json`
- `swl task execution-fit-json`
- `swl task retrieval-json`
- `swl doctor codex`

Task state and artifacts are written under:

```text
.swl/
  tasks/
    <task-id>/
      state.json
      events.jsonl
      retrieval.json
      compatibility.json
      execution_fit.json
      validation.json
      route.json
      topology.json
      dispatch.json
      handoff.json
      memory.json
      artifacts/
        summary.md
        resume_note.md
        compatibility_report.md
        execution_fit_report.md
        route_report.md
        topology_report.md
        dispatch_report.md
        handoff_report.md
        retrieval_report.md
        source_grounding.md
        validation_report.md
        executor_stdout.txt
        executor_stderr.txt
```

The current `run` command performs retrieval, invokes the selected executor, evaluates route compatibility, evaluates execution-fit against the active topology baseline, runs validation, records state and events, persists task memory, and writes executor, summary, resume note, grounding, route, topology, dispatch, handoff, execution-fit, compatibility, and validation artifacts.

Current task-state semantics are intentionally small and explicit:

- `status` is the lifecycle result: `created`, `running`, `completed`, or `failed`
- `phase` is the current or last real workflow step: `intake`, `retrieval`, `executing`, or `summarize`
- a task only switches phase when that step actually begins
- final `completed` or `failed` is written only after `summary.md` and `resume_note.md` have been persisted

`events.jsonl` is append-only and records run-attempt boundaries explicitly. A normal successful run looks like:

```text
task.created
task.run_started
task.phase        # retrieval
retrieval.completed
task.phase        # executing
executor.completed
task.phase        # summarize
compatibility.completed
validation.completed
artifacts.written
task.completed
```

Repeated `swl task run` calls append another `task.run_started -> ... -> task.completed|task.failed` segment instead of rewriting prior history.

The current implementation now includes an explicit executor selection seam with a small built-in executor set:

- task-level selection: set `--executor` on `swl task create` or `swl task run`
- `codex`: run `codex exec` against the task workspace
- `local`: write a deterministic local execution update so executor replaceability is testable without a live backend
- `mock`: deterministic test executor for local verification
- `note-only`: skip live execution and directly write a structured continuation note
- legacy compatibility: `AIWF_EXECUTOR_MODE` still works as a fallback when the task itself stays on the default `codex` executor
- timeout control: set `AIWF_EXECUTOR_TIMEOUT_SECONDS` to bound non-interactive executor runs
- fallback control: `AIWF_EXECUTOR_FALLBACK=structured-note` by default, or set it to `off` to disable fallback note generation
- execution artifacts:
  - `executor_prompt.md`
  - `executor_output.md`
  - `executor_stdout.txt`
  - `executor_stderr.txt`

When live `codex exec` fails, the task still remains failed. The fallback does not pretend execution succeeded; it only writes a structured persisted note into `executor_output.md` so the run is easier to resume or inspect.

Current executor failures are classified into small, explicit categories such as `timeout`, `unreachable_backend`, `launch_error`, and `generic_failure`.

For `unreachable_backend`, the persisted fallback guidance now explicitly points the operator to check outbound network and websocket access before retrying live execution.

The raw `executor_stdout.txt` and `executor_stderr.txt` artifacts are preserved so operators can distinguish between code-path failures and environment/backend failures without relying only on summarized notes.

Artifact roles are also intentionally distinct:

- `summary.md` is the run record: task, final state, retrieved context, executor result, and executor output
- `resume_note.md` is the hand-off note: ready state, latest executor message, and suggested next actions
- `route_report.md` is the readable route provenance artifact: selected route, declared backend, execution-site metadata, and route reason
- `route.json` is the structured route record for later automation or inspection
- `compatibility_report.md` is the human-readable route-policy compatibility result for the run
- `compatibility.json` is the structured compatibility record for later automation or inspection
- `source_grounding.md` is the retrieval-grounding artifact: citations, scores, matched terms, and previews for the run
- `validation_report.md` is the human-readable validation result for the run
- `validation.json` is the structured validation record for later automation
- `memory.json` is the compact task-memory packet reused by later runs and later review
- `executor_output.md` remains the persisted execution result or fallback note, while `executor_stdout.txt` and `executor_stderr.txt` preserve diagnostic streams

`swl doctor codex` is a minimal preflight. It can distinguish between:

- binary not found
- local launch failure
- local binary is launchable, while live backend reachability remains unknown

## Working Convention

To make interrupted terminal sessions recoverable, keep the repo-level checkpoint updated here:

- [current_state.md](./current_state.md)

## License

TBD
