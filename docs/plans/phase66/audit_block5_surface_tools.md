---
author: codex
phase: phase66
slice: audit-block5-surface-tools
status: review
depends_on:
  - docs/plans/phase66/kickoff.md
  - docs/plans/phase66/design_decision.md
  - docs/plans/phase66/risk_assessment.md
  - docs/plans/phase66/context_brief.md
  - docs/plans/phase66/review_comments_block1_3.md
  - docs/concerns_backlog.md
---

TL;DR: Block 5 audited 17 files / 8588 LOC with 14 findings: 0 high / 11 med / 3 low. CLI subcommands were all mounted and dispatchable; the main debt is repeated surface plumbing and hardcoded local-stack / taxonomy values.

## Coverage

Audited files:

- `src/swallow/cli.py` - 3832 LOC
- `src/swallow/paths.py` - 250 LOC
- `src/swallow/identity.py` - 5 LOC
- `src/swallow/workspace.py` - 20 LOC
- `src/swallow/web/__init__.py` - 21 LOC
- `src/swallow/web/api.py` - 428 LOC
- `src/swallow/web/server.py` - 17 LOC
- `src/swallow/meta_optimizer.py` - 1320 LOC
- `src/swallow/consistency_audit.py` - 515 LOC
- `src/swallow/mps_policy_store.py` - 161 LOC
- `src/swallow/doctor.py` - 489 LOC
- `src/swallow/consistency_reviewer.py` - 108 LOC
- `src/swallow/capabilities.py` - 78 LOC
- `src/swallow/librarian_executor.py` - 518 LOC
- `src/swallow/ingestion_specialist.py` - 90 LOC
- `src/swallow/literature_specialist.py` - 455 LOC
- `src/swallow/quality_reviewer.py` - 281 LOC

Block total: 8588 LOC.

Note: Phase 66 revised kickoff says block 5 includes `web/*.py`. The actual audited set is 17 files, including `web/__init__.py`.

## CLI Segment Index

`cli.py` was scanned by segment because it is 3832 LOC:

- `src/swallow/cli.py:1-240` imports and shared artifact labels.
- `src/swallow/cli.py:241-742` formatting, JSON, staged-knowledge, and route report helpers.
- `src/swallow/cli.py:750-1229` task queue/control/run helpers.
- `src/swallow/cli.py:1231-2320` parser tree and subcommand registration.
- `src/swallow/cli.py:2349-2799` knowledge, proposal, audit, synthesis, and route dispatch.
- `src/swallow/cli.py:2805-3199` note/ingest/task lifecycle dispatch.
- `src/swallow/cli.py:3199-3563` task inspect/review/capabilities views.
- `src/swallow/cli.py:3563-3788` report/json artifact printers.
- `src/swallow/cli.py:3788-3832` migrate and doctor dispatch.

## Skip List Applied

Loaded the Phase 66 skip list from `design_decision.md` and `docs/concerns_backlog.md`: 13 pre-Phase-65 Open items plus 3 Phase-65 known gaps, 16 total.

Block-specific skipped items:

- Phase 50: `extract_route_weight_proposals_from_report()` markdown parsing fragility in `meta_optimizer.py`; already tracked, not counted.
- Phase 50: `_FAIL_SIGNAL_PATTERNS` false fail verdict risk in `consistency_audit.py`; already tracked, not counted.
- Phase 61 / 63: durable proposal artifact lifecycle remained skipped when scanning proposal CLI paths.
- Phase 65 known gaps: review artifact outside SQLite transaction, audit snapshot size policy, and full migration runner deferred; not counted as new block 5 findings.

`tests/` was not audited as a subject. It was used only as a callsite oracle for dead-code checks.

## Method

- File inventory: `wc -l` for the 17 block files.
- CLI inventory: `rg -n 'add_parser|if args\\.command|task_command|doctor_command|route_command|knowledge_command' src/swallow/cli.py`.
- Dead-code check: two-pass grep for suspected helpers and doctor/specialist entry points.
- Literal / helper checks: targeted `rg` for JSON print handlers, local stack URLs, route-mode choices, MPS policy kinds, ingestion formats, policy write transactions, specialist agent prompt/execute structure, and meta-optimizer thresholds.

## Finding Summary

| Severity | dead-code | hardcoded-literal | duplicate-helper | abstraction-opportunity | Total |
|---|---:|---:|---:|---:|---:|
| high | 0 | 0 | 0 | 0 | 0 |
| med | 0 | 5 | 4 | 2 | 11 |
| low | 0 | 3 | 0 | 0 | 3 |
| **Total** | **0** | **8** | **4** | **2** | **14** |

The count is inside the design expectation for block 5(12-26 findings).

## Findings

### [med][duplicate-helper] CLI JSON artifact printers repeat the same read/parse/dump handler shape

- **位置**:
  - `src/swallow/cli.py:3651-3713`
  - `src/swallow/cli.py:3716-3725`
  - `src/swallow/cli.py:3760-3785`
- **判定依据**:
  - `rg -n 'print\\(json\\.dumps\\(json\\.loads|print\\(json\\.dumps\\(load_json' src/swallow/cli.py`
  - More than 20 task subcommands repeat `json.loads(path.read_text(...))`, `json.dumps(..., indent=2)`, `print(...)`, and `return 0`.
  - `load_json_if_exists(...)` and `load_json_lines_if_exists(...)` already exist in the same file, but several handlers bypass them.
- **建议处理**:
  - In a later cleanup phase, replace the repeated branches with a small mapping from task command to path loader / report loader.
  - Preserve commands that need special loaders such as `load_knowledge_objects(...)`.
- **影响范围**:single-file / CLI surface.
- **关联**:none.

### [med][duplicate-helper] CLI and Web API duplicate task focus filtering

- **位置**:
  - `src/swallow/cli.py:881-897`
  - `src/swallow/web/api.py:16-32`
- **判定依据**:
  - `rg -n 'def _filter_task_states|def filter_task_states|needs-review|focus' src/swallow/web/api.py src/swallow/cli.py`
  - The functions are line-for-line equivalent for `all`, `active`, `failed`, `needs-review`, and `recent`.
  - Both are production callsites: CLI task list and Web API `/api/tasks?focus=...`.
- **建议处理**:
  - In a later cleanup phase, move focus filtering to a shared surface helper used by CLI and Web API.
  - Keep Web API payload construction separate; only the predicate table is duplicated.
- **影响范围**:cross-module surface behavior.
- **关联**:none.

### [med][abstraction-opportunity] CLI parser registration and dispatch maintain parallel command trees

- **位置**:
  - `src/swallow/cli.py:1231-2320`
  - `src/swallow/cli.py:2354-3831`
- **判定依据**:
  - `rg -n 'add_parser|if args\\.command|args\\.task_command|args\\.route_command|args\\.knowledge_command' src/swallow/cli.py`
  - The parser tree has 80+ `add_parser` entries, and dispatch repeats a long chain of `if args.command == ...` / `if args.task_command == ...` branches.
  - This clears the N>=3 abstraction-opportunity threshold; it is not a safe mechanical refactor because many commands have side effects and governance constraints.
- **建议处理**:
  - Mark design-needed. A later phase can introduce table-driven dispatch in small groups, starting with read-only artifact printers.
  - Keep governance paths (`proposal apply`, route/policy apply, migration) explicit until reviewed.
- **影响范围**:single-file / public CLI surface.
- **关联**:none.

### [med][abstraction-opportunity] `task inspect` and `task review` duplicate large snapshot assembly blocks

- **位置**:
  - `src/swallow/cli.py:3199-3384`
  - `src/swallow/cli.py:3412-3558`
- **判定依据**:
  - Both commands load handoff, compatibility, execution-fit, retry/budget/stop policy, checkpoint, knowledge policy/index, knowledge decisions, canonical reuse eval/regression, canonical registry/reuse policy, retrieval, and shared attention helpers.
  - Both then render overlapping route, handoff, checks, canonical reuse, policy snapshot, and artifact sections.
  - The structures differ in density but clear the N>=3 repeated-section abstraction threshold.
- **建议处理**:
  - In a later cleanup phase, extract shared snapshot collection into a read-only data object, leaving view-specific rendering separate.
  - Avoid changing output text without CLI golden tests.
- **影响范围**:single-file / operator-facing CLI.
- **关联**:none.

### [med][hardcoded-literal] `doctor.py` bakes local stack topology, URLs, tunnel, proxy, and timeout defaults into code

- **位置**:
  - `src/swallow/doctor.py:81-143`
  - `src/swallow/doctor.py:148-183`
  - `src/swallow/doctor.py:205-242`
  - `src/swallow/doctor.py:244-265`
- **判定依据**:
  - `rg -n 'http://localhost:3000/api/status|https://ifconfig.me|10\\.8\\.0\\.1|8888|timeout|docker|postgres|new-api|tensorzero' src/swallow/doctor.py`
  - The diagnostics encode container names (`new-api`, `tensorzero`, `postgres`), URL `http://localhost:3000/api/status`, WireGuard endpoint `10.8.0.1`, proxy `http://10.8.0.1:8888`, external IP URL `https://ifconfig.me`, and raw timeouts 5 / 10.
  - URL literals and timeout magic numbers are hardcoded-literal findings by Phase 66 rules.
- **建议处理**:
  - In a later cleanup phase, introduce named constants or a local-stack config object for doctor defaults.
  - Keep the command read-only and avoid requiring config for the default local setup.
- **影响范围**:single-file / diagnostic CLI.
- **关联**:none.

### [med][hardcoded-literal] Meta-optimizer recommendation thresholds are source-level policy

- **位置**:
  - `src/swallow/meta_optimizer.py:477-482`
  - `src/swallow/meta_optimizer.py:482`
  - `src/swallow/meta_optimizer.py:625-808`
  - `src/swallow/meta_optimizer.py:820-884`
  - `src/swallow/meta_optimizer.py:1223`
  - `src/swallow/meta_optimizer.py:1313`
- **判定依据**:
  - `rg -n '0\\.25|0\\.5|0\\.15|0\\.2|0\\.10|1\\.5|0\\.3|0\\.99|0\\.75|last_n: int = 100|last_n\", 100' src/swallow/meta_optimizer.py`
  - Failure, fallback, degradation, cost, trend, debate retry, capability score, and scan-window thresholds are hardcoded numbers in source.
  - Phase 50 markdown parsing fragility was skipped; this is separate threshold ownership hygiene.
- **建议处理**:
  - In a later design/cleanup phase, move these values into a meta-optimizer policy object or named constants with rationale.
  - Preserve current proposal behavior until policy ownership is designed.
- **影响范围**:single-file / self-evolution policy.
- **关联**:Phase 50 `extract_route_weight_proposals_from_report()` skipped, not counted.

### [med][duplicate-helper] Policy SQLite write and legacy-bootstrap envelopes are duplicated in MPS and consistency audit stores

- **位置**:
  - `src/swallow/consistency_audit.py:212-290`
  - `src/swallow/mps_policy_store.py:77-160`
  - `src/swallow/router.py:811-878` (cross-block comparison)
  - `src/swallow/truth/policy.py:25-70` (cross-block comparison)
- **判定依据**:
  - `rg -n 'def _run_policy_write|def _bootstrap_.*legacy_json|BEGIN IMMEDIATE|COMMIT|ROLLBACK|_upsert_.*policy' src/swallow/consistency_audit.py src/swallow/mps_policy_store.py src/swallow/router.py src/swallow/truth`
  - `consistency_audit.py` and `mps_policy_store.py` each define local `_run_policy_write(...)` wrappers and bootstrap legacy JSON into `policy_records` with the same transaction envelope.
  - The same shape already appeared in M1 route/policy findings; block 5 adds two more policy namespaces.
- **建议处理**:
  - Mark design-needed. A later cleanup phase can evaluate a tiny internal policy repository helper while preserving namespace clarity.
  - Do not collapse policy writes until Phase 65 SQLite truth tradeoffs are reviewed.
- **影响范围**:cross-block / policy truth surface.
- **关联**:M1 block 1 transaction-envelope abstraction opportunity.

### [med][duplicate-helper] Specialist/validator agent classes repeat prompt + execute + async wrapper boilerplate

- **位置**:
  - `src/swallow/ingestion_specialist.py:15-90`
  - `src/swallow/consistency_reviewer.py:16-108`
  - `src/swallow/literature_specialist.py:64-455`
  - `src/swallow/quality_reviewer.py:30-281`
  - `src/swallow/librarian_executor.py:211-518`
- **判定依据**:
  - `rg -n '_build_prompt|execute_async|ExecutorResult\\(|agent_name|system_role|memory_authority' src/swallow/ingestion_specialist.py src/swallow/literature_specialist.py src/swallow/quality_reviewer.py src/swallow/consistency_reviewer.py src/swallow/librarian_executor.py`
  - Multiple classes assign `agent_name/system_role/memory_authority`, build a prompt header, return `ExecutorResult(...)`, and wrap sync execution in `asyncio.to_thread(...)`.
  - Implementations are not identical enough for one base class today, but the boilerplate repeats across 5 production agent surfaces.
- **建议处理**:
  - In a later cleanup phase, consider a small helper for prompt headers and async execution wrappers before introducing inheritance.
  - Keep specialist-specific side-effect and LLM-call behavior explicit.
- **影响范围**:cross-module specialist surface.
- **关联**:none.

### [med][hardcoded-literal] Specialist executor identity and taxonomy strings are scattered across modules

- **位置**:
  - `src/swallow/ingestion_specialist.py:10-12`
  - `src/swallow/consistency_reviewer.py:11-13`
  - `src/swallow/literature_specialist.py:16-18`
  - `src/swallow/quality_reviewer.py:13-15`
  - `src/swallow/librarian_executor.py:37-39`
- **判定依据**:
  - `rg -n 'EXECUTOR_NAME|SYSTEM_ROLE|MEMORY_AUTHORITY|specialist|validator|stateless|staged-knowledge|task-memory'` across specialist modules.
  - Executor names, taxonomy roles, and memory-authority strings are source-level constants spread across each executor file.
  - Phase 66 hardcoded-literal rules count taxonomy / provider / route-like names as findings when ownership is unclear.
- **建议处理**:
  - In a later cleanup phase, evaluate a shared registry or import from `EXECUTOR_REGISTRY`-adjacent runtime data if such a runtime owner exists.
  - Do not put brand names into design documents; this is implementation metadata ownership only.
- **影响范围**:cross-module specialist metadata.
- **关联**:none.

### [low][hardcoded-literal] Capability reference sets are hardcoded in `capabilities.py`

- **位置**:
  - `src/swallow/capabilities.py:6-16`
  - `src/swallow/capabilities.py:48-77`
- **判定依据**:
  - `rg -n 'KNOWN_PROFILE_REFS|KNOWN_WORKFLOW_REFS|KNOWN_VALIDATOR_REFS|KNOWN_SKILL_REFS|KNOWN_TOOL_REFS|baseline_local|doctor.executor|plan-task' src/swallow/capabilities.py`
  - Capability profiles, workflows, validators, skills, and tool refs live as source constants.
  - These are operator-visible capability names and are not currently derived from route metadata or a manifest file.
- **建议处理**:
  - In a later cleanup phase, keep the current constants but add an ownership comment or move them into a declarative manifest if capability refs grow.
- **影响范围**:single-file.
- **关联**:none.

### [med][hardcoded-literal] Route-mode choices are duplicated between CLI and router policy

- **位置**:
  - `src/swallow/router.py:47-55`
  - `src/swallow/cli.py:1424-1427`
  - `src/swallow/cli.py:1757-1760`
  - `src/swallow/cli.py:1858-1935`
- **判定依据**:
  - `rg -n 'choices=\\[\"auto\", \"live\", \"deterministic\", \"detached\", \"offline\", \"summary\"\\]|ROUTE_MODE_ALIASES|normalize_route_mode' src/swallow/cli.py src/swallow/router.py`
  - CLI repeats the same route-mode list for route selection, create, run, retry, resume, rerun, and acknowledge paths.
  - The canonical normalization table lives in `router.py`; CLI has no single imported source for the choices.
- **建议处理**:
  - In a later cleanup phase, export valid route-mode choices from the router layer for CLI parser consumption.
  - Keep parser help text stable.
- **影响范围**:cross-block CLI / router surface.
- **关联**:none.

### [low][hardcoded-literal] MPS policy kinds are duplicated between CLI choices and policy store

- **位置**:
  - `src/swallow/mps_policy_store.py:13-15`
  - `src/swallow/mps_policy_store.py:34-35`
  - `src/swallow/cli.py:1313-1316`
- **判定依据**:
  - `rg -n 'mps_round_limit|mps_participant_limit|MPS_POLICY_KINDS|choices=\\(\"mps_round_limit\", \"mps_participant_limit\"\\)' src/swallow/cli.py src/swallow/mps_policy_store.py`
  - The MPS policy store owns `MPS_POLICY_KINDS`, but CLI repeats the same choices rather than importing the owner.
  - The hard max `3` for round limit is also embedded in validation text.
- **建议处理**:
  - In a later cleanup phase, have CLI consume `MPS_POLICY_KINDS` and name the round-limit max constant.
  - Keep the current ORCHESTRATION §5.3 limit unchanged.
- **影响范围**:cross-module surface / policy store.
- **关联**:none.

### [med][hardcoded-literal] CLI repeats ingestion format choices instead of consuming parser-owned formats

- **位置**:
  - `src/swallow/cli.py:1518-1521`
  - `src/swallow/ingestion/parsers.py:10-15` (cross-block owner)
  - `src/swallow/ingestion/parsers.py:63-92` (cross-block parser dispatch)
- **判定依据**:
  - `rg -n 'SUPPORTED_INGESTION_FORMATS|choices=\\(\"chatgpt_json\", \"claude_json\", \"open_webui_json\", \"generic_chat_json\", \"markdown\"\\)' src/swallow/cli.py src/swallow/ingestion/parsers.py`
  - CLI manually repeats parser-owned supported formats, creating a stale-surface risk when a parser format is added or renamed.
  - This is the block 5 side of the block 4 ingestion-format finding.
- **建议处理**:
  - In a later cleanup phase, import `SUPPORTED_INGESTION_FORMATS` for CLI `choices`.
  - Keep `tests/eval` fixture format names stable.
- **影响范围**:cross-block CLI / ingestion parser.
- **关联**:Block 4 ingestion format hardcoded-literal finding.

### [low][hardcoded-literal] Deprecated `doctor codex` alias and `aider` defaults keep brand names in surface code

- **位置**:
  - `src/swallow/cli.py:1672-1673`
  - `src/swallow/cli.py:2314`
  - `src/swallow/cli.py:3797`
  - `src/swallow/doctor.py:322-323`
- **判定依据**:
  - `rg -n 'doctor codex|Deprecated alias|codex\"|aider\"|AIWF_AIDER_BIN|AIWF_EXECUTOR_MODE' src/swallow/cli.py src/swallow/doctor.py`
  - `doctor codex` is still mounted as a deprecated alias for `doctor executor`, and task creation / doctor executor default to `"aider"`.
  - Brand strings in runtime surface code are allowed when tied to implementation, but Phase 66 hardcoded-literal rules still count them for cleanup review.
- **建议处理**:
  - In a later cleanup phase, either keep these as intentional compatibility aliases with comments/tests or route defaults through executor registry/runtime config.
  - Do not remove deprecated CLI aliases without a compatibility decision.
- **影响范围**:CLI compatibility surface.
- **关联**:none.

## Checked But Not Counted

- CLI subcommands were checked for "registered but never dispatched" risk. The current `add_parser` and `if args.command...` scan did not reveal a clearly dead subcommand; deprecated `doctor codex` is still dispatchable and was counted only as a low hardcoded-literal/compatibility item.
- `extract_route_weight_proposals_from_report(...)` remains fragile but was skipped as Phase 50 backlog.
- `_FAIL_SIGNAL_PATTERNS` remains fragile but was skipped as Phase 50 backlog.
- `paths.py`, `identity.py`, and `workspace.py` are intentionally small centralized layers. No finding was counted for their many path helper functions because they are the ownership point, not duplication by themselves.
