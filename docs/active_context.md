# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Knowledge Authoring`
- latest_completed_phase: `lto-1-wiki-compiler-second-stage`
- latest_completed_slice: `merged to main at 21f8dc8; roadmap synced at 25f7848`
- active_track: `Retrieval Quality`
- active_phase: `lto-2-retrieval-quality-evidence-serving`
- active_slice: `M3 retrieval / EvidencePack dedup`
- active_branch: `feat/lto-2-retrieval-quality-evidence-serving`
- status: `lto2_m3_validation_passed_waiting_human_commit`

## 当前状态说明

当前 git 分支为 `feat/lto-2-retrieval-quality-evidence-serving`。`docs/roadmap.md` 已把 LTO-1 Wiki Compiler 第二阶段标为完成,并将下一轮 Direction Gate 的最强候选指向 **LTO-2 retrieval quality 增量**。

本轮计划按 roadmap §三 / §五 的最高优先级信号起草:消化 LTO-1 stage 2 留下的 cross-candidate evidence dedup 风险,并把它扩展为 bounded retrieval / EvidencePack / source grounding quality increment。

Human Plan Gate 已通过,实现分支已创建。当前 M3 已完成实现与 focused validation,等待 Human milestone commit:

- Codex 已产出 `docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md`。
- Claude / design-auditor 已产出 `docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md`(has-concerns;0 blockers / 5 concerns / 2 nits)。
- Codex 已吸收 C1-C5 / N1-N2 到 `plan.md`。
- Human 已提交 plan/audit absorption commit `8878fd7 docs(plan): absorb lto-2 retrieval audit`。
- M1 Source-anchor identity contract 已提交为 `f9b683a feat(wiki): add source anchor evidence identity`。
- M2 Governed evidence dedup on promotion 已提交为 `9b0a381 feat(wiki): dedupe source evidence on promotion`。
- M3 Retrieval / EvidencePack dedup 已完成实现与 focused validation,待 Human 审阅提交。

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `docs/roadmap.md`
4. `docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md`
5. `docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md`
6. `docs/concerns_backlog.md`
7. `docs/design/INVARIANTS.md`
8. `docs/design/KNOWLEDGE.md`
9. `docs/design/DATA_MODEL.md`
10. `docs/design/HARNESS.md`
11. `docs/engineering/CODE_ORGANIZATION.md`
12. `docs/engineering/TEST_ARCHITECTURE.md`
13. `docs/engineering/ADAPTER_DISCIPLINE.md`
14. `docs/plans/retrieval-u-t-y/plan.md`
15. `docs/plans/lto-1-wiki-compiler-second-stage/closeout.md`
16. `docs/plans/lto-1-wiki-compiler-second-stage/review_comments.md`

## 当前推进

已完成:

- **[Human]** LTO-1 Wiki Compiler 第二阶段已 merge 到 `main` at `21f8dc8 Knowledge Authoring / LLM Wiki Compiler(authoring specialist)`。
- **[Claude / roadmap-updater]** post-merge roadmap 已同步 at `25f7848 docs(state): update roadmap`;roadmap 当前近期队列为空,Direction Gate 候选中 LTO-2 retrieval quality 优先级最高。
- **[Codex]** 已阅读 roadmap / active state / LTO-2 相关设计与现有 retrieval/evidence 实现,产出 LTO-2 plan。
- **[Codex]** 已完成 M0 plan/state sync:`docs/active_context.md` 与 `current_state.md` 已切到 LTO-2 plan gate 状态。
- **[Claude / design-auditor]** 已产出 `plan_audit.md`:has-concerns;0 blockers / 5 concerns / 2 nits。
- **[Codex]** 已吸收 audit:
  - C1/C2:固定 `source-anchor-v1` canonical JSON hash 输入、5 字段顺序、`heading_path` list/string 归一化。
  - C3/N1:固定 cross-task lookup 使用 `knowledge_object_exists(base_dir, evidence-src-<key>)`;不做 legacy evidence row backfill。
  - C4:固定 `derived_from` relation id 改为 source object + evidence id pair hash。
  - C5:固定 `source_anchor_key` 由 retrieval pipeline 写入 `RetrievalItem.metadata`,EvidencePack 不做 store lookup。
  - N2:固定 M4 excerpt 来源为 stored `entry_json["preview"]`,不做 fresh raw material resolution。
- **[Human]** Plan Gate 已通过并切至 `feat/lto-2-retrieval-quality-evidence-serving`;plan/audit absorption 已提交为 `8878fd7 docs(plan): absorb lto-2 retrieval audit`。
- **[Codex]** 完成 M1 Source-anchor identity contract:
  - 新增 `source-anchor-v1` canonical JSON identity helper,hash 输入为 `source_ref/content_hash/parser_version/span/heading_path` 五字段。
  - `heading_path` list/string 统一归一化为 ` > ` join;空 `span` 可由 `line_start/line_end` fallback 为 `line:<start>-<end>`。
  - source-pack evidence entry 改为 stable `evidence-src-<source_anchor_key>` id,并写入 `source_anchor_key/source_anchor_version` metadata。
  - Knowledge Plane facade 新增 `build_source_anchor_identity()` wrapper。
- **[Human]** M1 milestone 已提交:`f9b683a feat(wiki): add source anchor evidence identity`。
- **[Codex]** 完成 M2 Governed evidence dedup on promotion:
  - `materialize_source_evidence_from_canonical_record()` 先用 `knowledge_object_exists(base_dir, evidence-src-<key>)` 做跨 task lookup。
  - 已存在的 evidence object 不再在当前 task 重写;仍返回同一个 `source_evidence_ids`。
  - 同一 source_pack 内重复 evidence id 会去重。
  - `derived_from` relation id 改为 `derived-from-v1` source/evidence pair hash;同一 source/evidence pair upsert 到同一 relation row,不同 wiki 指向同一 evidence 产生不同 relation row。
- **[Human]** M2 milestone 已提交:`9b0a381 feat(wiki): dedupe source evidence on promotion`。

已验证待提交:

- **[Codex]** M3 Retrieval / EvidencePack dedup:
  - retrieval item metadata 传播 `source_anchor_key/source_anchor_version/content_hash/parser_version/span/heading_path/source_pack_reference/source_pack_index`。
  - EvidencePack 按 anchor metadata 去重 supporting evidence / fallback hits / source pointers,并在 summary 中暴露 suppressed counts。
  - relation expansion 多路径命中同一对象时保留单条结果,并记录 `expansion_path_count` / `dedup_reason`。

待执行:

- **[Human]** 审阅 M3 diff 并提交 milestone。

## 当前验证

计划产出后需完成:

```bash
git diff --check
git status --short --branch
```

最近结果:

- plan/audit absorption 后 `git diff --check` passed。
- 当前分支为 `feat/lto-2-retrieval-quality-evidence-serving`。
- M1 focused validation:
  - `.venv/bin/python -m pytest tests/test_knowledge_store.py tests/test_knowledge_plane_facade.py -q` -> `10 passed`
  - `.venv/bin/python -m pytest tests/test_governance.py tests/integration/cli/test_wiki_commands.py -q -k "source_evidence or materializes_source_pack"` -> `2 passed, 15 deselected`
  - `.venv/bin/python -m pytest tests/eval/test_wiki_compiler_second_stage_quality.py::test_second_stage_eval_source_pack_materializes_matching_evidence_objects -m eval -q` -> `1 passed`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q -k "evidence_objectization or knowledge_plane"` -> `5 passed, 35 deselected`
  - `.venv/bin/python -m pytest tests/test_governance.py tests/test_knowledge_relations.py tests/test_sqlite_store.py -q` -> `38 passed`
  - `.venv/bin/python -m pytest tests/integration/cli/test_wiki_commands.py tests/eval/test_wiki_compiler_second_stage_quality.py -m "not eval" -q` -> `5 passed, 4 deselected`
  - `.venv/bin/python -m compileall -q src/swallow` passed
  - `git diff --check` passed
- M2 milestone commit:`9b0a381 feat(wiki): dedupe source evidence on promotion`
- M1 milestone commit:`f9b683a feat(wiki): add source anchor evidence identity`
- M2 focused validation:
  - `.venv/bin/python -m pytest tests/test_knowledge_store.py -q` -> `5 passed`
  - `.venv/bin/python -m pytest tests/test_governance.py -q -k "source_evidence or reuses_source_evidence"` -> `2 passed, 11 deselected`
  - `.venv/bin/python -m pytest tests/integration/cli/test_wiki_commands.py -q -k materializes_source_pack` -> `1 passed, 4 deselected`
  - `.venv/bin/python -m pytest tests/test_knowledge_relations.py -q` -> `11 passed`
  - `.venv/bin/python -m pytest tests/test_governance.py tests/test_knowledge_relations.py tests/test_sqlite_store.py -q` -> `39 passed`
  - `.venv/bin/python -m pytest tests/integration/cli/test_wiki_commands.py tests/eval/test_wiki_compiler_second_stage_quality.py -m "not eval" -q` -> `5 passed, 4 deselected`
  - `.venv/bin/python -m pytest tests/eval/test_wiki_compiler_second_stage_quality.py::test_second_stage_eval_source_pack_materializes_matching_evidence_objects -m eval -q` -> `1 passed`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q` -> `40 passed`
  - `.venv/bin/python -m pytest tests/integration/http/test_knowledge_browse_routes.py tests/unit/application/test_knowledge_queries.py -q` -> `7 passed`
  - `.venv/bin/python -m compileall -q src/swallow` passed
  - `git diff --check` passed
- M3 focused validation:
  - `.venv/bin/python -m pytest tests/test_evidence_pack.py tests/test_retrieval_adapters.py -q` -> `33 passed`
  - `.venv/bin/python -m pytest tests/test_grounding.py -q` -> `6 passed`
  - `.venv/bin/python -m pytest tests/unit/orchestration/test_task_report_module.py tests/unit/orchestration/test_harness_facade.py -q` -> `8 passed`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q -k knowledge_plane` -> `4 passed, 36 deselected`
  - `.venv/bin/python -m pytest tests/test_knowledge_store.py -q` -> `5 passed`
  - `.venv/bin/python -m pytest tests/integration/cli/test_wiki_commands.py -q -k materializes_source_pack` -> `1 passed, 4 deselected`
  - `.venv/bin/python -m compileall -q src/swallow` passed
  - `git diff --check` passed

本 phase 默认实现期验证计划已写入 `docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md` §Validation Plan。

## 当前阻塞项

- 无。

## Tag 状态

- 最新已执行 tag: **`v1.8.0`**
- tag target: `d6f2442 docs(release): sync v1.8.0 release docs`
- 标记意义: **LTO-1 Wiki Compiler 第一阶段落地**。
- LTO-1 第二阶段已 merge,但 roadmap / review 建议不单独 cut tag。
- 下一 tag: 无 pending decision;后续可在 LTO-2 retrieval quality / Wiki Compiler 闭环成熟后再评估 `v1.9.0`。

## 当前下一步

1. **[Human]** 审阅 M3 diff 并提交 milestone。
2. **[Codex]** Human 提交后同步状态进入 M4 Operator report quality。

```markdown
plan_gate:
- latest_completed_phase: lto-1-wiki-compiler-second-stage
- latest_completed_merge: 21f8dc8 Knowledge Authoring / LLM Wiki Compiler(authoring specialist)
- latest_roadmap_sync: 25f7848 docs(state): update roadmap
- latest_release_tag: v1.8.0 at d6f2442 docs(release): sync v1.8.0 release docs
- active_branch: feat/lto-2-retrieval-quality-evidence-serving
- active_track: Retrieval Quality
- active_phase: lto-2-retrieval-quality-evidence-serving
- active_slice: M3 retrieval / EvidencePack dedup
- status: lto2_m3_validation_passed_waiting_human_commit
- roadmap: docs/roadmap.md §三 Direction Gate candidate + §五 recommendation;LTO-2 retrieval quality has strongest current trigger
- plan: docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md (Codex; status: review; audit absorbed)
- plan_audit: docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md (Claude/design-auditor; has-concerns; 0 blockers / 5 concerns / 2 nits)
- concerns_backlog: docs/concerns_backlog.md (LTO-1 stage 2 source-anchor dedup risk is Roadmap-Bound to LTO-2; task-scoped knowledge_evidence schema mismatch remains Active Open/deferred)
- recommended_implementation_branch: feat/lto-2-retrieval-quality-evidence-serving
- next_gate: Human M3 milestone commit -> Codex sync state to M4
```

## 当前产出物

- `docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md`(codex, 2026-05-04, LTO-2 retrieval quality / evidence serving phase plan;audit absorbed with explicit C1-C5/N1-N2 decisions)
- `docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md`(claude, 2026-05-04, has-concerns — 0 blockers / 5 concerns / 2 nits; C1–C5 / N1-N2 absorbed into plan.md)
- `src/swallow/knowledge_retrieval/_internal_knowledge_store.py`(codex, 2026-05-04, M1 source-anchor identity helper + stable source-pack evidence ids + metadata)
- `src/swallow/knowledge_retrieval/knowledge_plane.py`(codex, 2026-05-04, M1 `build_source_anchor_identity` facade wrapper)
- `tests/test_knowledge_store.py`(codex, 2026-05-04, M1 source-anchor normalization/key and materialization metadata coverage)
- `tests/test_governance.py` + `tests/integration/cli/test_wiki_commands.py` + `tests/eval/test_wiki_compiler_second_stage_quality.py`(codex, 2026-05-04, M1 expected stable evidence id sync)
- `src/swallow/knowledge_retrieval/_internal_knowledge_store.py`(codex, 2026-05-04, M2 cross-task evidence id lookup/reuse)
- `src/swallow/truth_governance/truth/knowledge.py`(codex, 2026-05-04, M2 source/evidence pair-based `derived_from` relation id)
- `tests/test_knowledge_store.py` + `tests/test_governance.py` + `tests/integration/cli/test_wiki_commands.py`(codex, 2026-05-04, M2 cross-candidate evidence reuse and relation id coverage)
- `src/swallow/knowledge_retrieval/retrieval.py`(codex, 2026-05-04, M3 source-anchor metadata propagation + supporting_evidence policy + relation expansion duplicate-path metadata)
- `src/swallow/knowledge_retrieval/evidence_pack.py`(codex, 2026-05-04, M3 metadata-only dedup for supporting evidence / fallback hits / source pointers)
- `tests/test_evidence_pack.py`(codex, 2026-05-04, M3 EvidencePack source-anchor dedup coverage)
- `tests/test_retrieval_adapters.py`(codex, 2026-05-04, M3 retrieval metadata propagation + relation expansion dedup coverage)
- `docs/active_context.md`(codex, 2026-05-04, M3 validation passed; waiting Human milestone commit)
- `current_state.md`(codex, 2026-05-04, recovery checkpoint sync to M3 validation-passed state)
