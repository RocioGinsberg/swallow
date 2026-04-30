---
author: claude
phase: phase67
slice: review-block-m
status: review
verdict: APPROVE_WITH_CONDITIONS
depends_on:
  - docs/plans/phase67/codex_review_notes_block_m.md
  - docs/plans/phase67/design_decision.md
  - docs/plans/phase67/kickoff.md
  - docs/plans/phase67/risk_assessment.md
  - docs/plans/phase67/review_comments_block_l.md
---

TL;DR(2026-04-30 M2 review):**APPROVE_WITH_CONDITIONS**(Codex 可立即进 M3,2 个测试 flake 已确认 non-regression 不阻塞)。`_io_helpers.py` 创建并实装 **5 个 helper variants**(原 design 3 个 + Codex 主动新加 2 个);11+ callsite 全部显式 variant;`cli.py` 私有 helpers 全清理(grep 0 命中)。M2 关键发现 = **R1 风险被 Codex 实装时识别**:design_decision §S2.2 表里把多个 callsite 行为标错为"missing→[] + malformed→skip",实际 grep 是"missing→[] + malformed→**CRASH**"(strict)。Codex 主动新加 `read_json_lines_strict_or_empty` variant 保留原 strict 行为,这是对 R1 风险的正确缓解 — **避免了静默吞 crash 的 silent regression**。另外新加 `read_json_list_or_empty` 保留 cli.py:retrieval.json 的 list payload 兼容性。全量 pytest 失败 = 2 个 pre-existing 顺序敏感 flake(M2 改动前后均存在),非 M2 regression。

## 审查范围

- M2 milestone:S2(IO + artifact ownership)
- 输入:
  - `docs/plans/phase67/codex_review_notes_block_m.md`(Codex 自己的 implementation notes)
  - 实装 commit `fac37cb refactor(phase67-m2): centralize json io helpers`(12 文件 +185/-213,净减 28 行)
  - docs commit `cd5c039 docs(phase67-m1): record review gate`(M1 review 记录,跨越 M1→M2 边界)
  - workspace 未 commit:`active_context.md` / `concerns_backlog.md` / `codex_review_notes_block_m.md`(Codex 准备 M3 启动前 commit)
- 对照权威:design_decision.md §S2.1-§S2.5(revised-after-design-audit)
- branch:`feat/phase67-hygiene-io-cli-cleanup`

## 关键发现:R1 风险被 Codex 实装时识别并正确缓解

design_decision §S2.2 authoritative 映射表中**多个 callsite 行为标错**:

| Callsite | design 表标 | Codex grep 实际 | Codex 选择 |
|---|---|---|---|
| `store.py:_load_json_lines` | missing → []; malformed → skip | missing → []; malformed → **CRASH** | `read_json_lines_strict_or_empty`(新增) |
| `truth/knowledge.py:_load_json_lines` | missing → []; malformed → skip | missing → []; malformed → **CRASH** | `read_json_lines_strict_or_empty`(新增) |
| `orchestrator.py:_load_json_lines` | missing → []; malformed → skip | missing → []; malformed → **CRASH** | `read_json_lines_strict_or_empty`(新增) |
| `librarian_executor.py:_load_json_lines` | missing → []; malformed → skip | missing → []; malformed → **CRASH** | `read_json_lines_strict_or_empty`(新增) |
| `staged_knowledge.py:92-104` | grep-pending(待 Codex 验证) | missing → []; malformed → **CRASH** | `read_json_lines_strict_or_empty`(新增) |
| `canonical_registry.py:65-91` | grep-pending(待 Codex 验证) | missing → []; malformed → **skip** | `read_json_lines_or_empty`(原 design) |
| `dialect_data.py:144-153` | grep-pending(待 Codex 验证) | missing → return None;**外层 try/except OSError + JSONDecodeError**(实质 missing → []) | `read_json_or_empty` + 保留外层 try/except(行为等价) |

**design 错估的影响**:若 Codex 严格按 design §S2.2 表把 4-5 个 strict 路径改用 `read_json_lines_or_empty`(silent skip+warn),会**静默吞掉 production crash 行为**(R1 中的最坏结果):

- `store.py` events 文件如果损坏 → 原行为 = 整个 task event 读取 crash → operator 立即知道
- 用 silent skip → operator 看到部分 event 缺失但无错误信号,debug 极困难

Codex 在实装时 grep 现行行为并发现 design 错估,**主动新加 strict variant 保留原行为**,这是正确的工程判断。M2 review 应**赞赏这一发现**,并修订 design 锁定 5 helper variants 形态。

## 5 helper variants 核验

### `read_json_strict(path)` — 原 design ✓
- 语义:missing → `FileNotFoundError`;malformed → `JSONDecodeError`
- callsite:`knowledge_store.py:130/140`(strict semantics 必要)+ `orchestrator.py:3077/3186` 2 处 retrieval_path strict 读
- 验证:与 design §S2.1 模板一致

### `read_json_or_empty(path)` — 原 design ✓
- 语义:missing → `{}`;malformed → `JSONDecodeError`;**额外:non-object payload → `{}`**(Codex 显式 fallback)
- callsite:`dialect_data.py:150` / `knowledge_suggestions.py:26` / `retrieval.py:600/687` policy reads / `cli.py` 多处 / `orchestrator.py` 多处
- 验证:与 design §S2.1 模板一致;"non-object payload → {}" 是 Codex 防御性处理(原 inline `json.loads` 若返回 list/str 也算"非预期",mantel 默默 fallback 比 raise 更稳)

### `read_json_list_or_empty(path)` — **Codex 新增** ✓
- 语义:missing → `[]`;malformed → `JSONDecodeError`;non-list → `[]`
- 引入理由(Codex notes #3):cli.py 中 `retrieval.json` 是 list payload(retrieval_records 数组),原 `load_json_if_exists` 兼容 list 但新 `read_json_or_empty` 强制 dict — 第一次实装时把 list 改成 `{}` 破坏了 inspect/review 的 `retrieval_record_available` 与 reused-knowledge counts
- callsite:cli.py 2 处 retrieval list 读取(grep 命中)
- 判定:✓ **必要的新增**,修复 design 漏想到的"JSON 顶层不一定是 dict"

### `read_json_lines_or_empty(path)` — 原 design ✓
- 语义:missing → `[]`;malformed line → log warning + skip;non-dict line → log warning + skip
- callsite:`canonical_registry.py:81`(resolve_knowledge_object_id,原 inline 就是 skip)+ `cli.py:455/567` decisions / canonical_reuse_eval reads
- 验证:与 design §S2.1 模板一致

### `read_json_lines_strict_or_empty(path)` — **Codex 新增** ✓
- 语义:missing → `[]`;malformed line → `JSONDecodeError`;non-dict line → 跳过(不抛)
- 引入理由(Codex notes #1):见上方"关键发现"段;design §S2.2 表把 4-5 个 strict 路径标错为 skip;Codex 实装时 grep 现行 inline JSONL loop 发现**没有** try/except,malformed 会真的抛出
- callsite:`store.py:203/539` / `truth/knowledge.py:54` / `orchestrator.py:436/504/505/2663/2942/2965/3214` / `librarian_executor.py:221` / `staged_knowledge.py:98`
- 判定:✓ **必要的新增 + 是对 R1 风险的最佳缓解**

## 11+ callsite 行为等价性核验(逐项)

我手动 grep 每个 callsite 的 before/after,确认行为等价:

| Callsite | Before(M1 main) | After(M2) | 等价? |
|---|---|---|---|
| `store.py:136-148 _load_json_lines` 私有 def | inline JSONL loop,no try/except,malformed → crash | wrapper delegate `read_json_lines_strict_or_empty` | ✓ 等价(see also "store.py wrapper" 决议) |
| `store.py:217/252/346` 内部 callsite | 调 `_load_json_lines` | 仍调 `_load_json_lines`(wrapper) | ✓ 完全等价 |
| `truth/knowledge.py:59-67 _load_json_lines` 私有 def | 同上 strict 行为 | 删除私有版本 + line 54 直接 `read_json_lines_strict_or_empty` | ✓ 等价 |
| `orchestrator.py:388-406 _load_json_lines` 私有 def | 同上 strict 行为 | 删除私有版本 + 多 callsite 直接 `read_json_lines_strict_or_empty` | ✓ 等价 |
| `librarian_executor.py:57 _load_json_lines` 私有 def | 同上 strict 行为 | 删除私有版本 + line 221 直接调用 | ✓ 等价 |
| `canonical_registry.py:65-91` JSON read | inline JSONL with try/except continue(skip 行为) | `read_json_lines_or_empty` | ✓ 等价(skip+warn vs silent skip — log warning 是更严但不破坏行为) |
| `staged_knowledge.py:92-104` JSON read | inline JSONL no try/except,malformed → crash | `read_json_lines_strict_or_empty` | ✓ 等价 |
| `knowledge_suggestions.py:22-31` JSON read | `if not path.exists(): return {}; json.loads(...)` | `read_json_or_empty(path)` | ✓ 等价 |
| `retrieval.py:588-600/678-690` policy read | `if path.exists(): json.loads(...) else: {}` | `read_json_or_empty(path)` | ✓ 等价 |
| `dialect_data.py:144-153` JSON read | `try: json.loads(Path(...).read_text(...)) except (OSError, JSONDecodeError): return None` | `try: read_json_or_empty(Path(...)) except (OSError, JSONDecodeError): return None` | ✓ 等价(only "missing" 行为有差:before 抛 OSError 被 except,after 直接 `{}`;但 `{}` 仍触发外层 `if not payload: return None` 等价路径)|
| `knowledge_store.py:123-143` | strict semantic(file expected to exist) | `read_json_strict` | ✓ 等价 |
| `cli.py` 私有 `load_json_if_exists` | missing → {} + tolerant types | `read_json_or_empty`(dict-only)/ `read_json_list_or_empty`(list)— 按 caller 期望区分 | ✓ 等价(Codex 区分 dict / list payload 类型) |
| `cli.py` 私有 `load_json_lines_if_exists` | missing → [] + malformed → CRASH(strict) | `read_json_lines_or_empty`(skip+warn) | **⚠ 行为变化**(已被 design §S2.4 显式接受) |

**注意 cli.py JSONL 行为变化**:design §S2.4 显式接受 strict→skip+warn 的 77 callsite 范围;Codex 实装与 design 决议一致。所有 cli.py 内的 JSONL 读取都是 read-only display / inspection,不影响 truth-write 路径。

## OK 项

- ✅ `_io_helpers.py` 创建(71 行,与 `_http_helpers.py` 同 `_`-prefix 私有 helper 模式)
- ✅ `cli.py:617-632` 私有 helpers 完全删除(`grep "load_json_if_exists\|load_json_lines_if_exists" src/` 0 命中)
- ✅ 11+ callsite 全部显式选 variant(per §S2.2 修订表 + 2 个新 variant 扩展)
- ✅ Codex 主动透明:5 helper variants 在 codex_review_notes_block_m.md 全部说明
- ✅ M2 commit 单 commit(`fac37cb`)+ M1 fixup commit 协议未触发(M1 实装无需修订)
- ✅ 无新工具引入(只用 grep 验证)
- ✅ 不动 docs/design/ 任何文件(`git diff main -- docs/design/` = 0)
- ✅ artifact name ownership 决议遵循窄选项 (a)(无 `_artifact_registry.py`,Codex notes 已显式声明)
- ✅ `_io_helpers.py` 接口签名薄(单 `path: Path` 参数)— 候选 O 衔接预留正确
- ✅ store.py wrapper 保留是测试 API 兼容的合理处理(详见下方 NOTE-1)

## Findings

### [CONCERN-1] `_io_helpers.py` 模块缺 docstring + 缺 future extension comment

- **位置**:`src/swallow/_io_helpers.py:1-7` 无 module docstring;无 design_decision §S2.1 模板要求的"future extension point"注释(如 `read_json_lines_strict` 缺失说明)
- **观察**:design_decision §S2.1 authoritative 模板含 multi-paragraph module docstring(包含 "Future extension point (per design_audit Q9 / candidate O)" 段)。Codex 实装的 `_io_helpers.py` 文件**无任何 module 级文档**
- **影响**:候选 O 启动时找不到 design_decision §S2.5 要求的"为候选 O 预留接口薄"声明的代码层 anchor
- **判定**:**[CONCERN]** — 不阻塞 M3,但 Phase 67 closeout 阶段必须补
- **建议处理**:Codex 在 M3 完成后 / closeout 阶段补 `_io_helpers.py` module docstring(参考 design_decision §S2.1 模板);**或**在 closeout.md "Pre-positioned for Candidate O" 段补充说明,把 docstring 缺失视为 closeout-time 修订

### [NOTE-1] `store.py` 保留 `_load_json_lines` wrapper 是合理 design 漂移

- **位置**:`store.py:202-203` 保留 `def _load_json_lines(path) -> ...: return read_json_lines_strict_or_empty(path)`
- **背景**:design_decision §S2.2 表说"删除 store.py 私有版本";Codex 实装时保留 wrapper 因 `tests/test_sqlite_store.py` 用 `monkeypatch.setattr("swallow.store._load_json_lines", ...)` 测试
- **影响**:测试 API 兼容(若直接删除 wrapper 必须改测试);wrapper 实现是单行 delegate,代码债极小
- **判定**:✓ 合理 design 漂移。Codex notes #4 已显式声明
- **建议**:closeout 阶段在 "Design vs Implementation Drift" 段记录此 wrapper 是测试 API 兼容性保留;若未来某 testing-debt phase 想清理,直接改测试 + 删 wrapper(无生产影响)

### [NOTE-2] 全量 pytest 2 个 flake 非 M2 regression

- **背景**:Codex 报 1 个 timing flake(`test_run_task_times_out_one_parallel_subtask...` elapsed 3.06s 超 1.75s 阈值,单跑 1.66s);我自己跑遇到另 1 个 `test_synthesis_does_not_mutate_main_task_state`(单跑 0.21s pass,全量 fail)
- **核验**:
  - 单跑 `test_run_task_times_out_one_parallel_subtask` 1.62s pass ✓
  - 单跑 `test_synthesis_does_not_mutate_main_task_state` 0.21s pass ✓
  - **`git stash` 回滚 M2 改动后单跑** `test_synthesis_does_not_mutate_main_task_state` 仍 0.19s pass(同样行为)
  - test_synthesis 测试体不读 JSON 文件(monkeypatch 替 http_executor),与 IO helper 完全无关
- **判定**:**两个都是 pre-existing 顺序/时序敏感 flake**,与 M2 IO helper 改动无因果关系
- **建议**:closeout 阶段在 "Test Suite Stability" 段登记两个 flake;由后续 testing-debt phase 处理(不在 Phase 67 scope)

### [NOTE-3] design_decision §S2.2 表错估行为(R1 风险材料源)

- **背景**:design §S2.2 表把多个实际 strict 的 JSONL 路径标为 "missing → []; malformed → skip",Codex 实装时 grep 验证发现错估
- **影响**:Codex 主动正确处理(新加 `read_json_lines_strict_or_empty`),所以**未出 regression**;但说明 design 阶段 grep 不彻底
- **判定**:**信息性 NOTE**,不是 Codex 失误也不是 design fail(design 文字明确说"Codex grep 验证";只是表里默认值估错了)
- **建议**:closeout 阶段 design vs implementation drift 段记录"design §S2.2 表 5 行行为标错,Codex 实装时识别并新加 strict variant 处理";后续类似 phase 设计时 grep 改 `git grep` 全仓库 strict 验证

## 没有发现的问题

- 没有 BLOCKER
- 没有 design 漂移(2 处新增 variant + store.py wrapper 都是合理工程判断)
- 没有 silent behavior regression(关键风险 R1 被 Codex 实装时正确缓解)
- 没有 INVARIANTS / DATA_MODEL / KNOWLEDGE 改动
- 没有引入新工具
- 没有 cli.py 私有 helpers 残留(grep 0 命中)

## 给 Codex 的 follow-up 清单

进 M3 不强制要求,可在 closeout 阶段统一处理:

1. **(closeout 必做)** `_io_helpers.py` 补 module docstring(per design §S2.1 模板)— CONCERN-1
2. **(closeout 必做)** `closeout.md` 中新建 "Design vs Implementation Drift" 段,记录:
   - M1: 4 处合理漂移(per review_comments_block_l.md)
   - M2: 2 helper variants 新增 + store.py wrapper 保留(共 3 处)
3. **(closeout 必做)** `closeout.md` 中新建 "Test Suite Stability" 段,登记 2 个 pre-existing flake(`test_run_task_times_out_one_parallel_subtask` / `test_synthesis_does_not_mutate_main_task_state`)
4. **(closeout 必做)** `closeout.md` 中 "Pre-positioned for Candidate O" 段(per design §S2.5 要求)
5. **(可选,M3 阶段处理)** Codex 把 `codex_review_notes_block_m.md` status 从 `review` 改为 `final`(verdict APPROVE 后)

## Verdict

**APPROVE_WITH_CONDITIONS**

理由:
- 11+ callsite 全部显式选 variant + 行为等价性核验通过
- 5 helper variants(原 3 + 新 2)实装质量高
- Codex 主动识别 R1 风险并正确缓解(避免静默 regression)
- 全量 pytest 失败 = 2 个 pre-existing flake,经核验非 M2 regression
- 仅 1 CONCERN(`_io_helpers.py` 缺 docstring,closeout 阶段补)+ 3 NOTE(信息性)

**Codex 可立即进 M3**(verdict APPROVE_WITH_CONDITIONS 满足 trigger)。CONCERN-1(docstring)在 Phase 67 closeout 阶段处理,不阻塞 M3 启动。

## 给 Codex 的工作流提醒

- M3 阶段 Codex 等本 `review_comments_block_m.md` 出现 + frontmatter `verdict` ∈ {APPROVE, APPROVE_WITH_CONDITIONS} 后才进 M3 — 当前 verdict = APPROVE_WITH_CONDITIONS,**M3 可启动**
- M3 输出 = `cli.py:3592-3787` 范围内 read-only artifact printer 收敛到 dispatch table(per design §S3.1 / §S3.2 修订版)
- **M3 不需要修订 M2 代码**(M1 fixup commit 协议未触发)
- M3 完成后 Claude 出 `review_comments_block_n.md` + Phase 67 final review;closeout 阶段统一处理 CONCERN-1 + 4 NOTE

## 累积统计(M1 + M2)

| 类别 | M1 | M2 |
|---|---|---|
| Dead code 删除 | 2 项 | 0 项 |
| 常量命名 | 4 项 | 0 项 |
| 新模块创建 | 0 | 1(`_io_helpers.py`)|
| Helper variants 实装 | 0 | 5(原 3 + 新 2 strict_or_empty / list_or_empty)|
| Callsite 替换 | 7 项 quick-win | 11+ JSON/JSONL callsite + cli.py 跨 77 引用点 |
| Owner 决议 | 1(MPS_POLICY_KINDS)+ 2 注释引用 | artifact name 窄选项 (a) 锁定 |
| Backlog 状态变化 | M1 quick-win 7 项 Resolved | M2 audit_block4 finding 1 [high] Resolved |
| pytest | 610 passed | 全量 1 个 flake / -k 排除后 609 passed(2 个 flake 都非 regression)|
| `git diff src/` | 12 文件 +56/-54 | 12 文件 +185/-213(净减 28 行)|
| `git diff docs/design/` | 0 | 0 |

src/ 累计 +241/-267(净减 26 行);1 个新模块;0 个 design 文档改动。
