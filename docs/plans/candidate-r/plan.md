---
author: codex
phase: candidate-r
slice: design-docs-observation
status: final
depends_on:
  - docs/active_context.md
  - docs/roadmap.md
  - docs/design/INVARIANTS.md
---

TL;DR:
Candidate R starts with `docs/design/` as the first real-use observation sample.
The goal is to expose retrieval / wiki / evidence / routing gaps from actual operator work, then classify them into follow-up candidates instead of starting implementation prematurely.
No runtime code, schema, governance rule, or design-doc body changes are in scope for this observation slice.

# Candidate R Plan

## Frame

- phase: `Candidate R / v1.5.0 Real-use Feedback & RAG Gap Triage`
- track: `Operations / Knowledge`
- active_sample: `docs/design/`
- recommended_branch: `main` for observation state only; create `feat/<candidate>` only after Human selects a follow-up implementation candidate
- goal: use the design document directory as a real local corpus to observe whether Swallow can ingest, retrieve, explain, cite, and route against its own architecture knowledge.
- command_environment: use `.venv/bin/swl` for Candidate R commands so the restored local `.env`, API embedding endpoint, and installed `sqlite-vec` are exercised consistently.
- non_goals:
  - Do not implement Candidate S/T/U/AA/AB/V/W/X/Y/Z during this slice.
  - Do not modify `docs/design/*.md` as part of observation.
  - Do not promote every design-doc chunk blindly; only promote selected staged candidates after operator review.
  - Do not treat schema v2 migration, durable proposal artifact restore, or object-storage backend as R-entry blockers.

## Anchors

- `docs/design/INVARIANTS.md` — Control / Truth / LLM path / `apply_proposal` boundaries stay fixed.
- `docs/design/KNOWLEDGE.md` — staged review, wiki/canonical, Evidence, Retrieval & Serving, and raw material boundaries.
- `docs/design/INTERACTION.md` — CLI / local FastAPI surface boundaries; CLI remains the primary operator path for this slice.
- `docs/design/DATA_MODEL.md` — SQLite namespace and repository write constraints.
- `docs/roadmap.md` — Candidate R observation dimensions and R2 follow-up classification rules.
- `docs/engineering/TEST_ARCHITECTURE.md` — only relevant if observation reveals test friction; do not start AA unless selected later.
- `docs/engineering/CODE_ORGANIZATION.md` — only relevant if observation reveals source-organization friction; do not start V/W/X/Y/Z unless selected later.

## Plan

| Milestone | Slice | Scope | Risk | Validation | Gate |
|---|---|---|---|---|---|
| M0 | R-entry state alignment | Record `docs/design/` as active observation sample and clear stale pending-review wording. | low | `git status --short --branch`; `git diff --check` | Human review + docs commit |
| M1 | Design-doc corpus intake smoke | Dry-run and selectively ingest representative files from `docs/design/`; inspect staged candidates before any promotion. | low | `.venv/bin/swl knowledge ingest-file <file> --dry-run --summary`; `.venv/bin/swl knowledge stage-list`; `.venv/bin/swl knowledge stage-inspect <candidate>` | Human decides which candidates, if any, to promote |
| M2 | Retrieval / serving task probes | Create 3-5 real tasks whose answers should depend on design-doc knowledge; inspect retrieval and task reports after each run. | medium | `.venv/bin/swl task inspect`; `.venv/bin/swl task retrieval`; `.venv/bin/swl task retrieval-json`; `.venv/bin/swl task artifacts` | Classify each miss or friction point into R2 buckets |
| M3 | R triage summary | Summarize observed gaps and recommend the next candidate: AA, V, S, T, U, AB/W/X, D, Y, or Z. | low | Observation notes are concrete enough to map each issue to a roadmap candidate. | Human Direction Gate for next phase |

## Observation Workflow

### 1. Pick the initial design-doc subset

Use this order unless Human chooses otherwise:

1. `docs/design/INVARIANTS.md`
2. `docs/design/KNOWLEDGE.md`
3. `docs/design/DATA_MODEL.md`
4. `docs/design/ORCHESTRATION.md`
5. `docs/design/PROVIDER_ROUTER.md`
6. `docs/design/INTERACTION.md`

This subset covers the core invariants, knowledge truth, retrieval, orchestration, routing, and operator surfaces without ingesting the entire directory on the first pass.

### 2. Run non-mutating intake first

For each file:

```bash
.venv/bin/swl knowledge ingest-file docs/design/INVARIANTS.md --dry-run --summary
```

Record whether section splitting, source refs, and candidate summaries are understandable. If dry-run output is too noisy or too thin, classify it before promoting anything.

Important operator note: `--dry-run` candidate IDs are preview-only. They are not written to `.swl/staged_knowledge/registry.jsonl`, so `.venv/bin/swl knowledge stage-inspect <candidate-id>` will report `Unknown staged candidate` for those IDs. To inspect candidates, rerun ingest without `--dry-run` first.

### 3. Ingest and review selectively

Only after dry-run output is acceptable:

```bash
.venv/bin/swl knowledge ingest-file docs/design/INVARIANTS.md --summary
.venv/bin/swl knowledge stage-list
.venv/bin/swl knowledge stage-inspect <candidate-id>
```

`stage-inspect` currently accepts one candidate ID per command. For multiple candidates, run it in a shell loop rather than passing all IDs as positional arguments.

Promote only high-signal candidates:

```bash
.venv/bin/swl knowledge stage-promote <candidate-id> --note "Candidate R design-doc observation"
```

Reject noisy candidates rather than forcing the corpus into canonical truth:

```bash
.venv/bin/swl knowledge stage-reject <candidate-id> --note "Too broad for canonical promotion during Candidate R"
```

### 4. Create retrieval probes

Create tasks that ask questions whose answers should be grounded in the design docs:

```bash
.venv/bin/swl task create \
  --title "R probe: apply_proposal boundary" \
  --goal "Explain which truth objects may be mutated through apply_proposal and why executors cannot write them directly." \
  --workspace-root .
```

Then run and inspect:

```bash
.venv/bin/swl task run <task-id>
.venv/bin/swl task inspect <task-id>
.venv/bin/swl task retrieval <task-id>
.venv/bin/swl task retrieval-json <task-id>
.venv/bin/swl task artifacts <task-id>
```

Recommended probes:

1. `apply_proposal` boundary: should cite or reuse INVARIANTS / DATA_MODEL / SELF_EVOLUTION concepts.
2. Path A/B/C boundary: should distinguish controlled HTTP, agent black-box, and specialist internal.
3. Raw material vs Knowledge Truth: should distinguish raw refs, staged candidates, wiki/canonical, and retrieval.
4. EvidencePack gap: should reveal whether serving can return structured evidence or only flat retrieval items.
5. CLI / FastAPI boundary: should explain why normal CLI commands bypass HTTP while Browser UI uses local FastAPI.

## R2 Classification Rules

Use these buckets when a probe fails or creates friction:

- Candidate S: answer needs wiki-style explanation or synthesis that deterministic canonical mapping cannot provide.
- Candidate T: answer finds the right knowledge but cannot trace supporting evidence or source pointers.
- Candidate U: retrieval mode, vector/text fallback, rerank, source policy, or eval quality is not visible enough.
- Candidate AA: writing or running the probe is slowed by test fixture / CLI harness / guard-test friction.
- Candidate AB: CLI / FastAPI / application command-query / persistence boundaries become unclear.
- Candidate V: Knowledge Plane import/API naming makes the next knowledge feature harder to express.
- Candidate W: Provider Router route policy, metadata, selection, or completion gateway ownership becomes unclear.
- Candidate X: orchestration, harness, executor, subtask, retrieval, or artifact flow is too coupled to inspect or change.
- Candidate D: a real multi-task dependency / Planner / DAG bottleneck appears in actual use.
- Candidate Y: CLI command or Meta Optimizer surface aggregation blocks routine operator work.
- Candidate Z: `apply_proposal` private handler complexity blocks governance review while preserving the single public entry.

## Observation Record Format

For each probe, record:

```text
probe:
sample_files:
command:
expected_grounding:
actual_grounding:
retrieval_mode_seen: knowledge | repo | notes | artifacts | vector | text_fallback | unknown
evidence_trace: clear | partial | missing
operator_friction:
classification:
next_action:
```

## Material Risks

- Over-promoting design-doc chunks: this could turn broad design prose into noisy canonical truth -> use dry-run, inspect, and selective promotion.
- Dry-run ID confusion: preview IDs are useful for counting and scanning but are not inspectable persisted records -> inspect only IDs from `.venv/bin/swl knowledge stage-list` after a non-dry-run ingest.
- Mistaking repo retrieval for knowledge retrieval: a correct answer from `repo` source may not prove the Knowledge Plane is healthy -> inspect `retrieval` and `retrieval-json` after each task.
- Treating observation as implementation: R should produce classified evidence for the next candidate, not opportunistic code edits.
- LLM / executor environment variability: if live execution is unavailable, record the blocker and continue with ingestion / retrieval inspect where possible.

## Validation

```bash
git status --short --branch
git diff --check
.venv/bin/swl doctor sqlite
.venv/bin/swl knowledge ingest-file docs/design/INVARIANTS.md --dry-run --summary
```

Task-level validation after each probe:

```bash
.venv/bin/swl task inspect <task-id>
.venv/bin/swl task retrieval <task-id>
.venv/bin/swl task retrieval-json <task-id>
.venv/bin/swl task artifacts <task-id>
```

## Completion Conditions

1. `docs/design/` has been used as the first Candidate R observation sample.
2. At least three retrieval probes have been run or explicitly blocked with concrete environment reasons.
3. Each meaningful miss or friction point is classified into the R2 buckets above.
4. Human selects the next candidate direction from the observed evidence, or decides to continue R with a second sample corpus.
5. `docs/plans/candidate-r/closeout.md` records the final R-stage observations and next-phase recommendation.
