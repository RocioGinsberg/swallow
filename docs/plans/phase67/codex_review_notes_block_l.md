---
author: codex
phase: phase67
slice: m1-small-hygiene-cleanup
status: final
depends_on:
  - docs/plans/phase67/kickoff.md
  - docs/plans/phase67/design_decision.md
  - docs/plans/phase67/risk_assessment.md
  - docs/plans/phase67/context_brief.md
  - docs/plans/phase66/audit_index.md
---

TL;DR: M1 implemented the seven quick-wins and stopped at the audit gate. Two implementation choices intentionally differ from the literal plan text: retrieval truncation constants live in `retrieval_config.py` to avoid a `retrieval.py`/`retrieval_adapters.py` import cycle, and `orchestrator.create_task(...)` now reuses `review_gate.DEFAULT_REVIEWER_TIMEOUT_SECONDS` because that import already exists safely.

# Codex Review Notes: Phase 67 M1

## Scope Completed

- Removed dead `run_consensus_review(...)` sync wrapper from `review_gate.py`.
- Removed module-level `_pricing_for(...)` from `cost_estimation.py`; retained live `StaticCostEstimator._pricing_for(...)`.
- Kept `rank_documents_by_local_embedding(...)` in `retrieval_adapters.py` and marked it `eval-only`.
- Named SQLite connect / busy-timeout constants in `sqlite_store.py`.
- Switched CLI MPS policy choices to `sorted(MPS_POLICY_KINDS)` from `mps_policy_store.py`.
- Named retrieval scoring / preview limits and ingestion report preview limits.
- Named executor timeout default; documented reviewer-timeout ownership where direct imports would add coupling.

## Implementation Notes For Claude

1. `RETRIEVAL_SCORING_TEXT_LIMIT` and `RETRIEVAL_PREVIEW_LIMIT` live in `retrieval_config.py`, not `retrieval.py`.
   The design text suggested importing the scoring limit from `swallow.retrieval`, but `retrieval.py` already imports `retrieval_adapters.py`. Having `retrieval_adapters.py` import back from `retrieval.py` would create a circular import. `retrieval_config.py` is already the owner for retrieval tunables and is imported by both modules without a cycle.

2. `retrieval.py` had an extra `[:220]` preview truncation in relation expansion.
   Phase 67 design listed several retrieval preview sites, but grep found one additional same-semantic preview in `expand_by_relations(...)`. I replaced it with `RETRIEVAL_PREVIEW_LIMIT` as part of the same quick-win instead of leaving a known same-semantic literal behind.

3. `quality_reviewer.py` still contains `preview[:4000]`.
   I intentionally left it unchanged because it is not a retrieval scoring callsite; it is an operator-facing quality-review preview. Pulling it into M1's retrieval scoring constant would broaden the scope beyond the Phase 67 M1 quick-win.

4. `orchestrator.create_task(...)` now imports and uses `DEFAULT_REVIEWER_TIMEOUT_SECONDS`.
   The design blocked imports from `models.py`/`planner.py` into `review_gate.py` because of coupling/cycle risk. `orchestrator.py` already imports review-gate objects, so reusing the constant there is safe and removes two extra `60` literals from the create-task normalization path.

5. `planner.py` still has two literal `60` values with an ownership comment.
   This follows the design's option (b): the literal mirrors `review_gate.DEFAULT_REVIEWER_TIMEOUT_SECONDS`, avoiding new coupling from planner to review-gate internals.

## Verification Completed

```bash
.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed

git diff -- docs/design
# no output

.venv/bin/python -m pytest -q tests/test_cost_estimation.py tests/test_retrieval_adapters.py tests/test_planner.py tests/test_review_gate.py tests/test_review_gate_async.py tests/test_executor_protocol.py tests/test_executor_async.py tests/test_sqlite_store.py tests/test_phase65_sqlite_truth.py tests/test_cli.py
# 353 passed, 10 subtests passed

.venv/bin/python -m pytest -q
# 610 passed, 8 deselected, 10 subtests passed
```

## Review Checks To Re-run

```bash
rg -n 'run_consensus_review\\b|def _pricing_for|\\[:4000\\]|\\[:220\\]|timeout=5\\.0|busy_timeout = 5000|choices=\\("mps_round_limit"' src tests
rg -n 'AIWF_EXECUTOR_TIMEOUT_SECONDS", "20"' src tests
git diff -- docs/design
git diff --check
.venv/bin/python -m pytest -q
```

Expected residuals for the first grep:

- `src/swallow/cost_estimation.py`: the live `StaticCostEstimator._pricing_for(...)` instance method remains.
- `src/swallow/quality_reviewer.py`: `preview[:4000]` remains intentionally out of M1 scope because it is a quality-review preview, not retrieval scoring.
