## Handoff Design in the Current Phase

### Why the current phase uses a self-built handoff

This project is currently a **CLI-first Phase 0 bootstrap** focused on validating the core loop: orchestration, harnessed execution, retrieval, state recording, and artifact generation 

At this stage, the goal is **not** to build a full general-purpose multi-agent runtime.
The goal is to make the project’s own system semantics clear first:

* what a task is
* how phases advance
* how context is assembled
* how execution results are recorded
* how work is resumed or continued later

Because of that, the current phase prefers a **self-built handoff mechanism** instead of introducing an external agent framework.

This keeps the architecture aligned with the project’s core layers:

* **Orchestrator** decides phase progression and overall task flow
* **Harness Runtime** executes the current step and records results
* **State / Memory / Artifacts** persist recoverable task context and outputs 

### What “handoff” means in this project

In this project, **agent handoff** is a runtime concept:

> transferring execution context from one role, phase, or backend to the next step in the workflow

This is different from persisted artifacts such as summaries or resume notes.
A handoff is not primarily a chat-style delegation mechanism. It is a **controlled transfer of task state and working context**.

In the current phase, handoff is intentionally defined in a narrow and engineering-oriented way:

> a structured transfer packet produced at the end of one step and consumed by the next step

### Why not start with an SDK handoff model

External frameworks can provide advanced runtime features such as:

* multi-agent delegation
* session inheritance
* nested history management
* tracing and runtime-level tool loops

Those are useful later, but they are not the immediate bottleneck in Phase 0.

Introducing them too early would blur the project’s own boundaries. The system could start inheriting the framework’s ideas of:

* what an agent is
* how handoff history should work
* how runtime control is transferred
* how tools and sessions are represented

That would make it harder to validate the project’s own architecture first.

For this reason, the current phase chooses:

> **system semantics first, framework borrowing later**

### Why self-built handoff is the right choice now

A self-built handoff is more suitable in the current phase for four reasons.

First, it matches the current architecture.
The project already separates orchestration from execution and persistence  

Second, it keeps the implementation small.
The current phase does not need a full multi-agent SDK. It only needs a reliable way to pass results from one step to the next.

Third, it makes the workflow easier to reason about.
Instead of hiding task transfer inside a framework runtime, the project can make handoff explicit in its own state, events, and artifacts.

Fourth, it preserves future flexibility.
Once the project’s own handoff semantics are stable, external runtimes can be added later as optional backends without redefining the system core.

---

## Minimal Handoff Model

### Current design principle

The project should treat handoff as:

> **phase-driven transfer**, not free-form multi-agent autonomy

That means the first useful handoff patterns are explicit transitions such as:

* planner → coder
* coder → verifier
* verifier → summarize

This is easier to validate than open-ended delegation between loosely defined agents.

### Minimum handoff responsibilities

A minimal self-built handoff needs only three parts:

#### 1. Handoff decision

This answers:

* should control move to another step?
* which role or backend should receive the next step?
* what phase does the task enter next?

This belongs to the **Orchestrator**.

#### 2. Handoff packet

This is the structured context transferred to the next step.

It should contain only the information needed to continue work, not the entire raw history.

#### 3. Handoff record

This captures the fact that a handoff occurred.

It should be written into task state, events, and artifacts so the workflow remains traceable and recoverable.

---

## Handoff Packet

A minimal handoff packet can be defined like this:

```text
handoff_packet
- task_id
- from_role
- to_role
- from_phase
- to_phase
- goal
- workspace_root
- retrieved_context_refs
- current_summary
- executor_output_ref
- next_action_hint
```

### Field intent

`task_id`
Identifies the task being continued.

`from_role` / `to_role`
Describe the transfer boundary in role terms rather than model terms.

`from_phase` / `to_phase`
Describe the workflow transition explicitly.

`goal`
Preserves the top-level objective.

`workspace_root`
Needed for code-oriented steps.

`retrieved_context_refs`
Points to the most relevant retrieved sources rather than duplicating all content.

`current_summary`
Provides a compact description of what has already been done.

`executor_output_ref`
Points to the artifact that the next step should inspect.

`next_action_hint`
Gives the next step a concrete starting direction.

### Why roles are better than model names

The handoff target should be expressed as a **role** or **backend type**, not as a model vendor.

Prefer:

* `planner`
* `coder`
* `verifier`
* `writer`

Avoid hard-coding handoff as:

* GPT → Claude
* Claude → Gemini

Roles are stable workflow concepts.
Model assignments can change later without changing the handoff model.

---

## Layer Responsibilities

### Orchestrator responsibilities

The **Orchestrator** should decide:

* whether a handoff is needed
* which role should receive the next step
* which phase the task moves into
* whether the workflow should continue, retry, or fail

This fits the project’s current definition of the Orchestrator as the layer that decides what to do, in what order, and with which workflow or profile 

### Harness responsibilities

The **Harness Runtime** should execute the transfer:

* assemble the handoff packet
* select the backend or executor for the receiving role
* pass the packet into the next step
* record handoff events
* persist resulting artifacts

This fits the current harness role: it assembles context, executes work, and writes results back into state and artifacts 

### State / Memory / Artifacts responsibilities

The persistence layer should record:

* that a handoff happened
* what the transition was
* which packet fields were persisted
* which artifact the next step should inspect

This keeps the workflow recoverable and inspectable.

---

## Backend Design

### Why “multiple backends” does not mean universal compatibility

The project may later allow multiple harness backends, but that does **not** mean every model, runtime, or executor supports the same features.

Different backends may support different capability levels.

For example:

```text
backend capabilities
- supports_structured_handoff
- supports_code_execution
- supports_tool_loop
- supports_multi_step_session
- supports_resume_after_failure
```

A backend should declare what it can do.
The Orchestrator and Harness should route work accordingly.

### Practical implication

The project should not assume:

* all models can act as full agents
* all executors can accept structured handoff
* all backends support multi-step runtime delegation

Instead, it should assume:

> the handoff protocol is stable, but backend support is graded

That keeps the architecture realistic and extensible.

---

## Model and Role Division

In the current phase, the project should divide work by **function**, not by vendor identity.

A practical early role model is:

### Planner

Responsible for:

* decomposing the task
* clarifying the current objective
* producing the next action hint

### Coder

Responsible for:

* code changes
* repository-local execution
* implementation work

### Verifier

Responsible for:

* checking diffs
* checking execution results
* identifying gaps or risks

### Writer / Summarizer

Responsible for:

* producing summaries
* writing resume notes
* consolidating outputs for continuation

This makes the workflow understandable even before advanced agent runtimes are introduced.

---

## Future Direction

The long-term system may still benefit from external runtimes or SDK-based agent delegation.
However, those should be introduced only after the project’s own handoff semantics are stable.

The intended evolution is:

### Phase 0

Self-built, minimal, phase-driven handoff.

### Phase 1

Role-based handoff such as planner → coder → verifier.

### Phase 2

Multiple harness backends with declared capabilities.

### Later

Optional integration of external runtime backends for richer agent delegation, sessions, tracing, or tool loops.

This keeps the project aligned with its current goal:

> validate the project’s own workflow architecture first, then borrow external runtime power where it is genuinely useful.

---

## Design rule

The current project rule is:

> **Build the system’s own handoff semantics first. Borrow framework runtime semantics later, only where they fit cleanly inside the harness boundary.**

That is the most suitable path for this project’s current phase and architectural direction.
