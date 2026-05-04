---
author: codex
phase: r-entry-real-usage
slice: design-doc-knowledge-chain-and-ui-smoke
status: final
depends_on:
  - docs/plans/r-entry-real-usage/plan.md
  - docs/active_context.md
  - /tmp/swl-r-entry-real-usage/notes/r-entry-issues.md
---

TL;DR:
R-entry real usage ran through CLI task/knowledge/wiki/retrieval and local Web UI surfaces against `/tmp/swl-r-entry-real-usage`.
The main findings are not connectivity blockers anymore: Wiki LLM and OpenRouter rerank work after environment setup.
The highest-value next Direction Gate inputs are retrieval source scoping, truth reuse visibility, and note-only/offline lifecycle semantics.

# R-entry Real Usage Findings

## Run Summary

- base_dir: `/tmp/swl-r-entry-real-usage`
- task_id: `b73f5c5e60f7`
- source materials:
  - `docs/design/INVARIANTS.md`
  - `docs/engineering/TEST_ARCHITECTURE.md`
  - `docs/engineering/ADAPTER_DISCIPLINE.md`
- local UI smoke: passed through HTTP checks for `/`, `/api/health`, task list/detail, artifacts, task knowledge, and staged knowledge.
- Wiki real draft: passed after sourcing `.env`; produced `staged-c85f2d29`, `wiki_compiler_prompt_pack.json`, and `wiki_compiler_result.json`.
- rerank: passed with OpenRouter `cohere/rerank-v3.5`; retrieval report shows `rerank_backend: dedicated_http`, `rerank_applied: True`, and `final_order_basis: dedicated_rerank`.
- nginx/Tailscale smoke: not executed by Codex because it needs host nginx changes and a second tailnet browser/device.

## Findings

### Retrieval Source Scoping Is The Main Product Gap

The task explicitly declared design/engineering source documents, but retrieval still behaved like broad workspace lexical search plus rerank. Top references were mostly repo code, generated metadata, and archived notes, including `src/swallow.egg-info/SOURCES.txt`, `src/swallow/knowledge_retrieval/*`, `tests/integration/cli/test_retrieval_commands.py`, and `docs/archive_phases/*`.

OpenRouter rerank is now working, so this is not a rerank connectivity problem. Rerank can only reorder the candidate pool it receives; it cannot recover task-declared source documents that were not strongly present in that pool. Next retrieval work should make `document_paths` influence candidate scope or priority, and should default generated/archive paths to lower priority or exclusion unless explicitly requested.

This does not look like a chunk-size problem first. Current retrieval chunking is simple but reasonable for this test: Markdown is split by heading section with an 80-line maximum, while non-Markdown repo text is split into 40-line chunks. The observed failure happened before chunk quality became the limiting factor: the retrieval request did not carry task-declared `document_paths`, so the candidate pool was dominated by broad workspace matches. Chunk strategy may need later tuning, but the first fix should be source scoping and noise filtering.

### Truth Reuse Visibility Is Not Clear Enough

A staged ingestion candidate was promoted successfully:

- staged candidate: `staged-aebad198`
- canonical id: `canonical-staged-aebad198`
- canonical audit: `total=1`, `active=1`, `duplicate_active_keys=0`, `orphan_records=0`

However, the subsequent retrieval report still showed:

- `reused_knowledge_count: 0`
- `reused_task_knowledge_count: 0`
- `reused_canonical_registry_count: 0`
- `reused_knowledge_references: none`

This may be policy-correct, but the operator cannot tell whether canonical reuse was not considered, considered and filtered out, or missed by query matching. The report should distinguish "canonical objects exist but were skipped" from "no truth-backed knowledge exists".

### Task Knowledge Capture And Staged Knowledge Surfaces Are Ambiguous

`task knowledge-capture` returned `added=1 total=1`, and the captured object was visible in `task inspect` and `/api/tasks/<task_id>/knowledge`. But `task staged --status all --task b73f5c5e60f7` returned `count: 0`.

This looks like a surface/boundary clarity issue rather than data loss. The CLI should either show task-scoped captured knowledge there or explain that `task staged` only covers global staged candidates and direct the operator to the right command.

### Wiki Compiler Environment And Observability Improved, But Dry-run Still Has A Gap

Without `.env` sourced, `wiki draft` failed with a Python traceback ending in `AgentLLMUnavailable: LLM enhancement unavailable: API key not configured.` After sourcing `.env`, the same real draft succeeded and wrote a proper staged candidate and prompt/result artifacts.

Remaining gaps:

- Swallow does not auto-load `.env`; this is acceptable for now, but runbooks should say `source .env` explicitly before real LLM paths.
- Missing LLM config should be rendered as an operator-facing error, not a traceback.
- `wiki draft --dry-run` returned `prompt_artifact=-`; dry-run did not expose a prompt/source-pack artifact through `task artifacts`, which limits operator review before real LLM calls.

### Note-only Offline Lifecycle Semantics Are Confusing

The run command:

```bash
.venv/bin/swl --base-dir /tmp/swl-r-entry-real-usage task run b73f5c5e60f7 --executor note-only --route-mode offline
```

produced retrieval and artifacts, but the task ended as:

- status: `failed`
- execution_phase: `analysis_done`
- failure_kind: `unreachable_backend`
- control recommendation: `resume`

The artifact says "Operator selected note-only non-live mode; live executor execution was skipped." That behavior may be internally consistent, but it is poor for real usage smoke. An explicit note-only/offline run should either complete as a non-live report-producing run, or clearly label the failure as intentional/non-live rather than backend unreachable.

### Local Web UI Reads The Same Truth

Local UI/API smoke passed:

- `GET /` returned UI HTML.
- `GET /api/health` returned ok.
- `GET /api/tasks` listed `b73f5c5e60f7`.
- `GET /api/tasks/b73f5c5e60f7` returned task detail.
- `GET /api/tasks/b73f5c5e60f7/artifacts` returned artifact list.
- `GET /api/tasks/b73f5c5e60f7/knowledge` returned task knowledge.
- `GET /api/knowledge/staged?status=all` returned staged candidates.

This confirms `swl serve --host 127.0.0.1 --port 8037` can browse the same `/tmp` truth as the CLI. Browser console was not checked in this Codex run.

### Nginx/Tailscale Remains A Host-level Smoke

Code inspection and local UI smoke support the planned topology:

```text
tailnet browser -> host nginx on Tailscale IP -> proxy_pass http://127.0.0.1:8037 -> swl serve
```

The frontend uses same-origin `/api/...` paths and `swl serve` intentionally refuses non-loopback binds, so host nginx reverse proxy should not require CORS or `0.0.0.0`. The remaining test needs host nginx config plus a second Tailscale device. Avoid mounting Swallow under a subpath like `/swallow/` unless the frontend/backend path strategy changes.

## Direction Gate Candidates

1. Retrieval Source Scoping And Truth Reuse Visibility
   - Make task-declared `document_paths` affect retrieval candidate scope or priority.
   - Downgrade or exclude generated/archive paths by default.
   - Explain canonical/task knowledge considered, matched, skipped, or absent in the retrieval report.
   - Keep chunk-size changes secondary; current Markdown heading chunks are acceptable enough for the next slice, while broad candidate selection is the clearer failure.

2. Offline Note-only Run Semantics
   - Decide whether note-only/offline is a successful non-live run mode or an intentional blocked run.
   - Align task status, failure kind, control guidance, and summary artifact wording.

3. Wiki Operator Ergonomics
   - Convert missing LLM/API key tracebacks into concise CLI errors.
   - Make `wiki draft --dry-run` produce inspectable prompt/source-pack artifacts or explain why it does not.
   - Document `.env` sourcing for real LLM paths.

4. Knowledge Surface Clarity
   - Clarify the boundary between task-scoped knowledge capture and global staged knowledge.
   - Make `task staged`, `task knowledge-review-queue`, `knowledge stage-list`, and UI knowledge sections point to each other when an operator is on the wrong surface.

5. Personal Tailnet UI Recipe
   - Add a small host-nginx/Tailscale runbook once the host smoke is completed.
   - Keep `swl serve` loopback-only and do not introduce Docker or public access in this track.

## Resolved Environment Items

- `.venv` was refreshed and `.venv/bin/swl` now points to `swallow.adapters.cli:main`.
- `uvicorn` was installed into `.venv`; local `swl serve` works.
- Wiki LLM path works after sourcing `.env`.
- New API rerank attempts with local BGE names were abandoned; OpenRouter `cohere/rerank-v3.5` is working through `https://openrouter.ai/api/v1/rerank`.
