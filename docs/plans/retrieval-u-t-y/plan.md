---
author: codex
phase: retrieval-u-t-y
slice: plan-definition
status: approved
depends_on:
  - docs/plans/candidate-r/closeout.md
  - docs/plans/candidate-r/observations.md
  - docs/roadmap.md
  - docs/design/INVARIANTS.md
  - docs/design/KNOWLEDGE.md
  - docs/design/INTERACTION.md
  - docs/engineering/GOF_PATTERN_ALIGNMENT.md
---

TL;DR:
This phase implements the U -> T -> Y retrieval follow-through on branch `feat/retrieval-u-t-y`.
U comes first: make retrieval mode, fallback, dedicated rerank order, source policy, and regression probes observable.
T and Y follow as bounded milestones: EvidencePack/source resolution, then narrow summary/QA surface clarification.

# Retrieval U-T-Y Plan

## Frame

- active branch: `feat/retrieval-u-t-y`
- track: `Retrieval Quality`
- bundled candidates:
  - Candidate U: Neural Retrieval Observability / Eval / Index Hardening
  - Candidate T: EvidencePack Assembly / Source Resolution
  - Candidate Y: Surface Command / Summary Route Ergonomics, narrow scope only
- implementation stance: one branch, separate milestone commits, no big-bang retrieval rewrite
- branch goal: turn Candidate R's real-use findings into operator-visible retrieval behavior and source evidence, then clarify the summary route surface enough that future probes are not misread.

## Goals

1. Make `swl task retrieval` and `swl task retrieval-json` show the effective retrieval path:
   - vector vs text fallback vs relation expansion
   - embedding backend / adapter
   - fallback reason when vector retrieval is unavailable
   - raw score vs final rerank order when a dedicated rerank adapter is configured
   - source policy labels for canonical, notes, archive, current-state, observation-doc, repo, and artifact hits
2. Preserve existing `RetrievalItem` compatibility while introducing bounded trace value objects where useful:
   - `RetrievalTrace`
   - `RetrievalMode`
   - `FallbackReason`
   - `RerankTrace`
3. Assemble an initial EvidencePack-compatible view without redefining Knowledge Truth:
   - primary / canonical objects
   - supporting evidence
   - fallback hits
   - source pointers
   - resolved line span / heading path where available
4. Clarify summary route ergonomics:
   - distinguish retrieval inspection from semantic answer production
   - prevent `--route-mode summary` probe output from being mistaken for a QA answer
   - keep current CLI entry points stable unless a small additive command is clearly required
5. Encode P1/P2/P3-style regression probes as lightweight local tests or fixtures where feasible.

## Non-Goals

- Do not change `docs/design/*.md` design semantics in this implementation phase.
- Do not make vector index or dedicated rerank output a source of truth.
- Do not use chat completion as a rerank fallback.
- Do not silently rerank unless a dedicated rerank model / endpoint is explicitly configured.
- Do not bypass retrieval source policy or governance filters during query rewrite / rerank.
- Do not change Path A/B/C Provider Router boundaries.
- Do not introduce a new orchestration platform, external database, or hosted retrieval service.
- Do not perform broad CLI / Meta Optimizer module splitting beyond the narrow Candidate Y surface fix.
- Do not implement LLM Wiki Compiler / Wiki Refinement here.
- Do not rewrite Provider Router, Orchestrator, Knowledge Plane, or governance handler modules as part of this phase.

## Design And Engineering Anchors

- `docs/design/INVARIANTS.md`
  - Control remains with Orchestrator / Operator.
  - Execution never writes Truth directly.
  - Path A/B/C boundaries remain unchanged.
  - `apply_proposal` remains the unique canonical / route / policy mutation entry.
- `docs/design/KNOWLEDGE.md`
  - Truth before retrieval.
  - Wiki / Canonical are default semantic retrieval entry points.
  - EvidencePack does not embed raw bytes as Truth.
  - Fallback hits must be explicit.
- `docs/design/INTERACTION.md`
  - CLI stays the primary local operator path.
  - FastAPI remains an adapter, not a second Orchestrator.
- `docs/engineering/GOF_PATTERN_ALIGNMENT.md`
  - Use patterns as responsibility language.
  - Candidate U first applies Value Object / Strategy / Adapter / Facade.
  - Candidate T uses EvidencePack / SourcePointer / ResolvedEvidence.
  - Candidate Y uses Command / Adapter / Facade to clarify surface semantics.
- `docs/engineering/CODE_ORGANIZATION.md`
  - Prefer facade-first migration.
  - Keep existing public imports and CLI/API behavior compatible.
- `docs/engineering/TEST_ARCHITECTURE.md`
  - Add focused tests close to touched behavior.
  - Keep guard tests visible and unchanged.

## Current Code Touch Map

Likely implementation surfaces:

- `src/swallow/knowledge_retrieval/retrieval.py`
  - retrieval item metadata, mode/fallback/rerank trace assembly
  - relation expansion and rerank trace annotation
- `src/swallow/knowledge_retrieval/retrieval_adapters.py`
  - vector adapter fallback reason and embedding backend details
- `src/swallow/knowledge_retrieval/grounding.py`
  - source pointer / resolved grounding entries
- `src/swallow/orchestration/models.py`
  - small value objects if the existing model layer is the least disruptive home
- `src/swallow/orchestration/harness.py`
  - `build_retrieval_report`, `build_source_grounding`, artifact assembly
- `src/swallow/surface_tools/cli.py`
  - `task retrieval`, `task retrieval-json`, narrow summary route messaging
- tests:
  - `tests/test_retrieval_adapters.py`
  - `tests/test_grounding.py`
  - `tests/test_cli.py`
  - optional focused new test module if it reduces `test_cli.py` growth

## Milestones

| Milestone | Candidate | Slice | Scope | Risk | Gate |
|---|---|---|---|---|---|
| M0 | U/T/Y | Plan and branch alignment | Create `feat/retrieval-u-t-y`, draft this plan, sync active context. | low | Human plan review before code implementation |
| M1 | U | Retrieval trace value objects, dedicated rerank adapter, and report header | Add structured mode/adapter/backend/fallback/rerank trace data; replace chat-completion rerank with explicit dedicated rerank configuration; surface all of it in retrieval report/json without breaking old fields. | medium | Focused retrieval tests + CLI report tests |
| M2 | U | Source policy labels and observation-noise warnings | Label archive/current-state/observation-doc/canonical/source types; warn when non-canonical operational docs outrank active canonical truth. | medium | Tests for labels and warning conditions |
| M3 | U | Regression probes and staged queue hygiene | Encode P1/P2/P3 retrieval expectations where feasible; add staged duplicate/source_object hygiene warnings or audit output. | medium | Focused regression/eval tests; no external API required by default |
| M4 | T | EvidencePack compatibility view | Add initial EvidencePack-style assembly from current `RetrievalItem[]`, preserving existing retrieval artifacts. | medium-high | Unit tests for primary/canonical/supporting/fallback/source_pointers |
| M5 | T | Source pointer resolution | Resolve `file://workspace/...`, artifact refs, line spans, and heading path where available through existing RawMaterialStore/file helpers. | medium-high | Grounding tests + raw material resolution tests |
| M6 | Y | Summary route surface clarification | Clarify summary route as inspection/local execution summary, or add a small explicit QA surface if current commands cannot express that boundary. | medium | CLI tests + task probe smoke |
| M7 | U/T/Y | End-to-end smoke and closeout | Re-run local retrieval probes with `.env` loaded; update closeout/current state. | medium | Focused pytest + CLI smoke + `git diff --check` |

## Slice Details

### M1: Retrieval Trace And Report Header

Expected additions:

- A top-level retrieval summary in report artifacts:
  - `retrieval_mode`
  - `retrieval_adapter`
  - `embedding_backend`
  - `fallback_reason`
  - `rerank_backend`
  - `rerank_model`
  - `rerank_enabled`
  - `rerank_configured`
  - `rerank_attempted`
  - `rerank_applied`
  - `rerank_failure_reason`
  - `final_order_basis`
- Per-item readability:
  - `final_rank`
  - `raw_score`
  - `vector_distance_milli` when present
  - `rerank_position` when present
  - existing `score_breakdown` remains available

Acceptance:

- Existing `retrieval-json` consumers still receive current item fields.
- Reports make it obvious when a run used `text_fallback`.
- Reranked order is readable without reverse-engineering raw score values.
- Chat-completion rerank is removed from retrieval.
- If a dedicated rerank endpoint/model is not configured, rerank is disabled and `final_order_basis` remains the normal retrieval score path.
- If a dedicated rerank endpoint/model is configured but unavailable or returns an unreadable payload, the report records the failure and keeps the pre-rerank order; it does not fall back to chat.

### M1b: Dedicated Rerank Adapter Boundary

Expected configuration direction:

- `SWL_RETRIEVAL_RERANK_ENABLED`
- `SWL_RETRIEVAL_RERANK_TOP_N`
- `SWL_RETRIEVAL_RERANK_MODEL`
- `SWL_RETRIEVAL_RERANK_URL` or an equivalent explicit endpoint setting
- optional `SWL_RETRIEVAL_RERANK_API_KEY`, falling back to `SWL_API_KEY`
- optional timeout setting for rerank only

Implementation constraints:

- Rerank must not call `provider_router.agent_llm.call_agent_llm`.
- Rerank must not call `/v1/chat/completions`.
- Rerank must use a dedicated adapter for a rerank-shaped HTTP contract.
- Default behavior without rerank configuration is no rerank, not chat fallback.
- The adapter should be narrow and replaceable; if New API exposes a rerank-compatible endpoint, configure that endpoint. If not, leave rerank disabled until a real rerank model is available.

### M2: Source Policy Labels

Expected additions:

- A per-item source policy label, such as:
  - `canonical_truth`
  - `active_note`
  - `archive_note`
  - `current_state`
  - `observation_doc`
  - `repo_source`
  - `artifact_source`
  - `fallback_text_hit`
- Warning section in retrieval report when:
  - archive/current-state/observation docs outrank active canonical truth
  - task observation docs self-reference the current probe
  - fallback hits are present without canonical/wiki primary objects

Acceptance:

- Candidate R P2-style archive outranking is visible as a warning, not just buried in raw references.
- The warning is advisory; it does not silently filter results unless later approved.

### M3: Regression Probes And Staged Hygiene

Expected additions:

- Lightweight regression coverage for:
  - P1: `apply_proposal` boundary should retrieve invariant canonical records.
  - P2: LLM Path A/B/C query should rank the LLM-call-path canonical record highly when vector/rerank metadata is present.
  - P3: Knowledge Truth query should prefer promoted `KNOWLEDGE.md` canonical records.
- Staged queue hygiene visibility for repeated `source_object_id`, repeated file ingestion, or confusing dry-run vs persisted candidate counts.

Acceptance:

- Tests do not require live embedding API by default.
- Live `.env` smoke can be documented separately from default pytest.
- Duplicate staged intake is visible before promotion.

### M4: EvidencePack Compatibility View

Expected additions:

- Initial value objects or structured dicts for:
  - `EvidencePack`
  - `SourcePointer`
  - `ResolvedEvidence`
- Assembly from existing retrieval items into:
  - `primary_objects`
  - `canonical_objects`
  - `supporting_evidence`
  - `fallback_hits`
  - `source_pointers`
- Retrieval report includes an EvidencePack summary while current top references remain.

Acceptance:

- EvidencePack does not become a second Truth store.
- Current `RetrievalItem[]` artifacts remain available.
- Fallback hits are explicitly labeled and not presented as primary truth.

### M5: Source Pointer Resolution

Expected additions:

- Resolve local source refs where possible:
  - `file://workspace/...`
  - artifact refs
  - markdown heading / line span metadata already present in retrieval metadata
- Show unresolved source pointers explicitly instead of implying full evidence resolution.

Acceptance:

- `source_grounding.md` and `retrieval_report.md` can point operators to the relevant file/span when metadata supports it.
- Source-only canonical records remain honest about their evidence status.

### M6: Summary Route Surface Clarification

Expected additions:

- Documentation and/or CLI output clarifies that `--route-mode summary` is a local summary/inspection path, not guaranteed semantic QA.
- If necessary, add a small explicit answer-producing surface rather than overloading `summary`.
- Preserve existing `local-summary` route fallback behavior.

Acceptance:

- Candidate R-style probes no longer look like failed semantic answers when they only asked for inspection artifacts.
- Existing tests for route fallback and local summary behavior continue to pass.

## Validation Plan

Default focused checks:

```bash
.venv/bin/python -m pytest tests/test_retrieval_adapters.py -q
.venv/bin/python -m pytest tests/test_grounding.py -q
.venv/bin/python -m pytest tests/test_cli.py -q -k "retrieval or grounding or summary"
git diff --check
```

Full check before PR:

```bash
.venv/bin/python -m compileall -q src/swallow
.venv/bin/python -m pytest -q
git diff --check
```

Live local smoke, only when `.env` is intentionally loaded:

```bash
set -a
. .env
set +a
.venv/bin/swl doctor stack
.venv/bin/swl task run 5e891023a196 --route-mode summary
.venv/bin/swl task retrieval 5e891023a196
.venv/bin/swl task retrieval-json 5e891023a196
```

The live smoke must not print secrets from `.env`.

## Risks And Controls

| Risk | Control |
|---|---|
| Retrieval JSON compatibility break | Add new fields, preserve existing item shape and metadata keys. |
| Over-filtering useful notes/archive hits | Label and warn first; do not silently suppress unless separately approved. |
| EvidencePack becomes a shadow Truth plane | Keep it as assembled serving output over source pointers and bounded excerpts. |
| Live embedding / rerank dependency makes tests flaky | Default tests mock vector and dedicated rerank behavior; live smoke remains manual. |
| Summary route UX grows into broad CLI refactor | Limit Candidate Y to messaging or a small additive command if required. |
| Pattern abstraction bloat | Only introduce value objects where reports/artifacts cross layer boundaries. |

## Commit / Review Gates

- M0: docs-only plan/state commit.
- M1 and M2 may share a milestone commit if the patch stays localized to retrieval trace/report labels.
- M3 should be its own commit if it adds eval/regression fixture structure.
- M4 and M5 should be separate commits because EvidencePack/source resolution touches a broader contract.
- M6 should be a separate surface commit.
- M7 closeout/state sync should be docs-only.

Suggested branch name is already active:

```bash
feat/retrieval-u-t-y
```

## Completion Conditions

- `swl task retrieval` exposes mode/fallback/rerank/source-policy information clearly.
- `swl task retrieval-json` preserves existing fields and includes enough structured trace data for future tooling.
- EvidencePack-compatible assembly exists without changing Knowledge Truth semantics.
- Source pointers are resolved where metadata supports it and unresolved states are explicit.
- Summary route behavior is no longer easy to confuse with semantic QA.
- Focused tests and final full pytest pass.
- `docs/plans/retrieval-u-t-y/closeout.md`, `docs/active_context.md`, and `current_state.md` are updated at phase closeout.
