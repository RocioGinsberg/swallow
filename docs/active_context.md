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
- active_track: `Release`
- active_phase: `v1.5.0 Tag Release`
- active_slice: `Release Doc Sync / Tag Prep`
- active_branch: `main`
- status: `v1.5.0_release_docs_ready_for_human_review`

## 当前状态说明

Phase 67 and Phase 68 have both been merged into `main`.

Current main checkpoint:

- `eb2c743 merge: code hygiene execute` — Phase 67 L+M+N cleanup + Candidate P module reorganization.
- `5cb08af merge: update knowledge plane raw material store` — Phase 68 Candidate O Raw Material Store boundary.

Latest executed public tag remains `v1.4.0`. The recommended pending release tag is `v1.5.0` because Phase 68 turns the roadmap Candidate O storage-backend-independence signal into implementation: `RawMaterialStore` interface, filesystem backend, stable `file://workspace/...` refs, and `artifact://...` evidence resolution.

Release-doc sync for `v1.5.0` is prepared in:

- `README.md`
- `current_state.md`
- `docs/active_context.md`
- `docs/concerns_backlog.md`
- `docs/roadmap.md`

No tag command has been executed yet.

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
- **[Codex]** `v1.5.0` release-doc sync prepared:
  - `README.md` release snapshot updated from `v1.4.0` to `v1.5.0`
  - `current_state.md` updated to Phase 68 main checkpoint with pending release tag
  - `docs/active_context.md` updated to tag release gate state
  - `docs/concerns_backlog.md` moved the old release-doc sync debt to Resolved
  - `docs/roadmap.md` factually synced Candidate L/M/N/P/O completion and pending `v1.5.0`
- **[Codex]** Release preflight exposed the known subtask timeout wall-clock flake; stabilized
  `tests/test_run_task_subtasks.py` by removing the brittle elapsed-time assertion while keeping artifact/event behavior assertions.

进行中:

- **[Human]** Review release docs before release commit and annotated tag.

待执行:

- **[Human]** Commit test stabilization separately from release docs.
- **[Human]** Commit release docs on `main`.
- **[Human]** Create annotated tag `v1.5.0`.
- **[Human]** Push `main` and tags.
- **[Codex]** After tag completion, update `docs/active_context.md` and `current_state.md` from pending tag to executed tag.

当前阻塞项:

- Waiting for Human release-doc review, commit, and tag execution.

## Tag 建议

- 建议: 打 tag
- 建议版本号: `v1.5.0`
- 理由: Phase 67 是内部 hygiene / module reorganization,单独不需要 tag;Phase 68 实装 `RawMaterialStore` raw-material 边界后,构成从 `v1.4.0` 治理闭合进入 storage-abstracted knowledge plane 的稳定 checkpoint。
- 等待条件: Human review release docs, commit, then create annotated tag.

## 当前下一步

1. **[Human]** Review release docs:
   - `README.md`
   - `current_state.md`
   - `docs/active_context.md`
   - `docs/concerns_backlog.md`
   - `docs/roadmap.md`
2. **[Human]** Commit test stabilization:
   - `test(orchestration): stabilize subtask timeout isolation`
3. **[Human]** Commit release docs:
   - `docs(release): sync v1.5.0 release docs`
4. **[Human]** Create annotated tag:
   - `git tag -a v1.5.0 -m "v1.5.0: raw material store boundary"`
5. **[Codex]** Sync tag result after Human confirms tag completed.

```markdown
milestone_gate:
- current: v1.5.0-release-doc-sync
- previous_gate: Phase 67 and Phase 68 merged into main
- next_gate: Human release-doc review / commit / annotated tag
- proceed_to_tag_result_sync: after Human confirms tag completed
- reason: tag commands are Human-owned; Codex only prepares release files
```

## 当前产出物

- `README.md`(codex, 2026-04-30, v1.5.0 release snapshot)
- `current_state.md`(codex, 2026-04-30, v1.5.0 pending release checkpoint)
- `docs/active_context.md`(codex, 2026-04-30, tag release gate state)
- `docs/concerns_backlog.md`(codex, 2026-04-30, release-doc debt resolved)
- `docs/roadmap.md`(codex, 2026-04-30, post-merge factual sync)
- `tests/test_run_task_subtasks.py`(codex, 2026-04-30, release preflight flake stabilization)
- `docs/plans/phase67/closeout.md`(codex, 2026-04-30, Phase 67 closeout)
- `docs/plans/phase68/closeout.md`(codex, 2026-04-30, Phase 68 closeout)
