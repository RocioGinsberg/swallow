---
author: codex
phase: phase67
slice: closeout
status: review
created_at: 2026-04-30
depends_on:
  - docs/plans/phase67/kickoff.md
  - docs/plans/phase67/design_decision.md
  - docs/plans/phase67/risk_assessment.md
  - docs/plans/phase67/context_brief.md
  - docs/plans/phase67/design_audit.md
  - docs/plans/phase67/codex_review_notes_block_l.md
  - docs/plans/phase67/review_comments_block_l.md
  - docs/plans/phase67/codex_review_notes_block_m.md
  - docs/plans/phase67/review_comments_block_m.md
  - docs/plans/phase67/codex_review_notes_block_n.md
  - docs/plans/phase67/review_comments_block_n.md
  - docs/plans/phase66/audit_index.md
  - docs/concerns_backlog.md
---

TL;DR: Phase 67 is implementation-complete and ready for PR / Human Merge Gate. It consumed Phase 66 audit candidates L+M+N through strict milestone gates: M1 handled seven quick wins, M2 centralized JSON / JSONL IO helper ownership, and M3 tightened read-only CLI artifact printer dispatch. Final review verdict is `APPROVE`; full pytest passed with `610 passed, 8 deselected, 10 subtests passed`.

# Phase 67 Closeout

## Conclusion

Phase 67 completed the consolidated L+M+N cleanup phase accepted by Human with strict milestone isolation:

- M1: Small Hygiene Cleanup.
- M2: IO Helper + Artifact Ownership.
- M3: CLI Read-Only Dispatch Tightening.

The phase made no `docs/design/` changes and did not alter governance write paths, `task inspect`, or `task review`.

## Milestone Review

### M1: Small Hygiene Cleanup

Completed:

- Removed dead `run_consensus_review(...)` sync wrapper.
- Removed dead module-level `_pricing_for(...)`.
- Marked `rank_documents_by_local_embedding(...)` eval-only.
- Named SQLite timeout constants.
- Moved CLI MPS policy choices to `MPS_POLICY_KINDS`.
- Named retrieval / ingestion preview constants.
- Named executor timeout default and clarified reviewer-timeout ownership.

Review:

- `review_comments_block_l.md` verdict: `APPROVE`.
- Human committed:
  - `b96c132 refactor(phase67-m1): complete hygiene quick wins`
  - `fc9ebba docs(phase67-m1): complete hygiene quick wins`
  - `cd5c039 docs(phase67-m1): record review gate`

### M2: IO Helper + Artifact Ownership

Completed:

- Added `src/swallow/_io_helpers.py`.
- Removed CLI-private `load_json_if_exists(...)` / `load_json_lines_if_exists(...)`.
- Replaced audited JSON / JSONL duplicate loader callsites with explicit helper variants.
- Preserved strict JSONL behavior through `read_json_lines_strict_or_empty(...)`.
- Preserved `retrieval.json` list payload behavior through `read_json_list_or_empty(...)`.
- Chose the narrow artifact ownership option: no global artifact registry in M2.

Review:

- `review_comments_block_m.md` verdict: `APPROVE_WITH_CONDITIONS`.
- Conditions were closeout-stage documentation items, not M3 blockers.
- Human committed:
  - `fac37cb refactor(phase67-m2): centralize json io helpers`
  - `fbaee98 docs(phase67-m2): record review gate`

### M3: CLI Read-Only Dispatch Tightening

Completed:

- Consolidated 51 read-only task artifact/report printer commands into `ARTIFACT_PRINTER_DISPATCH`.
- Split simple command ownership into `TEXT_ARTIFACT_PRINTERS` and `JSON_ARTIFACT_PRINTERS`.
- Kept `task dispatch` explicit for mock-remote marker behavior.
- Kept argparse parser registration and help text unchanged.
- Kept governance write commands, `task inspect`, and `task review` out of scope.

Review:

- `review_comments_block_n.md` verdict: `APPROVE`.
- Human committed:
  - `ec7fa76 refactor(phase67-m3): tighten cli artifact dispatch`

## Acceptance Checklist

M1:

- [x] Seven quick wins completed.
- [x] Dead helpers removed without production callsite regressions.
- [x] Constants named without introducing import cycles.
- [x] Full pytest passed during M1.

M2:

- [x] `_io_helpers.py` created.
- [x] JSON / JSONL callsites use explicit error-policy helpers.
- [x] CLI-private JSON helpers removed.
- [x] Artifact-name registry not introduced; narrow option recorded.
- [x] M2 review conditions recorded for closeout and handled here.

M3:

- [x] Read-only CLI artifact/report printer block is table-driven.
- [x] `task dispatch` remains explicit.
- [x] Governance write commands remain explicit.
- [x] `task inspect` / `task review` remain unchanged.
- [x] Parser registration remains unchanged.
- [x] Six manual CLI output comparisons matched byte-for-byte.

Whole phase:

- [x] `git diff -- docs/design` has no output.
- [x] `git diff --check` passes.
- [x] Full pytest passes.
- [x] `docs/concerns_backlog.md` updated for resolved / partial items.
- [x] `docs/active_context.md` synchronized.
- [x] `current_state.md` synchronized.

## Backlog Updates

Resolved in Phase 67:

- `high audit finding: dead run_consensus_review(...) wrapper` -> Phase 67 M1.
- `audit_index quick-win bundle` -> Phase 67 M1.
- `high audit finding: JSON/JSONL IO helper ownership` -> Phase 67 M2.

Partially consumed in Phase 67:

- `design-needed: table-driven CLI dispatch` -> read-only artifact/report printer subset consumed in M3; parser registration, governance write commands, and `task inspect` / `task review` remain explicit.
- `design-needed: artifact-name registry / owner table` -> narrow option chosen; M3 CLI table reduces surface-side repetition, but no global registry was introduced.

Still open:

- SQLite transaction envelope helper.
- Sync/async orchestration and executor duplication.
- Runtime provider / executor defaults.
- Taxonomy / authority / capability constants.
- Retrieval source policy ownership.
- Policy-result report/event pipeline.

## Design vs Implementation Drift

M1 approved drift:

- Retrieval constants live in `retrieval_config.py`, not `retrieval.py`, to avoid import cycles and align with existing retrieval tunables.
- `orchestrator.py` imports `DEFAULT_REVIEWER_TIMEOUT_SECONDS` directly because it already depends on `review_gate`; `models.py` and `planner.py` keep comments instead of importing.
- `retrieval.py:expand_by_relations(...)` had an extra same-semantic preview truncation and was included in the quick-win.
- `ingestion/pipeline.py` named ingestion report preview limit / suffix even though the design text did not name those constants.

M2 approved drift:

- Added `read_json_lines_strict_or_empty(...)` because several JSONL callsites were actually missing-empty + malformed-crash, not malformed-skip.
- Added `read_json_list_or_empty(...)` because `retrieval.json` is a list payload consumed by CLI inspect/review.
- Kept `store.py._load_json_lines(...)` as a compatibility wrapper for tests while delegating ownership to `_io_helpers.py`.

M3 approved drift / clarification:

- Design §S3.4 used command-name shorthand / typos such as `route-report`, `validation-report`, and `knowledge-policy-report`; the actual parser commands are `route`, `validation`, and `knowledge-policy`.
- Design estimated "21-command set-membership block + follow-up printers"; actual in-scope table covers 51 read-only printer commands. This is still within the intended `cli.py:3592-3787` read-only scope.

None of these required changes to `docs/design/`; they are implementation notes for closeout transparency.

## Pre-positioned for Candidate O

Phase 67 intentionally leaves a thin IO helper layer for a future Storage Backend Independence phase:

- `_io_helpers.py` helpers accept one `Path` and return parsed values.
- The helper semantics are explicit enough to evolve from `Path` to URI-like source references later without first changing error policy behavior.
- Candidate O can start from the M2 callsite list in `codex_review_notes_block_m.md`:
  - `canonical_registry.py`
  - `cli.py`
  - `dialect_data.py`
  - `knowledge_store.py`
  - `knowledge_suggestions.py`
  - `librarian_executor.py`
  - `orchestrator.py`
  - `retrieval.py`
  - `staged_knowledge.py`
  - `store.py`
  - `truth/knowledge.py`
- `read_json_lines_strict_or_empty(...)` is now a concrete strict JSONL extension point if a future ingestion or raw-material path needs corruption to remain fail-fast.
- `RawMaterialStore` itself remains out of Phase 67 scope.

## Test Suite Stability

M2 review identified two pre-existing, order-sensitive flakes:

- `tests/test_run_task_subtasks.py::RunTaskSubtaskIntegrationTest::test_run_task_times_out_one_parallel_subtask_without_canceling_other_work`
- `tests/test_synthesis.py::test_synthesis_does_not_mutate_main_task_state`

Both passed in isolated reruns during review. M3 and final review full-suite runs passed without reproducing them. They are recorded as test-suite stability observations, not Phase 67 regressions.

## Final Verification

Codex final closeout verification:

```bash
.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed

git diff -- docs/design
# no output

.venv/bin/python -m pytest -q
# 610 passed, 8 deselected, 10 subtests passed
```

M3 manual output comparison:

```text
base_dir: /tmp/swallow-phase67-m3-verify
task_id: 87f07afc59a6
commands: summarize, route, validation, knowledge-policy, knowledge-decisions, dispatch
result: matched 6
```

Claude final review verification:

```bash
pytest -q
# 610 passed
```

## Stop / Go

### Stop

Phase 67 implementation should stop here. Do not expand the cleanup to additional Phase 66 findings inside this branch.

### Go

Go to PR / Human Merge Gate:

- M1/M2/M3 review gates are complete.
- Final review verdict is `APPROVE`.
- Closeout documentation is complete.
- `docs/design/` is unchanged.
- Full pytest passes.

After merge, Claude/roadmap-updater should perform the roadmap factual update. Phase 67 review currently recommends no release tag because this is a cleanup phase rather than a user-visible capability milestone.
