---
author: claude/context-analyst
phase: phase67
slice: context-brief
status: draft
depends_on:
  - docs/roadmap.md
  - docs/active_context.md
  - docs/concerns_backlog.md
  - docs/plans/phase66/audit_index.md
  - docs/plans/phase66/audit_block1_truth_governance.md
  - docs/plans/phase66/audit_block2_orchestration.md
  - docs/plans/phase66/audit_block3_provider_router.md
  - docs/plans/phase66/audit_block4_knowledge_retrieval.md
  - docs/plans/phase66/audit_block5_surface_tools.md
  - docs/plans/phase66/closeout.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
  - docs/design/KNOWLEDGE.md
---

TL;DR: Phase 67 is a three-milestone cleanup phase (M1 = 7 quick-wins / M2 = IO + artifact ownership design+impl / M3 = CLI dispatch tightening). Milestones map to audit_index candidates L, M, N respectively. Human accepted the consolidated structure at the 2026-04-30 Direction Gate with strict milestone isolation as the minimum-violation form. Total phase risk = medium, driven by M2 IO helper design and M3 public CLI surface change; M1 alone is low risk. Recommended branch: `feat/phase67-hygiene-io-cli-cleanup`.

## 为什么不是分三个 Phase

`audit_index.md §Recommended Next Phase Seeds` 明确警告:"Do not combine all design-needed themes into one cleanup phase. The cross-block ownership items touch enough public surface that they should be split." 然而 Human 在 2026-04-30 Direction Gate 知情接受了合并,选择"严格分 milestone"作为最弱违反形式:每个 milestone 独立 commit + 独立 review_comments(类比 Phase 66 M1/M2/M3),milestone 之间有 Claude review checkpoint 作为隔离门控。audit_index 警告的核心风险点(设计决议与代码清理混入同一 review、CLI public surface 与 governance write 混同)被 milestone 分隔抵消。

## 变更范围

**M1 — 候选 L:Small Hygiene Cleanup**

直接影响文件:

| 文件 | 变更性质 |
|------|---------|
| `src/swallow/review_gate.py` | 删除 `run_consensus_review(...)` (line 617-632) |
| `src/swallow/cost_estimation.py` | 删除模块级 `_pricing_for(...)` (line 34-42) 或让 `StaticCostEstimator` delegate |
| `src/swallow/retrieval_adapters.py` | 将 `rank_documents_by_local_embedding(...)` (line 249-292) 移至 eval/test support 路径或接入生产 |
| `src/swallow/sqlite_store.py` | 提取 `SQLITE_CONNECT_TIMEOUT_SECONDS = 5.0` / `SQLITE_BUSY_TIMEOUT_MS = 5000` 常量 (lines 281/327/358/367/370/377/885) |
| `src/swallow/mps_policy_store.py` | 已有 `MPS_POLICY_KINDS` 常量 (line 15) |
| `src/swallow/cli.py` | CLI 改从 `mps_policy_store.MPS_POLICY_KINDS` import (当前 line 1315 手动重复) |
| `src/swallow/retrieval.py` + `src/swallow/retrieval_adapters.py` + `src/swallow/ingestion/pipeline.py` | 命名 preview/scoring 截断常量 (`[:220]` / `[:4000]` / `> 80`);retrieval.py lines 423/645/875/883;retrieval_adapters.py lines 267/312;ingestion/pipeline.py line 292 |
| `src/swallow/orchestrator.py` + `src/swallow/review_gate.py` + `src/swallow/planner.py` + 相关模块 | 集中化或文档化 orchestration timeout/card defaults;orchestrator.py:189 (`DEBATE_MAX_ROUNDS=3`) 已命名;review_gate.py:16 (`DEFAULT_REVIEWER_TIMEOUT_SECONDS=60`) 已命名;models.py:641 (`reviewer_timeout_seconds: int = 60`) 与 review_gate 值重复;executor.py:1167/1287/1428/1554 (`"20"` 重复 4 次);planner.py:8 (`MAX_SUBTASK_CARDS=4`) / planner.py:93 (`60` 硬编码) |

间接影响:`tests/` — 仅需通过全量 pytest 绿灯验证,不补 callsite scan 测试(Human 已确认)。

**M2 — 候选 M:IO + Artifact Ownership**

直接影响文件:

| 文件 | 变更性质 |
|------|---------|
| `src/swallow/_io_helpers.py` (新建) | 统一 JSON/JSONL 读取 helper,明确 error-policy variant 命名 |
| `src/swallow/store.py` (line 136-148) | 替换为 `_io_helpers` 调用 |
| `src/swallow/truth/knowledge.py` (line 59-67) | 替换为 `_io_helpers` 调用 |
| `src/swallow/orchestrator.py` (lines 388-406 + 2961-3248) | 替换为 `_io_helpers` 调用 |
| `src/swallow/librarian_executor.py` (line 57) | 替换为 `_io_helpers` 调用 |
| `src/swallow/canonical_registry.py` (line 65-91) | 替换为 `_io_helpers` 调用 |
| `src/swallow/staged_knowledge.py` (line 92-104) | 替换为 `_io_helpers` 调用 |
| `src/swallow/knowledge_suggestions.py` (line 22-31) | 替换为 `_io_helpers` 调用 |
| `src/swallow/retrieval.py` (lines 588-600, 678-690) | 替换为 `_io_helpers` 调用 |
| `src/swallow/dialect_data.py` (line 144-153) | 替换为 `_io_helpers` 调用 |
| `src/swallow/knowledge_store.py` (lines 123-143) | 替换为 `_io_helpers` 调用 |
| `src/swallow/cli.py` (lines 617-632) | 评估 `load_json_if_exists` / `load_json_lines_if_exists` 是否迁移或 delegate 到 `_io_helpers` |
| artifact name ownership (4 处,scope 待 design 决议) | `src/swallow/orchestrator.py:175-189` + `src/swallow/harness.py:309-521` + `src/swallow/cli.py:3564-3636` + `src/swallow/retrieval.py:64-79` |

间接影响:`src/swallow/_http_helpers.py`(同目录 pattern 参考,不改动)。

**M3 — 候选 N:CLI Dispatch Tightening**

直接影响文件:

| 文件 | 变更性质 |
|------|---------|
| `src/swallow/cli.py` (lines 3640-3830 重点) | read-only artifact printer 命令族 table-driven dispatch;预计 20+ handler 收敛 |

间接影响:若引入 `CLICommand` dataclass 或 registry,可能新建 `src/swallow/_cli_dispatch.py`。

不在 M3 scope:`proposal apply` / `route registry apply` / `route policy apply` / `migrate` / governance write 命令 — 保持 explicit dispatch。

## 近期相关变更 (git history)

| Commit | 描述 | 相关模块 |
|--------|------|---------|
| ed967b7 | docs(state): update roadmap | docs/roadmap.md — 候选 L/M/N 加入队列 |
| 7d25c26 | docs(design): refine knowledge frame | docs/design/KNOWLEDGE.md — 三层架构升级,Phase 67 不触动 |
| f2f39d3 | docs(state): sync phase66 post-merge state | docs/active_context.md |
| 596b54b | merge: read-only code hygiene audit | Phase 66 audit artifacts merge,Phase 67 的弹药来源 |
| a240d97 | docs(phase66): close out code hygiene audit | closeout.md — backlog 增量沉淀 |
| 9fdebdd | docs(phase66): add m3 audit review | audit_index.md + Block 2 final |
| ddc8153 | docs(phase66): add m2 audit review | Block 4 + Block 5 |
| 6e98509 | docs(phase66): add m1 code hygiene audit | Block 1 + Block 3 |
| 64cbba7 | merge: Truth Plane SQLite Transfer | Phase 65 — sqlite_store.py 新增的 timeout 字面量是 M1 quick-win 来源 |

## 关键上下文

**M1 行号验证**

以下 audit snapshot 行号经 2026-04-30 grep 验证与当前 HEAD 一致(无漂移):

- `run_consensus_review(...)`: `review_gate.py:617` — confirmed
- 模块级 `_pricing_for(...)`: `cost_estimation.py:34` — confirmed
- `rank_documents_by_local_embedding(...)`: `retrieval_adapters.py:249` — confirmed
- SQLite timeout literals: `sqlite_store.py:281/327/358/367/370/377/885` — confirmed(Phase 65 新增代码产生,audit snapshot 准确)
- CLI MPS choices: `cli.py:1315` — confirmed(audit snapshot 记为 1313-1316,实际主 choice line 为 1315,无实质漂移)
- retrieval preview limits: `retrieval.py:423/645/875/883` + `retrieval_adapters.py:267/312` + `ingestion/pipeline.py:292` — confirmed(retrieval_adapters.py 267 在 audit snapshot 中,实际确认 lines 267/312/452 均有 `[:4000]`;audit 只记录前两处,实装时需处理三处)
- orchestration defaults: `orchestrator.py:189` / `review_gate.py:16` / `planner.py:8/93` / `executor.py:1167/1287/1428/1554` / `synthesis.py:17-18` — confirmed

**M1 `_pricing_for` 混淆风险**

`cost_estimation.py` 同时存在:
- 模块级 `def _pricing_for(model_hint)` at line 34(dead code)
- `StaticCostEstimator._pricing_for(self, model_hint)` at line 59(live,被 `estimate_cost` at line ~50 通过 `self._pricing_for(...)` 调用)

两者函数体相同。删除模块级版本前必须确认无任何地方直接调用 `_pricing_for(...)` 非 self 形式。grep 结论:无 src/ 或 tests/ 非 self callsite。但删除后需保留 `StaticCostEstimator._pricing_for` instance method 不变(这是 live path)。

**M1 `rank_documents_by_local_embedding` 移动策略**

当前唯一 non-src callsite 在 `tests/eval/test_vector_retrieval_eval.py:82`。若从 `retrieval_adapters.py` 移走,eval test 的 import path 需随之更新。选项有二:(a) 在 `retrieval_adapters.py` 保留 re-export shim; (b) 直接更新 eval test import。选项 (b) 更干净,但触动 tests/eval/。Claude design_decision 应给出建议。

**M2 IO helper 现状:cli.py 已有私有 helpers**

`src/swallow/cli.py:617-632` 已定义 `load_json_if_exists` 和 `load_json_lines_if_exists`,但它们是 cli.py 私有。当前 orchestrator/knowledge/canonical 等模块各自实现变体而非复用 cli.py 的版本(cli.py 不是这些模块的自然 import 依赖)。新 `_io_helpers.py` 应成为跨模块共享 owner;cli.py 的私有版本可 delegate 或留 as-is 视 design 决议。

**M2 错误策略现状分类**

从 audit 证据推断,当前各 callsite 实际行为如下:
- `strict`(缺失文件 = crash): `orchestrator.py`的某些 canonical reuse 路径、`knowledge_store.py` 部分路径
- `missing-is-empty`(缺失文件 = 返回空 dict/list): `staged_knowledge.py` / `canonical_registry.py` / `knowledge_suggestions.py` / `retrieval.py` policy readers
- `malformed-is-empty`(JSON 解析失败 = 静默返回空): 部分 block 5 cli helper 路径

M2 的设计关键是:不可均质化。每个 callsite 必须显式选 variant,不能改变现有行为而只是把代码移到 helper。

**M2 Artifact name ownership 决议范围**

audit_index §Artifact Name Ownership 的推荐是"start with read-only artifact printer mapping in CLI as the narrowest reversible step"。M2 scope 内最窄的可逆步骤 = 决议是否引入 artifact name registry(如 `paths.py` 扩展或新模块),而非立即实装 CLI dispatch table(那是 M3)。若 M2 引入 registry,M3 的 dispatch table 直接消费;若 M2 不引入 registry 而只做 IO helper,则 M3 独立处理 artifact name ownership。design_decision 需明确这一选择。

**M3 CLI 行数与 dispatch 结构现状**

`cli.py` 当前 3832 行。Read-only artifact printer 命令族主要集中在:
- `cli.py:3640-3830`:20+ task subcommand handler,每个都重复 `json.loads(path.read_text(...))` + `json.dumps(..., indent=2)` + `print(...)` + `return 0`
- `cli.py:617-632`:已有 `load_json_if_exists` / `load_json_lines_if_exists` helpers,但 3640+ 段的多数 handler 未使用它们

Table-driven dispatch 的起步集合 = `cli.py:3640-3830` 的 20+ read-only JSON artifact printers。不包含:
- `task inspect` / `task review` (lines 3199-3558):逻辑复杂,有条件渲染,不适合简单 table dispatch
- governance write commands:保持 explicit

**M1 → M2 → M3 顺序依赖**

- M2 IO helper 决议完成后,M3 read-only artifact printer 可使用新 helper 替代内联 `json.loads(path.read_text(...))` 调用。M3 不必等 M2 完全完成,但 IO helper 模块必须先存在。
- M2 artifact name ownership 决议(若引入 registry)直接影响 M3 dispatch table 结构。M3 若在 M2 artifact name 决议前启动,dispatch table 的 key 设计无法收敛。
- 结论:M2 必须在 M3 之前完成。不可乱序。

**INVARIANTS / DATA_MODEL / KNOWLEDGE 约束**

Phase 67 不触动 `docs/design/` 任何文件。三层架构(KNOWLEDGE.md)、P2(SQLite primary truth)、P4(Taxonomy before brand)均不在 scope 内。M1 常量命名不影响任何设计约束;M2 IO helper 是纯实装层;M3 CLI dispatch 重构不影响 INVARIANTS §0 四条规则(read-only artifact printer 不写 Truth)。

**`_http_helpers.py` 模块位置参考**

`src/swallow/_http_helpers.py` 已是 `_`-prefix 私有 helper 模式,91 LOC。新 `src/swallow/_io_helpers.py` 延续同一模式,预计 60-100 LOC。

**全量 pytest 状态基准**

Phase 65 merge 时:610 passed / 8 deselected / 10 subtests。Phase 66 是 audit-only,无 src/ 变更,所以基准应接近此数字。M1/M2/M3 完成后需全量 pytest 绿灯。

## 风险信号

- **M1 `_pricing_for` 删除**:如上所述,需严格区分模块级(dead)与 instance method(live)。grep 确认无 non-self callsite 但 Codex 实装时须再验证。
- **M1 `rank_documents_by_local_embedding` 移动**:eval test import path 需同步更新;若 audit 后有新测试添加 import,可能漏改。
- **M1 retrieval_adapters.py `[:4000]` 有三处**:audit 记录了 lines 267/312,实际还有 line 452。实装时需处理三处一致命名。
- **M2 IO helper 错误策略均质化风险**:若 Codex 在实装时未仔细区分 callsite 的现有行为,可能将 strict caller 改为 missing-is-empty,导致无声失败代替原有 crash。这是 M2 最高风险点;design_decision 必须给出每个 callsite 的显式 variant 选择。
- **M2 artifact name ownership 决议影响 M3**:若 M2 没有给出明确决议(引入 registry 还是不引入),M3 的 dispatch table 设计会产生对 artifact name 字符串的隐式依赖,增加未来漂移风险。
- **M3 CLI golden output 风险**:read-only artifact printer 的输出格式与现有 `tests/test_cli.py` golden output 绑定(若有)。table-driven dispatch 重构必须保持完全相同的输出行为。如有 golden test,需比对 diff。
- **M3 argparse 兼容性**:table-driven dispatch 若不小心修改 subparser 注册顺序或 help text,`--help` 输出可能变化,构成 public surface 变更。应确认 M3 只改 dispatch handler,不改 parser registration。
- **Phase 67 总风险等级**:中等。M1 低 / M2 中 / M3 中。高风险不需要 GPT-5 model review(无 INVARIANTS 触动,无 DATA_MODEL/schema 变更,无状态转换影响)。

## Model Review Gate 推荐

**建议跳过**。理由:Phase 67 scope 全为清理性质(dead code 删除 + helper 提取 + dispatch 重构),无 INVARIANTS.md 触动,无 DATA_MODEL 变更,无新状态转换路径,max risk score 估计 4-5(阈值通常 6+)。M2 IO helper design 是 Phase 67 唯一设计决议,但其影响局限于 IO 错误策略显式化,不影响架构约束。Human 在 Design Gate 最终决定。

## 各 Milestone Review Checkpoint 产出物命名

- M1 完成 → Claude 产出 `docs/plans/phase67/review_comments_block_l.md`
- M2 完成 → Claude 产出 `docs/plans/phase67/review_comments_block_m.md`
- M3 完成 → Claude 产出 `docs/plans/phase67/review_comments_block_n.md` + final review

## Phase 67 总验收标准

- 7 quick-win 全部消化 + `docs/concerns_backlog.md` 对应条目标 Resolved
- JSON/JSONL helper 跨块统一 + 所有 callsite 显式选 variant
- Artifact name ownership 决议落地;Block 2 finding 7 + Block 4 finding 9 backlog 条目标 Resolved 或 Partial
- read-only CLI 命令族 table-driven dispatch 起步;audit_block5 finding 3 backlog 条目标 Resolved 或 Partial
- `git diff main -- docs/design/` = 0
- 全量 pytest 绿灯

## 推荐 Branch 名

`feat/phase67-hygiene-io-cli-cleanup`

备选:`feat/phase67-cleanup-trio`(若需更短名称)
