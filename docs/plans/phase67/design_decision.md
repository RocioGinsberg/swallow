---
author: claude
phase: phase67
slice: design-decomposition
status: revised-after-design-audit
depends_on:
  - docs/plans/phase67/kickoff.md
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

TL;DR(revised-after-design-audit,2026-04-30):**3 milestone / 3 slice**(M1 = 7 项 quick-win / M2 = `_io_helpers.py` 模块 + 3 variants + 11+ callsite 显式 variant + artifact name 窄选项 / M3 = read-only artifact printer table-driven dispatch)。**消化 design_audit 12 项 finding(2 BLOCKER + 6 CONCERN + 4 SUGGESTION)**。M2 关键决议:**IO helper 错误策略不可均质化** + 显式接受 `load_json_lines_if_exists` 行为变化(malformed-line strict → skip+warn,77 callsite 范围)。M3 范围扩到 `cli.py:3592-3787`(覆盖 21-command set-membership block + 后续 read-only printer)。每 milestone 独立 commit + 独立 review_comments(类比 Phase 66)。

## Revision Index(2026-04-30 design_audit 后)

本文件在 draft 基础上吸收 `design_audit.md`(2 BLOCKER + 6 CONCERN + 4 SUGGESTION)结论:

- **BLOCKER Q6 SQLite PRAGMA 决议** → §S1.3 锁定 f-string 插值
- **BLOCKER Q8 reviewer_timeout 循环 import** → §S1.6 改为选项 (b):`models.py:641` 保留字面量 `60` + 注释引用 `review_gate.DEFAULT_REVIEWER_TIMEOUT_SECONDS`
- **CONCERN Q10 §S2.2 三个 grep-pending 行** → 加 authoritative 映射规则:malformed→crash 用 strict;malformed→empty 用 or_empty
- **CONCERN Q11 cli.py malformed line 行为变化** → §S2.4 显式接受 strict→skip+warn;声明影响范围(77 callsite)
- **CONCERN Q12 dispatch table pseudocode 错误** → §S3.1 重写 pseudocode:用 inline lambda 而非 `summary_path` 这类不存在的 path resolver;handle 不同 signature 路径函数
- **CONCERN Q13 M3 scope 边界** → §S3.2 范围扩到 `cli.py:3592-3787`(覆盖 21-command set-membership block)
- **CONCERN Q5 _pricing_for grep 范围** → §S1.2 grep 改为 `.` 全仓库
- **CONCERN Q7 [:4000] 命名权威** → §S1.4 锁定 `RETRIEVAL_SCORING_TEXT_LIMIT` 应用三处(同语义 confirmed by audit)
- **SUGGESTION Q4 第三选项** → §S1.1 加注释解释为何不选 `_eval_support.py`(eval-only 单函数不值得新建模块)
- **SUGGESTION Q9 read_json_lines_strict 缺失说明** → §S2.1 helper 模块 docstring 加未来扩展点说明
- **SUGGESTION Q14 dispatch 命令验证缺失** → §S3.4 把 `dispatch` command 加入 manual 验证清单
- **SUGGESTION Q15 fallback 行为决议** → §S3.1 锁定 `raise NotImplementedError`(M3 完成后所有 read-only command 进 table)
- **SUGGESTION Q16 M2 倒灌 M1 机制** → §Review 分轮 加"M1 fixup commit"协议
- **SUGGESTION Q17 候选 O pre-positioning** → §S2.5 要求 closeout 显式声明 pre-positioned items
- **SUGGESTION Q18a MPS_POLICY_KINDS 排序** → §S1.5 锁定 `sorted(MPS_POLICY_KINDS)` 包裹
- **SUGGESTION A1 cli.py 私有 helpers 删除溢出 inspect/review** → §S2.4 显式接受 inspect/review 块 callsite 改动属于 M2 范围

修订点定位:
- §S1.1 / §S1.2 / §S1.3 / §S1.4 / §S1.5 / §S1.6:M1 各 quick-win 决议补全
- §S2.1 / §S2.2 / §S2.4 / §S2.5:M2 IO helper 行为变化显式 + 候选 O 衔接强化
- §S3.1 / §S3.2 / §S3.4:M3 dispatch 实装可执行性 + scope 边界
- §Review 分轮机制:M1 fixup commit 协议

## 方案总述

Phase 67 是三合一 phase,但**形态扎实而非凑数**:

- **M1(L)是清理 phase 的常规起步**:7 项 quick-win 都是 audit_index 列出的"local / 低风险 / 已有 behavior 测试覆盖"的项,scope 最清晰
- **M2(M)是 design 决议 phase**:IO helper 错误策略 + artifact name ownership 都是 audit_index 列入 design-needed 主题。M2 的关键不是"写代码",是"在 design_decision 中给每个 callsite authoritative variant 映射,Codex 不再自决"
- **M3(N)是接口收敛 phase**:cli.py 现在 3832 行,20+ read-only artifact printer 重复 5 行 boilerplate 是典型可 table-driven 化目标。M3 起步只做这一段,governance write 保持 explicit

**为什么三合一不是 design 漂移**:
- Phase 66 audit_index 推荐三个独立 phase 的核心理由是"避免 design 决议与代码清理混入同一 review"
- Phase 67 用"严格分 milestone + 独立 review_comments"绕过这一风险:每个 milestone 完成后 Claude review,verdict 通过才进下一 milestone;review_comments 文件名独立(`review_comments_block_l.md` / `_m.md` / `_n.md`),review 注意力不混合
- 这是 audit_index 警告的最弱违反形式;Human 知情接受

**等价性保证**:
- M1 后 src/ 行为零变化(纯删除 dead code + 常量命名替换;`_pricing_for` 删除前已确认 0 callsite;`rank_documents_by_local_embedding` 推荐保留)
- M2 后 src/ 行为零变化(IO helper 替换前后每个 callsite 选与原行为一致的 variant;`cli.py` 私有 helpers 删除后所有 callsite 改用 `_io_helpers`,行为一致)
- M3 后 src/ 行为 byte-for-byte 一致(read-only artifact printer 收敛到 dispatch 但 stdout 输出零变化)
- INVARIANTS / DATA_MODEL / KNOWLEDGE 零改动

## Slice 拆解

### S1 — Small Hygiene Cleanup(M1,低风险)

**目标**:消化 audit_index §Quick-Win Candidates 列出的 7 项 quick-win。

**影响范围**:
- 改动:`src/swallow/review_gate.py`(删 1 函数)/ `src/swallow/cost_estimation.py`(删 1 函数)/ `src/swallow/retrieval_adapters.py`(标注 1 函数 eval-only)/ `src/swallow/sqlite_store.py`(2 常量定义 + 7 callsite 替换)/ `src/swallow/cli.py`(1 import 加 + 1 行 choices 删)/ `src/swallow/retrieval.py`(2-3 常量定义 + 多 callsite)/ `src/swallow/retrieval_adapters.py`(同 RETRIEVAL 常量复用 / line 452 三处一致)/ `src/swallow/ingestion/pipeline.py`(同)/ `src/swallow/orchestrator.py`(timeout / card defaults)/ `src/swallow/review_gate.py` / `src/swallow/planner.py` / `src/swallow/executor.py` / `src/swallow/synthesis.py` / `src/swallow/models.py`(reviewer_timeout owner 决议)
- 0 docs/design/ diff / tests/ 跟随 callsite 改动

**关键设计决议**:

#### S1.1 `rank_documents_by_local_embedding` 移动决议(authoritative)

**采纳选项 (b)**:在 `retrieval_adapters.py` 保留实装 + 标 `# eval-only` 注释 + 不做物理移动。

理由:
- production 代码留 eval-only 函数破坏架构纯洁性,但**移动到 tests/eval/ 破坏"测试代码不依赖测试代码"的常规假设**
- 若移动,`tests/eval/test_vector_retrieval_eval.py:11` 的 import 必须改;但 import 来自 src/ 是 testing 框架的标准期望
- 标注 `# eval-only` 是 audit_block4 finding 2 推荐处理的合理扩展("either move the local embedding ranker under eval/test support or connect it to a production adapter path"— 第三种情况:就地标注)
- audit_block4 finding 2 backlog 标 Resolved(标注 = 显式归类,不是漏审)

#### S1.1 `rank_documents_by_local_embedding` 移动决议(authoritative,修订自 design_audit Q4)

**采纳选项 (b)**:在 `retrieval_adapters.py` 保留实装 + 标 `# eval-only` 注释 + 不做物理移动。

理由:
- production 代码留 eval-only 函数破坏架构纯洁性,但**移动到 tests/eval/ 破坏"测试代码不依赖测试代码"的常规假设**
- 若移动,`tests/eval/test_vector_retrieval_eval.py:11` 的 import 必须改;但 import 来自 src/ 是 testing 框架的标准期望
- 标注 `# eval-only` 是 audit_block4 finding 2 推荐处理的合理扩展("either move the local embedding ranker under eval/test support or connect it to a production adapter path"— 第三种情况:就地标注)
- audit_block4 finding 2 backlog 标 Resolved(标注 = 显式归类,不是漏审)

**第三选项(`src/swallow/_eval_support.py` 单独模块)未采纳的理由**(per design_audit SUGGESTION Q4):
- 单一函数 ~40 LOC 不值得新建独立模块(Phase 67 是清理 phase,引入新模块结构是过度设计)
- 若未来 eval-only 函数累积 ≥3 个,可在 audit phase 重新评估是否拆 `_eval_support.py`;Phase 67 不预判
- 当前 `# eval-only` 注释 + audit_block4 backlog Resolved 是足够的显式归类信号

#### S1.2 `_pricing_for` 删除步骤(authoritative,修订自 design_audit Q5)

```python
# cost_estimation.py - 删除模块级版本(line 34-42)
# 保留 StaticCostEstimator._pricing_for instance method (line 59) 不变
# 同名 instance method 通过 self._pricing_for(...) 调用,与模块级删除无关
```

Codex 实装步骤:
1. **`grep -rn '_pricing_for' .`(全仓库 scope,不限 src/ tests/)** — 包括 docs/、scripts/、配置文件;任何 match 是 BLOCKER,需暂停回写 design
2. 同时 grep 动态调用模式 `getattr.*_pricing_for` / `import.*_pricing_for` 兜底
3. 删除 cost_estimation.py:34-42(模块级 def + body)
4. `pytest -q` 全量绿灯
5. 若有任何 import error / NameError → grep 漏检,回滚

#### S1.3 SQLite timeout 常量命名 + PRAGMA 字符串(authoritative,修订自 design_audit Q6)

```python
# sqlite_store.py - 在 module top 加(_connect 函数定义之前):
SQLITE_CONNECT_TIMEOUT_SECONDS = 5.0
SQLITE_BUSY_TIMEOUT_MS = 5000
```

7 处 callsite(lines 281/327/358/367/370/377/885)替换:
- `timeout=5.0` → `timeout=SQLITE_CONNECT_TIMEOUT_SECONDS`
- `"PRAGMA busy_timeout = 5000"` → **使用 f-string 插值:`f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}"`**(authoritative,不再延迟决议)

f-string 是认可方案理由:
- 与常量命名意图一致(避免常量定义后 callsite 仍出现 magic number `5000`)
- SQLite PRAGMA 接受整数字面量 + f-string 产出相同字符串,行为等价无 SQL 注入风险(常量来源是 module-local literal)
- 不需要新增 helper 函数

#### S1.4 retrieval preview / scoring limits 命名(authoritative,修订自 design_audit Q7)

```python
# retrieval.py - module top
RETRIEVAL_SCORING_TEXT_LIMIT = 4000  # 原 [:4000] 用于评分文本截断
RETRIEVAL_PREVIEW_LIMIT = 220        # 原 [:220] 用于 preview 显示
RETRIEVAL_FRAGMENT_MIN_LENGTH = 80   # 原 > 80 用于 fragment 过滤(若是此语义)
```

callsite 替换(authoritative):
- `retrieval.py:423/645/875/883` 各按上下文选对应常量
- **`retrieval_adapters.py:267/312/452` 三处 `[:4000]` 全部替换为 `from swallow.retrieval import RETRIEVAL_SCORING_TEXT_LIMIT`**(design_audit 已确认三处全是 `score_search_document` 调用上下文,同语义)
- `ingestion/pipeline.py:292` 按上下文判断属于 preview 还是 scoring 限制

**Codex 不可独立创建新常量**:若发现某处 `[:4000]` 实际语义不同(已 audit 确认 retrieval_adapters.py 三处同语义,不会发生),需暂停回写 design,不可自决新常量名。

#### S1.5 CLI MPS_POLICY_KINDS 单 import owner(authoritative,修订自 design_audit Q18a)

```python
# cli.py:1313-1316 现状(手动重复 choices)
# 改为:
from swallow.mps_policy_store import MPS_POLICY_KINDS  # add to imports
# 然后:
parser.add_argument("--kind", choices=sorted(MPS_POLICY_KINDS), ...)  # 用 sorted 保证 --help 输出确定性
```

注意:`MPS_POLICY_KINDS` 是 `set`(`mps_policy_store.py:15`),iter order 跨进程不确定;`argparse --help` 渲染 choices 会暴露 set 的迭代顺序为 nondeterministic public surface。**用 `sorted()` 包裹**强制确定性输出,避免 CLI surface regression。

#### S1.6 orchestration timeout / card defaults owner 决议(authoritative,修订自 design_audit Q8 BLOCKER)

**reviewer_timeout owner — 采纳选项 (b)**(避免 `models.py ↔ review_gate.py` 循环 import):

`review_gate.py:16 DEFAULT_REVIEWER_TIMEOUT_SECONDS = 60` **保留为 owner**;`models.py:641 reviewer_timeout_seconds: int = 60` **保留字面量 `60` 不动 + 加注释**:

```python
# models.py:641 — 现状保留 + 注释:
@dataclass
class ...:
    # NOTE: 60 mirrors review_gate.DEFAULT_REVIEWER_TIMEOUT_SECONDS;
    # cannot import directly due to circular dependency (review_gate imports models).
    # If value changes, update review_gate.py:16 first then mirror here.
    reviewer_timeout_seconds: int = 60
```

理由:
- `review_gate.py:10` import `from .models import ExecutorResult, TaskCard, TaskState`(已 confirmed by design_audit),反向 import 会循环
- 选项 (a) 移到新 `constants.py` / `review_constants.py` 模块 = 引入新模块 + 跨多模块改动,**Phase 67 是清理 phase 不应新建模块结构**(类比 §S1.1 `_eval_support.py` 同款理由)
- 选项 (b) 注释引用 = 文档化 ownership,Codex 看到注释知道哪边是 owner,值变更时双向同步;trade-off 是 60 仍是字面量但有显式 ownership 声明

**executor timeout 命名**(authoritative,无循环 import 风险):
```python
# executor.py module top
DEFAULT_EXECUTOR_TIMEOUT_SECONDS = 20

# 4 处 callsite:
# 原:os.environ.get("AIWF_EXECUTOR_TIMEOUT_SECONDS", "20")
# 改:os.environ.get("AIWF_EXECUTOR_TIMEOUT_SECONDS", str(DEFAULT_EXECUTOR_TIMEOUT_SECONDS))
```

**`planner.py:93` 命名**(authoritative,修订自 design_audit Q8b):

`planner.py:93` 是 `semantics.get("reviewer_timeout_seconds", 60)`,与 `review_gate.DEFAULT_REVIEWER_TIMEOUT_SECONDS` 同语义。**采纳与 §S1.6 选项 (b) 一致的策略**:

```python
# planner.py:93 — 现状保留 + 注释:
# NOTE: 60 mirrors review_gate.DEFAULT_REVIEWER_TIMEOUT_SECONDS;
# kept as literal here to match models.py:641 (no direct import to avoid coupling).
timeout = semantics.get("reviewer_timeout_seconds", 60)
```

planner.py:93 与 planner.py:97 都涉及 60,处理一致(都加注释引用)。


**验收条件**:
- 7 项 quick-win 全部消化
- 全量 pytest 绿灯
- `git diff main -- docs/design/` = 0
- `docs/concerns_backlog.md` 7 quick-win 对应条目状态更新

**风险评级**:影响范围 1 / 可逆性 1 / 依赖 0 = 2(低)。

---

### S2 — IO + Artifact Ownership(M2,中风险:design 决议)

**目标**:创建 `_io_helpers.py` + 3 IO helper variants;11+ callsite 显式 variant;artifact name 窄选项;cli.py 私有 helpers 删除。

**影响范围**:
- 新增:`src/swallow/_io_helpers.py`(60-100 LOC,与 `_http_helpers.py` 同模式)
- 改动:11+ callsite(per kickoff §G2.2)
- 删除:`cli.py:617-632` 私有 helpers
- 0 docs/design/ diff

**关键设计决议**:

#### S2.1 `_io_helpers.py` 三个 IO helper variants(authoritative)

```python
# src/swallow/_io_helpers.py
"""Shared JSON / JSONL IO helpers with explicit error policy variants.

This module is private (_-prefix) and shared across truth/ / orchestrator /
knowledge_*/ / retrieval / cli surfaces. Each callsite must explicitly choose
a variant based on its existing error semantics; do NOT homogenize.

Future extension point (per design_audit Q9 / candidate O):
- If a strict JSONL variant is needed in future (e.g., a critical ingestion path
  that must fail on corruption rather than silently skip), add `read_json_lines_strict`
  following the same pattern. Phase 67 does not introduce it because no current
  callsite has strict-jsonl semantics (audit confirmed all jsonl callers use
  missing-or-empty + skip-malformed pattern).
- Candidate O (RawMaterialStore implementation) may evolve `path: Path` parameter
  to `source_ref: str` (URI string). The function signatures are intentionally thin
  (single Path parameter + return type) to ease that evolution.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_json_strict(path: Path) -> dict:
    """Read JSON object;raise FileNotFoundError if missing,JSONDecodeError if malformed.

    Use for: callers that depend on the file existing (e.g., truth schema reads,
    canonical registry that must exist after init).
    """
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_or_empty(path: Path) -> dict:
    """Read JSON object;return {} if file missing;raise JSONDecodeError if malformed.

    Use for: optional config / staged knowledge / retrieval artifacts where missing
    is expected but malformed indicates corruption.
    """
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_lines_or_empty(path: Path) -> list[dict]:
    """Read JSONL file;return [] if missing;skip+warn malformed lines.

    Use for: append-only event/registry logs where trailing partial lines or
    occasional corruption is a known habit (legacy compatibility).

    BEHAVIOR DELTA from cli.py:load_json_lines_if_exists (which raises JSONDecodeError
    on malformed lines): this helper silently skips + logs warning. The delta is
    intentionally accepted by Phase 67 design_decision §S2.4; callsites that need
    strict-jsonl behavior must use read_json_strict (object-level) or wait for
    future read_json_lines_strict variant.
    """
    if not path.exists():
        return []
    out: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.warning(
                "skipping malformed jsonl line",
                extra={"path": str(path), "line": line_no, "error": str(exc)},
            )
            continue
        if not isinstance(payload, dict):
            logger.warning(
                "skipping non-dict jsonl line",
                extra={"path": str(path), "line": line_no},
            )
            continue
        out.append(payload)
    return out
```

注意事项:
- **不引入 `read_json_lines_strict`**(JSONL 历史上无 strict 用法,原 callsite 全部容忍 missing/malformed;详见 docstring future extension point)
- **不引入 `read_json_or_default(default=...)` 等灵活 variant**(过度设计;若需要非空 default,callsite 显式 `read_json_or_empty(path) or {"key": "default"}`)
- 三 variant 命名遵循 `<操作>_<错误策略>` 模式

#### S2.2 11+ callsite authoritative variant 映射表(修订自 design_audit Q10)

Codex **必须**严格按此表替换;**Codex 不可自决**。

**对照规则**(Codex 实装时 grep 现行 callsite 行为后,按下方规则匹配 variant,无需暂停回写 design):

- **现行行为 = "missing → crash + malformed → crash"** → 用 `read_json_strict`
- **现行行为 = "missing → empty/{} + malformed → crash"** → 用 `read_json_or_empty`
- **现行行为 = "missing → empty/[] + malformed → skip"** → 用 `read_json_lines_or_empty`(仅 jsonl)
- **现行行为 = "missing → crash + malformed → empty"** → **暂停回写 design**(不应有此模式)

| Callsite | 现行行为(Codex grep 验证) | Variant | 备注 |
|---|---|---|---|
| `store.py:136-148` `_load_json_lines` | missing → []; malformed → skip | `read_json_lines_or_empty` | 删除 store.py 私有版本,改 import |
| `truth/knowledge.py:59-67` `_load_json_lines` | missing → []; malformed → skip | `read_json_lines_or_empty` | 删除私有版本 |
| `orchestrator.py:388-406` `_load_json_lines` | missing → []; malformed → skip | `read_json_lines_or_empty` | 删除私有版本 |
| `librarian_executor.py:57` `_load_json_lines` | missing → []; malformed → skip | `read_json_lines_or_empty` | 删除私有版本 |
| `canonical_registry.py:65-91` JSON read | **Codex grep 验证;按对照规则匹配** | 按规则 | 若 missing→crash + malformed→crash 用 strict;若 missing→{} + malformed→crash 用 or_empty |
| `staged_knowledge.py:92-104` JSON read | **Codex grep 验证;按对照规则匹配** | 按规则 | 同上 |
| `knowledge_suggestions.py:22-31` JSON read | missing → {} | `read_json_or_empty` | malformed 行为按现行 |
| `retrieval.py:588-600` policy read | missing → {} | `read_json_or_empty` | |
| `retrieval.py:678-690` policy read | missing → {} | `read_json_or_empty` | |
| `dialect_data.py:144-153` JSON read | **Codex grep 验证;按对照规则匹配** | 按规则 | dialect 数据**最可能**是 strict |
| `knowledge_store.py:123-143` | missing → {} | `read_json_or_empty` | |
| `cli.py:617-632` `load_json_if_exists` / `load_json_lines_if_exists` | **删除** | 改 callsite import `_io_helpers` | 详见 §S2.4 |

**Codex 实装规则**:
1. 对每个 callsite 先 grep 现行行为(是否 try/except FileNotFoundError;是否 except json.JSONDecodeError;是否 missing return {} or raise)
2. 按上方对照规则匹配 variant + 表中 authoritative 选择
3. 若 grep 结果未匹配任何对照规则模式 → 暂停,在 PR body 中标"行为不一致 callsite",由 Claude review 时修订映射
4. 替换后跑相关测试套件确认 no regression

#### S2.3 Artifact Name Ownership 决议 — 采纳窄选项 (a)(authoritative)

**M2 内不引入 artifact-name registry**;artifact 名仍散落在 4 处(orchestrator.py:175-189 / harness.py:309-521 / cli.py:3564-3636 / retrieval.py:64-79)。

理由:
- audit_index §Artifact Name Ownership 明确推荐"start with read-only artifact printer mapping in CLI as the narrowest reversible step"
- M3 dispatch table 内嵌 artifact 名 mapping = "narrowest reversible step",不需要全局 registry
- 引入 registry 是更大 design 决议(影响 paths.py / orchestrator / harness / cli / retrieval 5 处);留给后续 design phase
- audit_block2 finding 7 + audit_block4 finding 9 backlog 标 **Partial(M3 内 CLI 侧消化;orchestrator/harness/retrieval 侧未消化)**,不标 Resolved

#### S2.4 `cli.py:617-632` 私有 helpers 处理 — 采纳选项 (i)(authoritative,修订自 design_audit Q11 + A1)

**删除 cli.py 私有 `load_json_if_exists` / `load_json_lines_if_exists`**;所有 callsite 改 import `_io_helpers`。

理由:
- 与 single-owner 原则一致(每个 helper 只一个 owner)
- cli.py 已 3832 行,删除私有版本利好行数减少
- 名字映射:`load_json_if_exists` → `read_json_or_empty`;`load_json_lines_if_exists` → `read_json_lines_or_empty`(语义等价,**malformed-line 行为有变化,见下方**)

**malformed-line 行为变化(显式接受,修订自 design_audit Q11)**:

`cli.py:617-632 load_json_lines_if_exists` 当前实装(确认自 source):
- malformed line → `json.JSONDecodeError` 抛出(strict)

`_io_helpers.read_json_lines_or_empty` 实装:
- malformed line → log warning + skip(silent)

**Phase 67 显式接受这一行为变化**,理由:
- 行为变化影响范围 = `cli.py` 内 ~77 个 callsite(per design_audit count),其中 read-only display commands 占主要;display 场景下"trailing partial line crash 整个命令"反而 user-hostile
- 极端情况(corrupted artifact 文件):
  - 旧行为:`task summary` 命令直接抛 traceback,operator 必须看 stderr 才能定位
  - 新行为:`task summary` 跳过损坏行 + 输出 warning log,部分输出仍可读,operator 通过 log 定位
- 没有 callsite 依赖"malformed → crash"作为正确性保证(全部为 display / inspection 命令,无 truth-write 路径)

**Codex 实装时验证**:
- 替换 77 个 callsite 后,跑 `pytest tests/test_cli.py`(若有 malformed-line crash 测试,会暴露行为变化,届时 Claude review 阶段决定是改测试还是改 helper)
- 不主动构造 malformed-line 测试(留给后续 testing-debt phase)

**M2 callsite 改动溢出 inspect/review 块(authoritative,修订自 design_audit A1)**:

`cli.py:3199-3384` `task inspect` 块 + `cli.py:3412-3558` `task review` 块**含 `load_json_if_exists` / `load_json_lines_if_exists` 调用**(audit 已 confirm)。

**Phase 67 设计接受**:M2 删除私有 helpers 必然改这两个块的 callsite(rename import),即使 inspect/review 块本身在 M3 标 out-of-scope("不重构 task inspect / task review"):
- M2 改的是 **import 名字 + helper 替换**(机械重命名);**不动 inspect/review 块的渲染逻辑**
- M2 review 时 Claude 必须区分:(a) `load_json_*` rename 改动(M2 范围) vs (b) inspect/review 渲染逻辑改动(M3 也不改,Phase 67 完全不动)
- M3 review 时不再核 inspect/review 块的 helper 改动(已经在 M2 落地)

#### S2.5 候选 O 衔接预留 + closeout 强制声明(authoritative,修订自 design_audit Q17)

`_io_helpers.py` 三个 helper 接受 `Path` 参数。候选 O 实装 `RawMaterialStore` 时可能需要改为 `source_ref` (URI 字符串);M2 不解决此扩展,但确保接口足够薄(仅 1 个 path 参数 + return 类型),候选 O 时改 helper 签名 + 修改 11 callsite signature 即可,不需要重构其他逻辑。

**Phase 67 closeout.md 必含"Pre-positioned for Candidate O"段**(authoritative,Codex 在 closeout 阶段写):

```markdown
## Pre-positioned for Candidate O (Storage Backend Independence)

Phase 67 made the following intentional design choices to ease candidate O implementation:

- `_io_helpers.py` (created in M2) has thin signatures (`path: Path → return type`).
  Candidate O can evolve to `source_ref: str → return type` without restructuring helper internals.
- 11 callsites identified in §S2.2 will need signature updates (Path → source_ref) when
  RawMaterialStore is introduced. List of callsites for candidate O reference: [enumerate].
- `_io_helpers.py` module docstring already mentions `read_json_lines_strict` as a future
  extension point; candidate O may add it if a strict ingestion path emerges.
- KNOWLEDGE.md §3.3 `RawMaterialStore` interface contract (resolve / exists / content_hash)
  is the authoritative shape; `_io_helpers` does not implement this contract directly,
  but its callsite list is a natural starting point.
```

理由:若候选 O 启动时由不同 Codex session / 长时间间隔后,需要明确 artifact 知道 Phase 67 为它做了哪些预留。

**验收条件**:
- `_io_helpers.py` 创建 + 3 helper variants 实装 + 必要单元测试(可选,Codex 决定;若实装 ≤ 50 LOC 可不补单测)
- 11+ callsite 全部显式选 variant + 无均质化错误(per S2.2 表)
- `cli.py:617-632` 私有 helpers 删除 + 所有 callsite 改 import `_io_helpers`
- audit_block4 finding 1 [high] backlog 标 Resolved
- audit_block2 finding 7 + audit_block4 finding 9 backlog 标 Partial(M3 内 CLI 侧消化)
- 全量 pytest 绿灯

**风险评级**:影响范围 2 / 可逆性 1 / 依赖 2 = 5(中)。design 决议层面的风险点是 IO helper 错误策略均质化(R1),已通过 S2.2 authoritative 表锁定。

---

### S3 — CLI Read-Only Dispatch Tightening(M3,中风险:public CLI surface)

**目标**:`cli.py:3640-3830` 的 20+ read-only artifact printer table-driven dispatch;不动 governance write / `task inspect` / `task review`。

**影响范围**:
- 改动:`src/swallow/cli.py:3640-3830`(收敛 20+ handler);可能新建 `src/swallow/_cli_dispatch.py`(若 dispatch table 大到值得独立)
- 0 docs/design/ diff
- tests/test_cli.py 不动(若有 golden output 必须保持)

**关键设计决议**:

#### S3.1 数据结构 — 采纳选项 (a)(authoritative,修订自 design_audit Q12 + Q15)

`paths.py` 实际不暴露统一 `<command>_path(base_dir, task_id)` 形式的 path resolver;不同命令依赖不同 path 函数(有的需 `task_id`,有的只需 `base_dir`,有的是 `artifacts_dir(base_dir, task_id) / "filename"` 拼接)。

**Dispatch table 实际形态(authoritative,Codex 严格按此实装)**:

```python
# cli.py 或 _cli_dispatch.py 内
from collections.abc import Callable
from pathlib import Path
from swallow._io_helpers import read_json_or_empty

# Read-only artifact printer dispatch table
# Each entry maps subcommand name → handler closure that:
#   1. resolves the artifact path (from base_dir + optional task_id)
#   2. loads the JSON payload via _io_helpers
#   3. prints indented JSON
#   4. returns 0
ARTIFACT_PRINTER_DISPATCH: dict[str, Callable[[Path, str | None], int]] = {
    # task-scoped read-only printers (need base_dir + task_id):
    "summary":             lambda base_dir, task_id: _print_artifact_json(artifacts_dir(base_dir, task_id) / "summary.md", parser=read_json_or_empty),
    "route_report":        lambda base_dir, task_id: _print_artifact_json(route_report_path(base_dir, task_id), parser=read_json_or_empty),
    "validation_report":   lambda base_dir, task_id: _print_artifact_json(validation_report_path(base_dir, task_id), parser=read_json_or_empty),
    # ... etc

    # base_dir-only read-only printers (task_id is ignored, but signature uniform):
    "canonical_registry":  lambda base_dir, _task_id: _print_artifact_json(canonical_registry_path(base_dir), parser=read_json_or_empty),
    "canonical_reuse":     lambda base_dir, _task_id: _print_artifact_json(canonical_reuse_path(base_dir), parser=read_json_or_empty),
    # ... etc

    # special case (dispatch command with mock-remote check, see §S3.4):
    # NOT in dispatch table; remains explicit if-chain handler.
}


def _print_artifact_json(path: Path, parser: Callable[[Path], dict | list]) -> int:
    """Shared formatter: load JSON via parser, print indented JSON, return 0."""
    payload = parser(path)
    print(json.dumps(payload, indent=2))
    return 0


def _dispatch_artifact_printer(args, base_dir: Path) -> int:
    handler = ARTIFACT_PRINTER_DISPATCH.get(args.task_command)
    if handler is None:
        # Phase 67 design: M3 converts ALL read-only printers in scope range
        # cli.py:3592-3787; if this fallback fires, it's a runtime bug
        # (a read-only command was missed during M3 implementation).
        raise NotImplementedError(
            f"Read-only printer dispatch table missing handler for {args.task_command!r}; "
            f"either add entry or remove from in-scope list per Phase 67 §S3.2"
        )
    task_id = getattr(args, "task_id", None)
    return handler(base_dir, task_id)
```

**关键设计约束**:
- **Path resolver 用 lambda 包裹**:不同 path 函数 signature 差异通过 lambda 抹平,统一签名 `Callable[[Path, str | None], int]`(base_dir + optional task_id → exit code)
- **`_print_artifact_json` 统一 formatter**:确保 stdout 输出 byte-for-byte 一致(per §S3.4 验证);Codex 实装时若发现某命令的旧 inline 实现有不同 indent / sort_keys / trailing newline,在 dispatch entry 中传专用 formatter
- **`raise NotImplementedError` fallback 为 authoritative**(修订自 design_audit Q15):M3 完成后所有 read-only printer 都进 table,fallback 永不触发;若 production 触发 = M3 漏处理某命令(回滚或补 entry)
- **`dispatch` 命令(special case)不进 table**:`cli.py:3639-3645` 含 `if is_mock_remote_task(...)` 条件 + `[MOCK-REMOTE]` 输出,需要 state loading + 条件渲染,不适合简单 dispatch entry。保持 explicit 处理 + 加入 §S3.4 manual 验证清单

**不采纳选项 (b) `@dataclass class CLICommand`**:read-only artifact printer 不需要 metadata,dict + lambda 已足够。

#### S3.2 In-scope read-only commands(authoritative,修订自 design_audit Q13)

**M3 scope 范围扩到 `cli.py:3592-3787`**(覆盖原 audit_block5 提到的 21-command set-membership block + 后续 read-only printer):

- `cli.py:3592-3645` set-membership dispatch block(`if args.task_command in {"summarize", "semantics", ..., "route"}`):**完全收敛到 ARTIFACT_PRINTER_DISPATCH**;现有 dict 结构(at line 3615)被新 dispatch table 取代
- `cli.py:3647-3787` 后续 read-only artifact printer:同款收敛
- 一个统一 dispatch table,不留两种 dispatch 机制

**特殊命令 — 不在 ARTIFACT_PRINTER_DISPATCH(保留 explicit dispatch)**:
- `dispatch` 命令(`cli.py:3639-3645`):有 mock-remote 条件渲染,explicit 处理
- 其他 governance write / task lifecycle 命令(详见 §S3.3)

**Codex PR body 必给的最终表**:M3 完成后,Codex 在 PR body 中列出所有 IN_SCOPE 读取命令的清单,与 ARTIFACT_PRINTER_DISPATCH entries 对位 — 让 Claude review 时验证 zero gap。

#### S3.3 Out-of-scope commands(authoritative,M3 不动)

**保持 explicit dispatch**(不进 table):
- Governance write:`proposal apply` / `proposal register-*` / `route registry apply` / `route policy apply` / `migrate` / `migrate --status`
- Task lifecycle:`task create` / `task acknowledge` / `task retry` / `task resume` / `task review --apply` / 任何写 truth 的命令
- Complex rendering:`task inspect` / `task review`(条件渲染 / 跨 namespace 数据组装 / 不适合简单 dict dispatch)
- 非 task 子命令:`note` / `ingest` / `synthesis` / `knowledge stage-promote` / 等

#### S3.4 行为 byte-for-byte 一致性验证(authoritative,修订自 design_audit Q14)

M3 完成后,Codex **必须**手动验证以下 6 个命令输出与改动前完全一致:

- `task summary --task-id <test_task>`
- `task route-report --task-id <test_task>`
- `task validation-report --task-id <test_task>`
- `task knowledge-policy-report --task-id <test_task>`
- `task knowledge-decisions --task-id <test_task>`
- **`task dispatch --task-id <test_task>`(special case,mock-remote conditional path,explicit handler 而非 dispatch table entry,但仍需验证 M3 改动未误触动)**

验证方式:
1. M3 改动前,在 fixture task 上跑这 6 个命令,保存输出到临时文件
2. M3 改动后,再跑一次,`diff` 应为空
3. 若不空 → 回滚或修订 dispatch handler 的 formatter 实现

若 `tests/test_cli.py` 已有这些命令的 integration test(很可能有部分),M3 实装通过 = pytest 通过 + 上述手动验证;若整套 golden output test 缺失,**M3 内不补**(留给后续 testing-debt phase),只做手动验证。

#### S3.5 argparse parser registration 不改(authoritative)

M3 **只改 dispatch handler**,不改 `task_subparsers.add_parser(...)` 注册顺序 / help text / argument schema。`--help` 输出必须保持。

**验收条件**:
- `cli.py:3640-3830` 范围内 20+ read-only artifact printer 收敛到 dispatch table
- governance write commands 保持 explicit dispatch
- `task inspect` / `task review` 不动
- 5 个 read-only command 手动验证 byte-for-byte 一致 + pytest 整体绿灯
- audit_block5 finding 3 backlog 标 Partial(M3 内 read-only 子集消化;governance write + task inspect/review 未做)
- 全量 pytest 绿灯

**风险评级**:影响范围 2 / 可逆性 1 / 依赖 1 = 4(中)。public CLI surface 改动,但起步 read-only 子集 + 严格保持输出。

---

## 依赖与顺序

```
S1 (M1, 7 quick-win) ──> S2 (M2, IO helper + artifact ownership 决议) ──> S3 (M3, CLI dispatch)
                       (M2 IO helper 是 M3 read-only printer 的依赖)
                       (M2 artifact name 决议影响 M3 dispatch table 是否内嵌 artifact 名)
```

**不允许并行**:Codex 必须按 M1 → M2 → M3 顺序;Claude review 通过一个 milestone 才进下一个。理由:
- M2 IO helper 是 M3 read-only printer 的依赖(M3 用 `read_json_or_empty` 替代 inline `json.loads(path.read_text())`)
- M2 artifact name 决议(采纳窄选项 (a))= "M3 dispatch table 内嵌 artifact 名 mapping",M2 决议变更会需要 M3 重新对齐
- 倒序 / 并行会导致 review 被迫 cross-milestone 评估,违反 Phase 67 设计的"严格分 milestone"原则

## Milestone 与 review checkpoint

| Milestone | 包含 slice | review 重点 | 提交节奏 |
|-----------|-----------|------------|---------|
| **M1** | S1(7 quick-win) | 每项 quick-win 删除 / 命名是否对位 + `_pricing_for` grep 确认 + `[:4000]` 三处一致 + reviewer_timeout owner 决议 + 全量 pytest | 单 commit;Claude 产 `review_comments_block_l.md` |
| **M2** | S2(IO helper + artifact ownership) | `_io_helpers.py` 三 variant 是否对应 §S2.1 模板 + 11 callsite 是否按 §S2.2 表均质化 + cli.py 私有 helpers 删除 + 行为零变化(关键!) | 1-2 commit(可拆 helper 创建 vs callsite 替换);Claude 产 `review_comments_block_m.md` |
| **M3** | S3(CLI dispatch) | dispatch table 是否仅含 read-only artifact printer + governance write / task inspect/review 是否未触动 + 5 个手动验证命令 byte-for-byte 一致 + parser registration 不改 | 单 commit;Claude 产 `review_comments_block_n.md` + Phase 67 final review |

## Review 分轮机制

- Claude **不一次性 review 全 phase**;按 M1 → M2 → M3 分轮(类比 Phase 66)
- 每轮 review 产单独的 `review_comments_block_<l|m|n>.md`,Codex 据此修订 / 进下一 milestone
- 每轮 review 后 Codex 才进入下一 milestone(避免 review 反馈未消化前后续 milestone 已 baked in)
- 全 phase closeout 时 Claude 出 final review_comments(若 M1-M3 review 已无遗留可直接进 closeout)

### M2/M3 倒灌 M1 fixup commit 协议(authoritative,修订自 design_audit Q16)

若 M2 或 M3 review 阶段 Claude 发现 M1 已 commit 代码有遗漏 / 副作用 / defect:

1. Claude 在 M2(或 M3)的 `review_comments_block_<m|n>.md` 中显式标 "M1 fixup directive",描述 defect + 期望修订
2. Codex 在当前 branch(`feat/phase67-hygiene-io-cli-cleanup`)上**新建 fixup commit**(命名 `fixup(phase67-m1): <description>`),不要 amend M1 commit、不要 cross-milestone 混改
3. fixup commit 必须独立 commit,与 M2/M3 主 commit 平行;Claude 在最近的 review_comments 中标 fixup commit 已消化
4. Codex 只在收到 fixup directive 后才修;不主动跨 milestone "顺手修"

类比 Phase 66:M2 主动接受 M1 review CONCERN-1 把 finding 升级到 high(per Phase 66 patterns)。Phase 67 继承同款机制,**但更严格**:必须 explicit directive,不允许 Codex 自决跨 milestone 修订。

## phase-guard 检查

- ✅ 当前方案不越出 kickoff goals(G1-G4 与 S1-S3 + 跨 milestone 协调一一对应)
- ✅ kickoff non-goals 严守:**不修改 docs/design/**;不实装 RawMaterialStore;不重构 task inspect/review;不动 governance write;不审 tests/;不引入新工具;不消化 quick-win 之外 [low] 项
- ✅ INVARIANTS / DATA_MODEL / KNOWLEDGE 零改动(本 phase 是实装清理,不评判设计)
- ✅ slice 数量 3 个,符合"≤5 slice"指引
- ✅ 0 个高风险 slice;最高风险 = M2 IO helper(中,5 分),已通过 §S2.2 authoritative 表锁定
- ✅ Phase 66 audit findings 转化路径清晰(每条 finding → backlog 状态变化)

## Branch Advice

- 当前分支:`main`(Phase 66 已 merge,KNOWLEDGE 三层架构升级已 merge,roadmap 已更新)
- 建议 branch 名:`feat/phase67-hygiene-io-cli-cleanup`
- 建议 commit 节奏:M1 (1 commit) → M2 (1-2 commit) → M3 (1 commit) → docs (1 closeout commit) = 4-5 commits 上 PR

## Model Review Gate

**默认 skipped**(详见 kickoff §Model Review Gate):清理 phase + 不触动设计 + max risk score = 5,无触发条件。

## 不做的事(详见 kickoff non-goals)

- 不修改任何 docs/design/
- 不实装 RawMaterialStore(候选 O scope)
- 不重构 task inspect / task review
- 不动 governance write 命令的 dispatch
- 不审 tests/
- 不引入新工具
- 不消化 quick-win 之外的 [low] severity 项
- 不引入 multi-actor / authn

## 验收条件(全 phase)

详见 `kickoff.md §完成条件`。本 design_decision 与 kickoff 一致,无补充。
