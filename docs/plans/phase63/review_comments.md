---
author: claude
phase: phase63
slice: review
status: final
depends_on: ["docs/plans/phase63/design_decision.md", "docs/plans/phase63/kickoff.md", "docs/plans/phase63/risk_assessment.md", "docs/plans/phase63/commit_summary.md", "docs/plans/phase63/consistency_report.md"]
---

TL;DR: **Verdict: APPROVE.** 0 [BLOCK] / 2 [CONCERN] / 9 [NOTE]. M1/M2/M3 全部按 final-after-m0 设计落地;574 passed / 2 skipped(G.5)/ 8 deselected;`docs/design/` 零 diff;Repository 抽象层骨架与 §9 守卫批量未引入设计未授权的偏离。S3 一致性已由 consistency-checker 子代理交叉核验为 minor-drift(均为文档/描述类细节),无行为/架构问题。两条 [CONCERN] 建议本 PR 内消化:守卫名与实际范围不一致、commit_summary 缺 §S3 设计要求的 1:1 signature mapping table。

# Phase 63 PR Review

## 审阅范围

- 分支: `feat/phase63-governance-closure` vs `main`
- diff 体量: 35 文件,3053 insertions / 346 deletions
- commit 序列: c3637b1(M0)→ 1453ea7(design sync)→ e905eee(M1/S1)→ de06fef(M1 state)→ 088836f(M2/S2)→ 1df5992(M2/S3)→ 5489a16(M2 state)→ 5116b62(M3/S4)→ bf6caa4(M3 state)→ f9189b8(handoff)
- 设计基线: `design_decision.md` / `kickoff.md` / `risk_assessment.md`(均 status=final-after-m0)
- 一致性核验: `docs/plans/phase63/consistency_report.md`(consistency-checker subagent,verdict=minor-drift)
- 测试基线复跑: `.venv/bin/python -m pytest` → 574 passed / 2 skipped / 8 deselected(与 commit_summary 一致)

## 总体结论

| 维度 | 结果 |
|------|------|
| INVARIANTS.md / DATA_MODEL.md 文字未改 | ✅ `git diff main...HEAD -- docs/design/` 零行 |
| §9 守卫表完整性 | ✅ 17 条全部存在(15 active + 2 G.5 skip 占位) |
| Repository write 收敛 | ✅ `governance.py` 不再 import `save_route_*`/`save_*_policy` 写函数 |
| `apply_proposal(proposal_id, operator_token, target)` 三参数签名 | ✅ 不变 |
| 删除 dead code 等价性 | ✅ 测试 mock 重命名 + 断言反转,意图保留 |
| `_PENDING_PROPOSALS` duplicate 检测 | ✅ `DuplicateProposalError`(`target.value` + `proposal_id` 都在消息) |
| Repository 2 条 bypass 守卫 | ✅ 非 vacuous AST 扫描 |
| SQLite append-only triggers | ✅ 4 张表 × 2 trigger,idempotent |
| §7 集中化 + S1 守卫非 vacuous | ✅ `assert local_actor() == "local"` 锚定 + 26+ 处 path 集中化 |
| pytest 回归 | ✅ 574 passed / 2 skipped(G.5)/ 8 deselected |

**Verdict**: APPROVE for Human Merge Gate(待 [CONCERN] 二选一处理后入 PR body)。

---

## M1 / S1 — §7 集中化函数 + 守卫真实化

### [PASS] identity / workspace 模块设计

- `src/swallow/identity.py:4-5` —— `local_actor() -> str` 单函数,零参数。**唯一**返回 `"local"` 字面量的位置。设计意图完整落地。
- `src/swallow/workspace.py:7-13` —— `_workspace_base()` 优先级 `base > SWL_ROOT > cwd`,与 `design_decision.md` §S1 关键设计决策完全一致。
- `src/swallow/workspace.py:16-20` —— `resolve_path()` 对绝对路径直接 `.resolve()`,对相对路径先 join workspace base 再 `.resolve()`。

### [PASS] 生产路径迁移完整

`orchestrator.py` 引入 `_resolved_path_string(path)` helper(line 188-189),把 26+ 处 `str(path.resolve())` 一次性替换为 `_resolved_path_string(path)`。批量改动机械且无遗漏(grep 不再命中除 workspace.py 外的 `.resolve()`)。

### [PASS] S1 两条守卫均非 vacuous

- `tests/test_invariant_guards.py:219-238 test_no_hardcoded_local_actor_outside_identity_module` —— 用 AST 而非 grep,扫描 `kwarg.arg in ACTOR_SEMANTIC_KWARGS` 且 `kwarg.value` 是 `Constant("local")` 的位置;line 237 `assert local_actor() == "local"` 提供反 vacuous 锚点。
- `tests/test_invariant_guards.py:241-254 test_no_absolute_path_in_truth_writes` —— 扫描 `Path.resolve()` / `Path.absolute()` 调用,exempt `workspace.py`。

### [PASS] ACTOR_SEMANTIC_KWARGS 闭集扩展彻底

`tests/test_invariant_guards.py:20-54` 闭集列出 31 个 kwarg(actor / *_by / caller / owner / user / principal / operator / originator / agent / executor_name 等),远超 design_decision §S1 给的最小集。`action` 已正确**未列入**(M0 audit 后修正)。

### [NOTE M1-1] LOCAL_EXECUTOR_IDENTITY_CALLS 例外未在设计中显式授权

`tests/test_invariant_guards.py:55` 定义:
```python
LOCAL_EXECUTOR_IDENTITY_CALLS = {"ExecutorResult", "RouteSpec"}
```
随后在 `_is_allowed_local_executor_identity()`(line 158-159)对 `executor_name="local"` 出现在 `ExecutorResult(...)` / `RouteSpec(...)` 构造时豁免。

`design_decision.md` §S1 关键设计决策列出 `executor_name` 在 `ACTOR_SEMANTIC_KWARGS` 闭集内,但**未声明 ExecutorResult/RouteSpec 是合法的 site-semantic 容器**。这与 `execution_site="local"` 站点语义豁免性质类似,但需要补一句设计文字背书。

- 影响: 低。豁免范围具体且狭窄(仅 2 个构造函数);若未来误添加新的 actor-semantic call site 不在闭集里,守卫仍会命中。
- 建议: closeout 中补一句 "ExecutorResult/RouteSpec.executor_name='local' 视为 site-semantic 等价物,与 execution_site='local' 一致";或在 design_decision §S1 关键设计决策段添加该例外条款。

### [NOTE M1-2] test_no_absolute_path_in_truth_writes 名实不符

守卫名称暗示"truth 写入路径"专属,实际实装(`tests/test_invariant_guards.py:241-254`)扫描 `src/swallow/` **所有 .py** 中的 `Path.resolve()` / `Path.absolute()` 调用——比 design_decision.md §S1 描述("Truth 写入函数禁止接收 `Path.absolute()` 或 `Path.resolve()` 调用结果作为持久化字段")**更严格**。

- 影响: 中。实际语义是"`workspace.py` 之外不允许 `Path.resolve()/.absolute()`",这是 §7 集中化的硬约束。比 truth-writes-only 更彻底,符合本 phase 总目标。
- 建议: 在守卫 docstring 中补一句"strict superset of truth-write contexts: enforces §7 path resolution centralization"。或重命名守卫为 `test_no_absolute_path_resolution_outside_workspace_module`。

---

## M2 / S2 — 删除 `_route_knowledge_to_staged` dead code

### [PASS] 函数体 + 调用点 + 顶层 import 三处全清

- `src/swallow/orchestrator.py` line 139 原 `from .staged_knowledge import StagedCandidate, submit_staged_candidate` 整行删除
- `_route_knowledge_to_staged` 函数体(原 line 3131-3175)整段删除
- `staged_candidates = _route_knowledge_to_staged(base_dir, state)` 调用点替换为 `staged_candidate_count = 0`(line 3655)
- grep 验证: `grep -rn "submit_staged_candidate" src/swallow/` 仅命中 `staged_knowledge.py` 定义、`cli.py` 操作员路径、`ingestion/pipeline.py` 4 处 Specialist 路径——全部为 design 列出的合规位置

### [PASS] 测试 mock R16 等价性保持

`tests/test_cli.py` 测试函数重命名:
- 旧: `test_run_task_routes_promote_intent_knowledge_to_staged_for_canonical_forbidden_route`
- 新: `test_run_task_canonical_forbidden_route_does_not_stage_knowledge_in_orchestrator`

断言对应反转(`len(staged_records) == 1` → `staged_records == []`;`assertTrue(... task.knowledge_staged ...)` → `assertFalse(...)`;`staged_candidate_count == 1` → `staged_candidate_count == 0`);**保留** `task.canonical_write_guard_warning` 断言(canonical-write-guard 仍正常发出)。这是清晰的"原意图反转 = 新合约验证"模式,符合 R16 风险缓解策略。

### [PASS] test_meta_optimizer.py 未触动是正确选择

design_decision §S2 列出的 `tests/test_meta_optimizer.py:692 meta-optimizer-local` mock route 实际**没有 `taxonomy_memory_authority` 字段**(grep 验证),从未触发被删除的代码路径。Codex 正确判断不需要调整。design 当时是基于 M0 audit 报告的保守描述,未细看 RouteSpec 字段——属于 design 过度规约,实装未盲从,合理。

### [NOTE M2-1] staged_candidate_count = 0 是 vestigial 字段

`orchestrator.py:3655 staged_candidate_count = 0` 永远是 0,但仍在 line 3677 / line 3738 两处事件 payload 中保留。保留是为了不破坏现有事件 payload schema(向后兼容)。

- 影响: 低。事件消费者读到的字段值变化,但字段存在性不变。
- 建议: closeout 登记一条 backlog Open——"task.* 事件 payload 中的 `staged_candidate_count` 字段在 Phase 63 后永远为 0,可在某次未来事件 schema 演进时移除"。

---

## M2 / S3 — Repository 抽象层骨架(高风险切片)

> consistency-checker subagent 已并行核验,verdict = `minor-drift`,详见 `docs/plans/phase63/consistency_report.md`。

### [PASS] truth 模块结构与对外接口

| 文件 | 主类 | 私有写方法 | 验证 |
|------|------|----------|------|
| `truth/knowledge.py` | `KnowledgeRepo` | `_promote_canonical(...)` | knowledge.py:14-51 |
| `truth/route.py` | `RouteRepo` | `_apply_metadata_change(...)` | route.py:13-32 |
| `truth/policy.py` | `PolicyRepo` | `_apply_policy_change(...)` | policy.py:10-23 |
| `truth/proposals.py` | `PendingProposalRepo` + `DuplicateProposalError` | `register(...)` / `load(...)` | proposals.py:6-33 |
| `truth/__init__.py` | (re-export) | — | __init__.py:8-14 |

### [PASS] governance.py 完成切换

- `governance.py:9-14` 仅 import `load_route_capability_profiles`、`load_route_weights`、`normalize_route_name`、`route_by_name` 四个**读路径** + `route_by_name`,不再 import 任何 `save_*` / `apply_*_weights` / `apply_*_profiles` 写路径
- `governance.py:212-216 apply_proposal(proposal_id, operator_token, target) -> ApplyResult` 三参数签名严格保持
- 写入分发: `_apply_canonical` (line 260) / `_apply_route_metadata` (line 285 + line 529) / `_apply_policy` (line 563/580) 全部经 Repository 私有方法

### [PASS] _PENDING_PROPOSALS 重复检测

- `governance.py:86 _PENDING_PROPOSALS = PendingProposalRepo()` 模块级实例
- key 为 `(target, normalized_id)` 元组(`proposals.py:18`),与 design_decision §S3 一致
- 重复 register 抛 `DuplicateProposalError`,异常消息同时包含 `proposal_id` 与 `target.value`
- `tests/test_governance.py:117 test_duplicate_proposal_id_raises` 实测通过

### [PASS] 2 条 Repository bypass 守卫非 vacuous

- `test_only_governance_calls_repository_write_methods`(line 304-310): AST 扫描 `_promote_canonical`/`_apply_metadata_change`/`_apply_policy_change` 调用,allow-list = `{governance.py}`
- `test_no_module_outside_governance_imports_store_writes`(line 313-345): AST 扫描 ImportFrom,protected = 6 个写函数,allow-list = `{governance.py 不在内, truth/*, store.py, router.py, knowledge_store.py, mps_policy_store.py, consistency_audit.py}`(governance.py 因为已经不再 import 这些函数,所以不需要在 allow-list 里——consistency-checker 已确认这是正确而非缺失)

### [PASS] 既有 Phase 61 守卫扫描目标已扩展

`test_only_apply_proposal_calls_private_writers`(line 257-286)的 `allowed_files` 已加入 `truth/{knowledge,route,policy}.py` 三个新模块,符合 design_decision §S3 line 134 的更新要求。

### [PASS] 严格守住 Phase 63 scope 边界

consistency-checker 与本 review 双方核验:
- ❌ Repository 引入 read 方法 → **未发生**
- ❌ Repository 包 `BEGIN IMMEDIATE` 事务 → **未发生**
- ❌ 修改原始 store 函数 → **未发生**(diff stat 未触动 router.py / knowledge_store.py / store.py 写函数本身)
- ❌ 引入 durable proposal artifact 层 → **未发生**(`PendingProposalRepo._pending` 仍是 in-memory dict)

### [CONCERN M2-A] commit_summary.md 缺 1:1 signature mapping table

`design_decision.md §S3 line 152` 明确要求:
> S3 PR body 必须包含一份 actual signature mapping table(列出每个 Repository 私有方法的完整 Python 签名 vs 转发的原 store 函数签名),Claude review 时验证一致性。

`commit_summary.md` 现状仅给出 milestone 级描述,无 Repository 私有方法 ↔ store 写函数的逐行签名对照。

- 影响: 中。文档缺失但不影响行为正确性。在 Phase 64 调整事务边界时,缺这张表会让 implementer 不能快速核验"哪个 Repository 方法对应哪些 store 写"。
- 建议: Codex 在整理 `pr.md` 时,根据下表(本 review 整理)填入 PR body。**这是本 PR 内可消化的 [CONCERN]**。

| Repository 私有方法 | 转发到的原 store 函数 | 来源模块 |
|---|---|---|
| `KnowledgeRepo._promote_canonical(*, base_dir, canonical_record, write_authority, mirror_files, persist_wiki, persist_wiki_first, refresh_derived) -> tuple[str, ...]` | `persist_wiki_entry_from_record(base_dir, record, *, mirror_files, write_authority)` + `append_canonical_record(base_dir, record)` + (optional) `save_canonical_registry_index(base_dir, index)` + `save_canonical_reuse_policy(base_dir, summary)` | `knowledge_store.py` + `store.py` |
| `RouteRepo._apply_metadata_change(*, base_dir, route_weights=None, route_capability_profiles=None) -> tuple[str, ...]` | (条件)`save_route_weights(base_dir, weights)` + `apply_route_weights(base_dir)` ;(条件)`save_route_capability_profiles(base_dir, profiles)` + `apply_route_capability_profiles(base_dir)` | `router.py` |
| `PolicyRepo._apply_policy_change(*, base_dir, audit_trigger_policy=None, mps_kind=None, mps_value=None) -> tuple[str, Path]` | `save_audit_trigger_policy(base_dir, policy)` 或 `save_mps_policy(base_dir, kind, value)` | `consistency_audit.py` + `mps_policy_store.py` |

### [NOTE M2-2] DuplicateProposalError 消息字段顺序

design_decision.md §S3 line 161:"异常消息包含 `target.value` 与 `proposal_id`"——读起来像 `target.value` 先 / `proposal_id` 后。
实际(`proposals.py:21`):
```python
f"Duplicate proposal artifact: {normalized_id} ({target_value})"
```
两个值都在,顺序相反。`tests/test_governance.py:117` 仅匹配 `proposal_id` 子串,未强制顺序。功能正确。

- 影响: 低。
- 建议: 不改代码。closeout 时 design_decision §S3 line 161 措辞改为"消息同时包含 `proposal_id` 与 `target.value`(顺序无要求)",或保持现状不动。

### [NOTE M2-3] RouteRepo._apply_metadata_change 条件调用 vs 设计描述

design_decision.md §S3 line 148 表述:"顺序调用 `save_route_weights` → `apply_route_weights` → `save_route_capability_profiles` → `apply_route_capability_profiles`",读起来像无条件依次执行。
实装(`route.py:21-31`)对每对 save+apply 用 `if ... is not None:` 包起来,只在对应 payload 非 None 时执行。

- 这是更安全的实装(支持只更新 weights 或只更新 profiles 的 partial proposal),与 `_RouteMetadataProposal` dataclass 设计一致。
- 设计描述措辞偏差,**实装方向正确**。
- 建议: 不改代码,closeout 中标注 design 措辞 vs 实装的差异;或在 design §S3 line 148 加一句"两组写按对应 payload 是否非 None 条件触发"。

### [NOTE M2-4] _RouteMetadataProposal.review_path 字段未在 §S3 数据形态描述

`governance.py:65-71`:
```python
@dataclass(frozen=True)
class _RouteMetadataProposal:
    base_dir: Path
    route_weights: dict[str, float] | None = None
    route_capability_profiles: dict[str, dict[str, object]] | None = None
    review_path: Path | None = None
```
`review_path` 是为 `_apply_route_review_metadata`(line 300-558,处理 meta-optimizer 评审记录)专用的字段。design_decision §S3 仅描述 `route_weights` / `route_capability_profiles` 两个字段;新增 `review_path` 是保持 meta-optimizer review apply 路径走新边界的必需补丁,但**未在 design 中显式授权**。

- 影响: 低。该字段属于 governance 内部 dataclass,不暴露给外部调用方,边界守卫(2 条 bypass guard)依然有效。
- 建议: closeout 中登记说明"为兼容 meta-optimizer review apply 路径,_RouteMetadataProposal 增加 review_path 字段;非 §S3 设计预定义但属于必要补丁"。

### [NOTE M2-5] _apply_route_review_metadata 仍在 governance.py 内,~250 行业务逻辑

`governance.py:300-558` 实装 `_apply_route_review_metadata`,做 meta-optimizer 评审记录的字段 reconciliation(applied/noop/skipped 计数、rollback_weights 快照、route_capability_profiles 合并),最后在 line 529 调用 `RouteRepo()._apply_metadata_change`。

- 写路径合规(经 Repository),但 ~250 行 reconciliation 逻辑沉淀在 governance.py。
- 影响: 低。Phase 63 范围是治理边界收口,不要求拆分 governance.py 内部模块化。但这块代码长期看应该归到 `meta_optimizer/` 或独立 `route_review_apply.py`。
- 建议: 不改本 phase。closeout 或 backlog 登记一条"governance.py:_apply_route_review_metadata reconciliation 逻辑可在 meta-optimizer 或 truth 层独立重构"作为后续候选。

---

## M3 / S4 — §9 守卫批量实装 + SQLite trigger 基础设施

### [PASS] §9 标准表 17 条全部存在

| 类别 | 条目数 | 状态 |
|------|-------|------|
| Phase 61 既有 apply_proposal 守卫 | 3 | 全 active |
| Phase 63 / S1 集中化守卫 | 2 | 全 active |
| Phase 63 / S4 行为合规类 | 6(NO_SKIP 4 + 行为 1 + G.5 占位 2) | 4 active + 2 G.5 skip |
| Phase 63 / S4 ID & 不变量类 | 5 | 全 active |
| Phase 63 / S4 UI 边界 | 1 | active |
| **合计** | **17** | **15 active + 2 G.5 skip 占位** |

### [PASS] G.5 占位 skip 措辞标准化

`test_path_b_does_not_call_provider_router`(line 456-457) / `test_specialist_internal_llm_calls_go_through_router`(line 460-461):
```python
def test_*():
    pytest.skip(reason="G.5 will enable, see roadmap candidate G.5")
```
满足 `risk_assessment.md` R6 要求的"`pytest.skip(reason=...)` 占位 + 标 G.5"。

### [PASS] NO_SKIP_GUARDS 6 条全 active

design_decision §S4 列出的 6 条立即启用的 NO_SKIP_GUARDS:
- `test_no_executor_can_write_task_table_directly`(line 348)
- `test_state_transitions_only_via_orchestrator`(line 370)
- `test_validator_returns_verdict_only`(line 395) —— 含 `assert verdict_returns` 的反 vacuous 锚点
- `test_canonical_write_only_via_apply_proposal`(line 194,Phase 61 既有,allow-list 已扩展含 `truth/knowledge.py`)
- `test_only_apply_proposal_calls_private_writers`(line 257,Phase 61 既有,allow-list 已扩展含 `truth/{knowledge,route,policy}.py`)
- `test_route_metadata_writes_only_via_apply_proposal`(line 207,Phase 61 既有,allow-list 已扩展含 `truth/route.py`)

### [PASS] SQLite append-only trigger 基础设施

`src/swallow/sqlite_store.py:151 APPEND_ONLY_TABLES = ("event_log", "event_telemetry", "route_health", "know_change_log")` 与 design_decision §S4 完全一致。

`APPEND_ONLY_TRIGGER_SQLS`(line 152-167)为每张表生成 BEFORE UPDATE / BEFORE DELETE 两个 idempotent trigger(`CREATE TRIGGER IF NOT EXISTS`),每个 trigger 调用 `RAISE(FAIL, '{table} is append-only')`。

`SqliteTaskStore._connect` 初始化路径(line 207-220)无条件运行 `CREATE TABLE IF NOT EXISTS` 与全部 trigger SQL。**Idempotent**,既有 DB 升级时无破坏。

### [PASS] write_artifact 路径边界收紧

`src/swallow/store.py:714-723`:
```python
def write_artifact(base_dir: Path, task_id: str, name: str, content: str) -> Path:
    ensure_task_layout(base_dir, task_id)
    artifact_name = Path(name)
    if not str(name).strip() or artifact_name.is_absolute() or ".." in artifact_name.parts:
        raise ValueError("Artifact name must be relative to the task artifact directory.")
    path = artifacts_dir(base_dir, task_id) / artifact_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return path
```
匹配 `tests/test_invariant_guards.py:572-579 test_artifact_path_resolved_from_id_only` 的反例:`..` 与绝对路径都拒绝。

### [PASS] 跨命名空间 FK 守卫 + 既有 FK 移除

`tests/test_invariant_guards.py:501-515 test_no_foreign_key_across_namespaces` 实测全表 PRAGMA foreign_key_list 后断言为空。

`sqlite_store.py` 既有 3 处 FK 已移除:
- `events` 表 `FOREIGN KEY (task_id) REFERENCES tasks(task_id)` 删除
- `knowledge_evidence` 表 同上 删除
- `knowledge_wiki` 表 同上 删除

3 处都是从 events / knowledge 命名空间引向 tasks 命名空间的 task_id 外键,符合"no cross-namespace FK"语义。

### [CONCERN M3-A] test_no_foreign_key_across_namespaces 实际比命名严格

守卫名称暗示"no cross-namespace FK",实装(`tests/test_invariant_guards.py:515 assert {table: rows for table, rows in foreign_keys.items() if rows} == {}`)断言**任意表都不能有任何 FK**,包括同命名空间内的 FK。

- 影响: 中。本 phase 删除的 3 处 FK 全部是跨命名空间,实装与设计语义在当前快照下一致。但守卫本身硬约束"零 FK",未来若需要在 knowledge 命名空间内部建 FK(如 evidence → wiki 内部引用),会被守卫挡住。
- 建议(可选,本 PR 内消化):
  - 选项 A — 保持守卫名,改 docstring 注明"strict superset of cross-namespace: no FK at all in current schema"
  - 选项 B — 重命名为 `test_no_foreign_key_constraints`,与实装一致
  - 选项 C — 调整断言只过滤跨命名空间 FK(需先定义命名空间分组,工作量大,不建议本 phase)
  
  Claude 推荐选项 A(成本最低,语义清晰)。这是本 PR 内可消化的 [CONCERN]。

### [NOTE M3-1] append_event 双写 events + event_log

`sqlite_store.py:305-318 append_event` 在同一事务中先 INSERT 进既有 `events` 表,再 INSERT 进新增 `event_log` 表。

- 同事务保证原子性,新部署的 DB 两表完全同步;但**既有 DB 在升级到 Phase 63 后**,`events` 已有历史行,`event_log` 是空的——两表内容会持续一段时间不同步。
- Phase 63 不引入 backfill 脚本(out of scope)。事件日志读路径目前仍走 `events`,`event_log` 仅用于守卫 + 未来 Phase 64 切换。
- 建议: closeout 登记一条 backlog Open——"`event_log` 在既有 DB 升级时与 `events` 不同步;Phase 64 候选 H 应规划一次性 backfill 或在事件读路径切换时显式忽略 pre-Phase63 的 `events` 行"。

### [NOTE M3-2] test_event_log_has_actor_field 默认值字符串硬比

`tests/test_invariant_guards.py:498`:
```python
assert str(columns["actor"]["dflt_value"]).strip("'\"") == local_actor()
```
要求 SQLite DDL 中 `actor TEXT NOT NULL DEFAULT 'local'` 字面量与 `local_actor()` 返回值字符串一致。这意味着**未来若 `local_actor()` 实现切换**(如 multi-actor 改造),还必须**同步修改 SQL DDL 中的 DEFAULT 字符串**——否则守卫会红灯。这与"`local_actor()` 是唯一字面量入口、未来切换时调用方零改动"的 §7 集中化目标存在隐性张力。

- 影响: 低。本 phase 内行为正确;但耦合一条隐性 invariant("DDL DEFAULT 与 local_actor() 返回值同步")。
- 建议: closeout 登记。或在守卫旁加一句注释"这是 §7 集中化的边界例外:DDL DEFAULT 是 SQLite 引擎层语义,Python 层 `local_actor()` 切换时 DDL 必须同步迁移"。

---

## 全局一致性

### [PASS] INVARIANTS / DATA_MODEL 文字未改

```bash
$ git diff main...HEAD -- docs/design/ | wc -l
0
```
本 phase final-after-m0 non-goals 中"不修改 INVARIANTS 任何文字(包括 §5 矩阵)"严格守住。

### [PASS] 测试基线复跑一致

```
$ .venv/bin/python -m pytest --tb=line -q
574 passed, 2 skipped, 8 deselected, 10 subtests passed in 87.45s
```
与 `commit_summary.md` 报告完全吻合。2 skipped 即 G.5 占位的 2 条 NO_SKIP 守卫。

### [PASS] commit message 风格规范

10 commit 全部符合 conventional commit:`feat/refactor/test/docs(phase63): ...`,phase scope 明确。M1/M2/M3 各自有 implementation commit + state sync commit 配对,commit gate 留痕完整。

---

## 处理建议

### 进入 PR(本 PR 内消化)

1. **[CONCERN M2-A] 补 §S3 1:1 signature mapping table**: Codex 在 `pr.md` 整理时把上文 M2 章节的 mapping table 写入 PR body,锚定到 design_decision §S3 line 152 的明确要求。
2. **[CONCERN M3-A] test_no_foreign_key_across_namespaces 名实统一**: 推荐选项 A,在 guard 函数 docstring 中追加一句说明实装是 cross-namespace 的 strict superset。

### 进入 closeout 留痕(不入 PR body / 不入 backlog)

- M1-1 / M1-2:S1 守卫的两处实装超出/侧重设计描述,但方向正确——记录 design 与实装的差异。
- M2-2 / M2-3 / M2-4:S3 三条 minor drift,均为文档措辞或新增字段,不影响行为。
- M3-2:`test_event_log_has_actor_field` 与 `local_actor()` 之间的隐性 DDL 耦合,记录到 closeout。

### 进入 concerns_backlog(后续 phase 消化)

- **M2-1 staged_candidate_count = 0 vestigial 字段**:登记一条"task.* event payload `staged_candidate_count` 字段在 Phase 63 后永远为 0,可在事件 schema 演进 phase 移除"。
- **M2-5 _apply_route_review_metadata 长函数沉淀在 governance.py**:登记一条"governance.py 内 ~250 行 meta-optimizer reconciliation 逻辑可独立重构到 meta_optimizer 或 truth 层"。
- **M3-1 event_log/events 双写状态分歧**:登记一条"既有 DB 升级到 Phase 63 后 `event_log` 与 `events` 内容不同步;Phase 64 候选 H 的 SQLite 迁移应包含 backfill 或明确 cutoff 策略"。

### 进入 PR body 测试节

```
.venv/bin/python -m pytest
574 passed, 2 skipped, 8 deselected
git diff main...HEAD -- docs/design/  # 0 lines
git diff --check  # passed
```

skipped 2 条:
- `test_path_b_does_not_call_provider_router` — G.5 待启用
- `test_specialist_internal_llm_calls_go_through_router` — G.5 待启用

---

## Tag 建议

不建议本 PR 后立即打 tag:Phase 63 是治理债务收口的**第一段**,候选 G.5(`feat/phase63.5-no-skip-fixes`)与候选 H(Truth Plane SQLite)是配套延伸。建议 G.5 完成后再评估 `v1.4.0` minor bump,以"governance closure" 为主题集中描述这一组改动。

## 决议

**APPROVE**(待 [CONCERN M2-A] / [CONCERN M3-A] 二选一处理后写入 `pr.md`,Human 在 Merge Gate 决定本 PR 内是否消化或登记 backlog)。

下游动作:
1. **[Codex]** 整理 `pr.md`(含 mapping table、test 节、跳过守卫说明、closeout 留痕清单);可选消化 [CONCERN M3-A] guard docstring 补充
2. **[Codex]** Phase 63 closeout 文件 `docs/plans/phase63/closeout.md` 待 merge 后产出,内含本 review 的 NOTE/closeout-only 条目与 backlog 登记
3. **[Human]** push branch + 创建 PR
