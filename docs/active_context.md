# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Retrieval Quality`
- latest_completed_phase: `lto-2-retrieval-quality-evidence-serving`
- latest_completed_slice: `post-merge state sync committed at a3c1844`
- active_track: `Test Architecture`
- active_phase: `lto-4-test-architecture`
- active_slice: `M1 CLI command-family split complete; waiting Human commit`
- active_branch: `feat/lto-4-test-architecture`
- status: `lto4_m1_complete_waiting_human_commit`

## 当前状态说明

当前 git 分支为 `feat/lto-4-test-architecture`。LTO-4 Test Architecture 按压缩流程推进:不走完整 plan / plan_audit / review / closeout,以 multi-commit + git log + `docs/active_context.md` 记录为准,不 cut tag。authoritative boundary 为本文 "待执行" 中的 LTO-4 条目;若实现中出现该条目未覆盖的问题,先停下请 Human / Claude 决策。

LTO-2 Retrieval Quality / Evidence Serving 已 merge 到 `main` at `03744f0 Retrieval Quality / Evidence Serving`;post-merge state sync 已提交为 `a3c1844 docs(state): sync lto2 post-merge state`。

本轮计划按 roadmap §三 / §五 的最高优先级信号起草:消化 LTO-1 stage 2 留下的 cross-candidate evidence dedup 风险,并把它扩展为 bounded retrieval / EvidencePack / source grounding quality increment。

LTO-2 已完成并 merge:

- Codex 已产出 `docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md`。
- Claude / design-auditor 已产出 `docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md`(has-concerns;0 blockers / 5 concerns / 2 nits)。
- Codex 已吸收 C1-C5 / N1-N2 到 `plan.md`。
- Human 已提交 plan/audit absorption commit `8878fd7 docs(plan): absorb lto-2 retrieval audit`。
- M1 Source-anchor identity contract 已提交为 `f9b683a feat(wiki): add source anchor evidence identity`。
- M2 Governed evidence dedup on promotion 已提交为 `9b0a381 feat(wiki): dedupe source evidence on promotion`。
- M3 Retrieval / EvidencePack dedup 已提交为 `1590e62 feat(retrieval): dedupe evidence serving by source anchor`。
- M4 Operator report quality 已提交为 `62a2a7d feat(retrieval): surface source-anchor evidence quality`。
- M5 Eval, guards, closeout prep 已提交为 `d6967f3 test(retrieval): add lto2 evidence quality eval`。
- Claude review 已产出 `docs/plans/lto-2-retrieval-quality-evidence-serving/review_comments.md`: `recommend-merge`;0 blockers / 1 concern(closeout missing,已由 closeout.md 吸收) / 1 nit(active_context cosmetic,后续大修处理)。
- Codex 已产出 `docs/plans/lto-2-retrieval-quality-evidence-serving/closeout.md` 并同步 `pr.md` 到 review-passed 状态。
- Human 已完成 closeout commit `e8059d6 docs(closeout): finalize lto2 retrieval quality review`。
- Human 已 merge 到 `main` at `03744f0 Retrieval Quality / Evidence Serving`。

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
- **[Claude / roadmap-updater]** LTO-1 stage 2 post-merge roadmap 已同步 at `25f7848 docs(state): update roadmap`;当时 Direction Gate 候选中 LTO-2 retrieval quality 优先级最高,现已由本轮 LTO-2 消化。
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

已完成:

- **[Codex]** M3 Retrieval / EvidencePack dedup:
  - retrieval item metadata 传播 `source_anchor_key/source_anchor_version/content_hash/parser_version/span/heading_path/source_pack_reference/source_pack_index`。
  - EvidencePack 按 anchor metadata 去重 supporting evidence / fallback hits / source pointers,并在 summary 中暴露 suppressed counts。
  - relation expansion 多路径命中同一对象时保留单条结果,并记录 `expansion_path_count` / `dedup_reason`。
- **[Human]** M3 milestone 已提交:`1590e62 feat(retrieval): dedupe evidence serving by source anchor`。

已完成:

- **[Codex]** M4 Operator report quality:在 retrieval/source grounding report 中展示 source anchor key、source pointer status、dedup counts、stored preview excerpt 与 unresolved/missing reason。
- **[Human]** M4 milestone 已提交:`62a2a7d feat(retrieval): surface source-anchor evidence quality`。

已完成:

- **[Codex]** M5 Eval, guards, closeout prep:
  - 新增 deterministic LTO-2 retrieval quality eval,覆盖 duplicate source anchors、hash input discrimination、relation expansion dedup、stored preview reporting。
  - 新增 narrow invariant guard,确保 source-pack evidence id 继续使用 `evidence-src-<source_anchor_key>`。
  - 完成 focused validation 与默认 pytest,为 Human milestone commit 后的 PR review 做准备。

待执行:

- **[Human]** 审阅并提交 post-merge state sync。
- **[Human]** Tag 决策:Claude review 建议**不为本阶段单独 cut tag**(LTO-2 是 v1.8.0 能力的 retrieval quality 增量,非新能力跃迁)。可累积 Wiki Compiler 第三阶段 / LTO-4 / D2 driven ports 后续 phase 后 cut **v1.9.0**,语义 = "Knowledge Authoring 闭环 + Retrieval Quality 增量 + 工程纪律稳定"。最终 Human 决定。
- **[Codex]** 启动 **LTO-4 Test Architecture(压缩流程,与 D5 / Hygiene Bundle 同型,不走完整 plan/audit/review/closeout)**。**Direction Gate 决议(2026-05-04 Claude+Human)**:LTO-4 真实价值是**结构 + helpers**,不是性能。
  - **现状量化基线**(2026-05-04 measure):全量 802 tests / 19 deselected / **126 秒(2 分 6 秒)** / 平均 0.16 秒/test;最慢 20 个 test 占 27.45 秒(21.7%),全部是 `test_cli.py` 与 `test_retrieval_adapters.py` 中的真 integration test(跑完整 task lifecycle / retrieval pipeline);`test_cli.py` 单文件 11156 行 / 557 KB;`tests/helpers/` 现仅 2 个 helper(`cli_runner` + `workspace`)。
  - **必做**(真有价值):
    - **拆 `tests/test_cli.py` 11156 行 → `tests/integration/cli/test_<family>_commands.py` 多文件**(按 command family 拆:task / knowledge / wiki / proposal / route / system / etc)。**纯 mechanical move,不改测试逻辑,不删任何 test**。收益 = editor 友好 / grep 友好 / merge 冲突低 / `pytest -k` 只 import 相关文件。
    - **`tests/helpers/` 加 `builders.py` + `assertions.py`**(当前 cli test 每个文件自己写 ~10 行 setup,抽出 `WorkspaceBuilder` / `TaskBuilder` / `KnowledgeBuilder` 等)。**新增不删除**,test 主体不动。收益 = fixture 重复减少 30-40%(注意:不是 test 数量减少)。
    - **`tests/test_invariant_guards.py` 1435 行 guard helpers 提取到 `tests/helpers/ast_guards.py`**(当前 AST guard 测试套用同一 import-walking pattern,提出复用)。新增 invariant guard 时不再 copy-paste 30 行 boilerplate。
    - **`tests/conftest.py` 与 `tests/helpers/` 统一 fixture 入口**;`collect-only + full pytest gate` 检查。
  - **明确不做**(不要被诱惑):
    - ❌ **不删测试**:每个慢 test 都是有价值的 invariant 守卫(`stage_promote_with_force` / `stage_promote_supersedes` / `retrieve_context_relation_expansion_*` 等);删一个就少一份保护。**当前 R-entry 前的最后阶段不应减弱守卫密度**。
    - ❌ **不优化全量速度作为目标**:126 秒不是真痛点(每周累计 < 15 分钟);integration test 本质就需要真跑 lifecycle,不可压缩。
    - ❌ **不引入 pytest-xdist 并行**:当前 SQLite 写入 + 文件 IO 测试会 race condition;并行需要 fixture isolation 设计,复杂度大于收益。
    - ❌ **不 mock 掉 lifecycle**:integration test 的价值就是不 mock;一旦 mock 就退化成 unit test 重写。
    - ❌ **不引入 pytest-cache + selective rerun**:项目还小,缓存策略复杂度大于收益。
  - **流程**:类似 D5 Adapter Discipline / Hygiene Bundle —— 不走完整 plan / plan_audit / review / closeout 流程;multi-commit phase + git log + active_context 记录即文档;**不 cut tag**。
  - **R-entry 衔接**:LTO-4 完成后 active_context 标"R-entry ready",直接进入真实使用阶段。
  - **完成后**:近期队列清空,真实使用反馈作为下一 Direction Gate 选择的最强信号源。

## 当前验证

计划产出后需完成:

```bash
git diff --check
git status --short --branch
```

最近结果:

- plan/audit absorption 后 `git diff --check` passed。
- 当前分支为 `main`;LTO-2 实现期分支为 `feat/lto-2-retrieval-quality-evidence-serving`。
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
- M3 milestone commit:`1590e62 feat(retrieval): dedupe evidence serving by source anchor`
- M4 focused validation:
  - `.venv/bin/python -m pytest tests/unit/orchestration/test_task_report_module.py -q` -> `2 passed`
  - `.venv/bin/python -m pytest tests/test_evidence_pack.py -q` -> `5 passed`
  - `.venv/bin/python -m pytest tests/test_retrieval_adapters.py -q` -> `28 passed`
  - `.venv/bin/python -m pytest tests/test_grounding.py tests/unit/orchestration/test_harness_facade.py -q` -> `13 passed`
  - `.venv/bin/python -m pytest tests/test_cli.py -q -k "retrieval_reports_surface or retrieval_report_warns or retrieval_report_includes"` -> `3 passed, 239 deselected`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q -k knowledge_plane` -> `4 passed, 36 deselected`
  - `.venv/bin/python -m pytest tests/test_evidence_pack.py tests/test_grounding.py tests/test_retrieval_adapters.py tests/unit/orchestration/test_task_report_module.py tests/unit/orchestration/test_harness_facade.py -q` -> `48 passed`
  - `.venv/bin/python -m compileall -q src/swallow` passed
  - `git diff --check` passed
- M4 milestone commit:`62a2a7d feat(retrieval): surface source-anchor evidence quality`
- M5 milestone commit:`d6967f3 test(retrieval): add lto2 evidence quality eval`
- M5 focused validation:
  - `.venv/bin/python -m pytest tests/eval/test_lto2_retrieval_quality.py -m eval -q` -> `3 passed`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q -k "source_pack_evidence_id or evidence_objectization"` -> `2 passed, 39 deselected`
  - `.venv/bin/python -m pytest tests/test_governance.py tests/test_knowledge_relations.py tests/test_sqlite_store.py -q` -> `39 passed`
  - `.venv/bin/python -m pytest tests/test_evidence_pack.py tests/test_grounding.py tests/test_retrieval_adapters.py -q` -> `39 passed`
  - `.venv/bin/python -m pytest tests/unit/orchestration/test_task_report_module.py tests/unit/orchestration/test_harness_facade.py -q` -> `9 passed`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q` -> `41 passed`
  - `.venv/bin/python -m compileall -q src/swallow` passed
  - `.venv/bin/python -m pytest -q` -> `802 passed, 19 deselected`
  - `git diff --check` passed
- Closeout validation:
  - `.venv/bin/python -m pytest tests/eval/test_lto2_retrieval_quality.py -m eval -q` -> `3 passed`
  - `.venv/bin/python -m compileall -q src/swallow` passed
  - `.venv/bin/python -m pytest -q` -> `802 passed, 19 deselected in 131.59s`
  - `git diff --check` passed

LTO-4 compressed-flow validation:

- Baseline before LTO-4 edits:
  - `.venv/bin/python -m pytest -q --co 2>&1 | tail -1` -> `802/821 tests collected (19 deselected) in 0.67s`
  - `time .venv/bin/python -m pytest -q 2>&1 | tail -1` -> `802 passed, 19 deselected in 116.89s`; real `1m57.852s`
- M1 CLI command-family split:
  - `.venv/bin/python -m pytest -q --co 2>&1 | tail -1` -> `802/821 tests collected (19 deselected) in 0.82s`
  - `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py tests/integration/cli/test_knowledge_commands.py tests/integration/cli/test_route_commands.py tests/integration/cli/test_proposal_commands.py tests/integration/cli/test_synthesis_commands.py tests/integration/cli/test_retrieval_commands.py tests/integration/cli/test_system_commands.py -q` -> `253 passed in 78.09s`
  - test count change: `0` (baseline `802`, current `802`)

## 当前阻塞项

- 等待 Human 审阅并提交 LTO-4 M1 CLI command-family split。

## Tag 状态

- 最新已执行 tag: **`v1.8.0`**
- tag target: `d6f2442 docs(release): sync v1.8.0 release docs`
- 标记意义: **LTO-1 Wiki Compiler 第一阶段落地**。
- LTO-1 第二阶段已 merge,但 roadmap / review 建议不单独 cut tag。
- LTO-2 已 merge,Claude review 建议不单独 cut tag。
- 下一 tag: 无 pending decision;后续可在 Wiki Compiler 第三阶段 / LTO-4 / D2 driven ports 等后续 phase 累积后再评估 `v1.9.0`。

## 当前下一步

1. **[Human]** 审阅并提交 LTO-4 M1 CLI command-family split。
2. **[Codex]** Human 提交 M1 后继续 M2:`tests/helpers/builders.py` + `tests/helpers/assertions.py`。
3. **[Codex]** LTO-4 全部完成后把 status 改为 `lto4_complete_r_entry_ready`;不触发后续 phase,不 cut tag。

```markdown
compressed_gate:
- active_phase: lto-4-test-architecture
- active_slice: M1 CLI command-family split complete;waiting Human commit
- active_branch: feat/lto-4-test-architecture
- status: lto4_m1_complete_waiting_human_commit
- latest_completed_phase: lto-2-retrieval-quality-evidence-serving
- latest_completed_merge: 03744f0 Retrieval Quality / Evidence Serving
- latest_roadmap_sync: a3c1844 docs(state): sync lto2 post-merge state
- latest_release_tag: v1.8.0 at d6f2442 docs(release): sync v1.8.0 release docs
- workflow: compressed;no plan.md / plan_audit.md / review_comments.md / closeout.md;git log + active_context are documentation
- boundary: docs/active_context.md "待执行" LTO-4 block is authoritative
- baseline_count: 802/821 collected;19 deselected
- current_count: 802/821 collected;19 deselected
- next_gate: Human M1 commit
```

## 当前产出物

- `docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md`(codex, 2026-05-04, LTO-2 retrieval quality / evidence serving phase plan;audit absorbed with explicit C1-C5/N1-N2 decisions)
- `docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md`(claude, 2026-05-04, has-concerns — 0 blockers / 5 concerns / 2 nits; C1–C5 / N1-N2 absorbed into plan.md)
- `docs/plans/lto-2-retrieval-quality-evidence-serving/review_comments.md`(claude, 2026-05-04, **recommend-merge**;5/5 plan_audit concerns + 2/2 nits absorbed with explicit Codex 决议;0 blockers / 1 concern(C1 closeout 缺失,Codex 必做)/ 1 nit;`source-anchor-v1` version-prefixed canonical JSON + evidence id 单点 helper 升级 + `derived-from-v1` deterministic relation id + retrieval pipeline path A enrichment 四处实现强于 plan;tag 建议 = 不为本阶段单独 cut,累积后续 phase 后 cut v1.9.0)
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
- `docs/active_context.md`(codex, 2026-05-04, post-LTO-2 merge state sync to main Direction Gate)
- `current_state.md`(codex, 2026-05-04, recovery checkpoint sync to post-LTO-2 merge state)
- `src/swallow/orchestration/task_report.py`(codex, 2026-05-04, M4 retrieval/source grounding report source-anchor, dedup, pointer, and stored preview visibility)
- `src/swallow/knowledge_retrieval/retrieval.py`(codex, 2026-05-04, M4 stored `entry_json["preview"]` propagation as `source_preview`)
- `src/swallow/knowledge_retrieval/evidence_pack.py`(codex, 2026-05-04, M4 `source_preview_excerpt` on evidence entries)
- `tests/unit/orchestration/test_task_report_module.py`(codex, 2026-05-04, M4 report coverage for dedup counts, missing pointers, and stored preview excerpts)
- `tests/test_evidence_pack.py` + `tests/test_retrieval_adapters.py`(codex, 2026-05-04, M4 stored preview propagation coverage)
- `tests/eval/test_lto2_retrieval_quality.py`(codex, 2026-05-04, M5 deterministic LTO-2 retrieval quality eval)
- `tests/test_invariant_guards.py`(codex, 2026-05-04, M5 source-pack evidence id source-anchor-key guard)
- `pr.md`(codex, 2026-05-04, LTO-2 PR draft synced to review-passed / merge-ready state;ignored local file)
- `docs/plans/lto-2-retrieval-quality-evidence-serving/closeout.md`(codex, 2026-05-04, final closeout;review C1 absorbed;merge readiness recorded)
- `docs/roadmap.md`(codex, 2026-05-04, post-LTO-2 merge roadmap sync;LTO-2 marked complete;Direction Gate reset)
- `docs/concerns_backlog.md`(codex, 2026-05-04, LTO-2 cross-candidate evidence dedup concern moved from Roadmap-Bound to Resolved)
- `tests/integration/cli/test_task_commands.py` + `tests/integration/cli/test_knowledge_commands.py` + `tests/integration/cli/test_route_commands.py` + `tests/integration/cli/test_proposal_commands.py` + `tests/integration/cli/test_synthesis_commands.py` + `tests/integration/cli/test_retrieval_commands.py` + `tests/integration/cli/test_system_commands.py` + `tests/test_cli.py`(codex, 2026-05-04, LTO-4 M1 mechanical CLI command-family split;test count unchanged)
