# Architecture Layers

## Layer 1: Interaction / Workbench

Purpose:
- accept tasks
- display progress
- expose outputs and logs
- support human review and intervention

Phase 0 form:
- CLI only

## Layer 2: Orchestrator

Purpose:
- accept or normalize task intent
- break tasks into steps or phases
- decide when retrieval is needed
- decide when execution is needed
- select a workflow or profile when appropriate
- coordinate state transitions
- produce final summaries

Phase 0 form:
- minimal orchestrator with a small state machine

## Layer 3: Harness Runtime

Purpose:
- run a bounded task loop
- assemble execution context
- invoke tools and executor adapters
- apply permission checks
- run pre/post hooks
- return results into state and artifacts

Phase 0 form:
- a minimal retrieve → execute → record → summarize loop
- Codex-first local executor adapter
- explicit runtime boundaries, no broad multi-agent runtime yet

## Layer 4: Capabilities

Purpose:
- provide reusable execution and planning assets
- make tools, skills, profiles, workflows, and validators explicit
- avoid scattering task logic across ad hoc prompts

Capability categories:
- tools
- skills
- profiles
- workflows
- validators

Phase 0 form:
- minimal capability registry
- built-in tools only
- no broad external capability/plugin ecosystem yet

## Layer 5: State / Memory / Artifacts

Purpose:
- record current task state
- append process events
- register artifact outputs
- preserve task traceability
- store retrieval memory or summaries where needed

Recommended concepts:
- tasks
- events
- artifacts
- task-scoped output directories
- Git truth layer for code changes

## Layer 6: Provider Router

Purpose:
- route requests across providers and auth paths
- enforce cost or quality policies
- support proxy or provider abstraction
- separate executor choice from orchestration logic

Status:
- explicitly deferred from Phase 0
- expected no earlier than Phase 2

## Layer 7: External Models, Executors, and Utilities

Purpose:
- provide model inference
- provide local code execution
- provide shell, git, file system, and local utilities

Phase 0 form:
- local Codex execution
- local git/file access
- embedding/index backend kept minimal

## Phase 0 emphasis

The most important layers for Phase 0 are:
1. orchestrator
2. harness runtime
3. retrieval within state/memory/artifact handling
4. clear task/event/artifact tracking

The provider-routing layer should be prepared for conceptually, but not implemented broadly during Phase 0.
