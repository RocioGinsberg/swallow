# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `LTO-2 Retrieval Quality / Evidence Serving`
- latest_completed_phase: `lto-2-retrieval-source-scoping`
- latest_completed_slice: `merged to main at d4288a1`
- active_track: `R-entry Real Usage`
- active_phase: `r-entry-v1.9-real-usage`
- active_slice: `runbook ready;design-doc flow`
- active_branch: `main`
- status: `r_entry_v1_9_runbook_ready`

## 当前状态说明

当前 git 分支为 `main`。`v1.9.0` release docs 已提交为 `d598e58 docs(release): sync v1.9.0 release docs`,tag `v1.9.0` 已打在该 commit。Human 决定继续真实使用驱动优化,本轮不开开发 phase,而是用 Swallow 自身设计文档执行 post-v1.9.0 R-entry runbook:`docs/plans/r-entry-v1.9-real-usage/plan.md`。该 runbook 重点验证 retrieval source scoping、truth reuse visibility、Wiki Compiler authoring、CLI/Web operator flow 与 nginx/Tailscale smoke。

LTO-2 source scoping 实现内容:task-declared `document_paths` 现在进入 `RetrievalRequest.declared_document_paths`;`build_task_retrieval_request` 是唯一注入点并把路径规范为 workspace-relative;retrieval 在 rerank 前应用 declared-document priority 与 generated/archive/build-cache noise downgrade;`score_breakdown` 暴露 `declared_document_priority` / `source_noise_penalty`;`retrieval_report.md` 新增 `Truth Reuse Visibility`;task memory/summary 也记录 truth reuse visibility 状态。非目标仍保持:Graph RAG、schema migration、vector index overhaul、chunk 大改、provider/rerank 新集成。

本轮另外按 Human direction 取消 model_review gate 层:删除 `.agents/workflows/model_review.md`,并从 `claude/rules` `claude/role` `codex/rules` `codex/role` `shared/rules` `feature.md` `AGENTS.md` `.codex/session_bootstrap.md` 中移除所有 model_review 引用;plan gate 前不再要求第二模型审查,plan_audit 直接进入 Human Plan Gate。

LTO-4 已完成 M1-M4:CLI command-family split、shared builders/assertions、AST guard helper extraction、global builder fixture entry。最终 `collect-only` 为 `806/825 tests collected (19 deselected)`,比 LTO-4 起始 baseline `802/821` 增加 4 个 helper self-tests,没有测试数量减少。最终全量 pytest `806 passed, 19 deselected in 131.76s`,real `2m12.909s`,处于 LTO-4 允许耗时区间内。LTO-4 完成后没有 cut tag,随后进入 R-entry 并触发本次 LTO-2 source scoping phase。

最近稳定 checkpoint:

- LTO-2 Retrieval Quality / Evidence Serving 已 merge 到 `main` at `03744f0`;post-merge state sync 已提交为 `a3c1844`。
- LTO-4 Test Architecture 已 merge / synced 到 `main` at `ac2d3ff`;历史 phase 文档已归档到 `docs/archive_phases/`。
- R-entry Real Usage 不是开发 phase;R-entry runbook 与 findings 保留为 LTO-2 source scoping 的 evidence input。
- LTO-2 Retrieval Source Scoping And Truth Reuse Visibility 已 merge 到 `main` at `d4288a1`。

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `docs/roadmap.md`
4. `docs/plans/r-entry-v1.9-real-usage/plan.md`
5. `docs/plans/r-entry-v1.9-real-usage/findings.md`
6. `docs/plans/r-entry-real-usage/plan.md`
7. `docs/design/INVARIANTS.md`
8. `docs/design/KNOWLEDGE.md`
9. `docs/design/DATA_MODEL.md`
10. `docs/engineering/TEST_ARCHITECTURE.md`
11. `docs/engineering/ADAPTER_DISCIPLINE.md`
12. `docs/engineering/CODE_ORGANIZATION.md`
13. `docs/concerns_backlog.md`

## 当前推进

已完成:

- **[Human]** LTO-4 Test Architecture 已完成并 merge/sync 到 `main` at `ac2d3ff`;不 cut tag。
- **[Human]** 历史 phase 文档已移动到 `docs/archive_phases/` at `795aa4d docs(store): move history plans to archive`;`docs/plans/` 保留 R-entry runbook 与当前已完成的 LTO-2 source scoping phase 文档。
- **[Codex]** 已产出 `docs/plans/r-entry-real-usage/plan.md`,覆盖 CLI + knowledge chain + Wiki Compiler + Web UI + Tailscale/nginx smoke。
- **[Codex]** 已同步 `docs/roadmap.md` 到 LTO-4 complete / R-entry active 状态。
- **[Codex]** 已执行 R-entry 本机可验证部分并整理 `docs/plans/r-entry-real-usage/findings.md`,记录 retrieval source scoping / truth reuse visibility / note-only offline semantics / wiki ergonomics / nginx host smoke 等 Direction Gate 候选。
- **[Codex]** 已完成 R-entry UX 小修:Wiki CLI 捕获 `AgentLLMUnavailable` 并给出 `source .env` / `--dry-run` 提示;`task staged --task` 空 global staged 结果会提示 task-scoped knowledge surface;`plan.md` 补充 `.env` 与 OpenRouter rerank 配置示例。
- **[Human]** 已提交 R-entry UX 小修:`449ccda fix(cli): polish r-entry operator guidance`。
- **[Codex]** 已更新 `docs/roadmap.md`,将泛化的 `LTO-2 retrieval quality 后续增量` 收敛为 `LTO-2 Retrieval Source Scoping And Truth Reuse Visibility`,并明确 chunk 调整 / schema migration / Graph RAG 均不进入首个 slice。
- **[Codex]** 已产出 `docs/plans/lto-2-retrieval-source-scoping/plan.md`,拆分 M1 request context plumbing、M2 candidate source scoping、M3 truth reuse visibility、M4 R-entry regression smoke。
- **[Claude/design-auditor]** 已产出 `docs/plans/lto-2-retrieval-source-scoping/plan_audit.md`:0 blockers,5 concerns,2 nits。
- **[Codex]** 已吸收 plan audit:明确 `build_task_retrieval_request` 为 M1 唯一注入点;M2 指名 `source_policy_label_for` / `SOURCE_POLICY_NOISE_LABELS` 与 `score_breakdown` 验收;M4 使用 `pytest.mark.eval` 与显式 eval gate;移除 premature closeout 与 `harness.py` 主触点。
- **[Human]** 已切换到 `feat/lto-2-retrieval-source-scoping` 并在完成 review/closeout 后 merge 回 `main`。
- **[Codex]** 已完成 M1-M4 实现:request context plumbing、candidate source scoping、truth reuse visibility report/memory、R-entry regression eval fixture。
- **[Claude]** 已产出 `docs/plans/lto-2-retrieval-source-scoping/review_comments.md`:0 blocks,3 concerns,3 nits;独立验证 focused/eval/full pytest 与 Codex 报告一致(`812 passed, 20 deselected in 139.11s`)。
- **[Claude]** 已把 3 个 [CONCERN] 聚合为 `LTO-2 Source Scoping review follow-ups` 写入 `docs/concerns_backlog.md` Active Open。
- **[Codex]** 已产出 `docs/plans/lto-2-retrieval-source-scoping/closeout.md`,同步 review disposition / validation / deferred follow-ups / merge readiness。
- **[Codex]** 已更新 `pr.md` Review 段,记录 Claude review verdict、独立验证和 3 个 tracked concerns。
- **[Human]** 已 merge LTO-2 Retrieval Source Scoping And Truth Reuse Visibility 到 `main` at `d4288a1`。
- **[Codex]** 已同步 post-merge `docs/active_context.md` / `current_state.md` / `docs/roadmap.md`。
- **[Claude]** 已对 `main@d4288a1` 完成 tag 评估:推荐 cut **v1.9.0**(主题 Retrieval Quality 累积闭环 + R-entry-driven source scoping;v1.8.0 以来 5 个 phase / 3 个 operator-visible 增量;main 稳定;无 API drift 风险)。
- **[Claude]** 已按 Human 要求重写 `docs/roadmap.md`:压缩已完成内容(180→151 行),将 Direction Gate 候选与触发条件提到 §三,LTO 表按"仍在推进 vs 已闭合"分类,完成 phase 细节移交 git log + closeout。
- **[Human]** 已提交 `v1.9.0` release docs:`d598e58 docs(release): sync v1.9.0 release docs`。
- **[Human]** 已执行 tag:`v1.9.0` -> `d598e58`。
- **[Codex]** 已同步 `latest_executed_public_tag` / active context / roadmap tag 状态。
- **[Codex]** 已产出 `docs/plans/r-entry-v1.9-real-usage/plan.md`,作为 post-v1.9.0 设计文档真实使用 runbook。
- **[Codex]** 已产出 `docs/plans/r-entry-v1.9-real-usage/findings.md`,作为真实使用 issue log / Direction Gate evidence 模板。
- **[Codex]** 已执行 R0-R4 / R6 / R9 loopback smoke:preflight、declared-doc task、retrieval report、task knowledge capture、Wiki dry-run、Web API smoke。
- **[Codex]** 已记录 5 条 findings:R19-001 declared `document_paths` 未进入 task truth/source scoping 未应用(blocker);R19-002 note-only offline 被分类为 failed/unreachable_backend(concern);R19-003 Truth Reuse Visibility reason counts/ warning wording 复现 review concern(concern);R19-004 Wiki dry-run `prompt_artifact=-`(concern);R19-005 Web loopback smoke passed(observation)。

待执行:

- **[Human]** 审阅 `docs/plans/r-entry-v1.9-real-usage/findings.md`,决定是否先开小修处理 R19-001/R19-002/R19-003,或继续执行 R7/R8 real Wiki draft/refine。
- **[Codex]** 如 Human 选择修复,按流程输出对应 phase plan;如继续 R-entry,继续记录 findings。

## 当前验证

Post-merge state sync validation:

- `git diff --check` -> passed
- `git status --short --branch` -> `## main...origin/main`;modified `current_state.md`, `docs/active_context.md`, `docs/roadmap.md`
- `wc -l docs/roadmap.md` -> `180 docs/roadmap.md`(低于 300 行上限)

Pre-`v1.9.0` release docs validation:

- `git diff --check` -> passed
- `git status --short --branch` -> `## main...origin/main [ahead 1]`;modified `README.md`, `current_state.md`, `docs/active_context.md`, `docs/roadmap.md`
- `wc -l docs/roadmap.md README.md docs/active_context.md current_state.md` -> `151` / `359` / `246` / `174`

Post-`v1.9.0` tag sync validation:

- `git diff --check` -> passed
- `git status --short --branch` -> `## main...origin/main`;modified `current_state.md`, `docs/active_context.md`, `docs/roadmap.md`
- `wc -l docs/roadmap.md docs/active_context.md current_state.md` -> `150` / `248` / `169`

R-entry v1.9 runbook drafting validation:

- `git diff --check` -> passed
- `git status --short --branch` -> `## main...origin/main`;modified `current_state.md`, `docs/active_context.md`, `docs/roadmap.md`;untracked `docs/plans/r-entry-v1.9-real-usage/`
- `wc -l docs/plans/r-entry-v1.9-real-usage/plan.md docs/plans/r-entry-v1.9-real-usage/findings.md docs/active_context.md current_state.md docs/roadmap.md` -> `521` / `73` / `265` / `178` / `152`

R-entry v1.9 partial execution validation:

- R0 preflight -> `doctor --skip-stack` ok; isolated base migrate status `schema_version: 1, pending: 0`
- R2 task -> `10b2890bab71`
- R3/R4 retrieval run -> task failed due note-only offline semantics, but produced `retrieval_count=8`
- R4 task knowledge capture -> `knowledge_capture_added added=1 total=1`; review queue shows `knowledge-0001` blocked by `stage_not_verified`
- R6 Wiki dry-run -> `wiki_draft_dry_run source_count=1 prompt_artifact=-`
- R9 Web loopback smoke -> `GET /` 200; `/api/tasks` and `/api/tasks/10b2890bab71` returned task state; server stopped after smoke
- findings -> R19-001..R19-005 recorded in `docs/plans/r-entry-v1.9-real-usage/findings.md`
- final check -> `git diff --check` passed; port 8765 no longer listening; `wc -l findings/active/current` -> `161` / `276` / `179`

本轮文档同步验证:

- `git diff --check` -> passed
- `git status --short --branch` -> `## main...origin/main`;modified `current_state.md`, `docs/active_context.md`, `docs/roadmap.md`;untracked `docs/plans/`(contains `docs/plans/r-entry-real-usage/plan.md`)

Roadmap Direction Gate 同步验证:

- `git diff --check` -> passed
- `git status --short --branch` -> `## main...origin/main [ahead 2]`;modified `docs/active_context.md`, `docs/roadmap.md`
- `wc -l docs/roadmap.md` -> `184 docs/roadmap.md`(低于 300 行上限)

LTO-2 source scoping plan drafting validation:

- `git diff --check` -> passed
- `git status --short --branch` -> `## main...origin/main [ahead 3]`;modified `docs/active_context.md`;untracked `docs/plans/lto-2-retrieval-source-scoping/`;also present unrelated agent/workflow files outside this plan absorption scope
- `wc -l docs/plans/lto-2-retrieval-source-scoping/plan.md docs/active_context.md` -> `232` / `191`

Plan audit absorption validation:

- `git diff --check` -> passed
- `rg` confirmed plan now names `build_task_retrieval_request`, `SOURCE_POLICY_NOISE_LABELS`, `score_breakdown`, and `pytest.mark.eval`

LTO-2 source scoping implementation validation:

- `.venv/bin/python -m pytest tests/unit/orchestration/test_retrieval_flow_module.py -q` -> `12 passed in 0.19s`
- `.venv/bin/python -m pytest tests/unit/orchestration/test_task_report_module.py -q` -> `3 passed in 0.04s`
- `.venv/bin/python -m pytest -m eval tests/eval/test_lto2_retrieval_source_scoping.py -q` -> `1 passed in 0.03s`
- `.venv/bin/python -m pytest tests/integration/cli/test_retrieval_commands.py -q` -> `44 passed in 7.53s`
- `.venv/bin/python -m compileall -q src/swallow tests` -> passed
- `.venv/bin/python -m pytest -q` -> `812 passed,20 deselected in 110.51s`
- `git diff --check` -> passed

LTO-2 source scoping review / closeout validation:

- Claude independent focused tests -> `59 passed in 7.70s`
- Claude eval gate -> `1 passed in 0.02s`
- Claude full pytest -> `812 passed,20 deselected in 139.11s`
- `docs/concerns_backlog.md` -> appended `LTO-2 Source Scoping review follow-ups`
- closeout / PR sync -> `git diff --check` passed
- Human merge -> `d4288a1 LTO-2 Retrieval Source Scoping And Truth Reuse Visibility`

R-entry UX fixes validation:

- `.venv/bin/python -m pytest tests/integration/cli/test_wiki_commands.py::test_wiki_draft_cli_reports_llm_unavailable_without_traceback -q` -> `1 passed in 0.29s`
- `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py::test_task_staged_points_to_task_knowledge_surface_when_no_global_candidate -q` -> `1 passed in 0.45s`
- `.venv/bin/python -m pytest tests/integration/cli/test_wiki_commands.py -q` -> `6 passed in 1.46s`
- `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py -q` -> `41 passed in 14.87s`

LTO-4 compressed-flow validation:

- Baseline before LTO-4 edits:
  - `.venv/bin/python -m pytest -q --co 2>&1 | tail -1` -> `802/821 tests collected (19 deselected) in 0.67s`
  - `time .venv/bin/python -m pytest -q 2>&1 | tail -1` -> `802 passed, 19 deselected in 116.89s`; real `1m57.852s`
- M1 CLI command-family split:
  - commits: `d63a880 refactor(tests): split test_cli.py command-family modules`;`79f6695 docs(state): record lto4 m1 test split`
  - `.venv/bin/python -m pytest -q --co 2>&1 | tail -1` -> `802/821 tests collected (19 deselected) in 0.82s`
  - `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py tests/integration/cli/test_knowledge_commands.py tests/integration/cli/test_route_commands.py tests/integration/cli/test_proposal_commands.py tests/integration/cli/test_synthesis_commands.py tests/integration/cli/test_retrieval_commands.py tests/integration/cli/test_system_commands.py -q` -> `253 passed in 78.09s`
  - test count change: `0` (baseline `802`, current `802`)
- M2 shared builders/assertions helpers:
  - commits: `d20b99d refactor(tests): extract common builders into helpers`;`28f0e8f docs(state): record lto4 m2 helpers`
  - `.venv/bin/python -m pytest tests/unit/test_helpers_builders.py tests/integration/cli/test_task_commands.py tests/integration/cli/test_knowledge_commands.py tests/integration/cli/test_wiki_commands.py -q` -> `121 passed in 49.06s`
  - `.venv/bin/python -m compileall -q tests/helpers tests/unit/test_helpers_builders.py` passed
  - `.venv/bin/python -m pytest -q --co 2>&1 | tail -1` -> `806/825 tests collected (19 deselected) in 0.71s`
  - `git diff --check` passed
  - test count change: `+4` (new helper self-tests only; no test deletion)
- M3 invariant AST guard helper extraction:
  - commits: `ba5d3b1 refactor(tests): consolidate invariant guard helpers`;`97e3073 docs(state): record lto4 m3 guard helpers`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q` -> `41 passed in 6.49s`
  - `.venv/bin/python -m compileall -q tests/helpers/ast_guards.py tests/test_invariant_guards.py` passed
  - `.venv/bin/python -m pytest -q --co 2>&1 | tail -1` -> `806/825 tests collected (19 deselected) in 0.71s`
  - `git diff --check` passed
  - test count change: `0` (baseline after M2 `806`, current `806`)
- M4 conftest fixture entry consolidation + final gate:
  - `.venv/bin/python -m pytest tests/unit/test_helpers_builders.py tests/integration/cli/test_task_commands.py tests/integration/cli/test_knowledge_commands.py tests/integration/cli/test_wiki_commands.py -q` -> `121 passed in 33.93s`
  - `.venv/bin/python -m pytest -q --co 2>&1 | tail -1` -> `806/825 tests collected (19 deselected) in 0.66s`
  - `.venv/bin/python -m compileall -q src/swallow tests/helpers tests/conftest.py` passed
  - `time .venv/bin/python -m pytest -q 2>&1 | tail -1` -> `806 passed, 19 deselected in 131.76s`; real `2m12.909s`
  - `git diff --check` passed
  - test count change: `0` after M3;`+4` vs LTO-4 starting baseline from helper self-tests only

## 当前阻塞项

- 无 code blocker。LTO-2 source scoping 已 merge 到 `main`;3 个 review concerns 已登记为后续项。

## Tag 状态

- 最新已执行 tag: **`v1.9.0`**
- tag target: `d598e58 docs(release): sync v1.9.0 release docs`
- 标记意义: **Wiki Compiler 第二阶段 + Retrieval Quality / Evidence Serving + R-entry-driven Source Scoping / Truth Reuse Visibility 的稳定 checkpoint**。
- pending release tag: `none`

## 当前下一步

1. **[Human]** 审阅 R19-001..R19-005,尤其是 R19-001 declared document plumbing blocker。
2. **[Human]** 决定先开修复 phase,还是继续 R7/R8 real Wiki draft/refine。
3. **[Codex]** 按 Human 决策继续 plan 或继续 runbook。

```markdown
compressed_gate:
- active_phase: r-entry-v1.9-real-usage
- active_slice: runbook ready;design-doc flow
- active_branch: main
- status: r_entry_v1_9_runbook_ready
- latest_completed_phase: lto-2-retrieval-source-scoping
- latest_completed_commit: d4288a1 LTO-2 Retrieval Source Scoping And Truth Reuse Visibility
- latest_history_archive_commit: 795aa4d docs(store): move history plans to archive
- latest_release_tag: v1.9.0 at d598e58 docs(release): sync v1.9.0 release docs
- pending_release_tag: none
- workflow: formal phase plan;plan_audit.md produced and absorbed;implementation complete;Claude review acceptable to merge;merged to main;post-merge state synced;release docs committed;tag complete
- boundary: docs/plans/lto-2-retrieval-source-scoping/plan.md is current plan
- baseline_count: 802/821 collected;19 deselected
- current_count: 806/825 collected;19 deselected
- final_full_pytest: 806 passed, 19 deselected in 131.76s; real 2m12.909s
- r_entry_plan: docs/plans/r-entry-real-usage/plan.md
- findings: docs/plans/r-entry-real-usage/findings.md
- r_entry_v1_9_plan: docs/plans/r-entry-v1.9-real-usage/plan.md
- r_entry_v1_9_findings: docs/plans/r-entry-v1.9-real-usage/findings.md
- phase_plan: docs/plans/lto-2-retrieval-source-scoping/plan.md
- plan_audit: docs/plans/lto-2-retrieval-source-scoping/plan_audit.md
- ux_fixes: wiki llm unavailable CLI hint; task staged task-knowledge hint; env/rerank runbook docs
- next_gate: Human review findings and choose fix-vs-continue
```

## 当前产出物

- `docs/plans/r-entry-real-usage/plan.md`(codex, 2026-05-04, R-entry real usage runbook for design-doc knowledge chain, CLI, UI, nginx/Tailscale smoke, and issue logging)
- `docs/plans/r-entry-real-usage/findings.md`(codex, 2026-05-04, R-entry real usage findings and Direction Gate candidates)
- `src/swallow/adapters/cli_commands/wiki.py`(codex, 2026-05-04, operator-facing LLM unavailable handling for wiki CLI)
- `src/swallow/adapters/cli.py` / `src/swallow/adapters/cli_commands/tasks.py`(codex, 2026-05-04, task staged hint for task-scoped knowledge surface)
- `tests/integration/cli/test_wiki_commands.py` / `tests/integration/cli/test_task_commands.py`(codex, 2026-05-04, regression coverage for R-entry UX fixes)
- `docs/active_context.md`(codex, 2026-05-04, current state and checkpoint cleanup)
- `docs/roadmap.md`(codex, 2026-05-04, LTO-4 complete / R-entry active roadmap sync;LTO-2 Retrieval Source Scoping And Truth Reuse Visibility Direction Gate proposal)
- `current_state.md`(codex, 2026-05-04, recovery checkpoint sync to post-LTO-2 source scoping main state)
- `docs/plans/lto-2-retrieval-source-scoping/plan.md`(codex, 2026-05-04, LTO-2 source scoping / truth reuse visibility phase plan;revised after plan_audit)
- `docs/plans/lto-2-retrieval-source-scoping/plan_audit.md`(claude:design-auditor, 2026-05-04, plan gate audit — has-concerns;0 blockers, 5 concerns, 2 nits)
- `src/swallow/orchestration/models.py` / `src/swallow/orchestration/retrieval_flow.py`(codex, 2026-05-04, declared document request plumbing)
- `src/swallow/knowledge_retrieval/retrieval.py` / `src/swallow/knowledge_retrieval/evidence_pack.py` / `src/swallow/knowledge_retrieval/knowledge_plane.py`(codex, 2026-05-04, source scoping policy and truth reuse visibility helpers)
- `src/swallow/orchestration/task_report.py` / `src/swallow/orchestration/harness.py`(codex, 2026-05-04, truth reuse visibility report and memory surfaces)
- `tests/unit/orchestration/test_retrieval_flow_module.py` / `tests/unit/orchestration/test_task_report_module.py` / `tests/eval/test_lto2_retrieval_source_scoping.py`(codex, 2026-05-04, M1-M4 regression coverage)
- `.agents/workflows/feature.md` / `.agents/workflows/model_review.md`(deleted) / `.agents/claude/rules.md` / `.agents/claude/role.md` / `.agents/codex/rules.md` / `.agents/codex/role.md` / `.agents/shared/rules.md` / `AGENTS.md` / `.codex/session_bootstrap.md`(claude, 2026-05-04, remove model_review gate layer per Human direction)
- `docs/plans/lto-2-retrieval-source-scoping/review_comments.md`(claude, 2026-05-04, PR review — acceptable to merge with 3 concerns;0 blocks)
- `docs/concerns_backlog.md`(claude, 2026-05-04, append LTO-2 Source Scoping review follow-ups Active Open row)
- `docs/roadmap.md`(claude, 2026-05-04, 全面重写 —— 压缩已完成 phase 叙事,Direction Gate 候选与触发条件提到 §三,LTO 表按状态分类;180→151 行)
- `docs/plans/lto-2-retrieval-source-scoping/closeout.md`(codex, 2026-05-04, phase closeout — acceptable to merge with tracked concerns)
- `pr.md`(codex, 2026-05-04, PR body updated with Claude review disposition)
- `docs/active_context.md` / `current_state.md` / `docs/roadmap.md`(codex, 2026-05-04, post-merge state sync for `main@d4288a1`)
- `README.md` / `current_state.md` / `docs/active_context.md` / `docs/roadmap.md`(codex, 2026-05-04, pre-`v1.9.0` release docs sync)
- `current_state.md` / `docs/active_context.md` / `docs/roadmap.md`(codex, 2026-05-04, post-`v1.9.0` tag status sync)
- `docs/plans/r-entry-v1.9-real-usage/plan.md`(codex, 2026-05-05, post-v1.9.0 design-doc real usage runbook)
- `docs/plans/r-entry-v1.9-real-usage/findings.md`(codex, 2026-05-05, findings template for post-v1.9.0 real usage)
