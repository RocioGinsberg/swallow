# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Test Architecture`
- latest_completed_phase: `lto-4-test-architecture`
- latest_completed_slice: `M4 fixture consolidation complete;final full suite passed;R-entry ready`
- active_track: `LTO-2 Retrieval Quality / Evidence Serving`
- active_phase: `lto-2-retrieval-source-scoping`
- active_slice: `plan audit absorbed;awaiting human gate`
- active_branch: `main`
- status: `plan_revised_after_audit_waiting_human_gate`

## 当前状态说明

当前 git 分支为 `main`。LTO-4 Test Architecture 已 merge 到 `main`;R-entry 真实使用验证已完成本机可验证部分,并触发下一轮正式 phase:`lto-2-retrieval-source-scoping`。Plan drafting 已完成;plan audit 已由 Claude design-auditor 产出(0 blockers, 5 concerns, 2 nits);Codex 已吸收 concerns 并修订 plan。实现前必须 Human 审批 plan gate 并切换到 feature branch。

Codex 已产出并根据 `plan_audit.md` 修订 `docs/plans/lto-2-retrieval-source-scoping/plan.md`,作为 LTO-2 Retrieval Source Scoping And Truth Reuse Visibility phase 的唯一计划入口。计划边界:让 task-declared `document_paths` 影响 retrieval candidate scope/priority,默认降权或排除 generated/archive 噪声路径,并让 retrieval report 显示 declared source docs 与 canonical/task knowledge 的 considered/matched/skipped/absent 原因。非目标:Graph RAG、schema migration、vector index overhaul、chunk 大改、provider/rerank 新集成。Audit concerns 已吸收为明确实现约束:M1 唯一注入点、M2 source policy touch point 与 `score_breakdown` 验收、M4 eval marker/gate、去除过早 closeout 与不必要主触点。

本轮另外按 Human direction 取消 model_review gate 层:删除 `.agents/workflows/model_review.md`,并从 `claude/rules` `claude/role` `codex/rules` `codex/role` `shared/rules` `feature.md` `AGENTS.md` `.codex/session_bootstrap.md` 中移除所有 model_review 引用;plan gate 前不再要求第二模型审查,plan_audit 直接进入 Human Plan Gate。

LTO-4 已完成 M1-M4:CLI command-family split、shared builders/assertions、AST guard helper extraction、global builder fixture entry。最终 `collect-only` 为 `806/825 tests collected (19 deselected)`,比 LTO-4 起始 baseline `802/821` 增加 4 个 helper self-tests,没有测试数量减少。最终全量 pytest `806 passed, 19 deselected in 131.76s`,real `2m12.909s`,处于 LTO-4 允许耗时区间内。完成后不触发后续 phase,不 cut tag;下一步只进入真实使用 R-entry。

最近稳定 checkpoint:

- LTO-2 Retrieval Quality / Evidence Serving 已 merge 到 `main` at `03744f0`;post-merge state sync 已提交为 `a3c1844`。
- LTO-4 Test Architecture 已 merge / synced 到 `main` at `ac2d3ff`;历史 phase 文档已归档到 `docs/archive_phases/`。
- R-entry Real Usage 不是开发 phase;R-entry runbook 与 findings 保留为本 phase 的 evidence input。当前正式 phase 计划入口为 `docs/plans/lto-2-retrieval-source-scoping/plan.md`。

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `docs/roadmap.md`
4. `docs/plans/r-entry-real-usage/plan.md`
5. `docs/design/INVARIANTS.md`
6. `docs/design/KNOWLEDGE.md`
7. `docs/design/DATA_MODEL.md`
8. `docs/engineering/TEST_ARCHITECTURE.md`
9. `docs/engineering/ADAPTER_DISCIPLINE.md`
10. `docs/engineering/CODE_ORGANIZATION.md`
11. `docs/concerns_backlog.md`

## 当前推进

已完成:

- **[Human]** LTO-4 Test Architecture 已完成并 merge/sync 到 `main` at `ac2d3ff`;不 cut tag。
- **[Human]** 历史 phase 文档已移动到 `docs/archive_phases/` at `795aa4d docs(store): move history plans to archive`;`docs/plans/` 只保留当前 R-entry 计划。
- **[Codex]** 已产出 `docs/plans/r-entry-real-usage/plan.md`,覆盖 CLI + knowledge chain + Wiki Compiler + Web UI + Tailscale/nginx smoke。
- **[Codex]** 已同步 `docs/roadmap.md` 到 LTO-4 complete / R-entry active 状态。
- **[Codex]** 已执行 R-entry 本机可验证部分并整理 `docs/plans/r-entry-real-usage/findings.md`,记录 retrieval source scoping / truth reuse visibility / note-only offline semantics / wiki ergonomics / nginx host smoke 等 Direction Gate 候选。
- **[Codex]** 已完成 R-entry UX 小修:Wiki CLI 捕获 `AgentLLMUnavailable` 并给出 `source .env` / `--dry-run` 提示;`task staged --task` 空 global staged 结果会提示 task-scoped knowledge surface;`plan.md` 补充 `.env` 与 OpenRouter rerank 配置示例。
- **[Human]** 已提交 R-entry UX 小修:`449ccda fix(cli): polish r-entry operator guidance`。
- **[Codex]** 已更新 `docs/roadmap.md`,将泛化的 `LTO-2 retrieval quality 后续增量` 收敛为 `LTO-2 Retrieval Source Scoping And Truth Reuse Visibility`,并明确 chunk 调整 / schema migration / Graph RAG 均不进入首个 slice。
- **[Codex]** 已产出 `docs/plans/lto-2-retrieval-source-scoping/plan.md`,拆分 M1 request context plumbing、M2 candidate source scoping、M3 truth reuse visibility、M4 R-entry regression smoke。
- **[Claude/design-auditor]** 已产出 `docs/plans/lto-2-retrieval-source-scoping/plan_audit.md`:0 blockers,5 concerns,2 nits。
- **[Codex]** 已吸收 plan audit:明确 `build_task_retrieval_request` 为 M1 唯一注入点;M2 指名 `source_policy_label_for` / `SOURCE_POLICY_NOISE_LABELS` 与 `score_breakdown` 验收;M4 使用 `pytest.mark.eval` 与显式 eval gate;移除 premature closeout 与 `harness.py` 主触点。

待执行:

- **[Human]** 审批修订后的 `docs/plans/lto-2-retrieval-source-scoping/plan.md` 与 plan audit 吸收结果。
- **[Human]** plan gate 通过后从 `main` 切换到 `feat/lto-2-retrieval-source-scoping`;Codex 再开始实现。
- **[Human]** 如需完成 R9,在 host nginx + 第二台 Tailscale 设备执行反代 smoke,再把结果补入 findings 或后续部署 runbook。

## 当前验证

文档同步后需完成:

```bash
git diff --check
git status --short --branch
```

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

- 无 code blocker。等待 Human Plan Gate;实现不得在 `main` 开始。

## Tag 状态

- 最新已执行 tag: **`v1.8.0`**
- tag target: `d6f2442 docs(release): sync v1.8.0 release docs`
- 标记意义: **LTO-1 Wiki Compiler 第一阶段落地**。
- LTO-1 第二阶段已 merge,但 roadmap / review 建议不单独 cut tag。
- LTO-2 已 merge,Claude review 建议不单独 cut tag。
- LTO-4 已完成,压缩流程不 cut tag。
- 下一 tag: 无 pending decision;后续可在 R-entry 反馈触发的产品 phase 完成后再评估 `v1.9.0`。

## 当前下一步

1. **[Human]** 审批修订后的 plan gate。
2. **[Human]** gate 通过后切换到 `feat/lto-2-retrieval-source-scoping`。
3. **[Codex]** 在 feature branch 上按 plan M1-M4 实现。

```markdown
compressed_gate:
- active_phase: lto-2-retrieval-source-scoping
- active_slice: plan audit absorbed;awaiting human gate
- active_branch: main
- status: plan_revised_after_audit_waiting_human_gate
- latest_completed_phase: lto-4-test-architecture
- latest_completed_commit: ac2d3ff docs(state): mark lto4 r-entry ready
- latest_history_archive_commit: 795aa4d docs(store): move history plans to archive
- latest_release_tag: v1.8.0 at d6f2442 docs(release): sync v1.8.0 release docs
- workflow: formal phase plan;plan_audit.md produced and absorbed;implementation waits for Human Plan Gate and feature branch
- boundary: docs/plans/lto-2-retrieval-source-scoping/plan.md is current plan
- baseline_count: 802/821 collected;19 deselected
- current_count: 806/825 collected;19 deselected
- final_full_pytest: 806 passed, 19 deselected in 131.76s; real 2m12.909s
- r_entry_plan: docs/plans/r-entry-real-usage/plan.md
- findings: docs/plans/r-entry-real-usage/findings.md
- phase_plan: docs/plans/lto-2-retrieval-source-scoping/plan.md
- plan_audit: docs/plans/lto-2-retrieval-source-scoping/plan_audit.md
- ux_fixes: wiki llm unavailable CLI hint; task staged task-knowledge hint; env/rerank runbook docs
- next_gate: Human Plan Gate and feature branch switch
```

## 当前产出物

- `docs/plans/r-entry-real-usage/plan.md`(codex, 2026-05-04, R-entry real usage runbook for design-doc knowledge chain, CLI, UI, nginx/Tailscale smoke, and issue logging)
- `docs/plans/r-entry-real-usage/findings.md`(codex, 2026-05-04, R-entry real usage findings and Direction Gate candidates)
- `src/swallow/adapters/cli_commands/wiki.py`(codex, 2026-05-04, operator-facing LLM unavailable handling for wiki CLI)
- `src/swallow/adapters/cli.py` / `src/swallow/adapters/cli_commands/tasks.py`(codex, 2026-05-04, task staged hint for task-scoped knowledge surface)
- `tests/integration/cli/test_wiki_commands.py` / `tests/integration/cli/test_task_commands.py`(codex, 2026-05-04, regression coverage for R-entry UX fixes)
- `docs/active_context.md`(codex, 2026-05-04, current R-entry state and checkpoint cleanup)
- `docs/roadmap.md`(codex, 2026-05-04, LTO-4 complete / R-entry active roadmap sync;LTO-2 Retrieval Source Scoping And Truth Reuse Visibility Direction Gate proposal)
- `current_state.md`(codex, 2026-05-04, recovery checkpoint sync to post-LTO-4 / R-entry-ready main state)
- `docs/plans/lto-2-retrieval-source-scoping/plan.md`(codex, 2026-05-04, LTO-2 source scoping / truth reuse visibility phase plan;revised after plan_audit)
- `docs/plans/lto-2-retrieval-source-scoping/plan_audit.md`(claude:design-auditor, 2026-05-04, plan gate audit — has-concerns;0 blockers, 5 concerns, 2 nits)
- `.agents/workflows/feature.md` / `.agents/workflows/model_review.md`(deleted) / `.agents/claude/rules.md` / `.agents/claude/role.md` / `.agents/codex/rules.md` / `.agents/codex/role.md` / `.agents/shared/rules.md` / `AGENTS.md` / `.codex/session_bootstrap.md`(claude, 2026-05-04, remove model_review gate layer per Human direction)
