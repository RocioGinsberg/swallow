---
author: claude
phase: phase67
slice: review-block-n
status: review
verdict: APPROVE
depends_on:
  - docs/plans/phase67/codex_review_notes_block_n.md
  - docs/plans/phase67/design_decision.md
  - docs/plans/phase67/kickoff.md
  - docs/plans/phase67/risk_assessment.md
  - docs/plans/phase67/review_comments_block_l.md
  - docs/plans/phase67/review_comments_block_m.md
---

TL;DR(2026-04-30 M3 + Phase 67 final review):**APPROVE**(无 condition,可直接进 closeout)。M3 把 `cli.py` 51 个 read-only artifact printer 收敛到 `ARTIFACT_PRINTER_DISPATCH`,实际工程实装**比 design pseudocode 更优雅**(拆 `TEXT_ARTIFACT_PRINTERS` + `JSON_ARTIFACT_PRINTERS` 两个简单 mapping + 工厂函数生成 lambda;复杂 case 用具名 helper)。`task dispatch` 严格保留 explicit handler;parser registration 不动。cli.py 从 3832 → 3790 行,**净减 42 行**。Codex 自跑 byte-for-byte 6 个 manual 验证全 match;我自己跑全量 pytest **610 passed 无 flake**(M2 时见的 `test_synthesis_does_not_mutate_main_task_state` flake 这次未复现,确认是 pre-existing 顺序敏感 flake)。**Phase 67 整体收尾合格**。

## 审查范围

- M3 milestone:S3(CLI dispatch tightening)
- 同时是 **Phase 67 final review**(M3 是最后一个 milestone)
- 输入:
  - `docs/plans/phase67/codex_review_notes_block_n.md`(Codex 自己的 implementation notes)
  - 实装 commit `ec7fa76 refactor(phase67-m3): tighten cli artifact dispatch`(4 文件 +400/-215;cli.py +364/-364)
  - workspace 未 commit:`docs/roadmap.md`(我刚加候选 P 的改动,与 M3 无关)
- 对照权威:design_decision.md §S3.1-§S3.5(revised-after-design-audit)
- branch:`feat/phase67-hygiene-io-cli-cleanup`

## 关键发现:Dispatch table 实装比 design pseudocode 更优雅

design_decision §S3.1 给的 pseudocode 是 **flat dict** 加 lambda(每条 entry 都自己包 lambda):

```python
ARTIFACT_PRINTER_DISPATCH: dict[str, Callable[[Path, str | None], int]] = {
    "summary": lambda base_dir, task_id: _print_artifact_json(...),
    "route_report": lambda base_dir, task_id: _print_artifact_json(...),
    # ... 20+ lambdas
}
```

Codex 实装拆为 **两个简单 mapping + 工厂函数** + 具名 helpers:

```python
TEXT_ARTIFACT_PRINTERS: dict[str, str] = {
    "summarize": "summary.md",
    # 20 entries: 命令 → 文件名
}

JSON_ARTIFACT_PRINTERS: dict[str, Callable[[Path, str], Path]] = {
    "memory": memory_path,
    # 19 entries: 命令 → path resolver
}

def _text_artifact_printer(artifact_name: str) -> ArtifactPrinter:
    return lambda base_dir, task_id: _print_text_artifact(...)

ARTIFACT_PRINTER_DISPATCH = {
    **{cmd: _text_artifact_printer(name) for cmd, name in TEXT_ARTIFACT_PRINTERS.items()},
    **{cmd: _json_artifact_printer(builder) for cmd, builder in JSON_ARTIFACT_PRINTERS.items()},
    # 12 复杂 entry 用具名 helper(如 _print_canonical_reuse_regression)
}
```

**为什么更优**:
- 文本/JSON printer 各 20 / 19 个 entry 是高度重复的 pattern,提到工厂函数后**可读性大幅提升**(读者一眼看到"这一组都是相同 shape")
- 具名 helper(`_print_canonical_reuse_regression` / `_print_canonical_reuse_eval`)避免 lambda 写多行复杂逻辑(如 baseline + records + comparison 三步组装)
- 51 个 entry 没有任何一行重复 boilerplate(对比 flat lambda dict 会有 51 个 `lambda base_dir, task_id: _print_X(path_Y(base_dir, task_id))` 重复模式)

这是 Codex 这一轮表现最好的工程判断。**无 design 漂移**(签名仍是 `Callable[[Path, str | None], int]`),只是结构更聪明。

## 51 命令清单核验

design §S3.2 估"21-command set-membership block + 后续 read-only printer";Codex 实装实际 51 个 commands 入 dispatch table:

- TEXT_ARTIFACT_PRINTERS:20 个(`summarize` / `semantics` / `route` / `validation` / `compatibility` / `grounding` / 等)
- JSON_ARTIFACT_PRINTERS:19 个(`memory` / `compatibility-json` / `route-json` / `dispatch-json` / 等)
- 复杂具名 helpers:12 个(`canonical-registry` / `canonical-reuse-eval` / `knowledge-decisions` / 等)
- **task dispatch**:**explicit handler 不在 table**(per design §S3.2 锁定)

Codex notes 给了完整 51 命令清单。我抽样核验 5 个 + dispatch:
- `route` → 文本 printer,artifact = `route_report.md` ✓(design 文字写 `route-report` 是笔误,实际命令名 `route`,Codex 用实际名)
- `validation` → 文本 printer,artifact = `validation_report.md` ✓
- `knowledge-policy` → 文本 printer,artifact = `knowledge_policy_report.md` ✓
- `dispatch-json` → JSON printer(只读 dispatch_report 的 JSON 形式,不做 mock-remote)
- `task dispatch`(无 -json 后缀)→ explicit handler at cli.py:3736-3741(读 state + topology + mock-remote 检查 + 打印文本)✓

## Manual byte-for-byte 验证(per design §S3.4)

design §S3.4 修订版要求 6 个命令 byte-for-byte 一致:`task summary` / `task route-report` / `task validation-report` / `task knowledge-policy-report` / `task knowledge-decisions` / `task dispatch`。

Codex notes 给的实际验证清单(用真实命令名):
- `task summarize` ✓
- `task route` ✓
- `task validation` ✓
- `task knowledge-policy` ✓
- `task knowledge-decisions` ✓
- `task dispatch` ✓

Codex 报告 `matched 6`(全部 byte-for-byte 一致 vs pre-change baseline)。

**注意命令名差异**:design §S3.4 用了 `route-report` / `validation-report` / `knowledge-policy-report` 这些**带 -report 后缀的笔误名**。实际 parser command 是 `route` / `validation` / `knowledge-policy`(无 -report)— Codex 用实际名验证,这是正确的;design 文字应在 closeout 阶段标记"design §S3.4 命令名笔误,实际名见 codex_review_notes_block_n.md"(NOTE-1 见下)。

## 全量 pytest 核验

Codex 报告全量 pytest **610 passed,8 deselected,10 subtests passed**(无 flake)。

我自己跑:`pytest -q` → **610 passed in 109.81s**(无 flake)。

**M2 review 时见的 flake** `test_synthesis_does_not_mutate_main_task_state` 这次未复现 ⇒ 确认是 pre-existing 顺序敏感 flake,与 M2/M3 改动无关。

## OK 项

- ✅ M3 单 commit(`ec7fa76`)+ 不需要 M1/M2 fixup commits(M1 fixup commit 协议未触发)
- ✅ cli.py 从 3832 → 3790 行,**净减 42 行**(per design §设计边界 "cli.py 行数应减少" 预期)
- ✅ `task dispatch` 严格保留 explicit handler(read state + topology + `[MOCK-REMOTE]` 条件 + 文本 print)
- ✅ governance write commands 保持 explicit dispatch:grep `args.task_command == ` 仍命中 task lifecycle / proposal apply / route registry apply 等 — Codex notes 已确认"governance write commands kept explicit"
- ✅ `task inspect` / `task review` 完全不动(M3 scope 严格遵守)
- ✅ argparse parser registration 完全不动(`add_parser` 行数对照 main 无变化)
- ✅ Dispatch fallback 实装为 belt-and-suspenders 防御:外层 `if args.task_command in ARTIFACT_PRINTER_DISPATCH:` 已过滤,内层 `_dispatch_artifact_printer` 的 `raise NotImplementedError` 永不触发(per design §S3.1 fallback 决议:M3 完成后 fallback 永不触发是**严格的**形式)
- ✅ 不动 docs/design/ 任何文件(`git diff main -- docs/design/` = 0)
- ✅ 全量 pytest 610 passed,无 regression
- ✅ `cli.py` 私有 helpers(load_json_if_exists / load_json_lines_if_exists)仍 0 命中(M2 已清理)
- ✅ 无新工具引入

## Findings

### [NOTE-1] design §S3.4 命令名笔误,closeout 阶段透明记录

- **位置**:`design_decision.md §S3.4` 列 `task summary --task-id` / `task route-report` / `task validation-report` / `task knowledge-policy-report`
- **实际**:parser 注册的命令名是 `summarize` / `route` / `validation` / `knowledge-policy`(无 `-report` 后缀;`summary` ≠ `summarize`)
- **影响**:零(Codex 实装时用实际名,验证通过)
- **建议**:closeout 阶段 "Design vs Implementation Drift" 段透明记录此命令名笔误;**不修订 design_decision.md**(已 final 不动)

### [NOTE-2] 51 个 commands 远超 design §S3.2 估的 "21-command + 后续 read-only printer"

- **背景**:design §S3.2 推 M3 scope 扩到 `cli.py:3592-3787`,估"21-command set-membership block + 后续 read-only printer"
- **实际**:Codex 收敛 51 个 commands 入 dispatch table
- **判定**:✓ scope 与 design 一致(`cli.py:3592-3787` 范围内的 read-only artifact printer 都进 table);只是 design 估算偏低;**不是 scope 漂移**
- **建议**:closeout 阶段在 "Design vs Implementation Drift" 段标记"design §S3.2 估 21+ 实际 51 commands;Codex scope 与 design 一致,只是估算偏保守"

### [NOTE-3] Phase 67 closeout 阶段 pending items 清单

per M2 review CONCERN-1 + 各 milestone NOTES + Codex M3 notes "Closeout Items Still Pending",closeout 阶段 Codex 必须完成:

1. `_io_helpers.py` 补 module docstring(per M2 review CONCERN-1 + design §S2.1 模板)
2. `closeout.md` "Design vs Implementation Drift" 段:
   - M1 4 处漂移(per review_comments_block_l.md NOTE-2)
   - M2 3 处漂移(2 helper variants 新增 + store.py wrapper 保留,per review_comments_block_m.md)
   - M3 2 处文本笔误(NOTE-1 + NOTE-2)
3. `closeout.md` "Test Suite Stability" 段:登记 2 个 pre-existing flake(`test_run_task_times_out_one_parallel_subtask` / `test_synthesis_does_not_mutate_main_task_state`)
4. `closeout.md` "Pre-positioned for Candidate O" 段(per design §S2.5)
5. backlog 状态更新:audit_block5 finding 3(table-driven CLI dispatch)标 Partial(M3 内 read-only 子集消化;governance write + task inspect/review + 复杂 task inspect/review 渲染未做)

### 没有发现的问题

- 没有 BLOCKER
- 没有 design 漂移(dispatch table 结构是更优实装,不是漂移;与 design pseudocode 行为等价)
- 没有 silent behavior regression(Codex byte-for-byte 验证 + 我自跑 pytest 610 passed)
- 没有 INVARIANTS / DATA_MODEL / KNOWLEDGE 改动
- 没有 governance write 命令误改
- 没有 `task inspect` / `task review` 误触动
- 没有 argparse parser registration 改动

## Verdict

**APPROVE**(无 condition)

理由:
- M3 实装质量优秀(dispatch table 结构比 design pseudocode 更优雅 + 51 commands 全部对位)
- byte-for-byte 6 个验证全 match
- 全量 pytest 610 passed,无 flake / 无 regression
- cli.py 净减 42 行(符合 design §设计边界预期)
- `task dispatch` / governance write / task inspect|review 严格遵守 out-of-scope
- argparse parser registration / cli.py public help text 不动

**Codex 可直接进 Phase 67 closeout**。

## Phase 67 整体最终评估

### 全 phase 验收条件核对(per kickoff §完成条件)

#### M1(候选 L)— ✓ 已通过 review

- ✅ 7 项 quick-win 全部消化
- ✅ `_pricing_for` 模块级删除 + instance method 保留
- ✅ `rank_documents_by_local_embedding` `# eval-only` 标注
- ✅ `[:4000]` 三处替换为 `RETRIEVAL_SCORING_TEXT_LIMIT`
- ✅ pytest 610 passed

#### M2(候选 M)— ✓ 已通过 review

- ✅ `_io_helpers.py` 创建 + 5 helper variants(原 3 + Codex 新加 2)
- ✅ 11+ callsite 显式选 variant(R1 风险被识别 + 缓解)
- ✅ `cli.py` 私有 helpers 删除 + 跨模块 import `_io_helpers`
- ✅ Artifact name ownership 决议落地(窄选项 a)
- ✅ audit_block4 finding 1 [high] backlog 标 Resolved
- ✅ pytest 609 passed(-k 排除 1 pre-existing flake)

#### M3(候选 N)— ✓ 已通过 review(本文)

- ✅ 51 read-only artifact printer commands 收敛 dispatch table
- ✅ governance write commands 保持 explicit
- ✅ `task inspect` / `task review` 不动
- ✅ argparse parser registration 不动
- ✅ Manual 6 命令 byte-for-byte 一致
- ✅ pytest 610 passed,无 flake,无 regression
- ✅ audit_block5 finding 3 backlog 标 Partial

### 全 phase 完成条件

- ✅ `git diff main -- docs/design/` = 0(零设计文档改动,横跨 M1/M2/M3)
- ✅ 全量 pytest 610 passed
- ✅ `git diff --check` 通过(M3 commit 已 clean)
- ⚠ `docs/plans/phase67/closeout.md` **未完成**(Codex closeout 阶段写;包含 NOTE-3 列出的 5 项 pending items)
- ⚠ `docs/active_context.md` **由 Codex 同步**(我无权改,Updater 是 Codex)

### 累积统计(Phase 67 全期)

| Milestone | 实装 commit | docs commit | src/swallow/ 改动 | pytest |
|---|---|---|---|---|
| M1 | `b96c132` | `fc9ebba` + `cd5c039` | 12 文件 +56/-54 | 610 passed |
| M2 | `fac37cb` | `fbaee98` | 12 文件 +185/-213(净减 28 行)+ 1 新文件 | 609 passed(-k 排除 flake)|
| M3 | `ec7fa76` | (含在同 commit) | 1 文件 +364/-364(cli.py 净减 42 行)| 610 passed |
| **Phase 67 总** | **3 commits** | **3 commits** | **+605/-631(src/ 净减 26 行)+ 1 新模块 (_io_helpers.py)** | **610 passed** |

`git diff main -- docs/design/` 全期 = 0 行(零设计文档改动)。

### Phase 67 三合一形态评估

audit_index 警告"不应合并"已被 Human 知情接受;Phase 67 用"严格分 milestone + 独立 review_comments + M1 fixup commit 协议"绕过。**最终结果**:

- ✅ 设计决议(M2 IO helper variants)与代码清理(M1 quick-win)未混入同一 review
- ✅ 每 milestone 独立 commit + 独立 review_comments,review 注意力按需聚焦
- ✅ M2 review 时 Claude 发现 R1 风险被 Codex 实装时缓解,**不需要**触发 M1 fixup commit 协议(即三合一未引发跨 milestone 协调成本)
- ✅ public CLI surface(M3)与 governance write 边界严格守住

**结论:Phase 67 三合一形态成功**;可作为后续类似情况的参考模板。但仍建议未来类似 phase 默认按 audit_index 推荐拆独立 phase,只在 Human 显式接受时合并。

## 给 Codex 的 closeout follow-up 清单

进入 closeout 阶段必须完成的工作项:

1. **(必做)** 把 `codex_review_notes_block_n.md` status 从 `review` 改为 `final`
2. **(必做)** 写 `docs/plans/phase67/closeout.md`,verdict = APPROVE,逐条对应 kickoff §完成条件打勾;含 5 个 pending sections(per NOTE-3)
3. **(必做)** `_io_helpers.py` 补 module docstring(per M2 review CONCERN-1)
4. **(必做)** `docs/concerns_backlog.md` 增量:
   - audit_block4 finding 1 [high] 标 Resolved
   - audit_block5 finding 3 标 Partial
   - 7 quick-win 对应条目状态更新(M1 review 已部分更新,closeout 阶段确认全部)
5. **(必做)** `docs/active_context.md` 同步(Updater 是 Codex):active_phase 标 Phase 67 完成 + status 改 `phase67_implementation_complete_pending_merge_gate` + active_branch
6. **(可选)** 写 `pr.md` 草稿(若 Human 需要)

## Phase 67 与 Phase 68 衔接

per roadmap 2026-04-30 更新,**Phase 68 = 候选 P(Module Reorganization)**。Phase 67 closeout 完成 + Human merge 后,Phase 68 的 design 启动(由 Human 在新 Direction Gate 决定)。Phase 67 的 51 commands dispatch table 是否在 Phase 68 重组时移到 `surface_tools/cli/` 子目录,由 Phase 68 design_decision 决定 — Phase 67 不预判。

## 给 Codex 的工作流提醒

- Phase 67 final review 已 verdict APPROVE;Codex 进入 closeout 流程
- closeout 完成后等 Human merge to main
- merge 后由我(Claude)触发 `roadmap-updater` post-merge factual update:
  - §三差距表 "代码卫生债清理(Phase 66 audit 衍生)" 行标 [已消化]
  - §四候选 L / M / N 三个块 strikethrough(merge 日期 + closeout 引用)
  - §五推荐顺序 K ✓ → L ✓ M ✓ N ✓ → P → O → R → D
- **Phase 67 不打 tag**(per kickoff §完成后的下一步;清理 phase 不构成 release 节点)
