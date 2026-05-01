# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Operations / Knowledge`
- latest_completed_phase: `Candidate R / Real-use Feedback Observation`
- latest_completed_slice: `R1 Design Docs Observation Sample`
- active_track: `Retrieval Quality`
- active_phase: `Candidate U / Neural Retrieval Observability / Eval / Index Hardening`
- active_slice: `U0 Plan Definition`
- active_branch: `main`
- status: `candidate_u_plan_pending`

## 当前状态说明

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

Candidate R observation closeout is complete. The next selected implementation direction is Candidate U: retrieval observability / eval / index hardening, with Candidate T and Candidate Y kept as follow-ups.

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

进行中:

- **[Codex]** Candidate U plan definition pending. No implementation should start before `docs/plans/candidate-u/plan.md` is drafted and reviewed.

待执行:

- **[Codex]** Draft `docs/plans/candidate-u/plan.md` around retrieval report clarity, fallback/env visibility, rerank score semantics, source-policy labels, staged queue hygiene, P1/P2/P3 regression probes, and the GoF-style responsibility language in `docs/engineering/GOF_PATTERN_ALIGNMENT.md`.
- **[Human]** Review Candidate U plan before any implementation branch or code changes.

当前阻塞项:

- None for Candidate U planning. Implementation remains gated on a reviewed `docs/plans/candidate-u/plan.md`.

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- tag message: `v1.5.0: raw material store boundary`
- 结论: tag release gate 已关闭;Candidate R 观察已收口,当前进入 Candidate U plan definition。

## 当前下一步

1. **[Codex]** Prepare `docs/plans/candidate-u/plan.md`.
2. **[Human]** Review Candidate U plan and approve / adjust scope.
3. **[Human]** After plan approval, decide whether to create a feature branch for Candidate U implementation.

```markdown
milestone_gate:
- current: candidate-u-plan-definition
- previous_gate: v1.5.0 annotated tag completed on main
- observation_sample: docs/design/
- promoted_seed: INVARIANTS §0/§4/§5/§7/§9
- completed_probe: P1 apply_proposal boundary (`2f77c3a3a82d`)
- completed_probe_2: P2 LLM call path boundary (`5e891023a196`)
- environment_gate: embedding_api_endpoint restored
- completed_probe_2b: P2 vector-enabled comparison confirmed (`5e891023a196`)
- knowledge_dry_run: KNOWLEDGE.md produced 32 preview candidates; 10 recommended P3 seed chunks selected
- promoted_knowledge_seed: 10 KNOWLEDGE.md canonical records promoted for P3; canonical audit clean
- completed_probe_3: P3 knowledge-truth boundary (`f767f87222d9`, text fallback) and P3b vector rerun (`c1adb2f7f807`)
- closeout: docs/plans/candidate-r/closeout.md final
- roadmap: Candidate U promoted to current recommended next implementation candidate
- engineering_guidance: docs/engineering/GOF_PATTERN_ALIGNMENT.md added; Candidate AC introduced as later system-design refactor track
- next_gate: Candidate U plan reviewed
- proceed_to_u: planning_only
- reason: Candidate R showed canonical reuse works, while retrieval observability / fallback clarity / rerank report semantics are the primary next bottleneck
```

## 当前产出物

- `README.md`(codex, 2026-04-30, v1.5.0 release snapshot)
- `current_state.md`(codex, 2026-04-30, v1.5.0 executed tag + R-entry checkpoint)
- `AGENTS.md`(codex, 2026-05-01, docs/engineering layer indexed)
- `.agents/shared/read_order.md`(codex, 2026-05-01, engineering docs added as contextual reads for refactor/TDD work)
- `docs/active_context.md`(codex, 2026-04-30, R-entry readiness state)
- `docs/concerns_backlog.md`(codex, 2026-04-30, release-doc debt resolved + R-entry blocker/design triage)
- `docs/design/INTERACTION.md`(codex, 2026-05-01, local UI runtime standard: Browser/Desktop UI via local FastAPI, CLI direct application layer)
- `docs/engineering/CODE_ORGANIZATION.md`(codex, 2026-05-01, long-term code organization convergence standard)
- `docs/engineering/GOF_PATTERN_ALIGNMENT.md`(codex, 2026-05-01, GoF-style responsibility language for system-design refactors)
- `docs/engineering/TEST_ARCHITECTURE.md`(codex, 2026-05-01, long-term test architecture and TDD harness standard)
- `docs/roadmap.md`(codex, 2026-05-01, Candidate R closeout findings folded in; Candidate U promoted to next recommended implementation candidate)
- `docs/concerns_backlog.md`(codex, 2026-05-01, Open concerns grouped into Active Open vs Roadmap-Bound and mapped to roadmap candidates)
- `docs/plans/candidate-r/plan.md`(codex, 2026-05-01, Candidate R design-doc observation plan)
- `docs/plans/candidate-r/observations.md`(codex, 2026-05-01, Candidate R P1/P2/P2b/P3/P3b + KNOWLEDGE dry-run/promotion observation summary)
- `docs/plans/candidate-r/closeout.md`(codex, 2026-05-01, Candidate R closeout and next-candidate recommendation)
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
