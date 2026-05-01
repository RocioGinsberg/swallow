---
author: codex
phase: candidate-r
slice: design-docs-observation
status: final
depends_on:
  - docs/plans/candidate-r/plan.md
  - docs/plans/candidate-r/observations.md
  - docs/active_context.md
---

TL;DR:
Candidate R proved that promoted design-doc canonical records are reusable for real retrieval probes.
Vector + rerank works when the local `.env` is loaded, but operator-facing retrieval observability is still too easy to misread.
Recommended next implementation candidate: Candidate U first, with Candidate T and Candidate Y as tightly related follow-ups.

# Candidate R Closeout

## Scope

- phase: `Candidate R / Real-use Feedback Observation`
- sample corpus: `docs/design/`
- seed files:
  - `docs/design/INVARIANTS.md`
  - `docs/design/KNOWLEDGE.md`
- runtime baseline:
  - `.venv/bin/swl`
  - New API OpenAI-compatible endpoint at `http://localhost:3000`
  - local SQLite-first truth / retrieval

## What Was Completed

1. `INVARIANTS.md` ingestion produced 12 staged candidates.
2. 5 invariant records were promoted:
   - §0 invariant rules
   - §4 LLM call paths
   - §5 Truth write matrix
   - §7 single-user evolution boundary
   - §9 invariant guard tests
3. P1 `2f77c3a3a82d` tested the `apply_proposal` boundary.
4. P2 `5e891023a196` tested the Path A/B/C LLM call boundary.
5. Embedding / `sqlite-vec` environment was restored and P2b confirmed vector + rerank can prioritize canonical truth.
6. `KNOWLEDGE.md` dry-run produced 32 candidate previews.
7. 10 `KNOWLEDGE.md` boundary records were inspected and promoted for P3.
8. P3 `f767f87222d9` and P3b `c1adb2f7f807` tested raw material / Knowledge Truth / Evidence / EvidencePack / fallback boundaries.

## Promoted Knowledge State

`swl knowledge canonical-audit` after `KNOWLEDGE.md` promotion:

- total: `15`
- active: `15`
- superseded: `0`
- duplicate_active_keys: `0`
- orphan_records: `0`

The registry now has:

- 5 canonical records from `INVARIANTS.md`
- 10 canonical records from `KNOWLEDGE.md`

## Main Observations

### 1. Canonical Reuse Works

P1, P2, and P3 all reused promoted canonical records. The strongest positive result is P3b: the top 7 retrieval results were all promoted `KNOWLEDGE.md` canonical records, and the metadata confirmed:

- `embedding_backend=api_embedding`
- `knowledge_retrieval_adapter=sqlite_vec`
- `knowledge_retrieval_mode=vector`
- `rerank_applied=true`

This means the basic design-doc canonical reuse path is viable.

### 2. Environment Fallback Is Too Easy To Misread

P1 and P2 initially fell back to text because the embedding API / `.env` setup was unavailable. P3 also fell back when the tool shell did not load `.env`, even though `swl doctor stack` with `.env` loaded showed `embedding_api_endpoint=pass`.

This is not a model-quality failure, but the operator experience makes it easy to draw the wrong conclusion. Retrieval reports need clearer mode / dependency status at the top.

### 3. Retrieval Report Ordering Is Confusing After Rerank

In P2b and P3b, text reports showed final rerank order, while the visible `score` values were raw / blended scores and not monotonic. `retrieval-json` exposes `rerank_position`, but the human-readable report does not make final order vs score semantics obvious.

This is a Candidate U issue because it directly affects operator trust in retrieval inspection.

### 4. Source Policy Still Needs Tightening

Under fallback, historical `docs/archive_phases/*` notes outranked canonical design truth in P2. Under vector + rerank, canonical records recovered the top positions, but observation docs still appeared in retrieval because they quote the probe itself.

This suggests the system needs clearer retrieval source policy / archive weighting / self-reference handling, not just better embeddings.

### 5. Evidence Traceability Is Still Source-only

Canonical records carry `source_ref=file://workspace/docs/design/...`, but reports do not expose resolved line spans, heading paths, or EvidencePack-style source pointers. P3b grounding evidence still reports `evidence_status=source_only`.

This is Candidate T material, but it depends on Candidate U-style report clarity to be useful to operators.

### 6. Summary Route Is Not A QA Route

For all probes, `--route-mode summary` was useful for retrieval inspection, but executor output did not answer the semantic question. It produced a local execution update and "next action" guidance.

This is acceptable if summary mode is documented as inspection-only. It becomes Candidate Y if operators expect a question-answer behavior from this route.

### 7. Staged Queue Hygiene Is Visible

Repeated ingestion can leave pending candidates from earlier attempts alongside newly promoted records. This did not affect canonical audit or P3 retrieval, but it adds operator review noise.

This is another Candidate U / review-queue observability signal.

## Recommended Next Candidate

Recommended next implementation candidate: **Candidate U — Neural retrieval observability / eval / index hardening**.

Rationale:

- Candidate U directly addresses the highest-frequency friction found in P1/P2/P3:
  - vector vs text fallback clarity
  - `.env` / embedding dependency visibility
  - rerank order vs raw score report semantics
  - source weighting / archive and self-reference policy
  - staged queue / duplicate-ingest review hygiene
- It improves operator trust before deeper wiki compiler or EvidencePack work.
- It is lower risk than implementing a full EvidencePack source resolver first, because it can start with reporting and policy visibility around already-existing retrieval behavior.

Candidate T should follow closely:

- add resolved source spans / heading paths / EvidencePack-style source pointers once Candidate U makes retrieval reports easier to interpret.

Candidate Y should be scoped narrowly:

- clarify `summary` route semantics, or add a separate answer-oriented route if Human wants semantic answers from probes.

## Non-recommendations

- Do not start Candidate S yet. The current failure is not primarily "needs wiki synthesis"; promoted canonical records already retrieve well.
- Do not start Candidate D. No real multi-task orchestration bottleneck appeared.
- Do not start AA/AB/V/W/X/Z from this evidence. They remain roadmap candidates, but R did not surface them as the primary next bottleneck.

## Suggested Follow-up Shape

Candidate U should likely start as a small implementation phase with these slices:

1. Retrieval report clarity:
   - show retrieval mode at the top
   - show embedding backend / adapter / fallback reason
   - show final order, raw score, vector distance, and rerank position explicitly
2. Source policy visibility:
   - label archive/current-state/observation-doc hits clearly
   - consider report-only warnings when notes outrank active canonical knowledge
3. Staged queue hygiene:
   - expose duplicate `source_object_id` / repeated ingest candidates in `stage-list` or an audit command
4. Minimal eval / regression fixture:
   - keep P1/P2/P3 as regression probes for canonical reuse and source ordering

## Validation Commands Run

```bash
.venv/bin/swl knowledge canonical-audit
.venv/bin/swl task inspect c1adb2f7f807
.venv/bin/swl task retrieval c1adb2f7f807
.venv/bin/swl task retrieval-json c1adb2f7f807
.venv/bin/swl task artifacts c1adb2f7f807
git diff --check
```

## Completion Status

Candidate R has met its completion conditions:

1. `docs/design/` was used as the first real-use observation sample.
2. Three retrieval probes were completed: P1, P2, P3.
3. Vector-enabled reruns were completed for P2 and P3.
4. Meaningful misses and friction points were classified into Candidate U/T/Y.
5. The next implementation direction is ready for Human review.
