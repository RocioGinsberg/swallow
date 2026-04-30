# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Refactor / Hygiene`
- latest_completed_phase: `Phase 67`
- latest_completed_slice: `L+M+N Cleanup + Candidate P Module Reorganization + CLI Reference Sync`
- active_track: `Knowledge / Storage`
- active_phase: `Phase 68`
- active_slice: `S2 / Ingestion Raw Material Store Migration`
- active_branch: `feat/phase68-raw-material-store`
- status: `phase68_s2_complete_pending_human_review`

## 当前状态说明

Phase 67 implementation is complete on `feat/phase67-hygiene-io-cli-cleanup` and ready for Human push / PR / merge
handling. The Phase 67 PR body draft has been refreshed in ignored file `pr.md`.

Phase 68 starts as a stacked branch from the current Phase 67 HEAD because Phase 67 has not yet been merged into
`main` in this workspace. Merge order should be:

1. Merge Phase 67 first.
2. Rebase or retarget Phase 68 if needed.
3. Merge Phase 68 after its slice gates complete.

Phase 68 implements Candidate O from `docs/roadmap.md` as a narrow Raw Material Store boundary:

- S1: raw material interface, URI parser, filesystem backend, focused tests.
- S2: ingestion migration to stable source refs. Completed and waiting for Human review / manual commit.
- S3: artifact evidence reference normalization.

Phase 68 must not modify:

- `docs/design/INVARIANTS.md`
- `docs/design/DATA_MODEL.md`
- `docs/design/KNOWLEDGE.md`
- Knowledge Truth schema
- retrieval source type semantics

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `docs/plans/phase68/kickoff.md`
3. `docs/plans/phase68/breakdown.md`
4. `docs/roadmap.md`
5. `docs/design/INVARIANTS.md`
6. `docs/design/KNOWLEDGE.md`
7. `docs/plans/phase67/closeout.md`
8. `docs/plans/phase67/codex_review_notes_candidate_p.md`

## 当前推进

已完成:

- **[Codex]** Phase 67 PR body draft refreshed in `pr.md`.
- **[Codex]** Phase 68 branch created: `feat/phase68-raw-material-store`.
- **[Codex]** Phase 68 kickoff / breakdown created with Human direction to proceed without a separate Claude design
  gate.
- **[Codex]** Phase 68 S1 implementation completed:
  - added `src/swallow/knowledge_retrieval/raw_material.py`
  - added `tests/test_raw_material_store.py`
  - wrote `docs/plans/phase68/codex_review_notes_s1.md`
  - focused verification: `10 passed`
  - adjacent verification: `24 passed`
  - `git diff --check`: passed
  - `git diff -- docs/design`: no output
  - full pytest: `620 passed, 8 deselected, 10 subtests passed`
- **[Human]** Phase 68 S1 commits completed:
  - `97ab87d feat(phase68-s1): add raw material store interface`
  - `c5affe7 docs(phase68-s1): record raw material store gate`
- **[Codex]** Phase 68 S2 implementation completed:
  - routed local/session ingestion reads through `FilesystemRawMaterialStore`
  - changed new in-workspace ingestion refs to `file://workspace/<relative-path>`
  - preserved out-of-workspace source refs as absolute file URIs
  - kept clipboard and operator-note ingestion refs unchanged
  - wrote `docs/plans/phase68/codex_review_notes_s2.md`
  - focused verification: `20 passed`
  - invariant-adjacent verification: `21 passed`
  - CLI verification: `241 passed, 10 subtests passed`
  - full pytest: `621 passed, 8 deselected, 10 subtests passed`

进行中:

- **[Human]** Review Phase 68 S2 and manually commit if accepted.

待执行:

- **[Human]** Review S2 and manually commit if accepted.
- **[Codex]** Start S3 only after the S2 commit gate is accepted.

当前阻塞项:

- Waiting for Human review / manual commit gate for S2.
- Phase 68 is stacked on Phase 67 until Human merges Phase 67.

## 当前下一步

1. **[Human]** Review S2 diff.
2. **[Human]** Commit S2 if accepted.
3. **[Codex]** Continue to S3 after Human confirms commit.

```markdown
milestone_gate:
- current: phase68-s2-ingestion-raw-material-store
- next_gate: Human review / manual commit
- proceed_to_s3: after Human accepts and commits S2
- reason: ingestion source_ref semantics are now a persisted raw material boundary
```

## 当前产出物

- `docs/plans/phase68/kickoff.md`(codex, 2026-04-30, Phase 68 kickoff)
- `docs/plans/phase68/breakdown.md`(codex, 2026-04-30, Phase 68 slice breakdown)
- `docs/plans/phase68/codex_review_notes_s1.md`(codex, 2026-04-30, S1 review notes)
- `docs/plans/phase68/codex_review_notes_s2.md`(codex, 2026-04-30, S2 review notes)
- `src/swallow/knowledge_retrieval/raw_material.py`(codex, 2026-04-30, S1 implementation)
- `tests/test_raw_material_store.py`(codex, 2026-04-30, S1 tests)
- `src/swallow/knowledge_retrieval/ingestion/pipeline.py`(codex, 2026-04-30, S2 implementation)
- `pr.md`(codex, ignored PR body draft for Phase 67)
- `docs/active_context.md`(codex, 2026-04-30, Phase 68 S2 commit-gate state)
