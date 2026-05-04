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
- active_track: `R-entry Real Usage`
- active_phase: `r-entry-real-usage`
- active_slice: `real usage findings captured;direction gate candidates ready`
- active_branch: `main`
- status: `r_entry_findings_ready`

## 当前状态说明

当前 git 分支为 `main`。LTO-4 Test Architecture 已 merge 到 `main`;本轮进入 R-entry 真实使用验证,不触发新开发 phase,不走 plan audit / review / closeout,不 cut tag。

Codex 已产出 `docs/plans/r-entry-real-usage/plan.md`,作为本轮真实使用 runbook。R-entry 本机可执行部分已完成并整理到 `docs/plans/r-entry-real-usage/findings.md`:CLI task / knowledge / Wiki Compiler / promotion / retrieval 链路已跑通到真实问题定位;本机 Web UI smoke 通过;Wiki LLM 与 OpenRouter rerank 已验证可用;nginx/Tailscale 仍需 Human 在 host nginx 与第二台 tailnet 设备上执行。

LTO-4 已完成 M1-M4:CLI command-family split、shared builders/assertions、AST guard helper extraction、global builder fixture entry。最终 `collect-only` 为 `806/825 tests collected (19 deselected)`,比 LTO-4 起始 baseline `802/821` 增加 4 个 helper self-tests,没有测试数量减少。最终全量 pytest `806 passed, 19 deselected in 131.76s`,real `2m12.909s`,处于 LTO-4 允许耗时区间内。完成后不触发后续 phase,不 cut tag;下一步只进入真实使用 R-entry。

最近稳定 checkpoint:

- LTO-2 Retrieval Quality / Evidence Serving 已 merge 到 `main` at `03744f0`;post-merge state sync 已提交为 `a3c1844`。
- LTO-4 Test Architecture 已 merge / synced 到 `main` at `ac2d3ff`;历史 phase 文档已归档到 `docs/archive_phases/`。
- R-entry Real Usage 不是开发 phase;本轮唯一计划入口为 `docs/plans/r-entry-real-usage/plan.md`。

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

待执行:

- **[Human]** 审阅 `docs/plans/r-entry-real-usage/findings.md`,决定下一轮 Direction Gate 是否优先进入 Retrieval Source Scoping And Truth Reuse Visibility。
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

- 无 blocker。R-entry plan ready;等待 Human 按 runbook 执行真实使用验证。

## Tag 状态

- 最新已执行 tag: **`v1.8.0`**
- tag target: `d6f2442 docs(release): sync v1.8.0 release docs`
- 标记意义: **LTO-1 Wiki Compiler 第一阶段落地**。
- LTO-1 第二阶段已 merge,但 roadmap / review 建议不单独 cut tag。
- LTO-2 已 merge,Claude review 建议不单独 cut tag。
- LTO-4 已完成,压缩流程不 cut tag。
- 下一 tag: 无 pending decision;后续可在 R-entry 反馈触发的产品 phase 完成后再评估 `v1.9.0`。

## 当前下一步

1. **[Human]** 审阅 `docs/plans/r-entry-real-usage/findings.md`。
2. **[Human]** 决定下一轮 Direction Gate 的优先方向;当前 Codex 建议首选 `Retrieval Source Scoping And Truth Reuse Visibility`。
3. **[Human]** 可选执行 R9 host nginx/Tailscale smoke,补齐个人 tailnet UI 展示验证。

```markdown
compressed_gate:
- active_phase: r-entry-real-usage
- active_slice: real usage findings captured;direction gate candidates ready
- active_branch: main
- status: r_entry_findings_ready
- latest_completed_phase: lto-4-test-architecture
- latest_completed_commit: ac2d3ff docs(state): mark lto4 r-entry ready
- latest_history_archive_commit: 795aa4d docs(store): move history plans to archive
- latest_release_tag: v1.8.0 at d6f2442 docs(release): sync v1.8.0 release docs
- workflow: R-entry runbook;no plan_audit.md / review_comments.md / closeout.md;issue log drives next Direction Gate
- boundary: docs/plans/r-entry-real-usage/plan.md is current runbook
- baseline_count: 802/821 collected;19 deselected
- current_count: 806/825 collected;19 deselected
- final_full_pytest: 806 passed, 19 deselected in 131.76s; real 2m12.909s
- r_entry_plan: docs/plans/r-entry-real-usage/plan.md
- findings: docs/plans/r-entry-real-usage/findings.md
- next_gate: Human reviews findings and selects next Direction Gate priority
```

## 当前产出物

- `docs/plans/r-entry-real-usage/plan.md`(codex, 2026-05-04, R-entry real usage runbook for design-doc knowledge chain, CLI, UI, nginx/Tailscale smoke, and issue logging)
- `docs/plans/r-entry-real-usage/findings.md`(codex, 2026-05-04, R-entry real usage findings and Direction Gate candidates)
- `docs/active_context.md`(codex, 2026-05-04, current R-entry state and checkpoint cleanup)
- `docs/roadmap.md`(codex, 2026-05-04, LTO-4 complete / R-entry active roadmap sync)
- `current_state.md`(codex, 2026-05-04, recovery checkpoint sync to post-LTO-4 / R-entry-ready main state)
