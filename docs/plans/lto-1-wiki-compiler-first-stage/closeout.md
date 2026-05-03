---
author: codex
phase: lto-1-wiki-compiler-first-stage
slice: phase-closeout
status: final
depends_on:
  - docs/plans/lto-1-wiki-compiler-first-stage/plan.md
  - docs/plans/lto-1-wiki-compiler-first-stage/plan_audit.md
  - docs/plans/lto-1-wiki-compiler-first-stage/review_comments.md
  - docs/active_context.md
  - src/swallow/surface_tools/wiki_compiler.py
  - src/swallow/orchestration/executor.py
  - src/swallow/application/commands/wiki.py
  - src/swallow/application/queries/knowledge.py
  - src/swallow/adapters/cli_commands/wiki.py
  - src/swallow/adapters/cli.py
  - src/swallow/adapters/http/api.py
  - src/swallow/adapters/http/schemas.py
  - src/swallow/adapters/http/static/index.html
  - tests/test_invariant_guards.py
  - tests/test_executor_protocol.py
  - tests/eval/test_wiki_compiler_quality.py
---

TL;DR:
LTO-1 first-stage implementation and PR review are complete on the feature branch; the only review concern has been absorbed and the branch is ready for Human closeout commit / merge gate.
The phase adds a propose-only Wiki Compiler specialist with CLI draft/refine/refresh-evidence commands, read-only Knowledge Browse HTTP routes, a Web Knowledge panel, and M5 boundary/evidence guards.
Validation passed: focused M5 gates, eval signal `4 passed`, invariant guards `35 passed`, full pytest `773 passed, 12 deselected`, compileall, and diff check.

# LTO-1 Closeout: Wiki Compiler First Stage

## Outcome

LTO-1 delivers the first local knowledge-authoring loop for Swallow:

- `swl wiki draft` stages a new wiki draft from raw material / artifact sources.
- `swl wiki refine --mode supersede|refines` stages a reviewable refinement signal against an existing knowledge object.
- `swl wiki refresh-evidence` updates evidence anchors without an LLM call and without `apply_proposal`.
- Wiki Compiler is registered as a specialist executor and keeps the design tuple shape: propose-only, staged-knowledge/task-artifact writes, Specialist Internal LLM path through Provider Router.
- Staged candidates now preserve compiler metadata: `wiki_mode`, `target_object_id`, `source_pack`, `rationale`, `relation_metadata`, and `conflict_flag`.
- Operator promotion of `refines` metadata creates the approved `refines` relation in the application command layer; raw `derived_from` and `supersedes` review signals remain staged metadata in this first stage.
- Web Control Center now has a read-only Knowledge surface for wiki/canonical/staged lists, detail, source pack, and relation adjacency.

Canonical mutation ownership did not change. Wiki Compiler never calls `apply_proposal`; canonical knowledge / route metadata / policy writes remain behind the existing governance path.

## Scope Delivered

| Plan area | Result |
|---|---|
| M1 Wiki Compiler core | Delivered: specialist module, executor registration, CLI `draft` / `refine` / `refresh-evidence`, staged metadata extension, prompt/result artifacts, Provider Router LLM path, refresh-evidence no-LLM path. |
| M2 Knowledge browse routes | Delivered: read-only `GET /api/knowledge/wiki`, `/canonical`, `/staged` through `application.queries.knowledge` and Pydantic response envelopes. |
| M3 Detail + relations | Delivered: `GET /api/knowledge/{object_id}` and `/relations`; adjacency groups cover design metadata modes plus legacy relation buckets. |
| M4 Web panel | Delivered: static Control Center Tasks / Knowledge surface switch; Knowledge panel is read-only and does not expose Wiki Compiler LLM triggers. |
| M5 guards/eval/closeout | Delivered: Wiki Compiler boundary guard, refresh-evidence parser/version anchor guard, HTTP knowledge adapter boundary guard, relation metadata-mode guard, deselected eval signal, closeout draft, and PR body draft. |

## Implementation Notes

The application command layer is the adapter-facing wrapper for Wiki Compiler actions. The specialist identity remains in `src/swallow/surface_tools/wiki_compiler.py`, and both direct CLI commands and executor protocol tests exercise that identity.

Post-review cleanup removed the empty `WikiCompilerExecutor` compatibility subclass. `orchestration.executor` now registers `WikiCompilerAgent` directly, so the Wiki Compiler follows a single concrete class identity while still satisfying `ExecutorProtocol`.

`source_pack` entries follow the plan's `SourcePointer.to_dict()`-compatible shape extended with:

- `content_hash`
- `parser_version`
- `span`
- `preview`

`refresh-evidence` requires either `span` or `heading_path`, writes the parser version alongside the content hash, and updates task knowledge evidence anchors through Knowledge Plane facade functions.

The HTTP Knowledge Browse routes are read-only and follow the existing FastAPI adapter discipline:

- routes depend on `get_base_dir`
- responses use Pydantic success envelopes
- errors flow through centralized handlers
- route handlers call `application.queries.knowledge`, not lower-level Knowledge Retrieval internals or SQLite helpers

## Guard Behavior

M5 adds executable guard coverage for the phase boundary:

- `test_wiki_compiler_agent_boundary_propose_only`
  - rejects direct calls/imports of `apply_proposal`, canonical writers, route/policy writers, `save_state`, raw `submit_staged_candidate`, direct event append, and direct provider clients
  - requires Provider Router `call_agent_llm` / `extract_json_object`
  - requires staged writes through `knowledge_plane.submit_staged_knowledge`
- `test_wiki_compiler_refresh_evidence_updates_parser_version_anchor`
  - proves `refresh_wiki_evidence_command` updates `parser_version`, `content_hash`, `span`, and `heading_path`
  - rejects the known anti-pattern of content-hash-only evidence rebuilds
- `test_http_knowledge_routes_only_call_application_queries`
  - proves all Knowledge Browse HTTP GET routes call application query functions and do not reach Knowledge Retrieval internals directly
- `test_knowledge_relation_metadata_types_cover_design_modes`
  - proves staged/compiler metadata covers `supersedes`, `refines`, `contradicts`, `refers_to`, and `derived_from`
  - keeps raw-only `derived_from`, `supersedes`, and `refers_to` out of the persisted relation enum for this stage

## Eval Signal

`tests/eval/test_wiki_compiler_quality.py` is marked `pytest.mark.eval`, so it is deselected by default.

It provides a deterministic quality signal without live LLM calls:

- generated source packs contain one anchored source entry per source ref
- source anchors include `content_hash`, `parser_version`, `span`, line range, and preview
- mocked draft payloads preserve rationale/source references
- `draft` mode filters unintended `supersedes` / `refines` relation metadata
- `refine` modes insert the requested relation metadata
- `conflict_flag` survives parsing for Operator/Librarian review

## Validation

Final implementation validation:

```text
M5 eval:
- .venv/bin/python -m pytest -m eval tests/eval/test_wiki_compiler_quality.py -q
- 4 passed

M5 invariant guards:
- .venv/bin/python -m pytest tests/test_invariant_guards.py -q
- 35 passed

Focused phase gates:
- .venv/bin/python -m pytest tests/integration/cli/test_wiki_commands.py tests/test_specialist_agents.py tests/test_executor_protocol.py -q
- 48 passed
- .venv/bin/python -m pytest tests/integration/http/test_knowledge_browse_routes.py tests/unit/application/test_knowledge_queries.py -q
- 7 passed
- .venv/bin/python -m pytest tests/test_web_api.py tests/integration/http/test_web_write_routes.py -q
- 19 passed

Milestone/full gate:
- .venv/bin/python -m compileall -q src/swallow
- passed
- .venv/bin/python -m pytest -q
- 773 passed, 12 deselected
- git diff --check
- passed
```

## Plan Audit Absorption

`plan_audit.md` had 0 blockers / 5 concerns / 2 nits. The implementation absorbed them as follows:

- `StagedCandidate` slotted metadata was added with backward-compatible defaults, old-record loading coverage, and promote/reject passthrough preservation.
- Promotion-side relation creation is owned by `promote_stage_candidate_command`, not CLI/HTTP adapters.
- `derived_from` raw source refs remain staged/source-pack metadata and are not persisted as relation rows in this stage.
- Staged `relation_metadata` is raw compiler metadata; persisted relation rows remain limited to validated knowledge-object edges.
- `source_pack` schema is pinned to the extended `SourcePointer`-compatible anchor shape.
- Wiki Compiler tests live in the existing specialist/executor protocol files and focused CLI integration file.
- Wiki Compiler does not call `append_event` directly; task artifacts and staged candidates are written through existing governed paths.

## Deferred Follow-Ups

Intentionally deferred:

- Web-side Wiki Compiler draft/refine/refresh trigger buttons.
- Background job runner or fire-and-poll flow for long-running LLM actions.
- Project-level full graph visualization.
- Automatic promotion, automatic supersede, or automatic conflict resolution.
- Target-id driven old wiki/canonical `superseded` status flip for `supersedes` review signals.
- Persisted relation rows for raw `derived_from` source refs unless backed by a future evidence/knowledge object id design.
- LTO-6 review C1 facade naming cleanup; it remains a non-blocking follow-up.
- Roadmap post-merge factual update and `current_state.md` main-checkpoint sync; the feature-branch closeout recovery entry is already updated.

## Review Status

Claude PR review returned `recommend-merge` with 0 blockers / 1 concern / 2 nits.

Disposition:

- C1 (`WikiCompilerExecutor` empty subclass): fixed by deleting the wrapper and registering `WikiCompilerAgent` directly in `EXECUTOR_REGISTRY`.
- N1 (`relation_records` on `StagePromoteCommandResult`): acknowledged. The field is returned from the application command for future surfaces; CLI/HTTP/UI do not need to consume it in this stage.
- N2 (metadata relation enum vs persisted relation enum): addressed with an inline comment on `WIKI_COMPILER_METADATA_RELATION_TYPES`; persisted relation rows remain deliberately narrower than staged review metadata.

Current next steps:

- Human reviews the final M5 diff and commits the implementation/guard/closeout state.
- Human opens or updates the PR using `./pr.md`.
- Merge gate can now proceed after Human approval.
