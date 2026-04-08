# Current Architecture

## Orchestrator

Responsible for:

- task creation
- run-start bookkeeping
- retrieval request construction
- route selection
- phase progression
- terminal task status writing

## Harness Runtime

Responsible for:

- retrieval execution
- executor invocation
- validation execution
- artifact writing
- task-memory and grounding persistence

## Capabilities

Current explicit capability categories in the repository include:

- tools
- skills
- validators
- route capability declarations

The capability surface is still intentionally small and local-first.

## State / Memory / Artifacts

Current persisted outputs include:

- `state.json`
- `events.jsonl`
- `retrieval.json`
- `route.json`
- `compatibility.json`
- `validation.json`
- `memory.json`
- `summary.md`
- `resume_note.md`
- `route_report.md`
- `compatibility_report.md`
- `retrieval_report.md`
- `source_grounding.md`
- `validation_report.md`
- executor prompt/output/stream artifacts

## Provider Router

The provider-router layer now exists as an early baseline.

Current implemented shape:

- explicit route records
- route selection
- route provenance
- route-policy input via `route_mode`
- backend-compatibility checks
- remote-ready execution-site metadata

Still deferred:

- real remote transport
- broad provider compatibility layers
- large backend registries

## Design rule

Keep routing explicit and narrow.

Do not hide executor behavior behind large abstractions before route provenance, capability declaration, and backend compatibility remain easy to inspect.
