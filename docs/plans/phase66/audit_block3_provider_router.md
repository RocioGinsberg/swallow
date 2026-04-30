---
author: codex
phase: phase66
slice: audit-block3-provider-router
status: review
depends_on:
  - docs/plans/phase66/kickoff.md
  - docs/plans/phase66/design_decision.md
  - docs/plans/phase66/risk_assessment.md
  - docs/plans/phase66/context_brief.md
  - docs/concerns_backlog.md
---

TL;DR: Block 3 audited 5 files / 1740 LOC with 4 findings: 0 high / 3 med / 1 low. The Phase 64 indirect chat-completion guard gap was skipped as already tracked; no code, tests, or design docs were changed.

## Coverage

Audited files:

- `src/swallow/router.py` — 1422 LOC
- `src/swallow/agent_llm.py` — 47 LOC
- `src/swallow/_http_helpers.py` — 91 LOC
- `src/swallow/cost_estimation.py` — 74 LOC
- `src/swallow/capability_enforcement.py` — 106 LOC

Block total: 1740 LOC.

## Skip List Applied

Loaded the Phase 66 skip list from `design_decision.md` and `docs/concerns_backlog.md`: 13 pre-Phase-65 Open items plus 3 Phase-65 known gaps, 16 total.

Block-specific skipped items:

- Phase 64 M2-2: chat-completion guard indirect URL binding gap. `router.invoke_completion(...)`, `_http_helpers.resolve_new_api_chat_completions_url()`, and related tests were not reported as a guard-strength finding.

The HTTP-default finding below is config hygiene, not a claim that the Phase 64 guard gap is new or untracked.

`tests/` was not audited as a subject. It was used only as a callsite oracle for dead-code checks, per Phase 66 design.

## Method

- File inventory: `wc -l` for the 5 block files.
- Symbol inventory: `rg -n 'def |class |^[A-Z][A-Z0-9_]+\\s*='`.
- Dead-code check: two-pass grep per design, with `src/swallow/` as production callsite source and `tests/` as oracle only.
- Literal / helper checks: targeted `rg` for provider/model names, route names, URL strings, timeout defaults, taxonomy/capability strings, and duplicate helper patterns.

## Finding Summary

| Severity | dead-code | hardcoded-literal | duplicate-helper | abstraction-opportunity | Total |
|---|---:|---:|---:|---:|---:|
| high | 0 | 0 | 0 | 0 | 0 |
| med | 1 | 2 | 0 | 0 | 3 |
| low | 0 | 1 | 0 | 0 | 1 |
| **Total** | **1** | **3** | **0** | **0** | **4** |

The count is inside the design expectation for block 3(3-6 findings).

## Findings

### [med][dead-code] Module-level `_pricing_for(...)` is unreachable behind `StaticCostEstimator._pricing_for(...)`

- **位置**:`src/swallow/cost_estimation.py:34-42`
- **判定依据**:
  - `rg -n '_pricing_for\\(' src/swallow tests`
  - Production hits are:
    - `src/swallow/cost_estimation.py:34` module-level definition
    - `src/swallow/cost_estimation.py:50` call to `self._pricing_for(...)`
    - `src/swallow/cost_estimation.py:59` instance method definition
  - No production callsite imports or calls the module-level `_pricing_for(...)`; tests also do not call it directly.
  - The module-level function duplicates the method body at `src/swallow/cost_estimation.py:59-67`.
- **建议处理**:
  - In a later cleanup phase, remove the module-level helper or make `StaticCostEstimator` delegate to it.
  - If removed, keep tests around `estimate_cost(...)` and `StaticCostEstimator.estimate(...)` as behavior coverage.
- **影响范围**:single-file.
- **关联**:none.

### [med][hardcoded-literal] Static cost pricing table hardcodes provider/model families in code

- **位置**:
  - `src/swallow/cost_estimation.py:5-15`
  - `src/swallow/cost_estimation.py:17-19`
- **判定依据**:
  - `MODEL_PRICING` embeds provider/model-family keys such as `"claude"`, `"deepseek"`, `"gemini"`, `"glm"`, `"qwen"`, and `"fim"`.
  - `LEGACY_MODEL_HINT_ALIASES` embeds `"codex": "fim"`.
  - Phase 66 hardcoded-literal rules count model/provider/dialect names as findings even on single occurrence.
  - Cost values are also policy-like operational data, but they currently live in Python source.
- **建议处理**:
  - In a later design/cleanup phase, decide whether cost pricing belongs in route metadata, route policy, or a separate cost-policy file.
  - Keep `StaticCostEstimator` injectable behavior; the issue is the default table location, not the estimator interface.
- **影响范围**:cross-module policy data, because `orchestrator.py` and `harness.py` consume cost estimates.
- **关联**:none.

### [low][hardcoded-literal] Chat-completion URL and timeout defaults are split across helpers

- **位置**:
  - `src/swallow/_http_helpers.py:7`
  - `src/swallow/_http_helpers.py:78-83`
  - `src/swallow/router.py:1216`
- **判定依据**:
  - `rg -n 'DEFAULT_NEW_API_CHAT_COMPLETIONS_URL|AIWF_EXECUTOR_TIMEOUT_SECONDS\", \"30\"|return 20' src/swallow/_http_helpers.py src/swallow/router.py`
  - `_http_helpers.py` hardcodes `http://localhost:3000/v1/chat/completions` as a default URL.
  - `router.py` uses `"30"` as the missing-env default for `AIWF_EXECUTOR_TIMEOUT_SECONDS`, while `parse_timeout_seconds(...)` falls back to `20` for invalid or non-positive values.
  - URL literals and timeout magic numbers are both in Phase 66 hardcoded-literal scope.
- **建议处理**:
  - In a later cleanup phase, centralize chat-completion defaults as named constants near `_http_helpers.py` or runtime config.
  - Preserve the environment override behavior; this is not a request to change provider routing.
- **影响范围**:single block / Specialist Internal LLM gateway.
- **关联**:Phase 64 M2-2 guard gap was skipped; this finding is only about literal/default placement.

### [med][hardcoded-literal] Capability enforcement repeats taxonomy and capability strings outside the taxonomy model

- **位置**:
  - `src/swallow/capability_enforcement.py:7-8`
  - `src/swallow/capability_enforcement.py:21-58`
- **判定依据**:
  - `TAXONOMY_CAPABILITY_CONSTRAINTS` embeds taxonomy keys such as `"validator/*"`, `"*/stateless"`, and `"*/canonical-write-forbidden"`.
  - It also embeds capability field names / values such as `"filesystem_access"`, `"network_access"`, `"supports_tool_loop"`, `"canonical_write_guard"`, `"workspace_read"`, `"workspace_write"`, `"optional"`, and `"required"`.
  - `rg -n 'VALIDATOR_SYSTEM_ROLE|VALIDATOR_MEMORY_AUTHORITY|MEMORY_AUTHORITY|system_role|memory_authority' src/swallow/validator_agent.py src/swallow/models.py src/swallow/capability_enforcement.py` shows related taxonomy constants and validation data already exist outside this module.
  - The duplication is not functionally wrong, but taxonomy/capability spellings now have more than one source inside production code.
- **建议处理**:
  - In a later cleanup phase, either import shared taxonomy constants where practical or move capability constraint data into one declarative table with explicit ownership.
  - Do not change enforcement semantics without a design decision; this is naming/data placement hygiene.
- **影响范围**:cross-module taxonomy / route capability handling.
- **关联**:none.

## Checked But Not Counted

- `router.invoke_completion(...)` calls `resolve_new_api_chat_completions_url()` directly; the known indirect URL guard limitation is already tracked as Phase 64 M2-2 and was not counted.
- `ROUTE_MODE_ALIASES` is still code-level, but route policy proper is SQLite/default-file backed after Phase 65. It was left as calibration material for Claude review rather than counted separately in M1.
- `agent_llm.py` is intentionally a thin Provider Router pass-through after Phase 64 and produced no finding.
