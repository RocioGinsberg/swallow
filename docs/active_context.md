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
- active_track: `Knowledge / Storage`
- active_phase: `Phase 68`
- active_slice: `Closeout / PR Merge Prep`
- active_branch: `feat/phase68-raw-material-store`
- status: `phase68_complete_pending_phase67_then_phase68_merge`

## 当前状态说明

Phase 67 implementation is complete on `feat/phase67-hygiene-io-cli-cleanup` and should be merged before Phase 68.

Phase 68 starts as a stacked branch from the current Phase 67 HEAD because Phase 67 has not yet been merged into
`main` in this workspace. Merge order should be:

1. Merge Phase 67 first.
2. Rebase or retarget Phase 68 if needed.
3. Merge Phase 68 after its slice gates complete.

Phase 68 implements Candidate O from `docs/roadmap.md` as a narrow Raw Material Store boundary:

- S1: raw material interface, URI parser, filesystem backend, focused tests.
- S2: ingestion migration to stable source refs.
- S3: artifact evidence reference normalization.
- Closeout / PR prep: complete; `pr.md` now describes Phase 68.

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
8. `docs/plans/phase68/closeout.md`
9. `docs/plans/phase67/codex_review_notes_candidate_p.md`

## 当前推进

已完成:

- **[Codex]** Phase 67 PR body draft was refreshed earlier; `pr.md` is now updated for Phase 68.
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
- **[Human]** Phase 68 S2 commits completed:
  - `2f04b63 refactor(phase68-s2): route ingestion through raw material store`
  - `d135001 docs(phase68-s2): record ingestion raw material gate`
- **[Codex]** Phase 68 S3 implementation completed:
  - routed librarian artifact evidence existence checks through `FilesystemRawMaterialStore`
  - normalized legacy `.swl/tasks/<task_id>/artifacts/<path>` refs internally to `artifact://...`
  - accepted already-normalized `artifact://...` refs
  - preserved persisted `artifact_ref` values and Knowledge Truth schema
  - wrote `docs/plans/phase68/codex_review_notes_s3.md`
  - focused verification: `16 passed`
  - invariant guard verification: `1 passed`
  - full pytest: `622 passed, 8 deselected, 10 subtests passed`
- **[Human]** Phase 68 S3 commits completed:
  - `550f3dc refactor(phase68-s3): normalize artifact raw material refs`
  - `6c4545f docs(phase68-s3): record artifact raw material gate`
- **[Codex]** Phase 68 closeout / PR prep completed:
  - wrote `docs/plans/phase68/closeout.md`
  - updated ignored `pr.md` to Phase 68 PR body
  - synchronized `docs/active_context.md` and `current_state.md`

进行中:

- **[Human]** Merge Phase 67 first, then merge Phase 68.

待执行:

- **[Human]** Push / PR / merge Phase 67.
- **[Human]** Rebase or retarget Phase 68 if needed after Phase 67 reaches `main`.
- **[Human]** Push / PR / merge Phase 68 using updated `pr.md`.
- **[Codex]** After merges, perform post-merge state sync if requested.

当前阻塞项:

- Phase 68 must wait for Phase 67 to merge first.

## 当前下一步

1. **[Human]** Merge Phase 67.
2. **[Human]** Rebase / retarget Phase 68 if needed.
3. **[Human]** Merge Phase 68.
4. **[Codex]** Sync post-merge state when Human confirms merge results.

```markdown
milestone_gate:
- current: phase68-closeout-merge-prep
- next_gate: Human merge Phase 67, then Human merge Phase 68
- proceed_to_post_merge_sync: after Human confirms merges
- reason: Phase 68 is stacked on Phase 67 and must not merge first
```

## 当前产出物

- `docs/plans/phase68/kickoff.md`(codex, 2026-04-30, Phase 68 kickoff)
- `docs/plans/phase68/breakdown.md`(codex, 2026-04-30, Phase 68 slice breakdown)
- `docs/plans/phase68/codex_review_notes_s1.md`(codex, 2026-04-30, S1 review notes)
- `docs/plans/phase68/codex_review_notes_s2.md`(codex, 2026-04-30, S2 review notes)
- `docs/plans/phase68/codex_review_notes_s3.md`(codex, 2026-04-30, S3 review notes)
- `docs/plans/phase68/closeout.md`(codex, 2026-04-30, Phase 68 closeout)
- `src/swallow/knowledge_retrieval/raw_material.py`(codex, 2026-04-30, S1 implementation)
- `tests/test_raw_material_store.py`(codex, 2026-04-30, S1 tests)
- `src/swallow/knowledge_retrieval/ingestion/pipeline.py`(codex, 2026-04-30, S2 implementation)
- `src/swallow/surface_tools/librarian_executor.py`(codex, 2026-04-30, S3 implementation)
- `pr.md`(codex, ignored PR body draft for Phase 68)
- `docs/active_context.md`(codex, 2026-04-30, Phase 68 closeout / merge-prep state)
