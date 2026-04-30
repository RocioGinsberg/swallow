---
author: codex
phase: phase67
slice: m3-cli-read-only-dispatch-tightening
status: final
depends_on:
  - docs/plans/phase67/kickoff.md
  - docs/plans/phase67/design_decision.md
  - docs/plans/phase67/risk_assessment.md
  - docs/plans/phase67/context_brief.md
  - docs/plans/phase67/review_comments_block_m.md
---

TL;DR: M3 consolidated the read-only task artifact/report printer block into `ARTIFACT_PRINTER_DISPATCH`, kept `task dispatch` explicit for mock-remote marker behavior, preserved parser registration/help text, and verified the required output samples byte-for-byte against a pre-change baseline. Full pytest passed.

# Codex Review Notes: Phase 67 M3

## Scope Completed

- Added table-driven read-only printer dispatch in `src/swallow/cli.py`:
  - `TEXT_ARTIFACT_PRINTERS`
  - `JSON_ARTIFACT_PRINTERS`
  - `ARTIFACT_PRINTER_DISPATCH`
  - `_dispatch_artifact_printer(...)`
- Replaced the `cli.py` read-only artifact/report printer if-chain with:
  - one explicit `task dispatch` special case
  - one dispatch-table call for all other read-only printer commands
- Kept argparse parser registration unchanged.
- Kept governance write commands explicit.
- Kept `task inspect` / `task review` unchanged.
- Updated `docs/concerns_backlog.md` to mark the table-driven CLI dispatch concern as partially consumed by the read-only printer subset.

## In-Scope Dispatch Entries

`ARTIFACT_PRINTER_DISPATCH` currently covers these 51 commands:

```text
canonical-registry
canonical-registry-index
canonical-registry-index-json
canonical-registry-json
canonical-reuse
canonical-reuse-eval
canonical-reuse-eval-json
canonical-reuse-json
canonical-reuse-regression
canonical-reuse-regression-json
capabilities-json
checkpoint-json
compatibility
compatibility-json
dispatch-json
execution-budget-policy
execution-budget-policy-json
execution-fit
execution-fit-json
execution-site
execution-site-json
grounding
handoff
handoff-json
knowledge-decisions
knowledge-decisions-json
knowledge-index
knowledge-index-json
knowledge-objects
knowledge-objects-json
knowledge-partition
knowledge-partition-json
knowledge-policy
knowledge-policy-json
memory
remote-handoff
remote-handoff-json
resume-note
retrieval
retrieval-json
retry-policy
retry-policy-json
route
route-json
semantics
semantics-json
stop-policy
stop-policy-json
summarize
topology
topology-json
validation
```

`task dispatch` is intentionally not in the table. It still reads `dispatch_report.md`, but first checks task state/topology and prints `[MOCK-REMOTE]` for mock-remote tasks. That conditional behavior remains explicit per design §S3.1 / §S3.2.

## Behavior Notes

- Text artifact commands still print file content with `end=""`.
- Strict JSON artifact commands now call `read_json_strict(...)` through `_print_json_artifact(...)`, preserving missing/malformed crash behavior.
- M2 helper-backed commands continue to use `read_json_or_empty(...)` / `read_json_lines_or_empty(...)` where M2 already established missing-empty display semantics.
- `knowledge-objects-json` still uses `load_knowledge_objects(...)`, matching the previous handler.
- `canonical-reuse-regression` and `canonical-reuse-eval` use small named helper functions to avoid re-reading paths several times in lambdas.

## Verification Completed

```bash
.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed

git diff -- docs/design
# no output

rg -n "load_json_if_exists|load_json_lines_if_exists" src/swallow
# no matches

.venv/bin/python -m pytest -q tests/test_cli.py
# 241 passed, 10 subtests passed

.venv/bin/python -m pytest -q
# 610 passed, 8 deselected, 10 subtests passed
```

## Byte-For-Byte Manual Verification

Pre-change fixture:

```text
base_dir: /tmp/swallow-phase67-m3-verify
task_id: 87f07afc59a6
baseline_dir: /tmp/swallow-phase67-m3-verify/baseline
after_dir: /tmp/swallow-phase67-m3-verify/after
```

Commands compared against baseline:

```text
task summarize 87f07afc59a6
task route 87f07afc59a6
task validation 87f07afc59a6
task knowledge-policy 87f07afc59a6
task knowledge-decisions 87f07afc59a6
task dispatch 87f07afc59a6
```

Result:

```text
matched 6
```

Note: design text names some commands as `route-report`, `validation-report`, and `knowledge-policy-report`; the actual parser commands are `route`, `validation`, and `knowledge-policy`. I verified the actual parser command names.

## Review Checks To Re-run

```bash
.venv/bin/python -m compileall -q src/swallow
git diff --check
git diff -- docs/design
.venv/bin/python -m pytest -q tests/test_cli.py
.venv/bin/python -m pytest -q
.venv/bin/python -c 'from swallow.cli import ARTIFACT_PRINTER_DISPATCH; print("\n".join(sorted(ARTIFACT_PRINTER_DISPATCH)))'
```

## Closeout Items Still Pending

From M2 review, Phase 67 closeout must still document:

- `_io_helpers.py` module docstring / Candidate O positioning.
- Design vs implementation drift from M1 and M2.
- Test suite stability notes for the previously observed full-suite flakes.
- Pre-positioned-for-Candidate-O section required by `design_decision.md` §S2.5.
