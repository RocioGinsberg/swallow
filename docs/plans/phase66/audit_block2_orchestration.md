---
author: codex
phase: phase66
slice: audit-block2-orchestration
status: final
depends_on:
  - docs/plans/phase66/kickoff.md
  - docs/plans/phase66/design_decision.md
  - docs/plans/phase66/risk_assessment.md
  - docs/plans/phase66/context_brief.md
  - docs/plans/phase66/review_comments_block1_3.md
  - docs/plans/phase66/review_comments_block4_5.md
  - docs/concerns_backlog.md
---

TL;DR: Block 2 audited 19 files / 12128 LOC with 13 findings: 1 high / 11 med / 1 low. The strongest signals are one unused sync review wrapper, duplicated sync/async orchestration paths, scattered executor/model defaults, and repeated orchestration artifact / policy string ownership.

## Coverage

Audited files:

- `src/swallow/orchestrator.py` - 3882 LOC
- `src/swallow/executor.py` - 1868 LOC
- `src/swallow/synthesis.py` - 442 LOC
- `src/swallow/dispatch_policy.py` - 66 LOC
- `src/swallow/checkpoint_snapshot.py` - 225 LOC
- `src/swallow/execution_fit.py` - 227 LOC
- `src/swallow/task_semantics.py` - 57 LOC
- `src/swallow/harness.py` - 1950 LOC
- `src/swallow/subtask_orchestrator.py` - 460 LOC
- `src/swallow/planner.py` - 227 LOC
- `src/swallow/execution_budget_policy.py` - 216 LOC
- `src/swallow/retry_policy.py` - 172 LOC
- `src/swallow/stop_policy.py` - 154 LOC
- `src/swallow/review_gate.py` - 649 LOC
- `src/swallow/validator.py` - 121 LOC
- `src/swallow/validator_agent.py` - 106 LOC
- `src/swallow/models.py` - 1042 LOC
- `src/swallow/runtime_config.py` - 61 LOC
- `src/swallow/compatibility.py` - 203 LOC

Block total: 12128 LOC.

## Skip List Applied

Loaded the Phase 66 skip list from `design_decision.md` and `docs/concerns_backlog.md`: 13 pre-Phase-65 Open items plus 3 Phase-65 known gaps, 16 total.

Block-specific skipped items:

- Phase 63 M2-1: `staged_candidate_count = 0` remains visible in `orchestrator.py` and related payloads; already tracked, not counted.
- Phase 63 M3-1: event type emission and event log tables were inspected, but historical `events` / `event_log` backfill is already tracked and not counted.
- Phase 64 M2-2: HTTP executor / review-gate URL guard coverage was not reported as a new guard-strength finding.
- Phase 65 known gaps: audit snapshot size policy and migration-runner deferral were skipped where policy/report payloads or schema-adjacent paths appeared.

`tests/` was not audited as a subject. It was used only as a callsite oracle for dead-code checks.

## Method

- File inventory: `wc -l` for the 19 block files.
- Symbol inventory: `rg -n '^def |^class |^[A-Z][A-Z0-9_]+\\s*='`.
- Dead-code check: two-pass grep per Phase 66 design, with `src/swallow/` as production callsite source and `tests/` as oracle only.
- Literal / helper checks: targeted `rg` for `json.loads`, `read_text`, sync/async twins, artifact names, event kinds, failure kinds, taxonomy strings, model/provider/executor names, timeout defaults, retry/debate limits, and report-builder patterns.

## Finding Summary

| Severity | dead-code | hardcoded-literal | duplicate-helper | abstraction-opportunity | Total |
|---|---:|---:|---:|---:|---:|
| high | 1 | 0 | 0 | 0 | 1 |
| med | 0 | 5 | 1 | 5 | 11 |
| low | 0 | 1 | 0 | 0 | 1 |
| **Total** | **1** | **6** | **1** | **5** | **13** |

The count is inside the design expectation for block 2(10-20 findings).

## Findings

### [high][dead-code] `run_consensus_review(...)` sync wrapper has no production or test callsite

- **位置**:`src/swallow/review_gate.py:617-632`
- **判定依据**:
  - `rg -n 'run_consensus_review\\(' src/swallow tests`
  - The only hit is `src/swallow/review_gate.py:617:def run_consensus_review(...)`.
  - Production uses `run_review_gate(...)`, `run_review_gate_async(...)`, and `run_consensus_review_async(...)`; tests also import / exercise those paths, not the sync `run_consensus_review(...)` wrapper.
  - Per Phase 66 two-pass dead-code rule, no src callsite and no test callsite = dead code.
- **建议处理**:
  - In a later cleanup phase, remove the sync wrapper or add a real public caller if it is intended API.
  - Keep `_run_review_gate_sync(...)` because `run_review_gate(...)` uses it.
- **影响范围**:single-file.
- **关联**:none.

### [med][duplicate-helper] Orchestrator repeats JSON / JSONL loader shapes already found in blocks 1 and 4

- **位置**:
  - `src/swallow/orchestrator.py:388-406`
  - `src/swallow/orchestrator.py:2961-2992`
  - `src/swallow/orchestrator.py:3099-3108`
  - `src/swallow/orchestrator.py:3211-3216`
  - `src/swallow/orchestrator.py:3239-3248`
- **判定依据**:
  - `rg -n 'def _load_json_lines|def _load_json\\(|knowledge_decisions_path\\(|canonical_registry_path\\(|retrieval_path\\(|canonical_reuse_eval_path\\(' src/swallow/orchestrator.py`
  - Orchestrator has local `_load_json_lines(...)` and `_load_json(...)`, plus several hand-written JSONL loops and JSON object fallbacks in phase recovery / canonical reuse paths.
  - This is the block 2 side of the same cross-block IO pattern found in Block 1 finding 1 and Block 4 finding 1.
- **建议处理**:
  - In a later cleanup phase, centralize JSON object and JSONL readers with explicit missing-file and malformed-file policies.
  - Do not collapse behavior mechanically; orchestrator has a mix of strict readers and empty-on-error recovery readers.
- **影响范围**:cross-block / cross-module.
- **关联**:M2 review CONCERN-1 asks `audit_index.md` to dedupe this theme under the broader Block 4 high finding.

### [med][hardcoded-literal] Runtime config owns source-level URL, model, and embedding defaults

- **位置**:
  - `src/swallow/runtime_config.py:6-9`
  - `src/swallow/runtime_config.py:12-61`
  - `src/swallow/retrieval_adapters.py:199-201` (cross-block consumer)
  - `src/swallow/router.py:1217` (cross-block consumer)
  - `src/swallow/doctor.py:149-176` (cross-block consumer)
- **判定依据**:
  - `rg -n 'resolve_swl_api_base_url|resolve_swl_chat_model|resolve_swl_embedding_model|resolve_swl_embedding_dimensions|DEFAULT_SWL_API_BASE_URL|DEFAULT_SWL_CHAT_MODEL' src/swallow tests`
  - Defaults include URL `http://localhost:3000`, chat model `"gpt-4o-mini"`, embedding model `"text-embedding-3-small"`, and dimension `1536`.
  - Phase 66 hardcoded-literal rules count URL / model names even when they are centralized constants.
- **建议处理**:
  - In a later cleanup phase, decide whether these defaults are acceptable runtime constants or should be sourced from route metadata / local-stack config.
  - Keep the resolver functions as the owner if the design accepts code-level defaults.
- **影响范围**:cross-block runtime config / router / retrieval / doctor.
- **关联**:joins Block 3 / Block 4 / Block 5 provider/model literal ownership theme.

### [med][hardcoded-literal] Executor brand, dialect, and fallback route names are embedded in `executor.py`

- **位置**:
  - `src/swallow/executor.py:165-193`
  - `src/swallow/executor.py:438-459`
  - `src/swallow/executor.py:498-505`
  - `src/swallow/executor.py:627-647`
  - `src/swallow/executor.py:682-702`
  - `src/swallow/executor.py:1703`
- **判定依据**:
  - `rg -n 'AIDER_CONFIG|CLAUDE_CODE_CONFIG|CODEX_CONFIG|BUILTIN_DIALECTS|aider|claude-code|codex|claude_xml|codex_fim|http-default|local-aider|local-claude-code' src/swallow/executor.py src/swallow/dialect_data.py src/swallow/cli.py src/swallow/doctor.py`
  - `executor.py` owns agent configs for `aider`, `claude-code`, and `codex`, dialect names such as `claude_xml` / `codex_fim`, route aliases such as `local-aider`, and a Codex websocket URL string in failure classification.
  - These values are valid implementation metadata, but Phase 66 rules count provider / executor / dialect / URL literals for cleanup ownership review.
- **建议处理**:
  - In a later design/cleanup phase, decide whether these runtime bindings should remain in `executor.py`, be derived from route metadata, or be centralized with executor registry data.
  - Do not remove compatibility aliases or brand defaults without a compatibility decision.
- **影响范围**:cross-block executor / CLI / doctor / dialect data.
- **关联**:same ownership theme as Block 3 finding 2, Block 4 finding 8, and Block 5 finding 14.

### [med][abstraction-opportunity] Sync and async debate loops duplicate orchestration control flow

- **位置**:
  - `src/swallow/orchestrator.py:1074-1173`
  - `src/swallow/orchestrator.py:1176-1364`
  - `src/swallow/orchestrator.py:1568-1773`
  - `src/swallow/orchestrator.py:2022-2288`
  - `src/swallow/subtask_orchestrator.py:198-460`
- **判定依据**:
  - `rg -n '_debate_loop_core|_debate_loop_core_async|_run_single_task_with_debate|_run_single_task_with_debate_async|_run_subtask_debate_retries|_run_subtask_debate_retries_async|SubtaskOrchestrator|AsyncSubtaskOrchestrator' src/swallow/orchestrator.py src/swallow/subtask_orchestrator.py`
  - Sync and async paths repeat the same retry-round state machine, feedback persistence, debate circuit-breaker events, subtask attempt bookkeeping, and final result reconstruction.
  - The paths are not safe to mechanically merge because sync/async execution, locks, and timeout behavior differ, but they clear the N>=3 abstraction-opportunity threshold.
- **建议处理**:
  - Mark design-needed. A later phase can extract smaller pure helpers for shared payload / result construction before considering a larger sync/async abstraction.
  - Keep control-plane sequencing explicit until test coverage can pin behavior.
- **影响范围**:single block / control-plane orchestration.
- **关联**:none.

### [med][abstraction-opportunity] Sync and async executor implementations repeat HTTP and CLI failure handling

- **位置**:
  - `src/swallow/executor.py:1156-1373`
  - `src/swallow/executor.py:1417-1665`
- **判定依据**:
  - `rg -n 'def run_cli_agent_executor|def run_http_executor|async def run_cli_agent_executor_async|async def run_http_executor_async|timeout_seconds = parse_timeout_seconds|failure_kind=\"http_timeout\"|failure_kind=\"timeout\"' src/swallow/executor.py`
  - HTTP sync/async paths repeat endpoint/header/payload setup, timeout errors, HTTP status handling, unreadable payload handling, fallback invocation, and result construction.
  - CLI sync/async paths repeat binary lookup, temp output path handling, timeout / launch / nonzero-exit result construction, and fallback invocation.
- **建议处理**:
  - In a later cleanup phase, factor shared result-construction helpers for timeout / launch / HTTP errors while leaving transport-specific execution separate.
  - Avoid changing fallback semantics as part of a helper extraction.
- **影响范围**:single-file / execution path.
- **关联**:Phase 64 indirect guard gap skipped; this finding is only duplicate control-flow hygiene.

### [med][hardcoded-literal] Orchestration artifact names are repeated across orchestration, harness, retrieval, and CLI surfaces

- **位置**:
  - `src/swallow/orchestrator.py:175-189`
  - `src/swallow/orchestrator.py:2640-2660`
  - `src/swallow/orchestrator.py:3560-3619`
  - `src/swallow/harness.py:309-521`
  - `src/swallow/cli.py:3564-3636` (cross-block consumer)
  - `src/swallow/retrieval.py:64-79` (cross-block consumer)
- **判定依据**:
  - `rg -n 'STANDARD_SUBTASK_ARTIFACT_NAMES|EXECUTOR_ARTIFACT_NAMES|executor_output\\.md|validation_report\\.md|retry_policy_report\\.md|stop_policy_report\\.md|execution_budget_policy_report\\.md|checkpoint_snapshot_report\\.md|compatibility_report\\.md|execution_fit_report\\.md|knowledge_policy_report\\.md' src/swallow/orchestrator.py src/swallow/harness.py src/swallow/paths.py src/swallow/cli.py`
  - The same artifact filenames and artifact path keys are listed in orchestration state, write paths, CLI artifact printers, and retrieval allow-lists.
  - These names are public workflow surface and should have an explicit owner.
- **建议处理**:
  - In a later cleanup phase, evaluate a shared artifact-name registry or path-owner table for stable run artifacts.
  - Preserve explicit allow-lists where retrieval intentionally excludes some artifacts.
- **影响范围**:cross-block orchestration / harness / CLI / retrieval.
- **关联**:Block 4 finding 9 is the retrieval side of the same artifact-name ownership theme.

### [med][hardcoded-literal] Retry, failure, checkpoint, and policy decision strings are scattered across policy modules

- **位置**:
  - `src/swallow/retry_policy.py:15-152`
  - `src/swallow/stop_policy.py:6-134`
  - `src/swallow/checkpoint_snapshot.py:6-192`
  - `src/swallow/execution_budget_policy.py:62-194`
  - `src/swallow/executor.py:1179-1642`
  - `src/swallow/orchestrator.py:760-3088`
- **判定依据**:
  - `rg -n 'timeout|launch_error|unreachable_backend|http_timeout|http_rate_limited|retry_ready|checkpoint_before_retry|detached_retry_review|budget_exhausted|debate_circuit_breaker|review_gate_retry_exhausted' src/swallow/retry_policy.py src/swallow/stop_policy.py src/swallow/checkpoint_snapshot.py src/swallow/execution_budget_policy.py src/swallow/executor.py src/swallow/orchestrator.py`
  - Failure kinds and decision strings are interpreted in more than one module: executor emits them, retry policy classifies them, stop/checkpoint policy maps them to operator actions, and orchestrator writes them into events.
  - These are not normal display strings; they are machine-readable workflow vocabulary.
- **建议处理**:
  - In a later cleanup phase, introduce a small constants module or enum-like table for failure kinds and checkpoint decisions.
  - Keep message text local; centralize only the machine-readable vocabulary.
- **影响范围**:cross-module policy / orchestration.
- **关联**:none.

### [low][hardcoded-literal] Timeout, round, worker, and card-count defaults have multiple owners

- **位置**:
  - `src/swallow/orchestrator.py:189`
  - `src/swallow/review_gate.py:16`
  - `src/swallow/planner.py:8`
  - `src/swallow/planner.py:91-98`
  - `src/swallow/subtask_orchestrator.py:14-95`
  - `src/swallow/execution_budget_policy.py:17`
  - `src/swallow/executor.py:1167`
  - `src/swallow/executor.py:1287`
  - `src/swallow/executor.py:1428`
  - `src/swallow/executor.py:1554`
  - `src/swallow/synthesis.py:17-18`
- **判定依据**:
  - `rg -n 'DEBATE_MAX_ROUNDS|DEFAULT_REVIEWER_TIMEOUT_SECONDS|MAX_SUBTASK_CARDS|MAX_SUBTASK_WORKERS|DEFAULT_SUBTASK_TIMEOUT_SECONDS|DEFAULT_TIMEOUT_SECONDS|reviewer_timeout_seconds.*60|AIWF_EXECUTOR_TIMEOUT_SECONDS.*20|ROUND_DEFAULT|PARTICIPANT_DEFAULT' src/swallow/orchestrator.py src/swallow/review_gate.py src/swallow/planner.py src/swallow/subtask_orchestrator.py src/swallow/execution_budget_policy.py src/swallow/synthesis.py src/swallow/models.py src/swallow/executor.py`
  - Several values are named, but ownership is split: reviewer timeout defaults appear in `models.py`, `planner.py`, `review_gate.py`, and subtask timeout fallback; executor timeout defaults appear in executor and budget policy.
  - Phase 66 hardcoded-literal rules count timeout / retry / limit values when ownership is unclear.
- **建议处理**:
  - In a later cleanup phase, document or centralize orchestration default constants by domain: review, executor timeout, subtask parallelism, MPS limits.
  - Keep current values unchanged.
- **影响范围**:cross-module operational defaults.
- **关联**:none.

### [med][abstraction-opportunity] Policy evaluators and report builders repeat a result/finding/report shape

- **位置**:
  - `src/swallow/validator.py:8-121`
  - `src/swallow/compatibility.py:6-203`
  - `src/swallow/execution_fit.py:6-227`
  - `src/swallow/retry_policy.py:19-172`
  - `src/swallow/stop_policy.py:6-154`
  - `src/swallow/execution_budget_policy.py:62-216`
  - `src/swallow/checkpoint_snapshot.py:6-225`
  - `src/swallow/harness.py:304-527`
- **判定依据**:
  - `rg -n 'compatibility\\.completed|execution_fit\\.completed|knowledge_policy\\.completed|validation\\.completed|retry_policy\\.completed|execution_budget_policy\\.completed|stop_policy\\.completed|checkpoint_snapshot\\.completed|build_.*_report|Finding\\(' src/swallow/harness.py src/swallow/compatibility.py src/swallow/execution_fit.py src/swallow/retry_policy.py src/swallow/stop_policy.py src/swallow/execution_budget_policy.py src/swallow/checkpoint_snapshot.py src/swallow/validator.py`
  - Each module builds findings, computes a status/message/recommended action, renders a Markdown report, and then harness repeats save/report/event plumbing for each result type.
  - The result classes differ enough that this is not a duplicate-helper deletion candidate, but the N>=3 abstraction-opportunity threshold is met.
- **建议处理**:
  - In a later cleanup phase, consider a small report/event helper for policy-result modules or a shared protocol for `status`, `message`, and `findings`.
  - Keep individual policy semantics in their own modules.
- **影响范围**:cross-module orchestration policy reporting.
- **关联**:none.

### [med][hardcoded-literal] Taxonomy and memory-authority strings are repeated across model, planner, dispatch, and executor modules

- **位置**:
  - `src/swallow/models.py:8-57`
  - `src/swallow/dispatch_policy.py:7-64`
  - `src/swallow/planner.py:7-34`
  - `src/swallow/validator_agent.py:10-18`
  - `src/swallow/capability_enforcement.py:22-55` (cross-block comparison)
  - `src/swallow/librarian_executor.py:37-39` (cross-block comparison)
- **判定依据**:
  - `rg -n 'SYSTEM_ROLES|MEMORY_AUTHORITIES|LIBRARIAN_BLOCKED_AUTHORITIES|WRITE_INTENT_KEYWORDS|PROMOTION_KEYWORDS|validator|canonical-write-forbidden|stateless|staged-knowledge|task-state|task-memory|canonical-promotion' src/swallow/models.py src/swallow/dispatch_policy.py src/swallow/planner.py src/swallow/capability_enforcement.py src/swallow/validator_agent.py src/swallow/librarian_executor.py src/swallow/ingestion_specialist.py src/swallow/literature_specialist.py src/swallow/quality_reviewer.py`
  - `models.py` validates the taxonomy vocabulary, but dispatch policy, planner, validator, capability enforcement, and specialist modules also own repeated spellings.
  - These strings govern execution rights, memory authority, and routing constraints, so stale spelling would be behavioral.
- **建议处理**:
  - In a later cleanup phase, import shared constants for taxonomy and memory-authority values where it improves clarity.
  - Do not move brand bindings into design documents; keep this as implementation metadata ownership.
- **影响范围**:cross-block taxonomy / dispatch behavior.
- **关联**:extends Block 3 finding 4 and Block 5 findings 8-10.

### [med][hardcoded-literal] Retrieval source type policy is split between task semantics, models, retrieval, and orchestrator route-family logic

- **位置**:
  - `src/swallow/task_semantics.py:5-56`
  - `src/swallow/models.py:596`
  - `src/swallow/retrieval.py:62-63`
  - `src/swallow/retrieval.py:142`
  - `src/swallow/orchestrator.py:195-199`
  - `src/swallow/orchestrator.py:3151-3189`
- **判定依据**:
  - `rg -n '_RETRIEVAL_SOURCE_POLICY|ALLOWED_RETRIEVAL_SOURCE_TYPES|source_types: list\\[str\\]|source_types=|\\[\"repo\", \"notes\"\\]|\"knowledge\", \"notes\"|\"autonomous_cli_coding\"|\"legacy_local_fallback\"|\"api\"' src/swallow/orchestrator.py src/swallow/task_semantics.py src/swallow/models.py src/swallow/retrieval.py tests/test_cli.py`
  - Allowed source types live in `task_semantics.py`, `RetrievalRequest` and retrieval defaults also own `["repo", "notes"]`, and orchestrator owns route-family source policies like `("api", "*"): ("knowledge", "notes")`.
  - The route-family labels are not brand names, but they are machine-readable retrieval policy data.
- **建议处理**:
  - In a later cleanup phase, decide whether source-type constants and route-family retrieval policy should share an owner with retrieval config.
  - Preserve the Phase 60/64 behavior that keeps API routes off repo by default.
- **影响范围**:cross-module retrieval policy / orchestration.
- **关联**:none.

### [med][abstraction-opportunity] `build_summary(...)` and `build_resume_note(...)` repeat long run-state rendering blocks

- **位置**:
  - `src/swallow/harness.py:1489-1763`
  - `src/swallow/harness.py:1765-1948`
  - `src/swallow/cli.py:3199-3558` (cross-block comparison)
- **判定依据**:
  - `rg -n 'def build_summary|def build_resume_note|task_semantics_report_artifact|knowledge_objects_report_artifact|route_report_artifact|execution_budget_policy_report_artifact|reused_verified_knowledge' src/swallow/harness.py src/swallow/cli.py`
  - Summary and resume-note rendering repeat many of the same task semantics, knowledge, retrieval, route, topology, policy, validation, and artifact path fields.
  - Block 5 already found a similar duplication between `task inspect` and `task review`; harness adds another operator-facing rendering surface.
- **建议处理**:
  - In a later cleanup phase, extract read-only snapshot collection into a data object and keep markdown rendering per view.
  - Avoid changing operator-facing report text without golden output tests.
- **影响范围**:cross-block harness / CLI surface.
- **关联**:Block 5 finding 4.

## Checked But Not Counted

- `staged_candidate_count = 0` in `orchestrator.py` was inspected and skipped as Phase 63 M2-1.
- `events` / `event_log` terminology and event type emission were inspected; the historical backfill concern is already Phase 63 M3-1 and not counted.
- `run_review_gate_async(...)` is production-used through `orchestrator.py:3520` and tested by `tests/test_review_gate_async.py`; only the sync `run_consensus_review(...)` wrapper is counted as dead.
- `dispatch_policy.py` helper functions are production-used by `orchestrator.py:2414-2423`; no dead-code finding was counted there.
- `synthesis.py` MPS route helpers are reachable through CLI `synthesis run`; no dead-code finding was counted.
