---
author: claude
phase: phase67
slice: kickoff
status: revised-after-design-audit
depends_on:
  - docs/plans/phase67/context_brief.md
  - docs/plans/phase67/design_audit.md
  - docs/plans/phase66/audit_index.md
  - docs/plans/phase66/closeout.md
  - docs/roadmap.md
  - docs/concerns_backlog.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
  - docs/design/KNOWLEDGE.md
---

TL;DR(revised-after-design-audit,2026-04-30):Phase 67 = roadmap 候选 **L+M+N 三合一大 phase**(audit_index 警告"不应合并"已被 Human 知情接受)。**消化 design_audit 12 项 finding(2 BLOCKER + 6 CONCERN + 4 SUGGESTION)**。**3 milestone**:M1 = 候选 L Small Hygiene Cleanup(7 项 quick-win;含 reviewer_timeout owner 选项 b 避免循环 import + SQLite PRAGMA f-string 锁定);M2 = 候选 M IO + Artifact Ownership(`_io_helpers.py` 三 variants + 11+ callsite 显式 + 显式接受 cli.py 私有 helpers malformed-line 行为变化 + closeout pre-positioned for 候选 O);M3 = 候选 N CLI Dispatch Tightening(scope 扩到 `cli.py:3592-3787` 覆盖 21-command set-membership block;`raise NotImplementedError` fallback;6 个手动验证含 dispatch 命令)。每 milestone 独立 commit + 独立 review_comments + M1 fixup commit 协议。**INVARIANTS / DATA_MODEL / KNOWLEDGE / 任何 design 文档零改动**。Phase 67 总风险中等(M1 低 / M2 中 / M3 中)。Model Review Gate 默认 skipped。

## 当前轮次

- track: `Refactor / Hygiene + Design / Refactor + Refactor / Surface`(三合一)
- phase: `Phase 67`
- 主题: 清理 + IO 设计 + CLI dispatch(L+M+N 三合一)
- 入口: Direction Gate 已通过(2026-04-30 Human 选定 LMN 顺序 + 知情接受合并)

## Phase 67 在 INVARIANTS / DATA_MODEL 框架中的位置

- **不触动 INVARIANTS.md / DATA_MODEL.md / KNOWLEDGE.md / 任何 design 文档**(本 phase 是实装清理,不评判设计)
- **不引入 §9 守卫新条目**(无新写权限路径)
- **不改 P2 truth schema**(M2 IO helper 是纯实装层 / M3 read-only CLI 不写 truth)
- 实装产出 = `src/swallow/` 下若干文件改动 + 1 个新文件(`_io_helpers.py`)+ `tests/` 必要时跟随更新 + `docs/concerns_backlog.md` 对应条目标 Resolved

## 目标(Goals)

### M1 — Small Hygiene Cleanup(候选 L,7 项 quick-win)

- **G1.1 — Dead code 删除(3 项)**:
  - `src/swallow/review_gate.py:617-632` 删除 `run_consensus_review(...)` (无 src / 无 tests callsite)
  - `src/swallow/cost_estimation.py:34-42` 删除模块级 `_pricing_for(...)` (保留 `StaticCostEstimator._pricing_for(self, ...)` instance method line 59,这是 live path)
  - `src/swallow/retrieval_adapters.py:249-292` `rank_documents_by_local_embedding(...)` 处理(详见 G1.2 决议)
- **G1.2 — `rank_documents_by_local_embedding` 移动决议**:由 design_decision §S1 给 authoritative;两选项:(a) 在 `retrieval_adapters.py` 保留 re-export shim + 实装移到 `tests/eval/`(更干净但触动 tests/);(b) 在 `retrieval_adapters.py` 保留实装 + 标 `# eval-only` 注释 + 不做移动(最小改动)。**Claude 推荐 (b)**,理由:eval-only 函数留 production 代码不破坏架构,只是显式标注;移动到 tests/eval/ 会破坏"测试代码不依赖测试代码"的常规假设
- **G1.3 — 常量命名(4 项)**:
  - `sqlite_store.py` 新增 `SQLITE_CONNECT_TIMEOUT_SECONDS = 5.0` + `SQLITE_BUSY_TIMEOUT_MS = 5000`,7 处 callsite 替换(lines 281/327/358/367/370/377/885)
  - `cli.py:1315` 改为 `from swallow.mps_policy_store import MPS_POLICY_KINDS`,删除手动重复
  - retrieval preview / scoring limits:`retrieval.py` + `retrieval_adapters.py` + `ingestion/pipeline.py` 命名 `[:4000]` / `[:220]` / `> 80` 等。**注意**:`retrieval_adapters.py` 中 `[:4000]` 实际有 3 处(lines 267/312/452),context_brief 已确认 audit_index 漏记 line 452;Codex 实装时处理三处一致命名
  - orchestration timeout / card defaults:`models.py:641` (`reviewer_timeout_seconds: int = 60`) 与 `review_gate.py:16` (`DEFAULT_REVIEWER_TIMEOUT_SECONDS = 60`) 重复 — 决议哪个为 owner;`executor.py:1167/1287/1428/1554` `"20"` 重复 4 次 — 命名为 `DEFAULT_EXECUTOR_TIMEOUT_SECONDS = 20`(或类似);`planner.py:93` `60` 硬编码 — 命名

### M2 — IO + Artifact Ownership(候选 M)

- **G2.1 — `_io_helpers.py` 模块创建**:`src/swallow/_io_helpers.py`(与 `_http_helpers.py` 同目录同 `_`-prefix 私有 helper 模式)。三个 IO helper variants(命名 authoritative,见 design_decision §S2):
  - `read_json_strict(path: Path) -> dict` — 缺失文件 = `FileNotFoundError`;malformed = `json.JSONDecodeError`(原样 raise)
  - `read_json_or_empty(path: Path) -> dict` — 缺失文件 = `{}`;malformed = `json.JSONDecodeError` raise
  - `read_json_lines_or_empty(path: Path) -> list[dict]` — 缺失文件 = `[]`;malformed = JSON line 静默 skip + log.warning(因为 .jsonl 文件历史上 trailing 半行 / 损坏 line 的容忍是 known habit)
- **G2.2 — 11+ callsite 显式 variant 替换**(per context_brief §变更范围 M2 表):每个 callsite 由 design_decision §S2 给 authoritative variant 选择(strict / or-empty),**不可均质化**(R1 风险点)。Codex 实装前需对每个 callsite 跑 grep 看现有行为,与 design_decision 给的 variant 对齐
- **G2.3 — Artifact Name Ownership 决议**:audit_index §Artifact Name Ownership 推荐"start with read-only artifact printer mapping in CLI as the narrowest reversible step"。M2 内决议范围两选一,由 design_decision §S2 authoritative:
  - (a) **窄选项**:M2 内不引入 artifact-name registry,仅在 M3 CLI dispatch table 内嵌 artifact 名 mapping;Block 2 finding 7 + Block 4 finding 9 backlog 标 Partial(等未来 design phase 决定 registry)
  - (b) **宽选项**:M2 内引入 `paths.py` 扩展或新建 `_artifact_registry.py`,跨 orchestrator / harness / cli / retrieval 4 处统一消费 registry;backlog 标 Resolved
  - **Claude 推荐 (a)**(窄选项,scope 控制 + 与 audit_index "narrowest reversible step" 推荐一致)
- **G2.4 — `cli.py:617-632` 现有私有 helpers 迁移**:`load_json_if_exists` / `load_json_lines_if_exists` 当前 cli.py 私有,跨模块未复用。M2 内决议:(i) 删除 cli.py 私有版本,所有 callsite 改用 `_io_helpers`;(ii) cli.py 私有版本 delegate 到 `_io_helpers`。**Claude 推荐 (i)**(更干净,与"single owner"原则一致)

### M3 — CLI Dispatch Tightening(候选 N)

- **G3.1 — Read-only artifact printer table-driven dispatch**:`cli.py:3640-3830` 的 20+ task subcommand handler(每个都是 `json.loads(path.read_text()) + json.dumps(indent=2) + print + return 0`)收敛到 table-driven dispatch。
- **G3.2 — 数据结构决议**:由 design_decision §S3 给 authoritative;两选项:(a) `dict[str, Callable]` mapping subcommand name → handler(轻量,延续 argparse 自然结构);(b) `@dataclass class CLICommand` + 列表(更结构化,支持 metadata 但 over-engineering)。**Claude 推荐 (a)**(轻量,不引入新抽象层)
- **G3.3 — Read-only 范围严格界定**:authoritative 不在 scope 的命令(保持 explicit dispatch):
  - `proposal apply` / `route registry apply` / `route policy apply` / `migrate` / `migrate --status`
  - `task create` / `task acknowledge` / `task retry` / `task resume` / 任何写 truth 的命令
  - `task inspect` / `task review`(虽然 read-only,但渲染逻辑复杂,有条件分支,不适合 table dispatch — Phase 67 不动)
- **G3.4 — Golden output 保持**:M3 改 dispatch handler **不改 stdout 输出**;若有 `tests/test_cli.py` golden output 测试,必须保持 byte-for-byte 一致

### G4 — 跨 milestone 协调

- **依赖锁定**:M1 → M2 → M3 严格顺序,**不允许并行 / 不允许倒序**
- **每 milestone 独立 commit + 独立 review_comments**:
  - M1 完成 → Codex 提交 1 commit → Claude 产 `docs/plans/phase67/review_comments_block_l.md` → M2 启动
  - M2 完成 → Codex 提交 1 commit → Claude 产 `docs/plans/phase67/review_comments_block_m.md` → M3 启动
  - M3 完成 → Codex 提交 1 commit → Claude 产 `docs/plans/phase67/review_comments_block_n.md` + Phase 67 final review
- **Codex handoff 信号**:每 milestone Codex 等对应 review_comments 文件出现 + frontmatter `verdict` 字段为 `APPROVE` 或 `APPROVE_WITH_CONDITIONS` 后才进下一 milestone(类比 Phase 66 review 分轮机制)

## 非目标(Non-Goals)

- **不修改 INVARIANTS.md / DATA_MODEL.md / KNOWLEDGE.md / 任何 docs/design/**(此 phase 是实装清理)
- **不引入对象存储后端 / 不实装 `RawMaterialStore` 接口**(那是候选 O scope)
- **不重构 `task inspect` / `task review` 的 snapshot rendering**(audit_block5 finding 4 标 [med] abstraction-opportunity,scope 大,留给后续 phase)
- **不动 governance write 命令的 dispatch**(`proposal apply` / `route registry apply` 等保持 explicit)
- **不审 / 不重写 tests/**(Phase 67 测试改动仅限于 callsite 跟随 src/ 改动)
- **不引入新工具**(vulture / pyflakes / radon / mypy strict 等留给后续 design phase)
- **不引入 multi-actor / authn / multi-host**(永久非目标)
- **不消化 audit_index 中未列入 quick-win 的 [low] severity 项**(只做 7 项 quick-win;其他 [low] 留给候选 R 观察期后由 Human 决定是否拉新 phase)

## 设计边界

- **read-only 边界已被 Phase 66 验证为可执行**;Phase 67 是实装 phase,**不再 read-only** — 但 commit 应严格分 milestone,不允许 cross-milestone scope 漂移
- **M2 IO helper 错误策略不可均质化**(R1 关键风险点):每个 callsite 必须显式选 variant + design_decision §S2 给 authoritative 映射;Codex 不可凭"语义理解"决定
- **M3 CLI golden output 必须 byte-for-byte 保持**;若发现 golden test 不存在某命令的输出,M3 内不补测试(留给 testing-debt phase),但需 manually 验证至少 5-10 个 read-only command 的输出与改动前一致
- **`cli.py` 大小变化预期**:M3 后 cli.py 行数应**减少**(20+ handler 收敛到 dispatch table,~200 行 → ~80 行 dispatch + table);若反而增加说明 over-engineering

## Slice 拆解(详细见 `design_decision.md`)

| Slice | 主题 | Milestone | 风险评级 |
|-------|------|-----------|---------|
| S1 | 7 项 quick-win | M1 | 低(2)|
| S2 | IO helper + artifact name ownership | M2 | 中(5)|
| S3 | CLI read-only dispatch table | M3 | 中(4)|

**slice 数量 3 个**,符合"≤5 slice"指引;**0 个高风险 slice**。

## Eval 验收

不适用。Phase 67 无功能新增 / 无设计改动;验收 = 全量 pytest 绿灯 + 行为 byte-for-byte 等价 + backlog 对应条目状态更新。

## 风险概述(详细见 `risk_assessment.md`)

- **R1**(中)— M2 IO helper 错误策略均质化风险:Codex 把 strict caller 改为 missing-is-empty,导致无声失败代替原有 crash。缓解:design_decision §S2 给每个 callsite authoritative variant 映射,Codex 不可自决
- **R2**(低-中)— M1 `_pricing_for` 模块级 vs instance method 混淆:删除前需 grep 验证无 non-self callsite。缓解:context_brief 已 grep 确认无 callsite,Codex 实装时再验证一次
- **R3**(低)— M1 `[:4000]` audit 漏记 line 452:Codex 处理时三处一致命名。缓解:context_brief 已标注
- **R4**(中)— M3 CLI golden output 破坏:dispatch 重构改输出格式。缓解:M3 完成后 manually 验证 5-10 个 read-only command 输出 diff = 0;若有 golden test 必须保持
- **R5**(低-中)— M3 argparse 兼容性:dispatch table 改注册顺序导致 `--help` 输出变化。缓解:M3 只改 handler,不改 parser registration
- **R6**(低)— M2 artifact name ownership 决议影响 M3:M2 选 (a) 窄选项后,M3 dispatch table 直接内嵌 artifact 名;若 M2 改选 (b) 需 M3 重新对齐。缓解:design_decision §S2 锁定 (a);M2 review 时若 Claude 主线决议改 (b),需要 reset M3 起点
- **R7**(零)— Phase 67 不触动设计文档,无设计漂移风险

## Model Review Gate

**默认 skipped**(per `.agents/workflows/model_review.md` 触发条件):
- 不触动 INVARIANTS / DATA_MODEL / KNOWLEDGE / SELF_EVOLUTION
- 不涉及 schema / state transition / truth write path / provider routing policy
- 不引入 NO_SKIP 红灯
- max risk score = 5(低于 6 阈值)
- scope 全为清理 + 实装层重构

若 design-auditor 复检后给出 [BLOCKER] 或多个 [CONCERN],再视情况触发。

## Branch Advice

- 当前分支:`main`(Phase 66 已 merge,KNOWLEDGE 三层架构升级已 merge,roadmap 已更新)
- 建议 branch 名:`feat/phase67-hygiene-io-cli-cleanup`
- 建议 commit 节奏:M1 (1 commit) → M2 (1-2 commit,IO helper + callsite 可拆) → M3 (1 commit) → docs (1 commit closeout / backlog) = 4-5 commits 上 PR

## 完成条件

**M1 完成条件**:
- 7 项 quick-win 全部消化(3 项 dead code 删除 + 4 项常量命名)
- `_pricing_for` 模块级删除后 `StaticCostEstimator._pricing_for` instance method 仍正常 + grep 确认无 non-self callsite
- `rank_documents_by_local_embedding` 决议执行(推荐保留 + `# eval-only` 注释)
- `[:4000]` 三处全替换为 `RETRIEVAL_PREVIEW_LIMIT`(或类似命名)
- 全量 pytest 绿灯

**M2 完成条件**:
- `src/swallow/_io_helpers.py` 创建,3 个 helper variants 实装
- 11+ callsite 全部显式选 variant(按 design_decision §S2 authoritative 映射)+ 无均质化错误
- `cli.py:617-632` 私有 helpers 删除,所有 callsite 改用 `_io_helpers`
- Artifact name ownership 决议落地(推荐 (a) 窄选项)
- audit_block4 finding 1 [high] backlog 标 Resolved;Block 2 finding 7 + Block 4 finding 9 backlog 标 Partial 或 Resolved 视决议
- 全量 pytest 绿灯

**M3 完成条件**:
- `cli.py:3640-3830` 范围内 20+ read-only artifact printer 收敛到 table-driven dispatch
- governance write commands 保持 explicit dispatch
- `task inspect` / `task review` 不动
- Manually 验证 5-10 个 read-only command 输出 byte-for-byte 与改动前一致(若有 golden test 通过)
- audit_block5 finding 3 backlog 标 Partial 或 Resolved
- 全量 pytest 绿灯

**全 phase 完成条件**:
- `git diff main -- docs/design/` = 0(零设计文档改动)
- `docs/concerns_backlog.md` 对应 7 quick-win + 3 design-needed 主题状态全部更新
- 全量 pytest 绿灯
- `git diff --check` 通过
- `docs/plans/phase67/closeout.md` 完成
- `docs/active_context.md` 由 Codex 同步

## Phase 67 与候选 O 的衔接

候选 O = Storage Backend Independence(`RawMaterialStore` 接口实装)在 Phase 67 之后启动。Phase 67 的 M2 IO helper 设计应**预留** RawMaterialStore 接口可能的影响:

- M2 IO helper 接受 `Path` 参数;候选 O 实装时可能需要改为接受 `source_ref`(URI 字符串)
- M2 不解决这一未来扩展;只确保接口足够薄,候选 O 时改 helper 签名即可,不需要重构所有 callsite

## 完成后的下一步

- Phase 67 closeout 后,触发 `roadmap-updater` subagent:
  - §三差距表"代码卫生债清理"行 [已消化]
  - §四候选 L / M / N 三个块 strikethrough(merge 日期 + closeout 引用)
  - §五推荐顺序 K ✓ → L ✓ M ✓ N ✓ → O / R / D
- **不打 tag**(Phase 67 是清理 phase,不构成 release 节点)
- 后续阶段:候选 O(Storage Backend Independence,你已说接 LMNO 顺序),由 Human 在新 Direction Gate 决定何时启动

## 不做的事(详见 non-goals)

- 不修改 INVARIANTS / DATA_MODEL / KNOWLEDGE / 任何 design 文档
- 不实装 `RawMaterialStore`(候选 O scope)
- 不重构 task inspect / task review
- 不动 governance write 命令的 dispatch
- 不审 tests/
- 不引入新工具
- 不消化 quick-win 之外的 [low] severity 项
- 不引入 multi-actor / authn

## 验收条件(全 phase)

详见上方 §完成条件。本 kickoff 与 design_decision 一致,无补充。
