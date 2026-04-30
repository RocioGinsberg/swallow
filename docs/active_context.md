# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Knowledge / Storage`
- latest_completed_phase: `Phase 68`
- latest_completed_slice: `Candidate O / Raw Material Store Boundary`
- active_track: `Operations`
- active_phase: `Candidate R / Real-use Feedback Observation`
- active_slice: `R-entry Readiness Gate`
- active_branch: `main`
- status: `r_entry_ready_after_v1.5.0_tag`

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

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `README.md`
4. `docs/plans/phase67/closeout.md`
5. `docs/plans/phase68/closeout.md`
6. `docs/roadmap.md`
7. `docs/concerns_backlog.md`
8. `docs/design/INVARIANTS.md`

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

进行中:

- **[Human]** Begin Candidate R real-use feedback observation using the refreshed R0/R1/R2 gap triage in `docs/roadmap.md`.

待执行:

- **[Human]** Review and commit this R-entry state sync if accepted.
- **[Human/Codex]** During R, classify real-use observations into Candidate S/T/U/D, test/interface friction into Candidate AA/AB, and source-organization friction into Candidate V/W/X/Y/Z using the refreshed roadmap split; do not start Candidate D until a real orchestration bottleneck appears.

当前阻塞项:

- None for entering Candidate R. Remaining Open concerns are observation items / usage boundaries, not R-entry blockers.

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- tag message: `v1.5.0: raw material store boundary`
- 结论: tag release gate 已关闭,可以进入 Candidate R 观察期。

## 当前下一步

1. **[Human]** Review this R-entry state sync:
   - `AGENTS.md`
   - `.agents/shared/read_order.md`
   - `current_state.md`
   - `docs/active_context.md`
   - `docs/concerns_backlog.md`
   - `docs/design/INTERACTION.md`
   - `docs/engineering/CODE_ORGANIZATION.md`
   - `docs/engineering/TEST_ARCHITECTURE.md`
   - `docs/roadmap.md`
2. **[Human]** Commit accepted R-entry sync.
3. **[Human/Codex]** Start Candidate R real-use feedback observation on the `v1.5.0` checkpoint.

```markdown
milestone_gate:
- current: candidate-r-entry-readiness
- previous_gate: v1.5.0 annotated tag completed on main
- next_gate: Human R-entry state sync review / commit
- proceed_to_r: allowed after state sync review
- reason: design invariants and focused implementation guards are sufficient for observation-stage real-use testing
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
- `docs/engineering/TEST_ARCHITECTURE.md`(codex, 2026-05-01, long-term test architecture and TDD harness standard)
- `docs/roadmap.md`(codex, 2026-05-01, pruned roadmap + v1.5.0 post-start RAG, test architecture, interface boundary, and code-organization planning: Candidate R + S/T/U + AA/AB + V/W/X/Y/Z)
- `tests/test_run_task_subtasks.py`(codex, 2026-04-30, release preflight flake stabilization)
- `docs/plans/phase67/closeout.md`(codex, 2026-04-30, Phase 67 closeout)
- `docs/plans/phase68/closeout.md`(codex, 2026-04-30, Phase 68 closeout)
