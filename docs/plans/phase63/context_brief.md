---
author: claude
phase: phase63
slice: context-analysis
status: draft
depends_on: ["docs/roadmap.md", "docs/design/INVARIANTS.md", "docs/design/DATA_MODEL.md", "docs/design/SELF_EVOLUTION.md"]
---

TL;DR: Phase 62 (MPS) and Phase 61 (apply_proposal) left 5 constitution-code drift Open items now formalized in `docs/concerns_backlog.md`. Scope spans `governance.py` / `orchestrator.py` / `staged_knowledge.py` / `paths.py` / `models.py` / `tests/test_invariant_guards.py`, plus two modules that do not yet exist (`identity.py` / `workspace.py`). Key risk: `identity.py` / `workspace.py` introduction will require call-site changes across at least 6 production files; §9 batch guard activation may expose undocumented drift in the existing codebase.

## 变更范围

- **直接影响模块**:
  - `src/swallow/governance.py` — `_PENDING_PROPOSALS` in-memory registry (line 95), `_apply_route_review_metadata` four-step write sequence (lines 552-560) lacking rollback, `apply_proposal` entry
  - `src/swallow/orchestrator.py` — line 3145 `submit_staged_candidate(...)` direct write violates §5 matrix (`Orchestrator` row, `stagedK` column is `-`)
  - `src/swallow/staged_knowledge.py` — `submit_staged_candidate` function (line 106); current callers: orchestrator.py:3145, cli.py:2590, ingestion/pipeline.py (4 call sites)
  - `src/swallow/paths.py` — current path resolution hub; `workspace.py` will need to absorb `.resolve()` absolutization
  - `src/swallow/models.py` — `event_log` / `task_records` / `task_handoffs` etc. have `actor` default `"local"` hardcoded as SQL DEFAULT strings; `action="local"` at line 297
  - `tests/test_invariant_guards.py` — 9 guards currently implemented (lines 54-186); 14 of the 17 INVARIANTS §9 guards are absent

- **间接影响模块**:
  - `src/swallow/router.py` — 11+ occurrences of `execution_site="local"` (lines 284-601); distinct semantic from actor `"local"` but same literal; will need careful scoping
  - `src/swallow/store.py` / `src/swallow/knowledge_store.py` / `src/swallow/mps_policy_store.py` — targets of the Repository abstraction layer scaffold (DATA_MODEL §4.1)
  - `src/swallow/cli.py` — `submit_staged_candidate` call at line 2590; `apply_proposal` calls at lines 2381, 2476, 2512, 2527, 2636, 2707
  - `src/swallow/ingestion/pipeline.py` — 4 `submit_staged_candidate` call sites; Specialist entity, `stagedK` write is §5-compliant here (Specialist row `stagedK = W`)

## 近期相关变更 (git history)

| Commit | 描述 | 相关模块 |
|--------|------|---------|
| d6e4b90 | docs(release): sync README and state for v1.3.1 | docs only |
| ce98f92 | merge: Complete Refine codes after PRD change | synthesis.py, mps_policy_store.py, cli.py, governance.py, test_invariant_guards.py |
| a148e3c | fix(synthesis): address MPS review concerns 2 | synthesis.py, cli.py, test_synthesis.py |
| 7e8b2a4 | fix(synthesis): address MPS review concerns | synthesis.py, cli.py |
| fd3a03c | feat(synthesis): add MPS staged knowledge bridge | synthesis.py, orchestrator.py |
| 35b8768 | feat(synthesis): add MPS runtime orchestration | synthesis.py, orchestrator.py |
| e0dc534 | feat(synthesis): add MPS policy plumbing | mps_policy_store.py, governance.py, cli.py |
| c66fa87 | merge: Refine codes after PRD change | governance.py, store.py, knowledge_store.py, test_governance.py, test_invariant_guards.py |
| 3dc9d93 | docs(governance): policy and concern | docs only |
| e48bf9b | feat(governance): policy apply_proposal boundary | governance.py, cli.py |

## 关键上下文

- **`_PENDING_PROPOSALS` 注册表行为**: `governance.py:95` — `dict[tuple[ProposalTarget, str], object]`. `register_*` functions silently overwrite on duplicate `proposal_id` (e.g. `_PENDING_PROPOSALS[(target, normalized_id)] = ...` with no existence check). No eviction or lifecycle cleanup; the registry grows monotonically for the process lifetime.

- **`apply_proposal` transaction gap**: The four-step sequence in `_apply_route_review_metadata` (lines 552-560) runs `save_route_weights` then `apply_route_weights` then `save_route_capability_profiles` then `apply_route_capability_profiles` as four independent calls. `rollback_weights` and `rollback_capability_profiles` fields exist in `OptimizationProposalApplicationRecord` (lines 385-386, 572-573) but contain pre-write snapshots only — no code path reads them to execute a rollback. A failure between calls 2 and 3 leaves weights applied to the live registry but profiles not yet updated.

- **`identity.py` / `workspace.py` confirmed absent**: `find src/swallow -name 'identity.py' -o -name 'workspace.py'` returned zero matches. INVARIANTS §7 requires `"local"` actor literal to appear exactly once (in `swallow.identity.local_actor()`). Actual count: the literal `"local"` appears 25+ times across `models.py`, `router.py`, `orchestrator.py`, `execution_fit.py`, `cost_estimation.py`, `dialect_data.py` — though many are `execution_site="local"` semantics (different from actor identity). The actor-semantic uses are in SQL DEFAULT strings and `models.py:297 action="local"`. Guards `test_no_hardcoded_local_actor_outside_identity_module` and `test_no_absolute_path_in_truth_writes` are listed in INVARIANTS §9 but do not exist in `test_invariant_guards.py`.

- **`.resolve()` sites**: 25+ occurrences across `orchestrator.py` (lines 2595-2630+), `executor.py:791`, `literature_specialist.py:80`, `quality_reviewer.py:41`, `ingestion/pipeline.py` (lines 52, 125), `web/api.py` (lines 12, 35). DATA_MODEL §6 requires all path absolutization to route through `swallow.workspace.resolve_path()`.

- **`orchestrator.py:3145` call site confirmed**: `submit_staged_candidate(base_dir, StagedCandidate(..., submitted_by=state.executor_name, ...))` — this is within the Librarian-side-effect application path in the orchestrator (not Specialist code). INVARIANTS §5: Orchestrator row, stagedK column is `-`. The call is architecturally in the Orchestrator, not in a Specialist, making it a §5 violation. Ingestion pipeline's 4 call sites are within a Specialist path (§5-compliant).

- **Currently implemented §9 guards** (9 of 17): `test_canonical_write_only_via_apply_proposal`, `test_route_metadata_writes_only_via_apply_proposal`, `test_only_apply_proposal_calls_private_writers`, `test_mps_policy_writes_via_apply_proposal`, `test_mps_no_chat_message_passing`, `test_synthesis_uses_provider_router`, `test_mps_default_route_is_path_a`, `test_synthesis_clones_state_per_call`, `test_synthesis_module_does_not_call_submit_staged_candidate`. **Missing 8 of 17** from the INVARIANTS §9 table: `test_no_executor_can_write_task_table_directly`, `test_state_transitions_only_via_orchestrator`, `test_path_b_does_not_call_provider_router`, `test_validator_returns_verdict_only`, `test_specialist_internal_llm_calls_go_through_router`, `test_all_ids_are_global_unique_no_local_identity`, `test_event_log_has_actor_field`, `test_no_hardcoded_local_actor_outside_identity_module`, `test_no_absolute_path_in_truth_writes`, `test_no_foreign_key_across_namespaces`, `test_append_only_tables_reject_update_and_delete`, `test_artifact_path_resolved_from_id_only`, `test_route_override_only_set_by_operator`, `test_ui_backend_only_calls_governance_functions`. Count: 14 missing (the Phase 61 non-goal Open figure of 14 is consistent after accounting for the 4 MPS guards added in Phase 62 — net still 14 unimplemented against the full §9 table of 17).

- **DATA_MODEL §4.1 Repository classes**: `KnowledgeRepo` / `RouteRepo` / `PolicyRepo` described with `swallow.truth.knowledge` / `swallow.truth.route` / `swallow.truth.policy` module paths. These modules do not exist. Current implementation uses `store.py`, `knowledge_store.py`, `router.py` (for route health writes), `mps_policy_store.py` directly from `governance.py` via imports at lines 13-22.

- **`cli.py:2590` `submit_staged_candidate` call**: This is an Operator CLI path (`swl synthesis stage`), meaning the Operator column in §5 is `W` for `stagedK` — this call is §5-compliant. Only `orchestrator.py:3145` is the drift site.

## 风险信号

- **Repository 接口设计破坏现有调用方**: `governance.py` currently imports `save_route_weights`, `save_route_capability_profiles`, `apply_route_weights`, `apply_route_capability_profiles` from `router.py` directly (lines 13-22). Introducing `RouteRepo._apply_metadata_change` as the sole write path requires rerouting these imports and may require changing `governance.py`'s internal call structure at lines 309-316 and 552-560.

- **`identity.py` / `workspace.py` 引入的 import 改动规模**: `"local"` literal distinguishing between actor-semantic and execution-site-semantic uses requires careful disambiguation before centralization. `execution_site="local"` in `router.py` (11+ sites) is a different semantic from `actor="local"`. Automated grep-based guards may catch both unless the guard pattern is precise.

- **§9 14-guard batch activation may surface existing drift**: Guards `test_no_executor_can_write_task_table_directly`, `test_state_transitions_only_via_orchestrator`, and `test_append_only_tables_reject_update_and_delete` (SQLite trigger enforcement) may reveal compliance gaps in existing store code not previously scanned. `test_append_only_tables_reject_update_and_delete` requires SQLite triggers to be deployed in test DB setup — no such trigger infrastructure is visible in current test fixtures.

- **Transaction rollback and SQLite schema**: `rollback_weights` / `rollback_capability_profiles` data is already captured in `OptimizationProposalApplicationRecord`. Implementing actual rollback execution does not necessarily require a new SQLite table — the application record artifact already stores pre-write state. However, if rollback is to be idempotent and auditable, a `policy_change_log` or `route_change_log` append-only table may be needed (DATA_MODEL §3 has `know_change_log` but no route/policy equivalent).
