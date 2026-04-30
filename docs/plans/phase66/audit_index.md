---
author: codex
phase: phase66
slice: audit-index
status: final
depends_on:
  - docs/plans/phase66/audit_block1_truth_governance.md
  - docs/plans/phase66/audit_block2_orchestration.md
  - docs/plans/phase66/audit_block3_provider_router.md
  - docs/plans/phase66/audit_block4_knowledge_retrieval.md
  - docs/plans/phase66/audit_block5_surface_tools.md
  - docs/plans/phase66/review_comments_block1_3.md
  - docs/plans/phase66/review_comments_block4_5.md
---

TL;DR: Phase 66 audited 75 Python files / 30954 LOC and found 46 findings: 2 high / 36 med / 8 low. Highest-value cleanup themes are JSON/JSONL IO helper ownership, SQLite transaction envelopes, executor/provider/model literal ownership, artifact registry ownership, and table-driven CLI dispatch.

## Scope Summary

Phase 66 was a strict read-only hygiene audit over `src/swallow/`. It produced audit documents only. No code, tests, or design documents were intentionally modified.

Audited LOC are from `wc -l` in each block report. The actual total is 30954 LOC; this differs slightly from the kickoff estimate because the final block inventory counted the current committed files exactly.

## Finding Count Matrix

| Block | dead-code | hardcoded-literal | duplicate-helper | abstraction-opportunity | Block total | LOC |
|---|---:|---:|---:|---:|---:|---:|
| Block 1 Truth & Governance | 0 | 1 | 1 | 1 | 3 | 2671 |
| Block 2 Orchestration | 1 | 6 | 1 | 5 | 13 | 12128 |
| Block 3 Provider Router & Calls | 1 | 3 | 0 | 0 | 4 | 1740 |
| Block 4 Knowledge & Retrieval | 1 | 7 | 1 | 3 | 12 | 5827 |
| Block 5 Surface & Tools | 0 | 8 | 4 | 2 | 14 | 8588 |
| **Total** | **3** | **25** | **7** | **11** | **46** | **30954** |

Total finding count is inside the design expectation of 40-80.

## Severity Matrix

| Block | high | med | low | Total |
|---|---:|---:|---:|---:|
| Block 1 Truth & Governance | 0 | 1 | 2 | 3 |
| Block 2 Orchestration | 1 | 11 | 1 | 13 |
| Block 3 Provider Router & Calls | 0 | 3 | 1 | 4 |
| Block 4 Knowledge & Retrieval | 1 | 10 | 1 | 12 |
| Block 5 Surface & Tools | 0 | 11 | 3 | 14 |
| **Total** | **2** | **36** | **8** | **46** |

## Cross-Block Consensus

### JSON / JSONL Loader Duplication

- Related findings:
  - Block 1 finding 1: `_load_json_lines(...)` duplication in `store.py` / `truth/knowledge.py`.
  - Block 2 finding 2: orchestrator JSON / JSONL helpers and local read loops.
  - Block 4 finding 1: broad JSON / JSONL loader duplication across knowledge, canonical, retrieval, and surface paths.
  - Block 5 finding 1: CLI JSON artifact printers repeat read / parse / dump handlers.
- Dedupe decision:
  - Final governance recommendation is **one design-needed cleanup theme**, owned by Block 4 finding 1 as the broadest cross-block view and kept at `[high][duplicate-helper]`.
  - Block 1 finding 1 is the narrow block-local view and is treated as subsumed by the broader Block 4 theme for prioritization, while remaining counted in its block report.
  - Block 2 and Block 5 findings show additional callsite surfaces, not separate root causes.
- Recommended direction:
  - Create small JSON object / JSONL read helpers with explicit error-policy variants: strict, missing-is-empty, malformed-is-empty.
  - Do not silently homogenize callsites that intentionally fail fast today.

### SQLite Transaction Envelope Duplication

- Related findings:
  - Block 1 finding 3: Phase 65 route / policy repository transaction envelopes.
  - Block 5 finding 7: consistency audit and MPS policy stores duplicate policy SQLite write / legacy-bootstrap envelopes.
- Dedupe decision:
  - Treat as one cross-block design-needed theme across route / policy / audit-trigger / MPS namespaces.
  - Keep severity at `[med]` for now. It is real duplication, but Phase 65 intentionally favored namespace clarity and explicit transactions.
- Recommended direction:
  - Evaluate a tiny repository transaction helper or context manager only if it preserves namespace-specific audit rows and route rollback redo behavior.
  - This is not a quick-win deletion.

### Executor / Provider / Model Literal Ownership

- Related findings:
  - Block 2 findings 3-4: runtime URL/model/embedding defaults and executor brand/dialect configs.
  - Block 3 finding 2: static cost pricing table hardcodes provider/model families.
  - Block 4 finding 8: `dialect_data.py` defaults executor identity to `"aider"`.
  - Block 5 finding 14: deprecated `doctor codex` alias and `aider` defaults in surface code.
- Dedupe decision:
  - These are independent code locations, so they remain counted separately.
  - They form one consensus theme: implementation-level brand/model/default ownership is spread across runtime config, executor, cost estimation, prompt dialect data, CLI, and doctor diagnostics.
- Recommended direction:
  - Decide whether defaults stay as runtime constants, move to route metadata / route policy, or get an executor-registry-adjacent runtime owner.
  - Keep P4 discipline: do not move brand lists into design document bodies.

### Artifact Name Ownership

- Related findings:
  - Block 2 finding 7: orchestration artifact names repeat across orchestrator, harness, CLI, and retrieval.
  - Block 4 finding 9: retrieval artifact allow-lists duplicate task artifact names.
  - Block 5 finding 1: CLI artifact printers repeat loader/printer handlers.
- Dedupe decision:
  - One design-needed theme: stable task artifact names need a single implementation owner or a consciously explicit allow-list strategy.
- Recommended direction:
  - Start with read-only artifact printer mapping in CLI as the narrowest reversible step.
  - Consider an artifact-name registry only after deciding which artifacts should be retrievable by default.

### Taxonomy / Capability / Authority Strings

- Related findings:
  - Block 2 findings 10-11: taxonomy and memory-authority strings repeated across model, planner, dispatch, and executor-adjacent modules.
  - Block 3 finding 4: capability enforcement repeats taxonomy/capability strings.
  - Block 4 finding 12: ingestion staged-candidate authority/source-kind strings.
  - Block 5 findings 8-10: specialist / validator metadata and capability reference sets.
- Dedupe decision:
  - One medium-priority ownership theme, not a single mechanical duplicate.
- Recommended direction:
  - Import shared constants where the model layer is already the owner.
  - Leave behavior-specific messages local.

### CLI Dead Subcommand Negative Finding

Block 5 explicitly checked the CLI parser/dispatch tree and found no registered-but-undispatched dead subcommand. Deprecated `doctor codex` is still reachable, so it was counted only as a low brand/compatibility literal. This negative finding should be preserved: the CLI debt is not dead subcommands; it is the parallel parser/dispatch tree.

Recommended seed: table-driven dispatch, starting with read-only artifact/report commands before governance write paths.

## Quick-Win Candidates

These are suitable seeds for a narrow cleanup phase because they are local, low-risk, or already covered by behavior tests.

| Candidate | Source finding | Why quick |
|---|---|---|
| Remove or intentionally wire `run_consensus_review(...)` | Block 2 finding 1 | No src or tests callsite; one wrapper around existing async path |
| Remove module-level `_pricing_for(...)` or make `StaticCostEstimator` delegate to it | Block 3 finding 1 | Single-file duplicate with tests around estimator behavior |
| Move `rank_documents_by_local_embedding(...)` to eval/test support or connect it to production | Block 4 finding 2 | Production-dead, test/eval-only caller is explicit |
| Name SQLite timeout / busy-timeout constants | Block 1 finding 2 | Single-file constant extraction, behavior unchanged |
| Have CLI consume `MPS_POLICY_KINDS` | Block 5 finding 12 | Store already has an owner constant; CLI repeats it |
| Name retrieval preview / scoring limits | Block 4 finding 6 | Pure naming cleanup if values stay unchanged |
| Document or centralize orchestration timeout/card defaults | Block 2 finding 9 | Low-severity constant ownership cleanup |

Quick wins should still get normal tests. Phase 66 did not implement them.

## Design-Needed Candidates

These need a follow-up design decision because they touch cross-module ownership, public CLI/API behavior, or control-plane readability.

| Theme | Source findings | Design question |
|---|---|---|
| JSON / JSONL IO helper ownership | Blocks 1, 2, 4, 5 | Which error policies are shared, and which callsites must remain strict? |
| SQLite transaction envelope helper | Blocks 1, 5 | Can a helper preserve namespace clarity, audit row ownership, and route rollback redo? |
| Table-driven CLI dispatch | Block 5 finding 3 + M2 NOTE-1 | Which command families are safe to table-drive first? |
| Sync/async orchestration and executor duplication | Block 2 findings 5-6 | Can shared pure helpers reduce duplication without hiding control-plane sequence? |
| Artifact-name registry / owner table | Blocks 2, 4, 5 | Which artifacts are stable public surface, retrievable, or intentionally private? |
| Runtime provider / executor defaults | Blocks 2, 3, 4, 5 | Should defaults live in runtime config, route metadata, route policy, or executor registry data? |
| Taxonomy / authority / capability constants | Blocks 2, 3, 4, 5 | Which vocabulary has a single implementation owner, and which messages remain local? |
| Retrieval source policy ownership | Block 2 finding 12 | Should source-type constants and route-family retrieval policy live with retrieval config? |
| Policy-result report/event pipeline | Block 2 finding 10 | Is a shared result protocol worth introducing for policy modules? |

## Checked But Not Counted

- `store.py` JSON write helpers were checked after M1 review NOTE-1. They remain legacy/task-store ownership code and were not counted as a separate finding beyond the JSON/JSONL loader consensus theme.
- `staged_candidate_count = 0` in Block 2 was inspected and skipped as Phase 63 M2-1.
- CLI dead subcommands were checked and no dead subcommand was counted.
- Phase 64 indirect chat-completion URL guard was skipped in Block 3 / Block 4 / Block 2 as already tracked.
- Phase 65 known gaps were not re-counted: review artifact write after SQLite commit, audit snapshot size policy absent, and full migration runner deferred.

## Skip List Compliance

The Phase 66 skip list contains 16 items: 13 pre-Phase-65 Open backlog items plus 3 Phase-65 known gaps. All five block reports list the relevant block-specific skips, and skipped items are not counted in the 46 findings.

Skipped items:

- Phase 45 `_select_chatgpt_primary_path()` same-depth tie heuristic.
- Phase 49 `_sqlite_vec_warning_emitted` race.
- Phase 50 `extract_route_weight_proposals_from_report()` markdown parsing fragility.
- Phase 50 `_FAIL_SIGNAL_PATTERNS` false fail verdict.
- Phase 57 `VECTOR_EMBEDDING_DIMENSIONS` import-time fixed.
- Phase 58 `_is_open_webui_export` auto-detect semantic change.
- Phase 59 release doc sync debt.
- Phase 61/63 `PendingProposalRepo` in-memory.
- Phase 61/63 `librarian_side_effect` INVARIANTS §5 drift.
- Phase 63 M2-1 `staged_candidate_count` always 0.
- Phase 63 M2-5 `_apply_route_review_metadata` long reconciliation logic.
- Phase 63 M3-1 `events` / `event_log` historical backfill.
- Phase 64 M2-2 indirect chat-completion URL guard gap.
- Phase 65 review application artifact outside SQLite transaction.
- Phase 65 audit snapshot size policy absent.
- Phase 65 full migration runner deferred.

## Recommended Next Phase Seeds

1. **Small hygiene cleanup phase**: remove or wire dead/test-only helpers, name constants, and consume existing owner constants. This can include `run_consensus_review(...)`, `_pricing_for(...)`, MPS policy choices, and low-severity timeout / preview constants.
2. **IO and artifact ownership design phase**: decide JSON/JSONL helper behavior variants and task artifact-name ownership before touching broad cross-block callsites.
3. **CLI dispatch tightening phase**: start with read-only artifact/report command table dispatch, then evaluate whether governance write commands should remain explicit.

Do not combine all design-needed themes into one cleanup phase. The cross-block ownership items touch enough public surface that they should be split.
