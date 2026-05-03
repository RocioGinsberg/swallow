---
author: claude
phase: lto-1-wiki-compiler-first-stage
slice: pr-review
status: final
depends_on:
  - docs/plans/lto-1-wiki-compiler-first-stage/plan.md
  - docs/plans/lto-1-wiki-compiler-first-stage/plan_audit.md
  - docs/plans/lto-1-wiki-compiler-first-stage/closeout.md
  - src/swallow/surface_tools/wiki_compiler.py
  - src/swallow/application/commands/wiki.py
  - src/swallow/application/commands/knowledge.py
  - src/swallow/application/queries/knowledge.py
  - src/swallow/adapters/cli_commands/wiki.py
  - src/swallow/adapters/http/api.py
  - src/swallow/adapters/http/schemas.py
  - src/swallow/adapters/http/static/index.html
  - src/swallow/knowledge_retrieval/_internal_staged_knowledge.py
  - src/swallow/knowledge_retrieval/knowledge_plane.py
  - src/swallow/orchestration/executor.py
  - tests/test_invariant_guards.py
  - tests/eval/test_wiki_compiler_quality.py
---

TL;DR: recommend-merge — 0 blockers / 1 concern / 2 nits. LTO-1 第一阶段 cleanly 落地 5 milestones,7 项 plan_audit findings(5 concerns + 2 nits)全部吸收;Wiki Compiler 是真 specialist(注册到 EXECUTOR_REGISTRY,Path C 走 Provider Router),不绕过任何 governance path。一个 concern 是 `WikiCompilerExecutor` compatibility wrapper 命名带来的 dual-class 困惑。

# LTO-1 PR Review

## Verdict

**recommend-merge** — 5 实现 commits(`178f9ee` M1 / `8e03ddd` M2+M3 / `c4fb52c` M4 / `5ca1e10` M5 / `8c7faba` state-sync)严格按 plan §Branch / Commit / Review Gates 拆分;无单 commit 跨 milestone 边界。

这 phase 真正落地了 v1.8.0 候选能力点:**首次 LLM-内知识编译能力进入本地 operator workflow**。Wiki Compiler 与 Librarian 上下游关系如设计文档所定;canonical write authority 边界 100% 保留;ADAPTER_DISCIPLINE 6 条规则在 M2-M4 Web 实现中 fully 套用。

Diff scale: **+3289 / -26** across 26 files。新增 4 个高价值文件(`surface_tools/wiki_compiler.py` 497 行 + `application/queries/knowledge.py` 584 行 + `application/commands/wiki.py` 174 行 + `tests/integration/cli/test_wiki_commands.py` 236 行);其余 22 文件多为受控扩展或测试。

## Verification of plan_audit Absorption

逐项核实 `plan_audit.md` 的 5 concerns + 2 nits:

### 5 concerns

| ID | Finding | Status | Evidence |
|---|---|---|---|
| C1 | `update_staged_candidate` 静默 strip 风险(slots dataclass 重建 path) | **Resolved** | `_internal_staged_knowledge.py:159-164` 显式列出 6 个新字段(`wiki_mode` / `target_object_id` / `source_pack` / `rationale` / `relation_metadata` / `conflict_flag`)在 candidate 重建中复制;`from_dict`(line 81-99)使用 `payload.get(..., default)` 模式保证旧记录加载;`tests/test_staged_knowledge.py` 加 72 行新测试覆盖。 |
| C2 | Promotion path 中 `relation_metadata` 归属层未定 | **Resolved by application-layer ownership** | `application/commands/knowledge.py:213` `relation_records = _create_promoted_relation_records(base_dir, updated)` —— 在 `apply_proposal` 完成 canonical mutation **之后**调用;line 272-293 `_create_promoted_relation_records` 是 application 层私有 helper。**Governance 层零修改**(`apply_proposal` / `_promote_canonical` 仍纯净)。这是合适的层归属 —— relation 创建是 application service 的协调动作,不是 canonical mutation 本身。 |
| C3 | `derived_from` 目标类型冲突(raw_material URI vs knowledge object id) | **Resolved by conservative scope** | `_create_promoted_relation_records` 只在 `relation_type == "refines"` 创建 persisted relation row(line 277-278)。`derived_from` / `supersedes` / `refers_to` / `contradicts` **只保留为 staged metadata**,不持久化为 relation rows。Closeout §Deferred Follow-Ups 明示:"Persisted relation rows for raw `derived_from` source refs unless backed by a future evidence/knowledge object id design." 这是 plan_audit C3 给的两个选项中的"option 1:`derived_from` 不直接指 raw_material"的保守落地。 |
| C4 | Relation enum 升级跨 M1/M3 依赖边界 | **Resolved by separating two layers** | `WIKI_COMPILER_METADATA_RELATION_TYPES` 定义在 `wiki_compiler.py:26-32`(5 个类型 staged metadata-only)。`KNOWLEDGE_RELATION_TYPES`(persisted relation enum)**不动**,仍保留 `("refines", "contradicts", "cites", "extends", "related_to")`。两个枚举层职责清晰:metadata 层是 staged 草稿语义,relation 表是 governed 持久关系。`test_knowledge_relation_metadata_types_cover_design_modes`(`tests/test_invariant_guards.py:471`)守住 metadata 层 5 类型完整;`_create_promoted_relation_records` 守住 relation 表只接 `refines`。 |
| C5 | `source_pack` schema 未锚定到 Evidence anchor 字段 | **Resolved by SourcePointer-compatible schema** | `wiki_compiler.py:38-59` `WikiCompilerSourceAnchor` dataclass 显式列出 16 个字段,关键 5 个 anchor 字段(`source_ref` / `content_hash` / `parser_version` / `span` / `heading_path`)+ `preview` 全部对齐 Evidence schema;closeout §Implementation Notes 明示"`source_pack` entries follow the plan's `SourcePointer.to_dict()`-compatible shape extended with `content_hash` / `parser_version` / `span` / `preview`"。`tests/eval/test_wiki_compiler_quality.py` 验证 `source pack present for every source` + 5 个 anchor 字段。 |

### 2 nits

| ID | Finding | Status |
|---|---|---|
| N1 | `--task-id` 强制要求与"知识起草不必绑 task"场景的摩擦 | **Acknowledged; intentional v1 scope** | Plan §Implementation Decisions #6 已明示"keep staged candidates and compiler artifacts anchored to an existing task truth object"; deferred follow-up 可在真实摩擦出现后加 implicit authoring task。CLI `--task-id` 在 `cli_commands/wiki.py` 是必填(line 检查),与 plan 一致。 |
| N2 | `refresh-evidence` `--parser-version` 强制 flag 在 parser 未升级场景制造重复 | **Resolved by stricter guard semantics** | M5 `test_wiki_compiler_refresh_evidence_updates_parser_version_anchor`(`tests/test_invariant_guards.py:415`)证明 `refresh_wiki_evidence_command` 必须更新 `parser_version` + `content_hash` + (`span` 或 `heading_path`)。这是强约束而非弱建议 —— 与 KNOWLEDGE.md §A "Unversioned Evidence Rebuild" 反模式一致。Operator 提供 `--parser-version` 作为 explicit acknowledgment,即便值未变也是显式动作,符合 P7/P8 的 explicit governance 原则。 |

**5 / 5 concerns + 2 / 2 nits 全部吸收**。

## Findings

### [CONCERN] C1 — `WikiCompilerExecutor` compatibility wrapper 命名带来 dual-class 困惑

**Files**:
- `src/swallow/surface_tools/wiki_compiler.py:218-225` `class WikiCompilerAgent`
- `src/swallow/surface_tools/wiki_compiler.py:492-493` `class WikiCompilerExecutor(WikiCompilerAgent)`

```python
class WikiCompilerExecutor(WikiCompilerAgent):
    """Compatibility wrapper that preserves executor semantics while delegating to WikiCompilerAgent."""
```

`WikiCompilerExecutor` 是空 subclass,docstring 说"compatibility wrapper",但本 phase 是 **Wiki Compiler 首次实现** —— 没有任何已存在 caller 需要兼容,subclass 没有任何 override。`orchestration/executor.py:273-276` `_lazy_wiki_compiler` 返回 `WikiCompilerExecutor()`,但 `WikiCompilerAgent` 自己已经实现了 `execute` / `execute_async` / `compile`。

**Why it matters**: 与项目其他 specialist 不一致(`Librarian` / `Ingestion` / `Literature` / `Meta-Optimizer` 都是单类,无 `xxxAgent` + `xxxExecutor` 双层)。未来贡献者读 `wiki_compiler.py` 会问:这两个类各自的角色是什么?docstring 说 "compatibility" 但没有要兼容的对象。

**Why it likely happened**:可能是设计阶段(M1 实现初期)考虑过 Agent / Executor 分层(Agent = 业务逻辑,Executor = ExecutorProtocol 适配),实现中合并了两个职责,但没回头删 wrapper。

**Resolution options**(任一可接受,无 blocker):

- **(a)** 删除 `WikiCompilerExecutor` 类,把 `EXECUTOR_REGISTRY` 注册改为 `WikiCompilerAgent` 直接;~5 行 cleanup。
- **(b)** 保留 `WikiCompilerExecutor` 但改名 `WikiCompilerExecutorAdapter` + 写明为什么需要分层(若设计意图是预留 ExecutorProtocol/Agent 解耦);~2 行 docstring。
- **(c)** Defer 到下一个 specialist phase 顺手处理。

**Recommendation**: option (a)。LTO-13 C1(`schemas.py` 直接 import `knowledge_retrieval`)与 LTO-6 C1(`render_*` / `build_*` 配对别名)都是同类 — "看起来无害但增加未来贡献者认知负担" — 现在删比未来删便宜。

### [NIT] N1 — `relation_records` 在 `StagePromoteCommandResult` 中暴露但下游可能不消费

**File**: `src/swallow/application/commands/knowledge.py:214`

```python
relation_records = _create_promoted_relation_records(base_dir, updated)
return StagePromoteCommandResult(candidate=updated, notices=notices, relation_records=relation_records)
```

`StagePromoteCommandResult` 加了 `relation_records: list[dict[str, object]]` 字段,但需要核实:
- CLI `swl knowledge review --promote` 是否展示这个新字段?
- HTTP `POST /api/knowledge/staged/{id}/promote` Pydantic envelope 是否包含?
- Web Knowledge panel 是否消费?

如果都不消费,字段是 dead surface;如果都消费,值得在 closeout 显式记录。

**Suggestion**:closeout §Implementation Notes 加一行说明 `relation_records` 的下游消费者(若有);未消费则记录为预留字段 + deferred 改进项。Defer cleanup 不影响 merge。

### [NIT] N2 — `WIKI_COMPILER_METADATA_RELATION_TYPES` 与 `KNOWLEDGE_RELATION_TYPES` 双枚举无显式 docstring 对照

**Files**:
- `src/swallow/surface_tools/wiki_compiler.py:26-32` `WIKI_COMPILER_METADATA_RELATION_TYPES = ("supersedes", "refines", "contradicts", "refers_to", "derived_from")`
- (somewhere in `_internal_knowledge_relations.py`) `KNOWLEDGE_RELATION_TYPES = ("refines", "contradicts", "cites", "extends", "related_to")`

两个枚举各有职责:metadata 层(staged 草稿语义)vs relation 表(governed 持久关系)。**核心区别**:
- 两者只在 `refines` / `contradicts` 重叠
- metadata 独有:`supersedes` / `refers_to` / `derived_from`(staged-only signals)
- relation 表独有:`cites` / `extends` / `related_to`(legacy persisted types)

**Suggestion**:`wiki_compiler.py:26` 加 docstring 注释清晰说明这是 staged metadata 层,与 `KNOWLEDGE_RELATION_TYPES`(persisted relation 层)不重合。否则未来 Wiki Compiler 第二阶段(添加 supersede 自动化时)会面临"为什么没在 KNOWLEDGE_RELATION_TYPES 里"的迷惑。

## Confirmed Strengths

记录这些以便未来 specialist phase 复用模式:

- **Specialist 注册模式与现有 4 个 specialist 完全一致**:`orchestration/executor.py:273-276` `_lazy_wiki_compiler` 是 `Callable[[], ExecutorProtocol]` lazy factory,EXECUTOR_REGISTRY 加 `"wiki-compiler"` key(line 288)。无新机制引入。
- **Path C 严格走 Provider Router**:`wiki_compiler.py:18` `from swallow.provider_router.agent_llm import call_agent_llm, extract_json_object`,line 269 `call_agent_llm(prompt, system=..., model=...)`。**零** `httpx` / 直接 provider client import。INVARIANTS §5 cardinal rule 保留。
- **`apply_proposal` ownership 不变**:`application/commands/knowledge.py:212` `apply_proposal(updated.candidate_id, OperatorToken(source="cli"), ProposalTarget.CANONICAL_KNOWLEDGE)` —— canonical write authority 完全保持原 governance path。M5 `test_wiki_compiler_agent_boundary_propose_only` 强制守住此边界。
- **`relation_metadata` normalization 防止 LLM 越权**:`wiki_compiler.py:454-489` `_normalize_relation_metadata` 显式过滤(a)未在 5 个允许类型中的 relation;(b)`draft` mode 中包含 `supersedes` / `refines` 的输入(line 470-471);(c)对 `refine` mode 强制注入 requested type。这避免 LLM 自作主张写 supersede signal,保持 P7/P8 边界。
- **Staged metadata 与 Web Browse 的解耦**:M2/M3 routes(`api.py:GET /api/knowledge/wiki|canonical|staged|{id}|{id}/relations`)只调用 `application.queries.knowledge`,zero `knowledge_retrieval._internal_*` import — 完全符合 ADAPTER_DISCIPLINE §2 #5。
- **`source_pack` SourcePointer-compatible schema**:`WikiCompilerSourceAnchor`(line 38-56)5 个 anchor 字段对齐 Evidence,为未来 promotion → evidence 转换路径预留正确接口。
- **Eval signal 是 deterministic / mocked,不是 live LLM**:`tests/eval/test_wiki_compiler_quality.py` 用 mocked LLM JSON responses,可重复;不是 quality 度量(literary)而是 structural 检查(source pack 完整 / rationale 引用 / mode 一致)。这是正确的 eval 形态 — 用 deselected marker 记录质量信号但不阻塞 merge。
- **Web Knowledge panel 只读,不暴露 LLM trigger**:遵循 plan §Non-Goals "不做 Web 侧 LLM 触发按钮"。M4 `index.html` 增加 444 行但 zero `fetch(... POST /api/knowledge ...)` 路径。

## Validation Replay

未重跑测试,closeout 记录:

```text
M5 eval: 4 passed
M5 invariant guards: 35 passed
Focused phase gates:
  - tests/integration/cli/test_wiki_commands.py + tests/test_specialist_agents.py + tests/test_executor_protocol.py: 48 passed
  - tests/integration/http/test_knowledge_browse_routes.py + tests/unit/application/test_knowledge_queries.py: 7 passed
  - tests/test_web_api.py + tests/integration/http/test_web_write_routes.py: 19 passed
Full pytest: 773 passed, 12 deselected
compileall: passed
git diff --check: passed
```

预期 +28 net new tests(773 - 745 of LTO-6) 与 diff stat 中 `tests/` 新增量一致(`tests/integration/cli/test_wiki_commands.py` 236 行 + `tests/eval/test_wiki_compiler_quality.py` 173 行 + `tests/integration/http/test_knowledge_browse_routes.py` 172 行 + `tests/unit/application/test_knowledge_queries.py` 200 行 + 多个 invariant guards / staged_knowledge / specialist_agents 增量)。

## Recommendation

**recommend-merge** as-is。C1 `WikiCompilerExecutor` cleanup 可:

1. **Folded into LTO-1 merge**(option a:5 行删除)如果 Codex 想保持单一干净记录。
2. **Deferred to a tiny follow-up commit on `main`**(我的偏好,与 LTO-13 C1 / LTO-6 C1 处理方式一致)—— 让 LTO-1 review chain 完整。
3. **Logged 到 concerns_backlog.md**(但这是 5 行 cleanup,不值得长期 backlog 占用)。

我的偏好是 (2)。

## Deferred Items Confirmed

closeout 列出的 deferred 全部一致:

- Web 侧 Wiki Compiler trigger 按钮 — plan §Non-Goals 明示
- Background runner / fire-and-poll for long-running LLM — LTO-13 R2-1 同样 deferred
- Project-level 全图谱可视化 — Wiki Compiler 视图 3 deferred,roadmap 已记
- 自动 promote / supersede / conflict resolution — P7/P8 cardinal 保护
- `target-id 驱动旧 wiki/canonical superseded status flip` for `supersedes` review signals — 第二阶段课题
- `derived_from` raw source refs persisted relation rows — 等 evidence/knowledge object id 设计扩展
- LTO-6 review C1 facade naming cleanup — 仍 deferred follow-up
- `current_state.md` + roadmap post-merge sync — 标准 post-merge 动作

所有 deferral 都在 closeout / plan / roadmap 中显式记录,无静默吸收。

## Tag 节点确认

LTO-1 merge 后 cut **v1.8.0** annotated tag(roadmap §四已记):标记**首次 LLM-内编译能力增量进入本地 operator workflow**,与 LTO-13 → v1.7.0 的"首次 LLM-外可观察写表面"形成姐妹节点。
