---
author: codex
phase: candidate-r
slice: design-docs-observation
status: final
depends_on:
  - docs/plans/candidate-r/plan.md
  - docs/active_context.md
  - docs/roadmap.md
---

TL;DR:
Candidate R P1 confirmed that promoted `INVARIANTS.md` canonical records are reusable in task retrieval.
The first probe also exposed three observation signals: text fallback due to unavailable embedding API, current-state/plan notes outranking canonical knowledge, and `summary` route producing execution guidance rather than a direct answer.
These are observation inputs for Candidate U/Y, not immediate implementation blockers.

# Candidate R Observations

## P1: `apply_proposal` / Truth Write Boundary

- task_id: `2f77c3a3a82d`
- sample_files:
  - `docs/design/INVARIANTS.md`
- command:
  - `swl task run 2f77c3a3a82d --route-mode summary`
- result_path:
  - `results/R.md` (local observation transcript; not required as a committed artifact)

### Expected Grounding

The probe should reuse promoted invariant knowledge for:

- `apply_proposal` as the canonical / route / policy mutation boundary.
- Execution entities not writing Truth directly.
- Truth write matrix and invariant guard tests.

### Actual Grounding

- run status: completed
- route: `local-summary`
- retrieval_count: `8`
- reused_knowledge_count: `4`
- reused_canonical_registry_count: `4`
- grounding_refs:
  - `canonical:canonical-staged-d28f9cfe`
  - `canonical:canonical-staged-479e33f8`
  - `canonical:canonical-staged-ace36854`
  - `canonical:canonical-staged-74b558c6`
- source refs: all four canonical records point back to `file://workspace/docs/design/INVARIANTS.md`.
- retrieval mode visibility: `retrieval-json` reports `knowledge_retrieval_adapter: text_fallback` and `knowledge_retrieval_mode: text_fallback` for canonical records.

### Observations

1. Knowledge reuse works for the promoted invariant seed:
   - Canonical records were retrieved as cross-task knowledge.
   - Source traceability is present at the `source_ref` level.

2. Embedding fallback is visible but not healthy:
   - Run emitted `[WARN] embedding API unavailable, falling back to text search`.
   - This is useful observability, but it means P1 did not exercise vector retrieval.
   - Classification: Candidate U signal.

3. Current operational notes outrank canonical knowledge:
   - Top references were `docs/plans/candidate-r/plan.md` and `docs/active_context.md`.
   - These matched because the probe command text itself was recorded in current state/plan docs.
   - This creates self-referential retrieval noise during observation.
   - Classification: Candidate U signal, possibly source policy / notes weighting.

4. `summary` route does not answer the semantic question:
   - `executor_output.md` produced a local execution update and "next action" guidance.
   - It did not directly explain the `apply_proposal` boundary.
   - This is acceptable for retrieval inspection, but not sufficient for answer-quality evaluation.
   - Classification: Candidate Y/Interaction signal if operator expects `summary` mode to answer questions; otherwise expected route-mode behavior.

5. Evidence traceability is partial:
   - Canonical retrieval items include `source_ref=file://workspace/docs/design/INVARIANTS.md`.
   - They do not include a resolved source excerpt/span beyond canonical preview and `source_ref`.
   - Classification: mild Candidate T signal; not a blocker for P1.

### Classification

- Primary: Candidate U — retrieval observability / source weighting / fallback behavior.
- Secondary: Candidate Y — route/CLI ergonomics around `summary` mode and command transcript noise.
- Mild: Candidate T — source pointer exists, but structured EvidencePack-style source resolution is still absent.

### Next Action

Run P2 with a query that targets Path A/B/C and Provider Router boundaries, while avoiding exact duplication in `active_context.md` and `plan.md` where possible. Use `--route-mode summary` only for retrieval inspection; use a live route later if answer quality must be evaluated.

## P2: LLM Call Path / Provider Router Boundary

- task_id: `5e891023a196`
- sample_files:
  - `docs/design/INVARIANTS.md`
- command:
  - `swl task run 5e891023a196 --route-mode summary`

### Expected Grounding

The probe should retrieve the promoted §4 canonical record:

- Path A: Controlled HTTP, assembled by Orchestrator, goes through Provider Router.
- Path B: Agent Black-box, assembled by the agent, does not go through Provider Router.
- Path C: Specialist Internal, specialist pipeline, penetrates to Provider Router through Path A.

### Actual Grounding

- run status: completed
- route: `local-summary`
- retrieval_count: `8`
- reused_knowledge_count: `2`
- reused_canonical_registry_count: `2`
- grounding_refs:
  - `canonical:canonical-staged-090c3193`
  - `canonical:canonical-staged-d28f9cfe`
- target canonical record:
  - `canonical-staged-090c3193` was retrieved with `score=94`.
  - `source_ref=file://workspace/docs/design/INVARIANTS.md`.
  - `knowledge_retrieval_adapter=text_fallback`.
  - `knowledge_retrieval_mode=text_fallback`.

### Observations

1. Recall succeeded for the intended canonical knowledge:
   - The §4 LLM call path record was retrieved and exposed with useful metadata.
   - The retrieved preview contains the A/B/C table.

2. Ranking is dominated by historical archive notes:
   - The top five references were all `docs/archive_phases/phase64/*` notes.
   - These scored above the canonical §4 record because they contain many overlapping terms around Provider Router, HTTP, specialist, and internal calls.
   - This is a stronger repeat of the P1 source-weighting signal.
   - Classification: Candidate U signal; likely retrieval source policy / notes weighting / archive filtering.

3. Current-state command echo remains a retrieval contaminant:
   - `docs/active_context.md` appeared again because the exact P2 command is recorded there.
   - Classification: Candidate U/Y signal; observation docs can distort their own probes.

4. Embedding fallback repeated:
   - Run emitted `[WARN] embedding API unavailable, falling back to text search`.
   - Canonical metadata again reports `knowledge_retrieval_mode=text_fallback`.
   - Classification: Candidate U signal.

5. `summary` route again did not answer the semantic question:
   - `executor_output.md` returned local next-action guidance, not a Path A/B/C explanation.
   - This confirms `summary` mode is useful for retrieval inspection but not answer-quality evaluation.
   - Classification: Candidate Y/Interaction signal if the operator expects a question-answer mode.

### Classification

- Primary: Candidate U — archive notes outrank canonical design truth under text fallback, and vector retrieval was not exercised.
- Secondary: Candidate Y — `summary` route semantics and command-transcript retrieval contamination.
- Mild: Candidate T — source pointer exists, but no resolved EvidencePack/source span.

### Next Action

Before P3, ingest `docs/design/KNOWLEDGE.md` as the next design-doc sample. P3 should test raw material / staged knowledge / wiki-canonical / retrieval-serving boundaries, which are not sufficiently represented by the current invariant-only canonical seed.

## Environment Adjustment: Embedding API Restored

- command:
  - `swl doctor stack`
- result:
  - `new_api_http=pass`
  - `new_api_endpoint=pass`
  - `embedding_api_endpoint=pass`
  - `postgres_container=fail` / `pgvector_extension=skip`
  - `wireguard_tunnel=fail` / `egress_proxy=fail`

### Interpretation

The Candidate R P1/P2 text fallback signal was caused by missing local runtime configuration rather than an inherent retrieval baseline. The embedding endpoint now responds successfully through New API at `http://localhost:3000`.

Postgres / pgvector and WireGuard / egress proxy failures are not blockers for this local SQLite-first R observation slice.

### Next Action

Rerun P2, or create P2b with the same LLM call path query, and compare retrieval ranking / metadata against the text-fallback P2 result. If canonical §4 moves higher or metadata changes away from `text_fallback`, Candidate U should record this as an observability and fallback-policy issue rather than a confirmed vector-quality issue.

## P2b: LLM Call Path Probe After Embedding / sqlite-vec Restore

- task_id: `5e891023a196`
- sample_files:
  - `docs/design/INVARIANTS.md`
- command:
  - `.venv/bin/swl task retrieval 5e891023a196`
  - `.venv/bin/swl task retrieval-json 5e891023a196`

### Actual Grounding

- retrieval_count: `8`
- reused_knowledge_count: `3`
- reused_canonical_registry_count: `3`
- top reference:
  - `canonical-staged-090c3193` (`INVARIANTS.md` §4 LLM call paths)
- target canonical metadata:
  - `source_ref=file://workspace/docs/design/INVARIANTS.md`
  - `embedding_backend=api_embedding`
  - `knowledge_retrieval_adapter=sqlite_vec`
  - `knowledge_retrieval_mode=vector`
  - `rerank_applied=true`
  - `rerank_model=openai/gpt-4o-mini`
  - `rerank_position=1`

### Comparison Against P2 Text Fallback

- P2 text fallback ranked `canonical-staged-090c3193` at position 6, after five `docs/archive_phases/phase64/*` notes.
- P2b vector + rerank ranked `canonical-staged-090c3193` at position 1.
- This narrows the earlier Candidate U signal:
  - The core vector + rerank path can recover the intended canonical design truth.
  - The severe archive-note dominance was primarily a fallback-mode / dependency configuration problem.
  - Archive notes still appear in positions 2-6, so source policy / archive filtering remains a quality concern, but no longer blocks the current observation.

### Remaining Observability Issue

The retrieval report order is now rerank order, but displayed `score` values are not monotonic: notes with higher raw scores appear after the canonical record because rerank moved the canonical record to position 1. `retrieval-json` exposes `rerank_position`, but the text report does not make final ordering vs raw score obvious.

Classification: Candidate U, narrowed to retrieval report observability / fallback-mode clarity / archive source policy rather than a basic vector retrieval failure.

### Next Action

Continue to `docs/design/KNOWLEDGE.md --dry-run --summary` before P3. P3 should run with `.venv/bin/swl` and the restored `.env` / sqlite-vec environment so it observes vector-enabled retrieval rather than fallback behavior.

## P3 Seed Dry-run: `KNOWLEDGE.md` Knowledge Boundary Candidates

- sample_files:
  - `docs/design/KNOWLEDGE.md`
- command:
  - `.venv/bin/swl knowledge ingest-file docs/design/KNOWLEDGE.md --dry-run --summary`
- result:
  - `source_path=file://workspace/docs/design/KNOWLEDGE.md`
  - `detected_format=local_markdown`
  - `dry_run=yes`
  - `staged_candidates=32`
  - ingestion summary buckets: `Decisions=0`, `Constraints=0`, `Rejected Alternatives=0`

### Candidate Selection For P3

Use `source_object_id`, not dry-run preview IDs, as the stable review handle. Dry-run IDs are not inspectable persisted records.

Recommended P3 seed candidates:

| source_object_id | section / topic | reason |
|---|---|---|
| `ingest-knowledge-fragment-0001` | Design statement | Captures the top-level truth-first / evidence-backed / vector-assisted knowledge positioning. |
| `ingest-knowledge-fragment-0004` | Raw Material Layer | Needed for raw material vs truth boundary. |
| `ingest-knowledge-fragment-0005` | Knowledge Truth Layer | Needed for Evidence / Wiki / Canonical / Staged object boundary. |
| `ingest-knowledge-fragment-0006` | Evidence definition | Needed for Evidence-as-source-anchored-support, not chunk-store. |
| `ingest-knowledge-fragment-0008` | Retrieval & Serving Layer | Needed for retrieval-serving boundary and default retrieval order. |
| `ingest-knowledge-fragment-0009` | EvidencePack definition | Needed for structured serving output vs flat retrieval items. |
| `ingest-knowledge-fragment-0010` | Retrieval Source Types | Needed for `knowledge` / `notes` / `repo` / `artifacts` semantic boundary. |
| `ingest-knowledge-fragment-0011` | Source type stable boundaries | Needed for notes/repo/artifacts anti-confusion in P3. |
| `ingest-knowledge-fragment-0019` | Wiki / Canonical positioning | Needed for wiki/canonical as default semantic retrieval entry. |
| `ingest-knowledge-fragment-0029` | Raw Material vs Knowledge objects | Directly supports the P3 raw-material / knowledge-truth question. |

Optional candidates if P3 asks about routing defaults or index/backend boundaries:

| source_object_id | section / topic | reason |
|---|---|---|
| `ingest-knowledge-fragment-0012` | Default source type rules | Useful if P3 includes Path A/B/C source default behavior. |
| `ingest-knowledge-fragment-0013` | Storage backend independence / replaceable components | Useful if P3 asks whether indexes or raw backends are truth. |
| `ingest-knowledge-fragment-0020` | Knowledge write principles | Useful but overlaps with existing `INVARIANTS.md` canonical records. |
| `ingest-knowledge-fragment-0032` | Anti-patterns | Useful as an eval-style negative boundary list, but broad. |

Defer or reject for this seed:

- `0002` / `0003`: motivation and architecture diagram are useful context but too broad for P3 canonical seed.
- `0007`: governance mechanism overlaps existing `INVARIANTS.md` canonical records.
- `0014` / `0018`: misrouting protection is useful for a later routing probe, not the core P3 knowledge-boundary seed.
- `0015` / `0016` / `0017`: code-block fragments are split too mechanically; do not promote as canonical.
- `0021` / `0022` / `0023`: external AI session ingestion should be deferred unless R later probes external-import workflow.
- `0024` / `0025` / `0026` / `0027` / `0028`: command example fragments are too thin and should not be promoted.
- `0030`: future direction is time-sensitive / roadmap-like, not canonical operational truth for P3.
- `0031`: interface table is useful cross-reference but not central enough for this seed.

### Observations

1. Dry-run chunking is mostly semantically aligned for headings and boundary sections.
2. Code fences and command examples are over-fragmented into low-value candidates.
3. The report gives previews and `source_object_id`, but not line spans or heading paths; that limits review precision.
4. `fragments=0` while `staged_candidates=32` is confusing operator telemetry.
5. The summary classifier did not populate Decisions / Constraints / Rejected Alternatives, even though the source contains many boundary rules.

### Classification

- Primary: Candidate U — ingestion / retrieval observability, especially dry-run report clarity and source-span visibility.
- Secondary: Candidate T — evidence/source pointer traceability remains too coarse at dry-run review time.

### Next Action

Run non-dry-run ingestion for `docs/design/KNOWLEDGE.md`, inspect the real staged records, and promote only the recommended P3 seed candidates above before running the raw-material / staged-knowledge / wiki-canonical / retrieval-serving probe.

## P3 Seed Promotion: `KNOWLEDGE.md` Core Boundary Records

- command:
  - `.venv/bin/swl knowledge ingest-file docs/design/KNOWLEDGE.md --summary`
  - `.venv/bin/swl knowledge stage-inspect <candidate-id>` for each selected seed candidate
  - `.venv/bin/swl knowledge stage-promote <candidate-id> --note "Candidate R P3 knowledge-boundary seed"`
- validation:
  - `.venv/bin/swl knowledge canonical-audit`

### Promoted Records

| staged_id | canonical_id | source_object_id | topic |
|---|---|---|---|
| `staged-6c3bf658` | `canonical-staged-6c3bf658` | `ingest-knowledge-fragment-0001` | Design statement |
| `staged-35757554` | `canonical-staged-35757554` | `ingest-knowledge-fragment-0004` | Raw Material Layer |
| `staged-d153b1fc` | `canonical-staged-d153b1fc` | `ingest-knowledge-fragment-0005` | Knowledge Truth Layer |
| `staged-87b38d5f` | `canonical-staged-87b38d5f` | `ingest-knowledge-fragment-0006` | Evidence definition |
| `staged-f07145f3` | `canonical-staged-f07145f3` | `ingest-knowledge-fragment-0008` | Retrieval & Serving Layer |
| `staged-2dfb5d20` | `canonical-staged-2dfb5d20` | `ingest-knowledge-fragment-0009` | EvidencePack definition |
| `staged-a763b064` | `canonical-staged-a763b064` | `ingest-knowledge-fragment-0010` | Retrieval Source Types |
| `staged-5b08bc0a` | `canonical-staged-5b08bc0a` | `ingest-knowledge-fragment-0011` | Source type stable boundaries |
| `staged-383b9d7f` | `canonical-staged-383b9d7f` | `ingest-knowledge-fragment-0019` | Wiki / Canonical positioning |
| `staged-bdbd97a2` | `canonical-staged-bdbd97a2` | `ingest-knowledge-fragment-0029` | Raw Material vs Knowledge objects |

### Validation Result

- canonical registry total: `15`
- active: `15`
- superseded: `0`
- duplicate_active_keys: `0`
- orphan_records: `0`

### Observations

1. `stage-inspect` confirmed all selected records are semantically complete and suitable for P3.
2. The selected records cover the intended boundary surface without promoting code snippets or command examples.
3. The staged review queue still contains unpromoted `KNOWLEDGE.md` candidates and earlier pending candidates. This is acceptable for P3 because pending staged records are not default canonical truth, but it remains a queue-hygiene / duplicate-ingest observation for Candidate U.

### Next Action

Run P3 with vector-enabled `.venv/bin/swl` retrieval. The probe should ask for the boundary between raw material, staged knowledge, canonical/wiki knowledge, Evidence, EvidencePack, and vector/text fallback.

## P3/P3b: Knowledge Truth Boundary Probe

- task_id:
  - `f767f87222d9` (`P3`, first run; text fallback because the shell environment did not load `.env`)
  - `c1adb2f7f807` (`P3b`, vector-enabled rerun with `.env` loaded)
- sample_files:
  - `docs/design/KNOWLEDGE.md`
- command:
  - `.venv/bin/swl task create --title "R probe: knowledge truth boundary P3b" --goal "..."`
  - `set -a; . .env; set +a; .venv/bin/swl task run c1adb2f7f807 --route-mode summary`
  - `set -a; . .env; set +a; .venv/bin/swl task retrieval-json c1adb2f7f807`

### Expected Grounding

The probe should reuse the promoted `KNOWLEDGE.md` canonical records for:

- Raw Material Layer vs Knowledge Truth Layer.
- Evidence as source-anchored support, not a chunk store.
- EvidencePack as structured serving output.
- Wiki / Canonical as default semantic retrieval entries.
- Vector / text retrieval as fallback / auxiliary recall, not truth.

### Actual Grounding

- P3 first run completed, but emitted `[WARN] embedding API unavailable, falling back to text search`.
- Doctor with `.env` loaded reports `embedding_api_endpoint=pass`; Postgres / WireGuard failures remain non-blocking for this SQLite-first slice.
- P3b completed without fallback warning.
- P3b retrieval:
  - retrieval_count: `8`
  - reused_knowledge_count: `7`
  - reused_canonical_registry_count: `7`
  - top 7 results: all promoted `KNOWLEDGE.md` canonical records
  - result 8: `docs/plans/candidate-r/observations.md`, showing observation docs still act as self-referential notes retrieval
- P3b vector metadata:
  - `embedding_backend=api_embedding`
  - `knowledge_retrieval_adapter=sqlite_vec`
  - `knowledge_retrieval_mode=vector`
  - `rerank_applied=true`
  - `rerank_model=openai/gpt-4o-mini`

Top canonical hits:

| rerank_position | canonical_id | source_object_id | topic |
|---|---|---|---|
| 1 | `canonical-staged-bdbd97a2` | `ingest-knowledge-fragment-0029` | Raw Material vs Knowledge objects |
| 2 | `canonical-staged-2dfb5d20` | `ingest-knowledge-fragment-0009` | EvidencePack definition |
| 3 | `canonical-staged-35757554` | `ingest-knowledge-fragment-0004` | Raw Material Layer |
| 4 | `canonical-staged-383b9d7f` | `ingest-knowledge-fragment-0019` | Wiki / Canonical positioning |
| 5 | `canonical-staged-f07145f3` | `ingest-knowledge-fragment-0008` | Retrieval & Serving Layer |
| 6 | `canonical-staged-5b08bc0a` | `ingest-knowledge-fragment-0011` | Source type stable boundaries |
| 7 | `canonical-staged-6c3bf658` | `ingest-knowledge-fragment-0001` | Design statement |

### Observations

1. The promoted `KNOWLEDGE.md` seed works well for the intended boundary query under vector + rerank.
2. Retrieval still records `evidence_status=source_only`; source refs point to `file://workspace/docs/design/KNOWLEDGE.md`, but the report does not expose resolved line spans / heading paths.
3. Text `retrieval` report order follows rerank order, but displayed raw scores are not monotonic. Example: rerank position 1 has `score=95`, while positions 2 and 3 have higher raw scores. This repeats the P2b report-readability issue.
4. `summary` route still produces a local execution update / next-action artifact, not a direct semantic answer. Retrieval quality can be inspected, but answer quality cannot be judged from this route mode.
5. Loading `.env` is required in this tool shell for live embedding calls. The P3/P3b difference is an operator-environment observability issue, not a retrieval model issue.
6. Observation docs are now visible as notes retrieval. They did not outrank canonical knowledge under vector + rerank, but they remain a self-reference contaminant.

### Classification

- Primary: Candidate U — retrieval observability / report clarity / environment fallback clarity / source-policy self-reference.
- Secondary: Candidate T — source refs exist, but EvidencePack-style resolved source spans remain missing.
- Secondary: Candidate Y — `summary` route semantics are good for retrieval inspection but misleading for question-answer expectations.

### Next Action

Candidate R now has three concrete probes (`P1`, `P2`, `P3`) plus vector-enabled reruns (`P2b`, `P3b`). Prepare `docs/plans/candidate-r/closeout.md` with a recommendation that the next implementation candidate should prioritize Candidate U, with Candidate T and Candidate Y as closely related follow-ups.
