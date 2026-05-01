# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Retrieval Quality`
- latest_completed_phase: `Retrieval U-T-Y / Observability, EvidencePack, Summary Surface`
- latest_completed_slice: `Retrieval U-T-Y M1-M6 Implementation`
- active_track: `Architecture / Engineering`
- active_phase: `Architecture Recomposition First Branch`
- active_slice: `M6 closeout and next subtrack selection`
- active_branch: `feat/architecture-recomposition-ad1-v`
- status: `roadmap_lto_reorganization_complete`

## 当前状态说明

Human has merged Retrieval U-T-Y. Per Human request, Codex did not perform an extra Retrieval U-T-Y file closeout and moved directly into the next architecture phase.

Current branch `feat/architecture-recomposition-ad1-v` has committed the first bounded Architecture Recomposition pilot: minimal test helper foundation, a Knowledge Plane facade, narrow upper-layer import migration, and focused test relocation.

The optional M5 AB pilot from `docs/plans/architecture-recomposition/plan.md` has also been committed as `e36e854 refactor(application): add control center query pilot`. Current docs reconciliation clarifies that `docs/plans/architecture-recomposition/plan.md` is the active plan, but it authorizes only the first AD branch plus one optional AB pilot. The roadmap has been reorganized around long-term optimization goals (`LTO-*`) plus short-term phase tickets, so partially advanced areas stay visible without making completed candidates look unfinished. The next step is M6 closeout / PR material / next subtrack selection, not continuing into later AD subtracks implicitly.

Phase 67 and Phase 68 have both been merged into `main`.

Current main checkpoint:

- `eb2c743 merge: code hygiene execute` — Phase 67 L+M+N cleanup + Candidate P module reorganization.
- `5cb08af merge: update knowledge plane raw material store` — Phase 68 Candidate O Raw Material Store boundary.
- `bc8abb1 docs(release): sync v1.5.0 release docs` — release snapshot and tag target.

Latest executed public tag is `v1.5.0`(annotated tag, points to `bc8abb1`). Phase 68 turns the roadmap Candidate O storage-backend-independence signal into implementation: `RawMaterialStore` interface, filesystem backend, stable `file://workspace/...` refs, and `artifact://...` evidence resolution.

R-entry design / implementation readiness has been checked against:

- `docs/design/INVARIANTS.md`
- `docs/design/ARCHITECTURE.md`
- `docs/design/DATA_MODEL.md`
- `docs/design/STATE_AND_TRUTH.md`
- `docs/design/KNOWLEDGE.md`
- `docs/design/AGENT_TAXONOMY.md`
- `docs/design/PROVIDER_ROUTER.md`
- `docs/design/ORCHESTRATION.md`
- `docs/design/HARNESS.md`
- `docs/design/SELF_EVOLUTION.md`
- `docs/design/INTERACTION.md`
- `docs/design/EXECUTOR_REGISTRY.md`

Candidate R observation closeout is complete. Human selected a unified retrieval implementation branch for the U -> T -> Y follow-through: retrieval observability first, EvidencePack / source resolution second, and narrow summary-route surface clarification third.

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `README.md`
4. `docs/plans/phase67/closeout.md`
5. `docs/plans/phase68/closeout.md`
6. `docs/roadmap.md`
7. `docs/concerns_backlog.md`
8. `docs/design/INVARIANTS.md`
9. `docs/plans/candidate-r/plan.md`
10. `docs/plans/candidate-r/observations.md`
11. `docs/plans/candidate-r/closeout.md`
12. `docs/engineering/GOF_PATTERN_ALIGNMENT.md`
13. `docs/plans/retrieval-u-t-y/plan.md`
14. `docs/plans/architecture-recomposition/plan.md`

## 当前推进

已完成:

- **[Human]** Phase 67 merged into `main`:
  - `eb2c743 merge: code hygiene execute`
- **[Human]** Phase 68 merged into `main`:
  - `5cb08af merge: update knowledge plane raw material store`
- **[Codex]** Release preflight on `main`:
  - `git diff --check`: passed
  - `git diff -- docs/design`: no output
  - `.venv/bin/python -m compileall -q src/swallow`: passed
  - `.venv/bin/python -m pytest -q`: `622 passed, 8 deselected, 10 subtests passed`
- **[Codex]** `v1.5.0` release-doc sync completed:
  - `README.md` release snapshot updated from `v1.4.0` to `v1.5.0`
  - `current_state.md` updated to Phase 68 main checkpoint and later synced to executed tag state
  - `docs/active_context.md` updated to tag release gate state and later synced to R-entry state
  - `docs/concerns_backlog.md` moved the old release-doc sync debt to Resolved
  - `docs/roadmap.md` factually synced Candidate L/M/N/P/O completion and `v1.5.0`
- **[Codex]** Release preflight exposed the known subtask timeout wall-clock flake; stabilized
  `tests/test_run_task_subtasks.py` by removing the brittle elapsed-time assertion while keeping artifact/event behavior assertions.
- **[Codex]** R-entry triage completed:
  - `docs/concerns_backlog.md` now records no must-fix blocker before real-use testing
  - `docs/roadmap.md` records R-entry gate guardrails and confirms Candidate R can start after release/tag closeout
- **[Human]** `v1.5.0` annotated tag completed on `main`:
  - tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- **[Codex]** R-entry design / implementation cross-check completed:
  - `docs/design/` remains unchanged
  - focused readiness tests passed: `51 passed` + Phase 65 SQLite governance tests `21 passed`
- **[Codex]** RAG / Retrieval follow-up planning refreshed in `docs/roadmap.md`:
  - Candidate R now starts from `v1.5.0` real-use feedback and RAG gap triage.
  - New follow-up candidates S/T/U cover LLM Wiki Compiler, EvidencePack / source resolution, and neural retrieval observability / eval / index hardening.
  - Consumed gap history and completed candidate detail blocks were pruned from roadmap; historical detail remains in git log and phase closeout files.
- **[Codex]** Source organization follow-up planning added to `docs/roadmap.md`:
  - New maintenance candidates V/W/X/Y/Z cover Knowledge Plane API simplification, Provider Router split, Orchestration facade decomposition, Surface command / Meta Optimizer split, and Governance apply handler split.
  - Recommended ordering keeps Candidate V as the low-risk foundation before deeper S/T/U work, with W/X/Y/Z triggered by touch surface and maintenance friction.
- **[Codex]** Test architecture and interface/application boundary planning added to `docs/roadmap.md`:
  - New candidates AA/AB cover Test Architecture / TDD Harness and Interface / Application Boundary Clarification.
  - Recommended ordering now treats AA as a TDD/restructuring prerequisite before V/W/X/AB-scale changes, while AB keeps FastAPI and CLI as adapters over shared application commands/queries and preserves local-first single-file SQLite truth.
- **[Codex]** Local UI runtime standard fixed in `docs/design/INTERACTION.md`:
  - Browser Web UI and future desktop apps use local loopback FastAPI over the same application commands/queries.
  - CLI normal commands bypass HTTP and call the application layer in-process; `swl serve` only starts FastAPI / Control Center.
  - `docs/roadmap.md` Candidate AB now references this design anchor.
- **[Codex]** Engineering organization standards fixed under `docs/engineering/`:
  - `CODE_ORGANIZATION.md` defines local-first clean monolith layering, facade-first migration, and V/W/X/Y/Z/AB convergence standards.
  - `TEST_ARCHITECTURE.md` defines test layers, TDD workflow, helpers, CLI test split, guard rules, and eval rules.
  - `AGENTS.md`, `.agents/shared/read_order.md`, and `docs/roadmap.md` now reference these long-term engineering standards.
- **[Codex]** Agent responsibility reweighting and plans artifact simplification documented:
  - Codex now owns phase plan definition through `docs/plans/<phase>/plan.md`.
  - Claude no longer defaults to heavy plan decomposition; Claude main handles PR review / tag evaluation, while Claude subagents handle `context_brief.md`, `plan_audit.md`, factual roadmap updates, and optional consistency checks.
  - New phase plans default to `context_brief.md` + `plan.md` + `plan_audit.md` + `review_comments.md` + `closeout.md`; legacy `kickoff.md` / `design_decision.md` / `risk_assessment.md` / `breakdown.md` remain readable but are not default outputs.
- **[Codex]** Concerns backlog hygiene pass completed:
  - `docs/concerns_backlog.md` Open items are now split into Active Open vs Roadmap-Bound, preventing long-running mapped concerns from remaining in the active Open table.
  - `docs/roadmap.md` candidates AA/AB/U/W/X/Y/Z now explicitly list the mapped concern groups they should consume.
- **[Codex]** Candidate R observation plan started:
  - `docs/plans/candidate-r/plan.md` fixes the first observation sample as `docs/design/`.
  - R1 will observe design-doc ingestion, staged review, retrieval reports, evidence traceability, and operator friction before selecting a follow-up implementation candidate.
- **[Human]** Candidate R `INVARIANTS.md` staged review seed completed:
  - `swl knowledge ingest-file docs/design/INVARIANTS.md --summary` created 12 staged candidates with `file://workspace/docs/design/INVARIANTS.md` source refs.
  - 5 high-signal invariant candidates were promoted: §0 invariant rules, §4 LLM call paths, §5 Truth write matrix, §7 single-user evolution boundary, and §9 invariant guard tests.
  - `swl knowledge canonical-audit` reports `total: 5`, `active: 5`, `duplicate_active_keys: 0`, `orphan_records: 0`.
- **[Human/Codex]** Candidate R retrieval probe P1 completed:
  - task: `2f77c3a3a82d` (`R probe: apply_proposal boundary`)
  - result transcript: `results/R.md` (local observation artifact)
  - retrieval reused 4 promoted canonical invariant records and exposed `knowledge_retrieval_mode: text_fallback` after embedding API fallback.
  - observation summary recorded in `docs/plans/candidate-r/observations.md`.
- **[Human/Codex]** Candidate R retrieval probe P2 completed:
  - task: `5e891023a196` (`R probe: LLM call path boundary`)
  - retrieval reused the target §4 canonical invariant record (`canonical-staged-090c3193`) plus invariant guard tests.
  - top 5 results were historical `docs/archive_phases/phase64/*` notes, exposing a stronger Candidate U source-weighting / archive-noise signal.
  - embedding API fallback repeated; canonical metadata still reports `knowledge_retrieval_mode: text_fallback`.
- **[Human]** Embedding API configuration restored:
  - `swl doctor stack` reports `embedding_api_endpoint=pass` at `http://localhost:3000/v1/embeddings`.
  - Postgres / pgvector and WireGuard / egress proxy checks remain non-blocking for this local SQLite-first R observation slice.
- **[Human/Codex]** Candidate R P2b vector-enabled comparison completed:
  - `.venv/bin/swl` with restored `.env` and `sqlite-vec` moved `canonical-staged-090c3193` from P2 rank 6 to rank 1.
  - `retrieval-json` now reports `embedding_backend=api_embedding`, `knowledge_retrieval_adapter=sqlite_vec`, `knowledge_retrieval_mode=vector`, and `rerank_applied=true`.
  - Candidate U signal narrowed from "basic vector path failure" to fallback-mode clarity, archive source policy, and retrieval report observability.
- **[Human/Codex]** Candidate R `KNOWLEDGE.md` dry-run intake completed:
  - `.venv/bin/swl knowledge ingest-file docs/design/KNOWLEDGE.md --dry-run --summary` reported 32 preview candidates.
  - Codex selected 10 recommended P3 seed chunks by `source_object_id` across design statement, Raw Material, Knowledge Truth, Evidence, Retrieval & Serving, EvidencePack, Retrieval Source Types, Wiki / Canonical, and raw-material-vs-knowledge boundaries.
  - Dry-run also exposed Candidate U/T signals: code / command fragment over-splitting, missing line spans / heading paths in the report, confusing `fragments=0` vs `staged_candidates=32`, and empty Decisions / Constraints summary buckets.
- **[Codex]** Candidate R `KNOWLEDGE.md` P3 seed promotion completed:
  - Persisted `KNOWLEDGE.md` staged candidates, inspected the selected 10 core records, and promoted them with note `Candidate R P3 knowledge-boundary seed`.
  - Promoted canonical IDs: `canonical-staged-6c3bf658`, `canonical-staged-35757554`, `canonical-staged-d153b1fc`, `canonical-staged-87b38d5f`, `canonical-staged-f07145f3`, `canonical-staged-2dfb5d20`, `canonical-staged-a763b064`, `canonical-staged-5b08bc0a`, `canonical-staged-383b9d7f`, `canonical-staged-bdbd97a2`.
  - `.venv/bin/swl knowledge canonical-audit` reports `total: 15`, `active: 15`, `duplicate_active_keys: 0`, `orphan_records: 0`.
- **[Codex]** Candidate R retrieval probe P3/P3b completed:
  - P3 task `f767f87222d9` completed but fell back to text because this tool shell had not loaded `.env`.
  - P3b task `c1adb2f7f807` reran the same knowledge-truth boundary probe with `.env` loaded and confirmed `embedding_backend=api_embedding`, `knowledge_retrieval_adapter=sqlite_vec`, `knowledge_retrieval_mode=vector`, and `rerank_applied=true`.
  - P3b reused 7 promoted `KNOWLEDGE.md` canonical records in the top 7 results; `docs/plans/candidate-r/observations.md` appeared as the 8th notes result.
  - Candidate U/T/Y signals remain: rerank order vs raw score readability, source-only evidence without resolved spans, self-referential notes retrieval, and summary route not producing a semantic answer.
- **[Codex/Human]** Candidate R closeout direction accepted and roadmap updated:
  - `docs/plans/candidate-r/closeout.md` records Candidate R complete and recommends Candidate U first.
  - `docs/roadmap.md` now marks R as completed observation, promotes Candidate U to the current recommended next phase, and adds Candidate AC as the later system-design refactor / GoF pattern alignment track.
  - Candidate T remains the next evidence/source-resolution follow-up; Candidate Y remains a narrow summary-route / surface ergonomics follow-up.
- **[Codex]** GoF-style system design guidance added:
  - `docs/engineering/GOF_PATTERN_ALIGNMENT.md` defines how Swallow should use Facade / Strategy / Command / Repository / Adapter / Value Object / State as responsibility language, not as pattern-for-pattern's-sake.
  - `docs/roadmap.md` now references Candidate AC for later coordination of AB/V/W/X/Y/Z system-design refactors.
- **[Codex/Human]** Retrieval U-T-Y implementation branch opened:
  - active branch: `feat/retrieval-u-t-y`
  - scope: Candidate U first, Candidate T second, Candidate Y narrow third
  - implementation remains gated on plan review.
- **[Codex]** Retrieval U-T-Y plan drafted:
  - `docs/plans/retrieval-u-t-y/plan.md`
  - milestones cover retrieval trace/report clarity, source policy labels, regression probes, EvidencePack compatibility, source pointer resolution, summary route surface clarification, and closeout smoke.
- **[Human/Codex]** Rerank boundary clarified for Retrieval U-T-Y:
  - chat-completion rerank is out of scope and should be removed from retrieval.
  - rerank must use an explicitly configured dedicated rerank model / endpoint.
  - if no dedicated rerank configuration exists, retrieval should not rerank and should report that state instead of falling back to chat.
- **[Codex]** Retrieval U-T-Y M1 implementation completed:
  - removed chat-completion rerank from retrieval.
  - added explicit dedicated HTTP rerank adapter using `SWL_RETRIEVAL_RERANK_MODEL` + `SWL_RETRIEVAL_RERANK_URL`.
  - default behavior without dedicated rerank configuration is no rerank with `rerank_failure_reason=not_configured`.
  - retrieval metadata/report now surface retrieval mode, adapter, embedding backend, fallback reason, rerank backend/model/configured/attempted/applied/failure, final order basis, final rank, raw score, vector distance, and rerank position.
  - validation passed: `tests/test_retrieval_adapters.py`, `tests/test_grounding.py`, focused CLI retrieval/grounding/summary tests, `tests/test_invariant_guards.py`, compileall, full `.venv/bin/python -m pytest -q` (`624 passed, 8 deselected, 10 subtests passed`), and `git diff --check`.
- **[Human]** M1 code committed:
  - `bcb984d feat(retrieval): replace chat rerank with dedicated rerank adapter`
- **[Codex]** Retrieval U-T-Y M2 implementation completed:
  - retrieval items now receive `source_policy_label` and `source_policy_flags`.
  - labels cover `canonical_truth`, `task_knowledge_truth`, `current_state`, `archive_note`, `observation_doc`, `repo_source`, `active_note`, and `artifact_source`.
  - non-truth source hits are flagged as `fallback_text_hit`; archive/current-state/observation docs are flagged as `operator_context_noise`.
  - retrieval report now includes `source_policy_warning_count`, a `Source Policy Warnings` section, and per-item source policy label/flags.
  - source grounding now includes source policy label/flags for each retrieved source.
  - warning coverage includes operational docs outranking canonical truth, observation-doc self-reference risk, and fallback hits without truth objects.
  - validation passed: `tests/test_retrieval_adapters.py`, `tests/test_grounding.py`, focused CLI retrieval/grounding/summary tests, `tests/test_invariant_guards.py`, compileall, full `.venv/bin/python -m pytest -q` (`626 passed, 8 deselected, 10 subtests passed`), and `git diff --check`.
- **[Codex]** Retrieval U-T-Y M3 implementation completed:
  - added offline P1/P2/P3 retrieval regression probes for `apply_proposal`, LLM Path A/B/C, and Knowledge Truth boundary canonical retrieval.
  - added staged intake hygiene warnings for duplicate source object IDs in a batch, repeated source object IDs in the registry, and repeated non-note source refs.
  - ingestion reports now include `hygiene_warning_count` and a `Hygiene Warnings` section.
  - validation passed: `tests/test_retrieval_adapters.py`, `tests/test_ingestion_pipeline.py`, `tests/test_grounding.py`, focused CLI retrieval/grounding/summary tests, `tests/test_invariant_guards.py`, compileall, full `.venv/bin/python -m pytest -q` (`630 passed, 8 deselected, 10 subtests passed`), and `git diff --check`.
- **[Codex]** Retrieval U-T-Y M4 implementation completed:
  - added `src/swallow/knowledge_retrieval/evidence_pack.py` as an EvidencePack-compatible serving view over current `RetrievalItem[]`.
  - EvidencePack groups `primary_objects`, `canonical_objects`, `supporting_evidence`, `fallback_hits`, and `source_pointers` without creating a second Truth store or changing `retrieval.json` shape.
  - retrieval reports now include EvidencePack counts and an EvidencePack summary section.
  - EvidencePack infers source policy labels for legacy retrieval items that predate M2 metadata.
- **[Codex]** Retrieval U-T-Y M5 implementation completed:
  - SourcePointer now carries `resolved_ref`, `resolved_path`, `resolution_status`, `resolution_reason`, line span, and heading path.
  - `file://workspace/...`, `artifact://...`, and legacy `.swl/tasks/<task>/artifacts/...` pointers are resolved through the existing filesystem RawMaterialStore where possible.
  - `source_grounding.md` and `retrieval_report.md` surface resolved/missing/unresolved source pointer state explicitly.
- **[Codex]** Retrieval U-T-Y M6 implementation completed:
  - local summary executor output now declares `surface_kind: local_execution_summary`, `semantic_answer_produced: no`, and `answer_contract: run_record_not_semantic_qa`.
  - `summary.md` now records `summary_surface_kind`, `semantic_answer_produced`, and `summary_route_boundary` so `--route-mode summary` is not mistaken for semantic QA.
- **[Codex]** Retrieval U-T-Y M4-M6 validation completed:
  - focused: `tests/test_evidence_pack.py`, `tests/test_retrieval_adapters.py`, `tests/test_ingestion_pipeline.py`, `tests/test_grounding.py tests/test_raw_material_store.py`, `tests/test_invariant_guards.py`, focused CLI retrieval/grounding/summary tests.
  - compile: `.venv/bin/python -m compileall -q src/swallow`
  - full: `.venv/bin/python -m pytest -q` -> `635 passed, 8 deselected, 10 subtests passed`
  - hygiene: `git diff --check` passed.
- **[Human]** Retrieval U-T-Y implementation committed:
  - `cda56d5 docs(plan): add retrieval u-t-y plan`
  - `bcb984d feat(retrieval): replace chat rerank with dedicated rerank adapter`
  - `0358114 feat(retrieval): add source policy evidence pack and summary surface`
  - `9f9764d docs(state): update retrieval u-t-y validation state`
- **[Codex]** Retrieval U-T-Y PR material prepared:
  - `pr.md` refreshed for this branch with context, implementation notes, test coverage, and review gate notes.
- **[Human]** AD1/V pilot committed on `feat/architecture-recomposition-ad1-v`:
  - `e449879 refactor(knowledge): add knowledge plane facade pilot`
  - `98313ed docs(state): update architecture recomposition pilot state`
- **[Codex]** Architecture Recomposition M5 AB query pilot completed:
  - added `src/swallow/application/queries/control_center.py` as a shared read-model layer for Control Center task list/detail/events/knowledge payloads.
  - kept `src/swallow/surface_tools/web/api.py` as the FastAPI adapter and compatibility import surface for existing Web API tests/callers.
  - added `tests/unit/application/test_control_center_queries.py` for the application query layer.
  - validation passed:
    - `.venv/bin/python -m pytest tests/unit/application/test_control_center_queries.py tests/test_web_api.py tests/test_sqlite_store.py -q` -> `26 passed`
    - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q` -> `25 passed`
    - `.venv/bin/python -m compileall -q src/swallow` -> passed
    - `.venv/bin/python -m pytest -q` -> `637 passed, 8 deselected, 10 subtests passed`
    - `git diff --check` -> passed
- **[Human]** M5 AB query pilot implementation committed:
  - `e36e854 refactor(application): add control center query pilot`
- **[Codex]** Roadmap / plan alignment completed:
  - `docs/roadmap.md` now marks AD as active execution rather than merely "current recommended next step".
  - `docs/plans/architecture-recomposition/plan.md` now distinguishes the AD program plan from the first implementation branch scope.
  - Current next step is M6 closeout / PR material / next subtrack selection.
- **[Codex]** Roadmap structure reorganized:
  - `docs/roadmap.md` now separates durable long-term optimization goals (`LTO-*`) from short-lived phase tickets.
  - completed / partially advanced old tickets now update their owning LTO state instead of remaining as awkward half-complete queue entries.
  - old candidate letters are no longer used as roadmap navigation; the near-term queue is expressed as closeout / PR, selected architecture subtrack, broad test/application/knowledge follow-up, and Wiki Compiler workflow.

进行中:

- **[Human/Codex]** Review the roadmap LTO reorganization and decide whether to prepare PR material for the current branch.

待执行:

- **[Human]** Commit the state / roadmap / plan alignment docs if accepted.
- **[Human/Codex]** Decide the next AD subtrack only after current branch M6 closeout / PR gate.

当前阻塞项:

- Waiting for Human review / commit of roadmap LTO reorganization docs.

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- tag message: `v1.5.0: raw material store boundary`
- 结论: tag release gate 已关闭;Retrieval U-T-Y 已 merge;当前处于 Architecture Recomposition first branch 的 M6 closeout / next subtrack selection gate。

## 当前下一步

1. **[Human]** Review roadmap / plan alignment docs.
2. **[Human]** Commit the docs if accepted.
3. **[Human/Codex]** Prepare M6 closeout / PR material or explicitly open a new subtrack gate.

```markdown
milestone_gate:
- current: architecture-recomposition-roadmap-lto-reorganization-complete
- active_branch: feat/architecture-recomposition-ad1-v
- previous_gate: Human merged Retrieval U-T-Y and requested direct next-stage implementation
- roadmap: Architecture Recomposition is tracked through LTO-3 and near-term phase tickets
- plan: docs/plans/architecture-recomposition/plan.md approved
- ad1: tests/conftest.py + tests/helpers/{workspace,cli_runner}.py added
- v_pilot: src/swallow/knowledge_retrieval/knowledge_plane.py facade added
- migration: truth_governance/store.py, governance.py, truth/knowledge.py migrated narrowly to facade-safe imports
- test_split: one CLI synthesis test moved to tests/integration/cli; one knowledge facade test added under tests/unit/knowledge
- guard_note: protected canonical writer persist_wiki_entry_from_record remains outside public facade after guard feedback
- committed_gate: AD1/V pilot committed as `e449879` + `98313ed`
- ab_pilot: Control Center task list/detail/events/knowledge read models moved from FastAPI adapter to `swallow.application.queries.control_center`
- ab_compatibility: `swallow.surface_tools.web.api` re-exports the same payload builders for existing callers
- ab_commit: `e36e854 refactor(application): add control center query pilot`
- validation: focused application/web/sqlite tests `26 passed`; invariant guards `25 passed`; compileall passed; full pytest `637 passed, 8 deselected, 10 subtests passed`; git diff --check passed
- roadmap_alignment: docs/roadmap.md now records AD first branch status and M6 gate
- roadmap_structure: docs/roadmap.md now separates long-term optimization goals from short-term phase tickets
- plan_alignment: docs/plans/architecture-recomposition/plan.md now separates program plan from first branch scope
- next_gate: Human review / commit docs, then M6 closeout / PR material
- reason: prevent AD program plan from being mistaken as implicit authorization for later subtrack implementation
```

## 当前产出物

- `README.md`(codex, 2026-04-30, v1.5.0 release snapshot)
- `current_state.md`(codex, 2026-04-30, v1.5.0 executed tag + R-entry checkpoint)
- `AGENTS.md`(codex, 2026-05-01, docs/engineering layer indexed)
- `.agents/shared/read_order.md`(codex, 2026-05-01, engineering docs added as contextual reads for refactor/TDD work)
- `docs/active_context.md`(codex, 2026-05-01, Architecture Recomposition M6 / roadmap-plan alignment state)
- `docs/plans/architecture-recomposition/plan.md`(codex, 2026-05-01, active AD program plan clarified with first-branch scope and M6 gate)
- `src/swallow/knowledge_retrieval/knowledge_plane.py`(codex, 2026-05-01, Knowledge Plane facade for migration-safe upper-layer imports)
- `src/swallow/application/__init__.py` / `src/swallow/application/queries/__init__.py`(codex, 2026-05-01, application layer package markers for AB pilot)
- `src/swallow/application/queries/control_center.py`(codex, 2026-05-01, Control Center task read models shared by interface adapters)
- `tests/conftest.py`(codex, 2026-05-01, shared src import setup for new layered tests)
- `tests/helpers/workspace.py` / `tests/helpers/cli_runner.py`(codex, 2026-05-01, minimal test helper foundation)
- `tests/unit/knowledge/test_knowledge_plane.py`(codex, 2026-05-01, Knowledge Plane facade compatibility coverage)
- `tests/unit/application/test_control_center_queries.py`(codex, 2026-05-01, application query read-model coverage)
- `tests/integration/cli/test_synthesis_commands.py`(codex, 2026-05-01, first CLI test moved into focused integration layer)
- `docs/concerns_backlog.md`(codex, 2026-04-30, release-doc debt resolved + R-entry blocker/design triage)
- `docs/design/INTERACTION.md`(codex, 2026-05-01, local UI runtime standard: Browser/Desktop UI via local FastAPI, CLI direct application layer)
- `docs/engineering/CODE_ORGANIZATION.md`(codex, 2026-05-01, long-term code organization convergence standard)
- `docs/engineering/GOF_PATTERN_ALIGNMENT.md`(codex, 2026-05-01, GoF-style responsibility language for system-design refactors)
- `docs/engineering/TEST_ARCHITECTURE.md`(codex, 2026-05-01, long-term test architecture and TDD harness standard)
- `docs/roadmap.md`(codex, 2026-05-01, reorganized around long-term optimization goals plus short-term phase tickets)
- `docs/concerns_backlog.md`(codex, 2026-05-01, Open concerns grouped into Active Open vs Roadmap-Bound and mapped to roadmap candidates)
- `docs/plans/candidate-r/plan.md`(codex, 2026-05-01, Candidate R design-doc observation plan)
- `docs/plans/candidate-r/observations.md`(codex, 2026-05-01, Candidate R P1/P2/P2b/P3/P3b + KNOWLEDGE dry-run/promotion observation summary)
- `docs/plans/candidate-r/closeout.md`(codex, 2026-05-01, Candidate R closeout and next-candidate recommendation)
- `docs/plans/retrieval-u-t-y/plan.md`(codex, 2026-05-01, unified U/T/Y retrieval implementation plan for `feat/retrieval-u-t-y`)
- `src/swallow/knowledge_retrieval/evidence_pack.py`(codex, 2026-05-01, EvidencePack-compatible retrieval serving view and source pointers)
- `tests/test_evidence_pack.py`(codex, 2026-05-01, EvidencePack grouping and source pointer resolution coverage)
- `pr.md`(codex, 2026-05-01, Retrieval U-T-Y PR body draft)
- `CLAUDE.md`(codex, 2026-05-01, Claude role narrowed to plan audit / PR review / tag evaluation)
- `.codex/session_bootstrap.md`(codex, 2026-05-01, Codex role expanded to plan definition via `plan.md`)
- `.agents/workflows/feature.md`(codex, 2026-05-01, feature workflow rewritten around `context_brief.md` + `plan.md` + `plan_audit.md`)
- `.agents/workflows/model_review.md`(codex, 2026-05-01, model review moved from legacy design artifacts to `plan.md` / `plan_audit.md`)
- `.agents/claude/role.md` / `.agents/claude/rules.md`(codex, 2026-05-01, Claude planning responsibilities reduced; review/audit responsibilities clarified)
- `.agents/codex/role.md` / `.agents/codex/rules.md`(codex, 2026-05-01, Codex planning + implementation ownership clarified)
- `.agents/shared/*.md`(codex, 2026-05-01, shared plan artifact and state sync conventions updated)
- `.claude/agents/*.md` + `.claude/skills/model-review/SKILL.md`(codex, 2026-05-01, subagent outputs and model review inputs updated for `plan.md`)
- `.agents/codex/templates/plan_template.md`(codex, 2026-05-01, new default phase plan template)
- `tests/test_run_task_subtasks.py`(codex, 2026-04-30, release preflight flake stabilization)
- `docs/plans/phase67/closeout.md`(codex, 2026-04-30, Phase 67 closeout)
- `docs/plans/phase68/closeout.md`(codex, 2026-04-30, Phase 68 closeout)
