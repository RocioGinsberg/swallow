---
author: gemini
phase: 35
slice: fresh_kickoff_required
status: draft
depends_on: []
---
TL;DR: Current context after Phase 34 completion, which introduced the Cognitive Router, Dialect Framework, and Binary Fallback. The system is ready for the next phase kickoff, with several open architectural concerns noted.

### 变更范围 (Scope of Change)

The following core modules and files were significantly modified in Phase 34 and represent the most recent areas of active development, likely influencing future phases:

- `src/swallow/router.py`: Implements the `Strategy Router` and `RouteRegistry` for capability-aware routing.
- `src/swallow/executor.py`: Integrated with the dialect registry for `Claude XML` and `Codex FIM`.
- `src/swallow/orchestrator.py`: Contains the logic for binary fallback execution paths and artifact retention.
- `src/swallow/dialect_adapters/__init__.py`: Package entry point for dialect adapters.
- `src/swallow/dialect_adapters/claude_xml.py`: Implementation of the Claude XML dialect adapter.
- `src/swallow/dialect_adapters/codex_fim.py`: Implementation of the Codex FIM dialect adapter.
- `tests/test_router.py`: Unit tests for router registry and priority selection.
- `tests/test_dialect_adapters.py`: Unit tests for dialect adapters.
- `tests/test_binary_fallback.py`: Integration tests for binary fallback.
- `tests/test_cli.py`: Regression assertions updated for dialect, fallback, and lifecycle.

### 近期变更摘要 (Recent Changes Summary)

Latest 10 commits reflecting recent development:

- `aba42b0 - docs(state): move entrypoint to post-phase34 kickoff`
- `e5958f0 - merge: phase34 Cognitive Router + Dialect Framework + Binary Fallback`
- `5572bfa - docs(phase34): finalize closeout and review sync`
- `ca93f57 - docs(phase34): sync review follow-up status`
- `366cdae - feat(fallback): add binary fallback for failed primary routes`
- `6a3c603 - feat(dialect): add claude xml and codex fim adapters`
- `5d472ce - feat(router): add route registry and strategy selection`
- `ca72c4b - docs(phase34):initialize phase34 design`
- `6c8ecea - docs(design): refine cowork of agents execytor, add UI proposal`
- `103adfe - docs(state): sync post-phase33 merge entrypoint`

### 关键上下文 (Key Context)

Phase 34 successfully completed, bringing the following core capabilities:
- The orchestration layer has been upgraded from static executor mapping to a capability-aware `Strategy Router`.
- Local gateway-side now supports `ClaudeXMLDialect` and `CodexFIMDialect` through concrete adapters.
- A `local-codex -> local-summary` one-time binary fallback mechanism has been established.
- It is crucial to note that this phase explicitly *did not* involve the actual deployment or implementation of the `Provider Connector` layer (e.g., `new-api` / `TensorZero`).
- The system is currently in a `fresh_kickoff_required` state, waiting for the Human Operator to select the next phase direction from `docs/roadmap.md` or `docs/system_tracks.md`.

### 风险信号 (Risk Signals)

Based on the `docs/concerns_backlog.md`, the following open concerns may impact future development, particularly as the system evolves in routing, execution, and dialect handling:

- **Phase 34 | S2: CodexFIMDialect**: `CodexFIMDialect.format_prompt()` does not escape `<fim_prefix>` / `<fim_suffix>` strings in task titles/goals. This could disrupt FIM prompt structure if external user input is introduced or if a unified prompt escaping mechanism is not implemented.
- **Phase 29 | Slice 3: structured_markdown**: There is an identified overlap in information collection logic between `StructuredMarkdownDialect.format_prompt()` and `build_executor_prompt()`. As more dialects are added, extracting a common data collection layer should be considered to avoid redundancy.
- **Phase 32 | S3: LibrarianExecutor**: `LibrarianExecutor.execute()` directly manipulates state and performs multiple layers of persistence (`save_state` / `save_knowledge_objects` / `append_canonical_record`). This deviates from the principle established in Phase 31, where "executor only produces result, state mutation belongs to orchestrator." This architectural deviation could pose risks when introducing concurrent orchestration or executor retry mechanisms, as side effects should be centralized in the orchestrator.
