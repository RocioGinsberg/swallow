---
author: claude
phase: 62
slice: design_decision
status: revised-after-model-review
created_at: 2026-04-28
revised_at: 2026-04-28
depends_on:
  - docs/plans/phase62/kickoff.md
  - docs/plans/phase62/context_brief.md
  - docs/plans/phase62/design_audit.md
  - docs/plans/phase62/model_review.md
  - docs/design/ORCHESTRATION.md
  - docs/design/INVARIANTS.md
  - docs/design/KNOWLEDGE.md
  - docs/design/STATE_AND_TRUTH.md
  - docs/plans/phase61/closeout.md
---

## TL;DR

新增 `src/swallow/synthesis.py` 模块,实现 ORCHESTRATION §5 的多 participant + 仲裁 artifact-pointer 编排;`SynthesisConfig` 进 `models.py`;在 `governance.py` 新增 `_MpsPolicyProposal` 独立 dataclass + `register_mps_policy_proposal()` 适配器,经 `apply_proposal(target=POLICY)` 写入(沿用 Phase 61 governance boundary,**不重构** `_PolicyProposal`,但同步扩 `_validate_target` 接受新类型);新增 `paths.mps_policy_path(base_dir)` helper 集中持久化路径;CLI 层提供 `swl synthesis policy set --kind <kind> --value <n>` / `swl synthesis run` / `swl synthesis stage`,与既有 `swl audit policy set` 互不耦合。**MPS Path A 调用走 Provider Router**:participant / arbiter 调用前由 synthesis.py 经 `router.route_by_name`(参与者 `route_hint` 显式)或 `router.select_route`(无 hint 时由 Strategy Router 选择,触发 capability boundary guard)解析 `RouteSpec`,**为每次调用 clone task state** 后再下传 `run_http_executor`(规避 `_apply_route_spec_for_executor_fallback` 在 fallback 时 mutate 主 state),不写回主 task truth。仲裁 artifact 进入 staged 走 Operator/CLI 路径(`swl synthesis stage`);`stage` 命令对同 task 已有同 `source_object_id` pending candidate 默认拒绝重复提交。Phase 62 **不引入** `test_stagedk_write_only_from_specialist_or_cli` 守卫(orchestrator.py:3145 已有 librarian-side-effect 等价路径,登记 backlog Open)。本轮拆 3 milestone 5 slice,守卫测试共 13 条(M1: 4 / M2-S2: 4 / M2-S3: 3 + 1 加强既有 / M3-S4: 1 / M3-S5: 1)。

# Phase 62 Design Decision: Multi-Perspective Synthesis 实装(model-review 修订稿)

## 0. design_audit + model_review 处理结果

### 0.1 design_audit.md(第一轮)处理

design_audit.md 列出 3 BLOCKER + 9 CONCERN(全部已在 revised-after-audit 阶段处理):

| Audit 问题 | 严重度 | 本稿处理 |
|------------|--------|---------|
| Q1 `_PolicyProposal` 单字段 vs MPS 新 kind 结构性缺口 | BLOCKER | §A.2 决议:新增独立 `_MpsPolicyProposal` dataclass + `register_mps_policy_proposal` 适配器,**不**修改 `_PolicyProposal`;dispatch 在 `_apply_policy` 内按 isinstance 分支 |
| Q2 `swl audit policy set` 不是 kind-generic | BLOCKER | §A.3 决议:新增独立 `swl synthesis policy set --kind <kind> --value <n>` 子命令组,与 `swl audit policy set` 解耦 |
| Q3 participant hard cap 矛盾 | CONCERN | §A.4 决议:`mps_participant_limit` **无 hard max**(与 ORCHESTRATION §5.3 "Operator 自主决策" 对齐);`test_mps_participants_within_hard_cap` 改名为 `test_mps_participants_within_policy_cap`,语义改为"运行时参与者数量不得超过 policy 当前值",不是"governance 拒绝高 value" |
| Q4 policy seed 时机 | CONCERN | §A.5 决议:`run_synthesis` 启动前调 `load_mps_policy(kind)`,若不存在记录则使用 ORCHESTRATION §5.3 默认值(2 / 4)且**不写入** policy_records;Operator 可显式经 `swl synthesis policy set` 写入持久化值 |
| Q5 policy reader API | CONCERN | §A.5 决议:`governance.py` 新增 `load_mps_policy(base_dir, kind) -> int | None`,与 `_apply_policy` 的写路径成对 |
| Q6 orchestrator.py:3145 pre-existing stagedK 直写 | BLOCKER | §E.2 决议:**Phase 62 不引入** `test_stagedk_write_only_from_specialist_or_cli` 守卫,该守卫即便加上也会因既有路径 fail;在 `docs/concerns_backlog.md` 登记新 Open "orchestrator.py:3145 librarian-side-effect 等价 stagedK 写未走 governance",作为后续治理 phase 候选 |
| Q7 `StagedCandidate` 字段映射错误 | BLOCKER | §E.3 决议:严格对齐既有 schema(`text` / `source_kind` / `source_task_id` / `source_object_id` / `source_ref`),**不**新增 `origin_artifact_ids` 字段——仲裁 artifact id 写入 `source_object_id` |
| Q8 `swallow.workspace.resolve_path` / `swallow.identity.local_actor()` 不存在 | CONCERN | §四 修订:接合点改为现存 API(`paths.artifacts_dir(base_dir, task_id)` + 沿用 orchestrator.py 现有 actor 处理模式);**新登记 backlog**:INVARIANTS §7 中提及的两个集中化函数实际不存在,守卫测试可能 vacuous,后续 governance phase 评估 |
| Q9 re-run 拒绝机制 | CONCERN | §三 S3 决议:`run_synthesis` 启动前检查 `synthesis_arbitration.json` 是否已存在,存在则报错退出,Operator 需新建 task 重跑(本 phase 不实装 reset CLI) |
| event_type vs kind 字段名错误 | CONCERN | §三 S3/S4 修订:统一为 `event_type`,与既有代码对齐 |

### 0.2 model_review.md(第二轮 / Codex)处理

`docs/plans/phase62/model_review.md` (reviewer = `codex-second-review`, verdict = BLOCK) 在第一轮 audit 修订稿之上又发现 1 BLOCK + 7 CONCERN。本稿处理:

| Model-review 条目 | 严重度 | 本稿处理 |
|------------------|--------|----------|
| MPS Path A / Provider Router governance 未明确定义 | BLOCK | **§B.1 新增 "MPS Path A route resolution seam"**:participant `route_hint` 走 `router.route_by_name`,无 hint 走 `router.select_route`(Strategy Router 选择 + capability boundary guard);默认 HTTP route family 为 ROUTE_REGISTRY 中 `path = "A"` 标记的最高 quality_weight 路由(实施时取 `local-claude-code`)。每次 participant / arbiter 调用前 clone task state 应用 RouteSpec,然后下传 `run_http_executor`,**不写回主 task truth**。新增守卫 `test_synthesis_uses_provider_router` |
| `run_http_executor` fallback mutates `TaskState` | CONCERN | **§B.2 新增 "task state isolation"**:synthesis.py 在每次 Path A 调用前用 `dataclasses.replace(task_state, ...)` 或等价 deep copy 生成 transient state,fallback 路径只能影响 transient copy,不污染主 state。新增守卫 `test_synthesis_does_not_mutate_main_task_state` |
| `_validate_target` 仅接受 `_PolicyProposal` | CONCERN | **§A.2 修订**:新增 `_MpsPolicyProposal` 后必须**同步**扩 `_validate_target`(governance.py:217),让 `ProposalTarget.POLICY` 接受 `_PolicyProposal` 或 `_MpsPolicyProposal`;否则 `apply_proposal(target=POLICY)` 会在 dispatch 前抛 TypeError |
| `.swl/policy/mps_policy.json` 路径未集中 | CONCERN | **§A.6 修订**:在 `src/swallow/paths.py` 新增 `mps_policy_path(base_dir) -> Path` helper(类比既有 `audit_policy_path`),`mps_policy_store.py` 与守卫均经此 helper |
| design 文档间 stale wording / guard 总数不一致 | CONCERN | **§五 修订**:守卫总数从 6 调整到 8(新增 2 条 model-review 项 + 加强 1 条);**同步修订 kickoff.md**:guard 列表与 design_decision §五 对齐;`.swl/artifacts/<task_id>/` 全部改为 `paths.artifacts_dir(base_dir, task_id)`;`hard cap` → `policy cap` |
| `swl synthesis stage` idempotency 未指定 | CONCERN | **§E.4 新增**:`stage` 命令在构造 `StagedCandidate` 前,先 `load_staged_candidates(base_dir)` 检查同 task / 同 `source_object_id=config_id` 是否已有 status=`pending` 的 candidate;若存在则 reject(打印现有 candidate_id),不静默重复 submit。新增守卫 `test_synthesis_stage_rejects_duplicate` |
| MPS event 测试范围 | CONCERN | **§五 修订**:`test_mps_arbiter_artifact_required` 同时断言 event 写入(append-only / event_type 正确 / config_id + artifact_id payload 完整 / 不触发 status 推进);避免新增 `"local"` 字面量(沿用 orchestrator 既有 actor 处理) |
| 仲裁 artifact 文件存在 ≠ 内容有效 | CONCERN | **§五 修订**:`test_mps_arbiter_artifact_required` 加强为内容级断言(`schema == "synthesis_arbitration_v1"` / `config_id` 非空 / `arbiter_decision.synthesis_summary` 非空 / `participants[].round_artifacts` 长度 = `rounds_executed`)|

---

## 一、方案总述

把 ORCHESTRATION §5 的 MPS 设计落到代码,但不破坏现有 orchestrator 主链路与权限矩阵。落地路径:

1. MPS 编排隔离到独立模块 `src/swallow/synthesis.py`,不复用 `_debate_loop_core` / `_run_subtask_orchestration`(语义不同,避免拓扑混淆)
2. 通过现有 `run_http_executor` 调用 Path A,**不修改其签名**——participant role prompt 在 synthesis.py 里预拼接成完整 prompt 后,作为 `prompt` 参数传入(executor.py:1184-1192 已确认接受 `prompt: str | None`)
3. 成本上限走 Phase 61 落地的 `apply_proposal()` 入口,新增 `_MpsPolicyProposal` 独立 dataclass + `load_mps_policy` reader,不绕过 governance boundary 也**不**改既有 `_PolicyProposal`
4. 仲裁 artifact 进入 staged knowledge 走显式 CLI 触发(`swl synthesis stage`),字段映射严格对齐既有 `StagedCandidate` schema;不引入 Orchestrator 的 stagedK 写权限,不实装"自动 promotion"
5. orchestrator.py:3145 既有 stagedK 直写路径**不在本 phase 修复**,登记 backlog Open;本 phase 守卫只覆盖 synthesis.py 自身不写 stagedK

---

## 二、关键设计决策(audit 修订后)

### A. 配置 Schema 与 Policy 数据结构

#### A.1 `SynthesisConfig` schema 位置:`src/swallow/models.py` 新增 dataclass

(同原稿)在 `src/swallow/models.py` 新增 `SynthesisConfig` / `SynthesisParticipant` 两个 frozen dataclass:

```python
@dataclass(frozen=True)
class SynthesisParticipant:
    participant_id: str               # ULID, 单次 synthesis 内唯一
    role_prompt: str                  # 角色提示原文(synthesis.py 拼接,不进 truth)
    route_hint: str | None = None     # 可选

@dataclass(frozen=True)
class SynthesisConfig:
    config_id: str
    participants: tuple[SynthesisParticipant, ...]
    rounds: int                       # 1..mps_round_limit (hard max 3)
    arbiter: SynthesisParticipant
    arbiter_prompt_extra: str | None = None
```

#### A.2 Policy 数据结构:**新增** `_MpsPolicyProposal`,**不**修改既有 `_PolicyProposal`

**决策**:在 `governance.py` 新增独立 dataclass + adapter,与 `_PolicyProposal`(audit_trigger_policy)并排存在。

```python
# governance.py 新增
@dataclass(frozen=True)
class _MpsPolicyProposal:
    base_dir: Path
    kind: str            # "mps_round_limit" | "mps_participant_limit"
    value: int

def register_mps_policy_proposal(
    *,
    base_dir: Path,
    proposal_id: str,
    kind: str,
    value: int,
) -> str:
    """Register an MPS policy proposal payload for the next apply_proposal call.

    Constants enforced:
    - kind ∈ {"mps_round_limit", "mps_participant_limit"}
    - kind == "mps_round_limit" → value ∈ [1, 3] (ORCHESTRATION §5.3 hard max=3)
    - kind == "mps_participant_limit" → value ≥ 1 (no hard max; Operator自主决策)
    """
    normalized_id = proposal_id.strip()
    if not normalized_id:
        raise ValueError("proposal_id must be a non-empty string.")
    if kind not in {"mps_round_limit", "mps_participant_limit"}:
        raise ValueError(f"unknown MPS policy kind: {kind!r}")
    if value < 1:
        raise ValueError(f"{kind} value must be >= 1, got {value}")
    if kind == "mps_round_limit" and value > 3:
        raise ValueError(
            "mps_round_limit value must be <= 3 (ORCHESTRATION §5.3 hard max)"
        )
    _PENDING_PROPOSALS[(ProposalTarget.POLICY, normalized_id)] = _MpsPolicyProposal(
        base_dir=base_dir, kind=kind, value=value,
    )
    return normalized_id
```

`_apply_policy` dispatch 改为按 isinstance 分支:

```python
def _apply_policy(...):
    proposal = ...  # fetched from _PENDING_PROPOSALS
    if isinstance(proposal, _PolicyProposal):
        # 既有 audit_trigger_policy 路径,无任何改动
        ...
    elif isinstance(proposal, _MpsPolicyProposal):
        from .mps_policy_store import save_mps_policy   # 新建模块,见下文
        save_mps_policy(proposal.base_dir, proposal.kind, proposal.value)
    else:
        raise TypeError(f"Unknown POLICY proposal type: {type(proposal).__name__}")
```

**`_validate_target` 同步扩展(model_review BLOCK 必修项)**:`apply_proposal` 在 dispatch 前先调用 `_validate_target(proposal, target)`(governance.py:212-218),目前 `ProposalTarget.POLICY` 分支强 type-check `isinstance(proposal, _PolicyProposal)`,会让 `_MpsPolicyProposal` 直接被拒于 dispatch 之前。M1 实施必须**同步**修改:

```python
# governance.py:217 修订
if target == ProposalTarget.POLICY and not isinstance(
    proposal, (_PolicyProposal, _MpsPolicyProposal)
):
    raise TypeError("policy proposal payload is invalid.")
```

新增守卫 `test_apply_proposal_accepts_mps_policy_kind`:断言 `apply_proposal(target=POLICY)` 在 proposal_id 指向 `_MpsPolicyProposal` 时正常执行 dispatch(不抛 TypeError)。

**理由**:
1. 不动 `_PolicyProposal` schema,**零回归风险**于 Phase 61 audit_trigger_policy 路径(audit 已确认 R8 此处无回归)
2. 类型分支 isinstance 比 hash kind 字符串更安全,IDE / mypy 直接报错
3. 后续若再增 policy kind(如 retry_limit 等),沿用相同模式
4. `_validate_target` 必须与 `_apply_policy` 同步扩展,这是 model_review §"`_MpsPolicyProposal` path must update `_validate_target`" 的 CONCERN 直译

**否决**:
- 重构 `_PolicyProposal` 为 generic `(kind, value)` carrier——会让 `audit_trigger_policy` 的复杂结构(多字段 dataclass)被压成 JSON,增加序列化复杂度,且违反 Phase 61 的最小侵入原则

#### A.3 CLI 入口:**新增** `swl synthesis policy set` 子命令组,**不**改 `swl audit policy set`

**决策**:新增独立子命令组 `swl synthesis`,包含:
- `swl synthesis policy set --kind {mps_round_limit, mps_participant_limit} --value <n>`
- `swl synthesis run --task <task_id> --config <config_path>`
- `swl synthesis stage --task <task_id>`

**理由**:
1. `swl audit policy set`(cli.py:1241-1285)当前与 `AuditTriggerPolicy` 多字段强耦合,改造成 kind-generic 会侵入既有 CLI 行为
2. `swl synthesis` 作为子命令组本来就要为 run / stage 创建,policy 子命令并入此组,语义内聚
3. 守卫测试自然分组:`tests/test_cli.py::test_synthesis_policy_*` 与 `tests/test_cli.py::test_audit_policy_*` 互不耦合

#### A.4 `mps_participant_limit` 无 hard max(与 ORCHESTRATION §5.3 对齐)

**决策**:`mps_round_limit` 有 governance 层 hard max 3(`register_mps_policy_proposal` reject `value > 3`);`mps_participant_limit` **无** hard max,Operator 可经 `apply_proposal` 设到任意 ≥1 的值。

**守卫测试调整**:
- `test_mps_rounds_within_hard_cap`:测试 `register_mps_policy_proposal(kind="mps_round_limit", value=4)` 抛 `ValueError`(hard max 强制)
- `test_mps_participants_within_policy_cap`(改名):测试 `run_synthesis(config)` 在 `len(config.participants) > load_mps_policy("mps_participant_limit")` 时抛 `ValueError`(运行时 policy enforcement,非 governance 层硬拒)

**对齐文档**:risk_assessment.md §R1 "残余风险" 段已与此一致(line 37-38)。

#### A.5 Policy seed 时机 + Reader API

**决策**:不做 seed 注入。

```python
# governance.py 新增
def load_mps_policy(base_dir: Path, kind: str) -> int | None:
    """Read current MPS policy value, or None if no record exists.

    Caller decides default fallback (typically 2 for round_limit, 4 for participant_limit
    per ORCHESTRATION §5.3)."""
    from .mps_policy_store import read_mps_policy
    return read_mps_policy(base_dir, kind)

# synthesis.py 中
ROUND_DEFAULT = 2          # ORCHESTRATION §5.3
PARTICIPANT_DEFAULT = 4    # ORCHESTRATION §5.3

def _resolve_round_limit(base_dir: Path) -> int:
    return load_mps_policy(base_dir, "mps_round_limit") or ROUND_DEFAULT

def _resolve_participant_limit(base_dir: Path) -> int:
    return load_mps_policy(base_dir, "mps_participant_limit") or PARTICIPANT_DEFAULT
```

**理由**:
1. 不主动 seed 避免初次 CLI 调用就写持久化数据(零摩擦原则)
2. default 在 synthesis.py 里集中常量,守卫测试可静态扫描这两个常量保证与 ORCHESTRATION §5.3 对齐
3. Operator 显式 `swl synthesis policy set` 时才写持久化记录,符合 truth-first(默认值不进 truth)

#### A.6 `mps_policy_store.py` 新模块 + `paths.mps_policy_path` helper

新增 `src/swallow/mps_policy_store.py`,实现 `save_mps_policy(base_dir, kind, value)` / `read_mps_policy(base_dir, kind) -> int | None`,持久化文件由 **新增 helper** `paths.mps_policy_path(base_dir) -> Path` 解析(类比既有 `paths.audit_policy_path(base_dir)`,line 201),路径 `.swl/policy/mps_policy.json`(单文件 JSON,kind→value map)。

```python
# paths.py 新增
def mps_policy_path(base_dir: Path) -> Path:
    return base_dir / ".swl" / "policy" / "mps_policy.json"
```

`mps_policy_store.py` 内所有 IO 通过 `mps_policy_path(base_dir)`,**禁止**直接拼路径字符串。守卫测试 `test_mps_policy_writes_via_apply_proposal` 同时验证:
1. `save_mps_policy` 在 src 中只能由 `governance._apply_policy` 调用(私有 writer 聚合到 `test_only_apply_proposal_calls_private_writers`)
2. `mps_policy_path` 是写入路径的唯一来源(路径集中化,与 Phase 61 同模式)

`_apply_policy` 中的 `save_mps_policy` 调用是该模块**唯一的写入入口**。

### B. Path A 调用层(model-review BLOCK 修订)

#### B.1 MPS Path A route resolution seam

**问题**:`run_http_executor`(executor.py:1184)是低层 HTTP caller,从 `TaskState` 读取 `route_model_hint` / `route_dialect` / `route_taxonomy_role` / `route_taxonomy_memory_authority` 后构造 payload,**不**调用 `router.select_route`,**不**解释 `SynthesisParticipant.route_hint`,**不**应用 capability boundary guard。直接传 live `TaskState`(默认 `route_model_hint = "aider"` 即 Path B 的 local-aider)进 `run_http_executor`,会以错误 model hint 发出 HTTP payload,违反 INVARIANTS §4(Path A 必须经 Provider Router)。

**决策**:在 synthesis.py 中**显式做完整 route resolution**,不依赖 executor 层兜底。每次 participant / arbiter 调用前的解析顺序:

```python
# synthesis.py 伪代码
def _resolve_participant_route(
    participant: SynthesisParticipant,
    base_state: TaskState,
) -> RouteSpec:
    # 1. 显式 route_hint:走 router.route_by_name(精确匹配 + detached 后缀回退)
    if participant.route_hint:
        route = router.route_by_name(participant.route_hint)
        if route is None:
            raise ValueError(
                f"unknown route_hint {participant.route_hint!r} for participant "
                f"{participant.participant_id}"
            )
        # 已知路由必须仍 path == "A"(Path A 调用)
        if route.path != "A":
            raise ValueError(
                f"route {route.name} is path={route.path}; MPS participant requires Path A"
            )
        return route

    # 2. 无 hint:走 Strategy Router 选择,触发既有 capability boundary guard
    selection = router.select_route(base_state)
    if selection.route.path != "A":
        # base_state.executor 配置了 Path B/C 路由,但 MPS 必须走 Path A:
        # 取 ROUTE_REGISTRY 中 path="A" 默认路由
        return _MPS_DEFAULT_HTTP_ROUTE
    return selection.route
```

**默认 HTTP route 定义**(`_MPS_DEFAULT_HTTP_ROUTE`):

- 实施时取 `router.route_by_name("local-claude-code")`(EXECUTOR_REGISTRY 中已登记的标准 Path A HTTP route)
- 该常量在 synthesis.py 顶部定义,守卫测试 `test_mps_default_route_is_path_a` 验证常量名解析后 `route.path == "A"`
- 若未来 ROUTE_REGISTRY 改名或废弃 `local-claude-code`,守卫测试 fail 提示更新

**capability boundary guard 不绕过**:`select_route` 已有的 `unsupported_task_types` / executor capability profile 检查继续生效;`route_by_name` 路径不经过该 guard,因此 `route_hint` 是 Operator 手动指定的"信任路径"——这与 INVARIANTS §7.1 task-level `route_override_hint` 的设计精神一致(特权字段,Operator 自主决策,留 audit 痕迹)。本 phase 不做 `route_hint` 与 `unsupported_task_types` 的双重交叉校验,登记后续 phase 评估。

**新增守卫**:
- `test_synthesis_uses_provider_router`:AST 扫描 synthesis.py 必须 import `router.route_by_name` 和 `router.select_route`,且不得直接构造 `RouteSpec` 字面量(防止绕过路由层)
- `test_mps_default_route_is_path_a`:`_MPS_DEFAULT_HTTP_ROUTE` 解析后 `route.path == "A"`

#### B.2 Task state isolation per Path A call

**问题**:`run_http_executor` 内部 fallback 路径会调 `_apply_route_spec_for_executor_fallback(state, fallback_route, reason)`(executor.py:515-525, 722, 763),这个函数**直接 mutate** 传入的 `TaskState`(写 `route_taxonomy_role` / `route_taxonomy_memory_authority` / `route_model_hint`)。如果 `run_synthesis` 把同一 `task_state` 对象顺序传给多个 participant 调用,任意一次 fallback 会污染后续 participant 的 route 配置,且最终 task truth 也被改写。

**决策**:synthesis.py 在每次 Path A 调用前生成 transient state copy:

```python
# synthesis.py 伪代码
def _participant_state_for_call(
    base_state: TaskState,
    route: RouteSpec,
) -> TaskState:
    # 用 dataclasses.replace 生成浅拷贝,只替换路由字段
    return dataclasses.replace(
        base_state,
        executor_name=route.executor_name,
        route_mode=route.route_mode,
        route_dialect=route.dialect or base_state.route_dialect,
        route_model_hint=route.model_hint,
        route_taxonomy_role=route.taxonomy.system_role,
        route_taxonomy_memory_authority=route.taxonomy.memory_authority,
        route_is_fallback=False,
    )

# 然后下传:run_http_executor(transient_state, prompt=composed_prompt, ...)
```

**约束**:
1. `run_synthesis` / `run_synthesis_round` / 仲裁调用**禁止**把 base_state 直接下传 `run_http_executor`,必须先经 `_participant_state_for_call` 生成 transient
2. 任何 fallback mutation 仅作用于 transient,不写回 base_state,也**不**经 `save_state` 持久化 transient
3. event_log 写入(`task.mps_completed` 等)仍用 base_state.task_id,`actor` 字段沿用 orchestrator 既有处理(不引入新 `"local"` 字面量)

**新增守卫**:
- `test_synthesis_does_not_mutate_main_task_state`:e2e 测试验证 `run_synthesis` 调用前后 `base_state` 的 route 字段未变,`save_state` 调用次数与 baseline 相同
- `test_synthesis_clones_state_per_call`:AST 扫描 synthesis.py,所有 `run_http_executor` 调用之前必须有 `dataclasses.replace` 或 `_participant_state_for_call` 调用

### C. role prompt 注入机制:在 synthesis.py 内预拼接,通过现有 prompt 字段传入

(audit 已确认,model-review 未异议)participant role prompt 由 synthesis.py 在每次 Path A 调用前拼接,生成完整 prompt string,通过 `run_http_executor(..., prompt=composed)` 传入。executor.py:1184-1192 接受 `prompt: str | None`,签名无需修改。

拼接顺序:

```
final_prompt = (
    role_prompt(participant)
    + "\n\n---\n\n"
    + task_semantics_prompt
    + "\n\n## Prior round artifacts\n"
    + load_artifacts_as_text(prior_round_artifacts)
)
```

`compose_participant_prompt(participant, task_semantics, prior_artifacts) -> str` 必须 pure function,无副作用。守卫 `test_mps_no_chat_message_passing` 通过 AST 静态扫描禁止 synthesis.py 调用 messages-list-style API。

### D. MPS 触发入口:仅 CLI(`swl synthesis run`),task semantics 不引入 synthesis 字段

(原稿不变)Phase 62 仅暴露 CLI 入口 `swl synthesis run --task <task_id> --config <config_path>`。`TaskSemantics` 不引入 `synthesis_config` 字段,避免 Planner 自动路由。

### E. Staged-Knowledge 写入路径(audit + model-review 修订)

#### E.1 走 Operator/CLI 路径(与原稿一致)

仲裁 artifact 进入 staged knowledge 通过 CLI 子命令 `swl synthesis stage --task <task_id>` 显式触发,走 Operator(via CLI)的 stagedK W 权限。

#### E.2 既有 orchestrator.py:3145 stagedK 直写路径(audit BLOCKER 处理)

**事实**:orchestrator.py:3145 既有 `submit_staged_candidate(base_dir, StagedCandidate(...))` 调用,处理 Librarian agent 在任务执行中产生的 verified knowledge → staged candidate 转换(librarian-side-effect 等价语义)。

**Phase 62 决议**:
- **不引入** `test_stagedk_write_only_from_specialist_or_cli` 守卫(原 risk_assessment §R5 line 101 提及,本稿移除)。该守卫即便加上也会因既有路径 fail
- **不修改** orchestrator.py:3145 既有调用——它在本 phase scope 之外,与 MPS 编排功能不耦合
- **新增 backlog Open**:"orchestrator.py:3145 librarian-side-effect 等价 stagedK 写入未经 governance",作为后续治理 phase 候选,与 Phase 61 三项 backlog 同等优先级
- **本 phase 守卫只覆盖 synthesis.py 不写 stagedK**:新增 `test_synthesis_module_does_not_call_submit_staged_candidate`,AST 扫描 `src/swallow/synthesis.py` 禁止 `submit_staged_candidate` import 或调用

**理由**:
1. 修复既有 librarian-side-effect 路径需要扩 OperatorToken.source enum(类比 Phase 61 决策),涉及 SELF_EVOLUTION 文档更新,超出 candidate E scope
2. Phase 62 守卫保护新增模块自身,既有问题不在本 phase 隐藏(显式登记 backlog 是诚实选择)

#### E.3 `StagedCandidate` 字段映射(audit BLOCKER 处理)

**事实**:`StagedCandidate`(staged_knowledge.py:15-32)实际字段为 `text` / `source_task_id` / `source_kind` / `source_ref` / `source_object_id` 等。原 design_decision §S4 line 246 使用的 `content=` / `source=` / `origin_artifact_ids=[]` 字段名错误,且 `source_task_id` 是必填字段。

**Phase 62 修订**:

```python
# cli.py 中 swl synthesis stage 实现
arbitration_path = paths.artifacts_dir(base_dir, task_id) / "synthesis_arbitration.json"
arbitration_data = json.loads(arbitration_path.read_text(encoding="utf-8"))
candidate = StagedCandidate(
    candidate_id="",  # auto-generated as "staged-<hex8>"
    text=arbitration_data["arbiter_decision"]["synthesis_summary"],
    source_task_id=task_id,
    topic="",  # 可选,从 arbitration_data 读取若有
    source_kind="synthesis",
    source_ref=str(arbitration_path.relative_to(base_dir)),
    source_object_id=arbitration_data.get("config_id", ""),
    submitted_by="cli",
    taxonomy_role="",
    taxonomy_memory_authority="",
)
submit_staged_candidate(base_dir, candidate)
```

字段映射表:

| design 意图 | 实际字段 | 内容 |
|------------|---------|------|
| 候选文本 | `text` | `arbiter_decision.synthesis_summary` |
| 来源任务 | `source_task_id` | task_id |
| 来源类型 | `source_kind` | `"synthesis"` |
| 来源引用 | `source_ref` | 仲裁 artifact 相对路径 |
| 关联对象 ID | `source_object_id` | `config_id`(`SynthesisConfig.config_id`) |
| 提交者 | `submitted_by` | `"cli"` |

**不新增** `origin_artifact_ids` 字段——`source_object_id` 携带 `config_id`,从 config 可反查所有 round artifacts;若需多 ID 列表,后续 phase 评估扩展 schema。

#### E.4 `swl synthesis stage` idempotency(model-review CONCERN 处理)

**问题**:Operator 重复执行 `swl synthesis stage --task <id>` 会向 `staged_knowledge_registry_path` 重复 append 同 `source_object_id` 的 candidate(`submit_staged_candidate` 内部仅 append-only,不去重),污染 staged 池。

**决策**:`swl synthesis stage` 在构造新 `StagedCandidate` 前,先调 `staged_knowledge.load_staged_candidates(base_dir)`,若已存在 `source_task_id == task_id` AND `source_object_id == config_id` AND `status == "pending"` 的 candidate,则**拒绝重复提交**,打印现有 `candidate_id` 与 `submitted_at`,exit code 非零。

**理由**:
1. staged candidate 的"重复提交"在语义上是错误——同一仲裁 artifact 应只产生一个待审 candidate
2. 已 promoted / rejected 状态(非 pending)的同 source_object_id 候选不阻断 stage——Operator 可能希望基于同一仲裁产物再触发新 candidate(虽然字段相同)。这种边界情况**不在本 phase 处理**,默认所有非 pending 状态都视为"已离开 staged 工作集",新 candidate 允许提交并打印 warning
3. 实现是 CLI 层的薄检查,不修改 `staged_knowledge.py` 任何函数,不引入新字段

**新增守卫** `test_synthesis_stage_rejects_duplicate`:end-to-end 测试,先 `swl synthesis stage` 一次成功,再次执行同 task 应 exit 非零并打印 candidate_id。

### F. 仲裁 artifact 物理格式(原稿,字段无变化)

仲裁 artifact 落 `paths.artifacts_dir(base_dir, task_id) / "synthesis_arbitration.json"`(具体为 `.swl/tasks/<task_id>/artifacts/synthesis_arbitration.json`)。

JSON schema:

```json
{
  "schema": "synthesis_arbitration_v1",
  "config_id": "<ULID>",
  "task_id": "<ULID>",
  "rounds_executed": 2,
  "participants": [
    {
      "participant_id": "<ULID>",
      "role_prompt_hash": "<sha256>",
      "round_artifacts": [
        {"round": 1, "artifact_id": "<ULID>", "path": "synthesis_round_1_participant_<id>.json"},
        {"round": 2, "artifact_id": "<ULID>", "path": "synthesis_round_2_participant_<id>.json"}
      ]
    }
  ],
  "arbiter": {
    "participant_id": "<ULID>",
    "role_prompt_hash": "<sha256>"
  },
  "arbiter_decision": {
    "selected_artifact_refs": ["<artifact_id>", ...],
    "synthesis_summary": "<text, non-empty>",
    "rationale": "<text>"
  },
  "raw_arbiter_output": "<full LLM output text>",
  "completed_at": "<ISO8601 UTC>"
}
```

participant 每轮 artifact 命名:`synthesis_round_{n}_participant_{participant_id}.json`,落同一 artifacts 目录。

### G. MPS 与 Review Gate 对接

(原稿不变)MPS 不引入专属 verdict,仲裁 artifact 完成后走现有 Validator → Review Gate 路径。

---

## 三、Slice 拆解(3 milestone × 5 slice,model-review 修订)

### M1: 配置与策略基线(S1)

**S1 - SynthesisConfig + MPS Policy Plumbing**
- 在 `src/swallow/models.py` 新增 `SynthesisConfig` / `SynthesisParticipant` dataclass
- 在 `src/swallow/paths.py` 新增 `mps_policy_path(base_dir) -> Path` helper(§A.6)
- 在 `src/swallow/governance.py` 新增 `_MpsPolicyProposal` dataclass + `register_mps_policy_proposal()` adapter + `load_mps_policy()` reader(§A.2 / §A.5);**同步扩** `_validate_target` 接受 `_MpsPolicyProposal`(§A.2 model-review BLOCK 必修项);`_apply_policy` 内 isinstance 分支扩展(§A.2)
- 新增 `src/swallow/mps_policy_store.py`:`save_mps_policy(base_dir, kind, value)` / `read_mps_policy(base_dir, kind) -> int | None`,持久化路径经 `paths.mps_policy_path(base_dir)`
- 新增 CLI:`swl synthesis policy set --kind <kind> --value <n>`(cli.py 新增 `swl synthesis` 子命令组,本 slice 仅实现 policy 子命令,run/stage 留 M2/M3)
- **守卫测试**(本 slice 落地 4 条):
  - `test_mps_rounds_within_hard_cap`(governance 拒绝 `mps_round_limit` value>3)
  - `test_mps_participants_within_policy_cap`(运行时 enforcement;**S3 落地完整 e2e**,本 slice 写好 stub 框架)
  - `test_mps_policy_writes_via_apply_proposal`(`save_mps_policy` 在 src 中只能由 `_apply_policy` 调用;聚合到既有 `test_only_apply_proposal_calls_private_writers`;同时验证 `mps_policy_path` 是写入路径唯一来源)
  - `test_apply_proposal_accepts_mps_policy_kind`(model-review 新增:验证 `_validate_target` 已扩展)
- **验证**:`pytest tests/test_governance.py tests/test_invariant_guards.py tests/test_cli.py -k "mps_"` 全 pass

**M1 commit 方案**:单 commit 包含 schema + paths helper + governance + policy_store + CLI + 4 测试。

### M2: MPS 编排核心(S2 + S3)

**S2 - 单轮 participant 循环 + Path A route resolution + state isolation + artifact 持久化**
- 新增 `src/swallow/synthesis.py`,核心函数:
  - `_MPS_DEFAULT_HTTP_ROUTE = router.route_by_name("local-claude-code")`(§B.1)
  - `_resolve_participant_route(participant, base_state) -> RouteSpec`(§B.1:hint→`route_by_name`,无 hint→`select_route`,fallback→`_MPS_DEFAULT_HTTP_ROUTE`,强 `route.path == "A"` 校验)
  - `_participant_state_for_call(base_state, route) -> TaskState`(§B.2:`dataclasses.replace` 生成 transient state)
  - `compose_participant_prompt(participant, task_semantics, prior_artifacts) -> str`(§C,pure function)
  - `run_synthesis_round(config, round_n, prior_artifacts, base_dir, base_state) -> list[ParticipantArtifact]`(顺序遍历 participants,**先解析路由再 clone state**,调 `run_http_executor(transient_state, prompt=composed)`,持久化产出)
  - `persist_participant_artifact(base_dir, task_id, round_n, participant_id, llm_output) -> str`(返回 artifact_id,路径经 `paths.artifacts_dir(base_dir, task_id)`)
- **守卫测试落地**(3 条):
  - `test_mps_no_chat_message_passing`(AST 扫描 synthesis.py 禁止 messages-list-style 接口)
  - `test_synthesis_uses_provider_router`(model-review BLOCK 新增:AST 扫描 synthesis.py 必须 import `router.route_by_name` 与 `router.select_route`,且不直接构造 RouteSpec 字面量)
  - `test_mps_default_route_is_path_a`(model-review BLOCK 新增:`_MPS_DEFAULT_HTTP_ROUTE` 解析后 `route.path == "A"`)
  - `test_synthesis_clones_state_per_call`(model-review CONCERN 新增:AST 扫描,所有 `run_http_executor` 调用之前必须有 `dataclasses.replace` 或 `_participant_state_for_call` 调用)

**S3 - 多轮 + 仲裁 + run_synthesis 入口**
- `run_synthesis(base_dir, base_state, config) -> ArbitrationResult`:
  - 启动前查询 `_resolve_round_limit(base_dir)` / `_resolve_participant_limit(base_dir)`,validate `config.rounds` / `len(config.participants)`,超过则抛 `ValueError`(运行时 enforcement)
  - **re-run 拒绝**:检查 `paths.artifacts_dir(base_dir, task_id) / "synthesis_arbitration.json"` 是否已存在,存在则抛 `RuntimeError("synthesis already completed for task; re-run requires new task")`
  - 顺序执行 N 轮 participant fan-out(每轮经 §B.1 路由解析 + §B.2 state clone)
  - 仲裁阶段:仲裁者也经 §B.1/§B.2 处理;加载所有 round artifacts,调 Path A 仲裁,产出 `synthesis_arbitration.json`(§F schema)
  - Orchestrator 在 event_log 写 `event_type = "task.mps_completed"`,payload 含 `config_id` / `arbitration_artifact_id` / `rounds_executed`
- 新增 CLI:`swl synthesis run --task <task_id> --config <config_path>` 解析 config JSON,调 `run_synthesis`
- **守卫测试落地**(3 条):
  - `test_mps_arbiter_artifact_required`(end-to-end + 内容级断言:`schema == "synthesis_arbitration_v1"` / `config_id` 非空 / `arbiter_decision.synthesis_summary` 非空 / `participants[].round_artifacts` 长度 = `rounds_executed`;同时验证 event 写入正确,不触发 status 推进)
  - `test_mps_participants_within_policy_cap`(完整 e2e,S1 stub 升级)
  - `test_synthesis_run_rejects_if_arbitration_exists`(re-run 守卫,audit Q9 新增)
  - `test_synthesis_does_not_mutate_main_task_state`(model-review CONCERN 新增:e2e 验证 `run_synthesis` 调用前后 `base_state` route 字段未变,`save_state` 调用次数不增加)

**M2 commit 方案**:S2 与 S3 在 milestone 内两次 commit,允许独立 review。

### M3: Staged 集成 + 守卫完整化(S4 + S5)

**S4 - Staged-knowledge CLI 桥接(含 idempotency 检查)**
- 新增 CLI:`swl synthesis stage --task <task_id>`
  - 读取 `paths.artifacts_dir(base_dir, task_id) / "synthesis_arbitration.json"`(若不存在则报错)
  - **idempotency 检查**(§E.4):`load_staged_candidates(base_dir)` 后查 `source_task_id == task_id AND source_object_id == config_id AND status == "pending"`;存在则 reject 退出
  - 构造 `StagedCandidate` 严格按 §E.3 字段映射
  - 调 `staged_knowledge.submit_staged_candidate(base_dir, candidate)`(走 Operator/CLI 路径)
  - 在 task event_log 写 `event_type = "task.synthesis_staged"`
- **不**新增 `StagedCandidate` schema 字段(§E.3)
- **守卫测试落地**(1 条):
  - `test_synthesis_stage_rejects_duplicate`(model-review CONCERN 新增:e2e 重复 stage 应 exit 非零)

**S5 - 守卫测试完整化 + 文档同步**
- 落地剩余守卫:
  - `test_synthesis_module_does_not_call_submit_staged_candidate`(§E.2;AST 扫描 synthesis.py 不 import / 不调用 `submit_staged_candidate`)
- 在 `docs/concerns_backlog.md` 登记两条 Phase 62 audit 暴露的 Open(已在本稿前置 commit 中添加,本 slice 仅核对状态):
  - "orchestrator.py:3145 librarian-side-effect 等价 stagedK 写入未经 governance"
  - "INVARIANTS §7 提及的 `swallow.workspace.resolve_path` / `swallow.identity.local_actor()` 集中化函数实际不存在,§9 守卫 `test_no_hardcoded_local_actor_outside_identity_module` / `test_no_absolute_path_in_truth_writes` 行为需复核"
- 同步 `docs/design/ORCHESTRATION.md` §5 注脚:**不**写实施细节(沿用 Phase 61 教训)
- 出具 `docs/plans/phase62/closeout.md`

**M3 commit 方案**:S4 一次 commit(CLI + idempotency 测试),S5 一次 commit(守卫 + 文档)。

---

## 四、与现有代码的接合点(audit + model-review 修订)

| 接合点 | 既有代码 | 本 phase 接入方式 |
|--------|----------|------------------|
| Path A 调用 | `executor.py:1184 run_http_executor`(`prompt: str | None = None` 参数) | synthesis.py 调用,**不修改签名**,prompt 预拼接;调用前先经 §B.1 路由解析 + §B.2 state clone |
| 路由解析 | `router.py:769 route_by_name` / `router.py:822 select_route` | synthesis.py 显式 import 调用,**不**绕过 Provider Router |
| Fallback mutation 隔离 | `executor.py:515 _apply_route_spec_for_executor_fallback` | synthesis.py 用 `dataclasses.replace` 隔离 base_state,fallback 仅作用 transient |
| Policy 写入 | `governance.py:553 _apply_policy`(isinstance 分支扩展) / `governance.py:174 apply_proposal` / `governance.py:212 _validate_target`(扩) | 新增 `_MpsPolicyProposal` 分支,沿用 `_PolicyProposal` 不动,`_validate_target` POLICY 分支接受两种类型 |
| Policy 读取 | **新增** `governance.load_mps_policy` + `mps_policy_store.read_mps_policy` | 仅 synthesis.py 调用 |
| Policy 持久化路径 | **新增** `paths.mps_policy_path(base_dir)` helper(类比 `paths.audit_policy_path`,line 201) | `mps_policy_store.py` 唯一 IO 入口 |
| Artifact 持久化 | `paths.artifacts_dir(base_dir, task_id)` → `.swl/tasks/<task_id>/artifacts/` | participant artifacts + 仲裁 artifact 落同一目录 |
| Staged candidate | `staged_knowledge.py:106 submit_staged_candidate(base_dir, candidate)` / `:92 load_staged_candidates(base_dir)` | CLI 路径调用,严格字段映射(§E.3),idempotency 经 `load_staged_candidates` 检查(§E.4)|
| Event log | `store.append_event(base_dir, Event(task_id=..., event_type=...))` | 新增两类 event:`task.mps_completed` / `task.synthesis_staged` |
| Path 解析 | **沿用** `paths.artifacts_dir`(orchestrator.py 模式),**不**引用虚构的 `swallow.workspace.resolve_path` | synthesis.py 直接调用 paths 模块 |
| Actor identity | **沿用** orchestrator.py 现有 actor 处理(具体值在 implementation 阶段对照既有 event 写入决定),**不**引用虚构的 `swallow.identity.local_actor()`,**不**新增 `"local"` 字面量 | event 字段沿用 orchestrator 现状 |
| Subtask Orchestrator | `subtask_orchestrator.py SubtaskOrchestrator` | **不复用,不替换** |
| `_debate_loop_core` | `orchestrator.py:1064-1252` | **完全独立**,代码无重叠 |

---

## 五、新增守卫测试清单(model-review 修订后,共 13 条)

| 守卫 | 验证 | 落地 slice |
|------|------|-----------|
| `test_mps_rounds_within_hard_cap` | governance 层拒绝 `mps_round_limit` value>3 | S1 |
| `test_mps_participants_within_policy_cap` | 运行时 enforcement,`run_synthesis` 在超 policy cap 时抛错 | S1(stub)→ S3(完整 e2e) |
| `test_mps_policy_writes_via_apply_proposal` | 聚合到 `test_only_apply_proposal_calls_private_writers`;`save_mps_policy` 在 src 中只能由 `_apply_policy` 调用;`mps_policy_path` 是写入路径唯一来源 | S1 |
| `test_apply_proposal_accepts_mps_policy_kind` | model-review CONCERN:`_validate_target` 已扩展接受 `_MpsPolicyProposal`,`apply_proposal(target=POLICY)` 不抛 TypeError | S1 |
| `test_mps_no_chat_message_passing` | AST 扫描 synthesis.py 禁用 messages-list-style 接口 | S2 |
| `test_synthesis_uses_provider_router` | model-review BLOCK:AST 扫描 synthesis.py 必须 import `router.route_by_name` / `router.select_route`,不直接构造 RouteSpec | S2 |
| `test_mps_default_route_is_path_a` | model-review BLOCK:`_MPS_DEFAULT_HTTP_ROUTE` 解析后 `route.path == "A"` | S2 |
| `test_synthesis_clones_state_per_call` | model-review CONCERN:AST 扫描,`run_http_executor` 调用前必须有 state clone | S2 |
| `test_mps_arbiter_artifact_required` | end-to-end + 内容级断言(schema/config_id/synthesis_summary 非空/round_artifacts 长度 = rounds_executed)+ event 写入正确不推进 status | S3 |
| `test_synthesis_run_rejects_if_arbitration_exists` | re-run 守卫:同 task 第二次 `run_synthesis` 抛错 | S3 |
| `test_synthesis_does_not_mutate_main_task_state` | model-review CONCERN:e2e 验证 `base_state` route 字段未被改写,`save_state` 调用计数不增 | S3 |
| `test_synthesis_stage_rejects_duplicate` | model-review CONCERN:重复 `swl synthesis stage` exit 非零 | S4 |
| `test_synthesis_module_does_not_call_submit_staged_candidate` | AST 扫描:synthesis.py 不写 stagedK | S5 |

注:总数 13 条(以上表格 13 行)。其中 model-review 新增 6 条(BLOCK 2 条 + CONCERN 4 条),其余沿用 audit 修订稿。

**移除**(audit Q6):`test_stagedk_write_only_from_specialist_or_cli`(原 risk_assessment §R5 line 101)— 本 phase 不引入,登记 backlog Open

**对现有 17 条 §9 守卫的影响**:零弱化,零删除,新增 13 条只增不减(Phase 61 阶段 §9 总量是 17 条,本 phase 新增让总量增至 30 条)。

---

## 六、与 Phase 61 governance 的交互边界

Phase 62 严格遵守 Phase 61 落地的 `apply_proposal()` 唯一入口:

1. `mps_round_limit` / `mps_participant_limit` 写入只能经 `register_mps_policy_proposal()` → `apply_proposal(target=POLICY)`
2. 不绕过 governance.py,不直接写 `mps_policy.json` 文件
3. CLI `swl synthesis policy set` 内部走 governance 路径,与既有 `swl audit policy set` 解耦
4. `test_only_apply_proposal_calls_private_writers` 守卫扩展:加入 `save_mps_policy` 到 protected writer 列表
5. 仲裁 artifact 进入 canonical knowledge **本 phase 不实装**

---

## 七、Out-of-scope / 留给后续 phase

(原稿不变)

- **synthesis 跨 session 状态恢复 / reset**:登记 backlog Open
- **Planner 自动路由到 MPS**:候选 D 范围
- **synthesis 仲裁后自动进入 canonical**:违反 INVARIANTS §8,永久非目标
- **`LogicalCallRequest` / `PhysicalCallPlan` 抽象层**:超出 candidate E 边界
- **Phase 61 三项遗留 backlog**:§9 剩余 14 条守卫 / Repository 抽象层 / apply_proposal 事务性回滚
- **orchestrator.py:3145 librarian-side-effect 等价 stagedK 写**:audit 暴露,登记 backlog,后续治理 phase 处理
- **INVARIANTS §7 集中化函数实际缺失**:audit 暴露,登记 backlog
