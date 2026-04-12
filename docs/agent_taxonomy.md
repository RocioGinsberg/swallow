# Agent Taxonomy

## Document Purpose

This document defines the **agent taxonomy** for `swallow`.

It answers the following questions:

- what kinds of agents should exist in the system
- how general executors differ from specialist agents
- how agent roles should be described beyond model or provider brand names
- how to reason about execution authority, memory authority, and deployment shape
- how to prevent new agents from collapsing into hidden orchestrators or implicit global memory writers

This document is not:

- a current phase status board
- a current active slice description
- a list of model brands to use
- a prompt collection
- a replacement for `AGENTS.md`

Current work status should continue to live in:

- `AGENTS.md`
- `docs/active_context.md`
- `current_state.md`

---

## Why Agent Taxonomy Is Needed

`swallow` is not a one-shot chat wrapper and is not only a shell around a single executor. The system is built around:

- task orchestration
- retrieval and context organization
- executor integration
- state, event, and artifact persistence
- review, recovery, and retry
- reusable capabilities and knowledge-object management

Because of that, simply saying "this is a Claude agent" or "this is a Telegram agent" is not enough.

Without a clear taxonomy, several problems appear quickly:

- a specialist helper is mistaken for a general executor
- an executor quietly starts making routing decisions
- a mobile or memory helper becomes a second orchestrator
- an agent with local task memory is mistaken for a safe canonical knowledge writer
- deployment labels such as "cloud" or "local" get confused with role labels such as "specialist" or "reviewer"

The purpose of this taxonomy is to keep those dimensions separate.

---

## Design Principles

The taxonomy follows the long-running `swallow` principles:

- orchestrator and harness runtime boundaries should stay clear
- capabilities should remain first-class objects
- state, events, and artifacts must stay layered and inspectable
- retrieval is a system capability, not a side effect of one executor
- provider, backend, executor family, and agent role should not be collapsed into one label
- knowledge promotion must remain explicit and policy-gated
- implicit global memory should not become the default behavior

The taxonomy therefore classifies an agent across **three explicit dimensions**:

1. **system role** — what place the agent holds in the system
2. **execution site** — where the agent runs or is backed
3. **memory authority** — what memory scope the agent may read or write

These dimensions should be treated as orthogonal.

---

## Overview

Every agent in `swallow` should be described using the following frame:

`[system role] + [execution site] + [memory authority] + [domain or function]`

Examples:

- `general-executor / local / task-state / codex-cli`
- `specialist / cloud-backed / task-memory / memory-curator`
- `validator / cloud-backed / stateless / consistency-review`
- `specialist / cloud-backed / staged-knowledge / reflective-hermes`

This naming frame avoids several common mistakes:

- calling something a "cloud agent" when cloud only describes location, not role
- calling something a "memory agent" without specifying whether it can write task memory, staged knowledge, or canonical knowledge
- calling something an "assistant" when it is actually a validator or reviewer

---

# I. System Role

## 1. Orchestrator

### Definition
The orchestrator decides:

- what should happen next
- which capability or executor should be called
- what context should be assembled before execution
- what should be recorded after execution
- whether review, retry, stop, resume, or rerun should occur

### Core Responsibility
The orchestrator owns **task progression semantics**.

### What It Is Not
The orchestrator is not just another agent among peers. It is the coordination layer that:

- determines order
- determines handoff
- determines route judgment
- determines how truth is recorded

### Why It Must Stay Separate
If a specialist agent or a general executor silently starts making routing or policy decisions, the system loses inspectability.

### Design Rule
New agents should not be allowed to become hidden orchestrators by accident.

---

## 2. General Executor

### Definition
A general executor performs a relatively complete class of work within the task flow.

### Typical Work
Examples include:

- repository work
- file editing
- command execution
- structured reasoning
- planning draft generation
- summarization within a task run

### Typical Families
Within the current `swallow` language, the most common families are:

- API executor
- CLI executor

### Core Trait
A general executor can take a substantial slice of the task and produce meaningful output artifacts.

### Important Boundary
A general executor may execute a task step, but it should not redefine:

- global routing policy
n- canonical memory policy
- active phase boundaries
- overall orchestrator truth

### Examples
- Codex-style repository executor
- API planning/summarization executor
- future local sandboxed executor

---

## 3. Specialist Agent

### Definition
A specialist agent is an agent with a **single high-value bounded responsibility**.

### Core Trait
A specialist agent does not attempt to own the whole task lifecycle. It exists to deepen one part of the system.

### Typical Characteristics
A specialist agent usually has:

- clearer input boundaries
- clearer output boundaries
- narrower write authority
- narrower success criteria
- lower governance risk than a general executor

### Examples
- memory curator
- knowledge intake agent
- retrieval evaluation agent
- failure analysis agent
- mobile interaction agent
- reflective agent such as Hermes when constrained to a bounded role

### Why This Category Matters
This is the most important category for keeping the system composable. Many useful capabilities should be modeled as specialist agents rather than as new general executors.

---

## 4. Validator / Reviewer

### Definition
A validator or reviewer does not primarily generate the main work product. It evaluates, checks, or audits the work of other system parts.

### Core Responsibility
It answers questions such as:

- is this output grounded
- does this patch drift from current design boundaries
- does this knowledge candidate look safe to promote
- does this retrieval result satisfy expected evidence quality
- does this request violate policy

### Examples
- consistency review agent
- retrieval evaluator
- risk auditor
- policy validator
- citation grounding checker

### Why Separate This From Specialist Agent
A validator/reviewer is still specialized, but its role in the system is different:

- it checks rather than carries the main execution load
- it often gates progression rather than generating the next artifact

For implementation convenience, validators may still be built as specialist capabilities. But in the taxonomy they should be named according to their reviewing function.

---

## 5. Human Operator

### Definition
The human operator is not an agent but remains a first-class role in the taxonomy discussion because many system guarantees are explicitly operator-facing.

### Core Responsibilities
The human operator:

- approves design direction
- reviews high-impact outputs
- decides merge and promotion outcomes
- resolves ambiguity the system should not auto-resolve

### Why This Matters
Any agent taxonomy that ignores the human role will over-automate by accident.

---

## System Role Summary Table

| System Role | Primary Function | Owns Full Task Progression | Typical Write Authority | Typical Risk |
|---|---|---:|---|---|
| Orchestrator | decide next step and coordination | yes | task truth, event ordering, routing records | highest |
| General Executor | perform substantial task work | partial but broad | task artifacts, run outputs | high |
| Specialist Agent | perform one bounded function | no | narrow task-scoped outputs | medium |
| Validator / Reviewer | check, audit, gate, compare | no | evaluation artifacts, judgments | medium |
| Human Operator | approve, decide, merge, promote | yes in governance sense | explicit operator decisions | intentional |

---

# II. General Executor vs Specialist Agent

## Why This Separation Must Be Explicit
A recurring design error is to label every new useful helper as an "agent" and stop there.

That creates confusion around:

- whether the helper can own a task run
- whether it can change system direction
- whether it should be routable like a main executor
- whether it should be allowed to write memory beyond the current task

The split between **general executors** and **specialist agents** prevents that collapse.

---

## General Executor

A general executor should be used when the system needs an agent to perform a meaningful chunk of work such as:

- implementing code
- editing files
- running commands and tools
- producing a substantive planning draft
- carrying a long execution step with broad context

A general executor is broad in **work surface**, even if it is still constrained by harness and policy.

### Strengths
- handles larger end-to-end work slices
- easier to route as a primary execution step
- aligns naturally with executor families such as CLI and API

### Risks
- more likely to overlap with orchestrator concerns
- more likely to overreach on scope expansion
- more likely to create large, mixed artifacts if not constrained

---

## Specialist Agent

A specialist agent should be used when the system needs focused depth in one area such as:

- memory curation
- mobile interaction
- retrieval evaluation
- failure analysis
- knowledge review
- route suggestion
- risk audit

A specialist agent is narrow in **responsibility**, even if it is deployed through the same runtime stack as a general executor.

### Strengths
- cleaner boundaries
- easier policy gating
- easier to test and inspect
- lower risk of hidden orchestration behavior

### Risks
- if poorly defined, it can become a prompt-shaped pseudo-agent with vague authority
- if given too much write access, it can still cause memory pollution or policy drift

---

## Decision Rule

Use a **general executor** when the role is expected to perform broad task execution.

Use a **specialist agent** when the role is expected to improve one bounded subsystem behavior.

A simple test:

- if the role can reasonably be asked to "take this task step and produce the main output," it is likely a general executor
- if the role is better phrased as "analyze, compress, review, validate, summarize, curate, or propose" within one bounded area, it is likely a specialist agent

---

# III. Execution Site

System role should not be confused with deployment shape. A role can stay the same while its execution site changes.

## 1. Local

### Definition
The agent runs on the same machine or workspace boundary as the main task environment.

### Typical Fit
- CLI executor
- local file-aware helpers
- local recovery or handoff helpers
- local workspace inspection tools

### Benefits
- direct access to workspace state
- lower latency for local operations
- easier alignment with local-first task loop

### Risks
- stronger coupling to host environment
- greater filesystem and execution risk if permissions are broad

---

## 2. Cloud-backed

### Definition
The agent is backed by a remote API or service, even if the call is made from local runtime.

### Typical Fit
- summarization agents
- reflective agents
- long-context consistency analysis
- mobile interaction interpretation

### Benefits
- stronger model availability
- easier access to long-context or specialized reasoning capabilities

### Risks
- more opaque runtime internals
- greater need for artifactized outputs and policy gates
- more temptation to grant broad authority because the external system feels powerful

---

## 3. Remote Worker

### Definition
The agent executes on a separate machine or distinct remote execution site rather than as a simple API-backed call.

### Typical Fit
- future remote execution topologies
- remote detached workers
- cross-machine delegated execution

### Benefits
- enables scale and separation of runtime environments

### Risks
- adds transport, handoff, and security complexity
- should not be conflated with simple cloud inference

### Current Status
This remains a future-oriented category. `swallow` currently keeps remote handoff contract truth explicit without implementing full remote worker orchestration.

---

## 4. Hybrid

### Definition
A hybrid role spans more than one execution site in a governed way.

### Typical Fit
- mobile interaction flows where a local gateway delegates interpretation to a cloud model
- local orchestrator calling remote summarization and then local validators

### Warning
Hybrid is useful as an execution description, but should not replace explicit role naming.

---

## Execution Site Summary Table

| Execution Site | What It Describes | Typical Examples | Main Risk |
|---|---|---|---|
| Local | same workspace or host boundary | CLI executor, local recovery helper | host coupling |
| Cloud-backed | remote model/service-backed call | reflective Hermes, mobile summarizer | opaque external behavior |
| Remote Worker | separate execution machine/site | future detached worker | topology and transport complexity |
| Hybrid | governed mix of sites | local gateway + cloud interpretation | boundary confusion |

---

# IV. Memory Authority

Memory authority must be explicit because `swallow` distinguishes task state, staged knowledge, and canonical knowledge. Not every agent should be allowed to cross those boundaries.

## 1. Stateless

### Definition
The agent does not keep persistent memory across calls beyond the explicit input it receives.

### Typical Fit
- one-shot reviewers
- retrieval evaluators
- citation checkers
- lightweight summarizers

### Benefits
- safest default
- easiest to replace
- easiest to reason about

### Risks
- may lose useful continuity unless context packaging is strong

---

## 2. Task-State Access

### Definition
The agent can read or write task-local state records, events, or runtime outputs needed for task execution.

### Typical Fit
- general executors
- checkpoint or resume helpers
- local recovery helpers

### Important Note
Task-state access is not the same as long-term memory authority.

---

## 3. Task-Memory

### Definition
The agent can read or write memory artifacts that are scoped to the current task or session continuity.

### Typical Fit
- memory curator
- failure analysis agent
- reflective task helper
- mobile interaction context helper

### Allowed Outputs
Typical outputs may include:

- resume note
- task reflection log
- local handoff note
- compact memory summary

### Risks
- can create noisy or stale task memory if not curated
- must not be mistaken for canonical knowledge promotion

---

## 4. Staged-Knowledge

### Definition
The agent can produce or modify staged knowledge candidates that are inspectable and await explicit review.

### Typical Fit
- knowledge intake agent
- reflective Hermes-style proposal agent
- memory-to-knowledge extraction helper
- research note structuring helper

### Allowed Outputs
Typical outputs may include:

- candidate knowledge object
- verified candidate draft
- reusable knowledge proposal

### Key Boundary
Staged-knowledge authority does not imply canonical promotion authority.

---

## 5. Canonical-Write-Forbidden

### Definition
This is not a memory scope by itself but a critical safety label. It should be applied to most agents by default.

### Meaning
The agent may:

- propose
- summarize
- evaluate
- draft
- prepare promotion candidates

But it may not directly mutate canonical knowledge truth.

### Recommendation
The default assumption for new agents should be:

- canonical-write-forbidden unless explicitly designed otherwise

---

## 6. Canonical Promotion Authority

### Definition
This is the narrowest and most sensitive category. In most cases it should belong to a controlled workflow and operator-confirmed promotion path rather than to an autonomous agent.

### Recommendation
Prefer:

- agent as proposer
- system workflow as promoter
- human operator as confirmer

### Why
This keeps knowledge promotion inspectable, reversible, and policy-gated.

---

## Memory Authority Summary Table

| Memory Authority | What The Agent May Touch | Good Fit | Main Risk |
|---|---|---|---|
| Stateless | only current call context | validators, one-shot summaries | lost continuity |
| Task-State Access | current task runtime truth | general executors | over-broad task mutation |
| Task-Memory | task-local continuity records | memory curator, failure review | noisy local memory |
| Staged-Knowledge | reviewable knowledge candidates | intake, research extraction, Hermes proposals | promotion pressure |
| Canonical-Write-Forbidden | explicit safety restriction | most agents | none; this is protective |
| Canonical Promotion Authority | final reusable truth | controlled workflow only | highest governance risk |

---

# V. Classification Rules

## Rule 1: Never Classify by Brand Name Alone

"Claude agent," "Gemini agent," or "Hermes agent" are not enough as taxonomy labels.

A complete classification should describe:

- the role in the system
- where it runs
- what memory scope it can access
- what function or domain it serves

---

## Rule 2: Role and Execution Site Must Stay Separate

"Cloud agent" is not a complete category.

Cloud only describes where the capability is backed, not whether it is:

- a general executor
- a specialist agent
- a validator
- a reviewer

---

## Rule 3: Memory Authority Must Be Stated Explicitly

Any agent touching memory, notes, review queues, or knowledge objects should declare whether it operates at:

- task-state
- task-memory
- staged-knowledge
- canonical promotion

If this is not stated, the role is underspecified.

---

## Rule 4: Most New Agents Should Start as Specialist + Canonical-Write-Forbidden

This is the safest default for system expansion.

---

## Rule 5: If An Agent Suggests System Direction, That Does Not Make It The Orchestrator

A route suggestion agent, planner helper, or reflective agent may propose next steps. The orchestrator remains responsible for authoritative progression.

---

## Rule 6: Validators Should Not Quietly Become Executors

A consistency checker or risk auditor may recommend changes, but it should not silently mutate task state beyond its declared evaluation artifacts.

---

# VI. Canonical Role Patterns In `swallow`

## 1. Code Agent

### Recommended Classification
- `general-executor / local / task-state / code-execution`

### Typical Responsibilities
- repository work
- file edits
- command execution
- test runs
- patch generation

### Typical Risks
- scope expansion
- overly large diffs
- accidental policy drift if not bounded by phase and review rules

---

## 2. API Planning Agent

### Recommended Classification
- `general-executor / cloud-backed / task-state / planning-and-summarization`

### Typical Responsibilities
- structured planning draft
- summarization
- route judgment assistance
- handoff preparation

### Typical Risks
- drifting into orchestrator authority
- generating persuasive but weakly grounded plans if retrieval and validation are weak

---

## 3. Memory Curator

### Recommended Classification
- `specialist / local-or-cloud-backed / task-memory + staged-knowledge / memory-curation`
- `canonical-write-forbidden`

### Typical Responsibilities
- compress task history
- draft resume notes
- deduplicate memory fragments
- propose reusable knowledge candidates

### Why Specialist
It improves one subsystem deeply without owning general task execution.

---

## 4. Knowledge Intake Agent

### Recommended Classification
- `specialist / cloud-backed / staged-knowledge / knowledge-intake`
- `canonical-write-forbidden`

### Typical Responsibilities
- transform external materials into staged knowledge objects
- extract claim, evidence, and source structure
- prepare items for review queue

---

## 5. Knowledge Review Agent

### Recommended Classification
- `validator / cloud-backed / staged-knowledge / knowledge-review`
- `canonical-write-forbidden`

### Typical Responsibilities
- assess candidate quality
- identify redundancy or conflict
- recommend promote/reject decisions

---

## 6. Retrieval Evaluation Agent

### Recommended Classification
- `validator / local-or-cloud-backed / stateless / retrieval-evaluation`

### Typical Responsibilities
- assess retrieval quality
- compare evidence slices
- flag weak grounding or missing support

---

## 7. Consistency Review Agent

### Recommended Classification
- `validator / cloud-backed / stateless / consistency-review`

### Typical Responsibilities
- compare docs and code
- detect drift from active design boundaries
- generate review artifacts for operator inspection

---

## 8. Failure Analysis Agent

### Recommended Classification
- `specialist / local-or-cloud-backed / task-memory / failure-analysis`

### Typical Responsibilities
- read logs and failed runs
- propose root-cause hypotheses
- suggest retry or recovery strategies

---

## 9. Hermes As A Reflective Specialist

### Recommended Classification
- `specialist / cloud-backed / task-memory + staged-knowledge / reflective-hermes`
- `canonical-write-forbidden`

### Why Hermes Fits Better As A Specialist Than As A Platform Core
Hermes becomes useful when constrained to:

- task-local reflection
- strategy proposal
- experience compression
- staged knowledge proposal

It should not be allowed to:

- own routing authority
- rewrite canonical knowledge directly
- mutate global policy silently
- replace the orchestrator

---

## 10. Mobile Interaction Agent

### Recommended Classification
- `specialist / cloud-backed-or-hybrid / stateless-or-task-memory / mobile-operator-interaction`
- `canonical-write-forbidden`

### Typical Responsibilities
- parse mobile requests
- map them to controlled read or action commands
- compress task state into small-screen summaries
- push high-value notifications

### Why Specialist
This role improves the operator interface layer. It should not become a second assistant shell or orchestrator.

---

# VII. Anti-Patterns

## 1. The Brand-Only Agent

Bad pattern:

- "This is the Gemini agent"
- "This is the Telegram agent"

Why bad:

- does not describe role
- does not describe authority
- does not describe memory scope

---

## 2. The Hidden Orchestrator

Bad pattern:

A planner, route helper, reflective agent, or mobile agent quietly decides what the entire system should do next.

Why bad:

- collapses inspectability
- makes progression truth hard to recover
- weakens harness governance

---

## 3. The Implicit Global Memory Writer

Bad pattern:

A memory, research, or reflective agent silently promotes its own outputs into long-term reusable knowledge.

Why bad:

- causes knowledge pollution
- weakens review gates
- makes provenance and reversibility weaker

---

## 4. The Everything Agent

Bad pattern:

A role that says it can plan, execute, review, summarize, route, and curate memory.

Why bad:

- usually means the role is underspecified
- increases governance risk
- creates overlapping authority with orchestrator and validators

---

## 5. The Location-Only Category

Bad pattern:

Calling something a "cloud agent" or "remote agent" as its main taxonomy label.

Why bad:

- describes deployment, not role
- makes system responsibilities unclear

---

# VIII. Recommended Naming Format

Each agent should be named using four fields:

`[system role] / [execution site] / [memory authority] / [function]`

Examples:

- `general-executor / local / task-state / codex-cli`
- `general-executor / cloud-backed / task-state / planning-api`
- `specialist / cloud-backed / task-memory / memory-curator`
- `validator / cloud-backed / stateless / consistency-review`
- `specialist / cloud-backed / staged-knowledge / reflective-hermes`
- `specialist / hybrid / stateless / mobile-operator-interaction`

This format should be preferred in design discussions over vague labels such as:

- cloud agent
- memory agent
- Telegram agent
- smart assistant
- thinking agent

---

# IX. Recommended Defaults For New Agents

When introducing a new agent, the default assumptions should be:

- system role: `specialist` unless broad execution is clearly needed
- execution site: whichever is operationally simplest, but do not treat site as role
- memory authority: `stateless` or `task-memory` first
- canonical authority: forbidden by default
- routing authority: no
- promotion authority: no

Only widen those powers deliberately.

---

# X. Practical Evaluation Checklist

Before adding a new agent, answer these questions:

1. What is its **system role**?
2. Is it a **general executor** or a **specialist agent**?
3. Where does it execute: **local**, **cloud-backed**, **remote worker**, or **hybrid**?
4. What memory scope does it need: **stateless**, **task-state**, **task-memory**, or **staged-knowledge**?
5. Is it explicitly **canonical-write-forbidden**?
6. Could it accidentally become a hidden orchestrator?
7. Could a validator or reviewer artifact be enough instead of adding a new executor?
8. Is the role actually provider-specific, or can it be expressed as a stable system function?

If these cannot be answered clearly, the proposed agent role is not yet ready.

---

# XI. Final Position

The `swallow` agent taxonomy should remain centered on **role clarity**, not vendor identity.

The most important split is:

- **general executors** for broad task execution
- **specialist agents** for bounded, high-value subsystem work

Those roles should then be made explicit across:

- **system role**
- **execution site**
- **memory authority**

This keeps the system expandable without collapsing into:

- hidden orchestration
- implicit global memory
- vague assistant roles
- provider-driven architecture

A good taxonomy should make every agent easier to:

- route
- govern
- inspect
- replace
- constrain
- evolve

That is the purpose of this document.
