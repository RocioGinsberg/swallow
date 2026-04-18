---
author: claude
phase: 31
slice: runtime-v0
status: draft
depends_on: [docs/plans/phase31/kickoff.md, src/swallow/models.py, src/swallow/orchestrator.py, src/swallow/executor.py, src/swallow/router.py]
---

> **TL;DR**: 引入 `TaskCard` 数据模型和规则驱动的 `Planner`，将现有执行逻辑收敛到 `ExecutorProtocol` 统一接口，在 executor 产出后插入 `ReviewGate` Schema 校验。重构 `run_task()` 为 Planner→Executor→ReviewGate 三段式流程。

# Phase 31 Design Decision — Runtime v0

## 方案总述

Phase 31 的核心目标是将 `orchestrator.run_task()` 从"单体顺序执行函数"重构为"Planner→Executor→ReviewGate"三段式调度流程。

**为什么这么做**：当前 `run_task()` 长约 350 行，内联了路由选择、retrieval、execution、artifact 写入等全部逻辑。未来引入并发编排（Phase 33）和降级矩阵（Phase 34）时，如果没有统一接口，每新增一种 executor 都需要深入改动 `run_task()` 内部。Runtime v0 通过引入 TaskCard（标准化子任务描述）和 ExecutorProtocol（统一执行接口），为后续扩展建立稳定的扩展点。

**刻意不做什么**：
- 不引入 LLM 驱动的智能 Planner（v0 是规则驱动的 1:1 映射）
- 不改变现有 `select_route()` 的路由逻辑
- 不引入并发 TaskCard 执行
- 不引入 ReviewGate 的语义审查能力
- 不改变 `TaskState` 的持久化格式（保持向后兼容）

---

## Slice 拆解

### Slice 1: TaskCard 模型 + Planner v0

**目标**：定义 `TaskCard` dataclass，实现规则驱动的 `plan()` 函数。

**影响范围**：`models.py`（新增 dataclass）、新文件 `planner.py`

**设计细节**：

```python
# models.py 新增
@dataclass(slots=True)
class TaskCard:
    card_id: str                          # uuid hex[:12]
    goal: str                             # 从 TaskState.goal 继承
    input_context: dict[str, Any]         # retrieval hints, knowledge refs 等
    output_schema: dict[str, Any]         # 期望产出的 schema 描述（v0 为空 dict，表示无约束）
    route_hint: str                       # 建议的 route name（如 "local-codex"）
    executor_type: str                    # "cli" | "api" | "mock"（v0 只有 cli/mock）
    constraints: list[str]                # 从 TaskSemantics.constraints 继承
    parent_task_id: str                   # 关联的 TaskState.task_id
    status: str = "planned"               # planned → dispatched → completed → failed
    created_at: str = field(default_factory=utc_now)
```

```python
# planner.py
def plan(state: TaskState) -> list[TaskCard]:
    """v0 规则驱动：1 个 TaskState 生成 1 个 TaskCard（1:1 映射）。
    
    未来 Phase 33+ 将支持 1:N 拆解。
    """
    card = TaskCard(
        card_id=uuid4().hex[:12],
        goal=state.goal,
        input_context={
            "title": state.title,
            "workspace_root": state.workspace_root,
            "task_semantics": state.task_semantics,
        },
        output_schema={},  # v0: 无 schema 约束
        route_hint=state.route_name,
        executor_type=state.route_executor_family,
        constraints=list(state.task_semantics.get("constraints", [])),
        parent_task_id=state.task_id,
    )
    return [card]
```

**验收条件**：
- `TaskCard` dataclass 可实例化、序列化为 dict
- `plan()` 输入 TaskState，返回包含 1 个 TaskCard 的列表
- TaskCard 正确继承 TaskState 中的 goal、constraints、route_name
- 新增单元测试覆盖 plan() 和 TaskCard 序列化

**风险评级**：影响 1 / 可逆 1 / 依赖 1 = **3（低）**

---

### Slice 2: ExecutorProtocol + 现有 Executor 适配

**目标**：定义 `ExecutorProtocol`，将 `harness.run_execution()` 包装为 `LocalCLIExecutor`，`MockExecutor` 同步适配。

**影响范围**：`executor.py`（新增 Protocol + 实现类）、`harness.py`（被包装，不改动内部逻辑）

**设计细节**：

```python
# executor.py 新增

class ExecutorProtocol(Protocol):
    """统一执行器接口。所有 executor 实现此协议。"""
    
    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult: ...


class LocalCLIExecutor:
    """包装现有 harness.run_execution()，适配 ExecutorProtocol。"""
    
    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult:
        return run_execution(base_dir, state, retrieval_items)


class MockExecutor:
    """包装现有 mock 执行路径，适配 ExecutorProtocol。"""
    
    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult:
        return run_execution(base_dir, state, retrieval_items)
```

```python
# executor.py 新增
def resolve_executor(executor_type: str, executor_name: str) -> ExecutorProtocol:
    """根据 executor_type 和 name 返回对应的 executor 实例。"""
    if executor_name == "mock" or executor_name == "mock-remote":
        return MockExecutor()
    return LocalCLIExecutor()
```

**关键决策**：v0 阶段 `LocalCLIExecutor` 和 `MockExecutor` 的 `execute()` 内部都委托给现有 `run_execution()`。这是**有意为之**——保持行为完全不变，只建立接口抽象。当 Phase 33 引入真正不同的 executor（如 API executor）时，该接口才会体现价值。

**验收条件**：
- `ExecutorProtocol` 定义完成，支持 `isinstance` 式的 Protocol 检查
- `LocalCLIExecutor` 和 `MockExecutor` 实现 ExecutorProtocol
- `resolve_executor()` 能根据 name 返回正确的 executor
- 现有所有测试通过（行为无变化）

**风险评级**：影响 2 / 可逆 2 / 依赖 2 = **6（中）**

**风险说明**：
- `run_execution()` 当前直接读写 `state` 的多个字段（side effect 较重）。v0 不重构这些 side effect，只在外层套接口。这意味着 `card` 参数在 v0 中实际未被 `run_execution()` 消费——这是可接受的，因为 v0 目标是建立接口，不是改变执行语义。
- 未来 Phase 33 应将 `run_execution()` 的 state mutation 逐步收敛到 orchestrator 层，executor 只返回结果。

---

### Slice 3: ReviewGate + run_task() 流程重构

**目标**：引入 `ReviewGate`（executor 产出的 Schema 校验），重构 `run_task()` 为三段式流程。

**影响范围**：新文件 `review_gate.py`、`orchestrator.py`（重构 `run_task()` 内部流程）

**设计细节**：

```python
# review_gate.py

@dataclass(slots=True)
class ReviewGateResult:
    status: str            # "passed" | "failed"
    message: str
    checks: list[dict[str, Any]]   # 每项检查的详情

def review_executor_output(
    executor_result: ExecutorResult,
    card: TaskCard,
) -> ReviewGateResult:
    """v0 Review Gate：Schema 校验 + 基本通过性检查。"""
    checks: list[dict[str, Any]] = []
    
    # Check 1: executor 是否报告成功
    checks.append({
        "name": "executor_status",
        "passed": executor_result.status == "completed",
        "detail": f"executor reported status={executor_result.status}",
    })
    
    # Check 2: output 非空
    checks.append({
        "name": "output_non_empty",
        "passed": bool(executor_result.output.strip()),
        "detail": "executor output is non-empty" if executor_result.output.strip() else "executor output is empty",
    })
    
    # Check 3: 如果 card 有 output_schema，校验产出格式（v0 默认空 schema，总是通过）
    if card.output_schema:
        # 未来扩展点：jsonschema 验证
        checks.append({
            "name": "output_schema",
            "passed": True,
            "detail": "schema validation skipped in v0",
        })
    
    all_passed = all(check["passed"] for check in checks)
    return ReviewGateResult(
        status="passed" if all_passed else "failed",
        message="All review gate checks passed." if all_passed else "One or more review gate checks failed.",
        checks=checks,
    )
```

**run_task() 重构要点**：

在 `run_task()` 内部，execution 阶段改为：

```python
# 现有代码（概念性）：
# executor_result = run_execution(base_dir, state, retrieval_items)

# 重构后：
from .planner import plan
from .executor import resolve_executor
from .review_gate import review_executor_output

cards = plan(state)
card = cards[0]  # v0: 只有 1 个 card
append_event(base_dir, Event(
    task_id=task_id,
    event_type="task.planned",
    message="Task planned into task cards.",
    payload={"card_count": len(cards), "card_id": card.card_id},
))

executor = resolve_executor(card.executor_type, state.executor_name)
executor_result = executor.execute(base_dir, state, card, retrieval_items)

gate_result = review_executor_output(executor_result, card)
append_event(base_dir, Event(
    task_id=task_id,
    event_type="task.review_gate",
    message=gate_result.message,
    payload={"status": gate_result.status, "checks": gate_result.checks},
))
```

**关键约束**：
- `run_task()` 的外部行为（输入参数、返回类型、artifact 写入路径）完全不变
- ReviewGate 结果记入 event log，但 v0 **不阻断**已有的 completion 判断逻辑（即 gate failed 时记录 event，但不改变 status 计算）。这是为了保证回归安全。未来 Phase 可以将 gate_result.status 纳入 completion 判断。
- selective retry（`skip_to_phase`）逻辑保持不变，plan() 在每次 run 都会执行（因为 TaskCard 是轻量的）

**验收条件**：
- `ReviewGateResult` dataclass 可实例化、序列化
- `review_executor_output()` 对 completed executor 返回 passed，对 failed executor 返回 failed
- `run_task()` 内部调用 plan() → executor.execute() → review_executor_output()
- event log 中新增 `task.planned` 和 `task.review_gate` 事件
- 所有现有测试通过
- 新增测试覆盖 ReviewGate 和重构后的 run_task() 流程

**风险评级**：影响 2 / 可逆 2 / 依赖 2 = **6（中）**

**风险说明**：
- `run_task()` 是系统最核心的函数，重构必须保持所有现有行为不变。建议 Codex 先跑 `pytest` 建立 baseline，每个子步骤后再跑一次。
- ReviewGate v0 刻意不阻断 completion 判断，这是为了降低引入风险。如果直接让 gate 影响 status，所有依赖 `state.status == "completed"` 的下游逻辑都需要适配。

---

## 依赖说明

```
S1 (TaskCard + Planner) 
  → S2 (ExecutorProtocol)  [execute() 签名依赖 TaskCard]
    → S3 (ReviewGate + 串联)  [review 依赖 TaskCard 和 ExecutorResult，串联依赖 S1+S2]
```

严格串行。

---

## 文件变更预估

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/swallow/models.py` | 修改 | 新增 `TaskCard` dataclass |
| `src/swallow/planner.py` | 新增 | `plan()` 函数 |
| `src/swallow/executor.py` | 修改 | 新增 `ExecutorProtocol`、`LocalCLIExecutor`、`MockExecutor`、`resolve_executor()` |
| `src/swallow/review_gate.py` | 新增 | `ReviewGateResult`、`review_executor_output()` |
| `src/swallow/orchestrator.py` | 修改 | `run_task()` 内部重构为三段式 |
| `tests/test_planner.py` | 新增 | Planner 单元测试 |
| `tests/test_executor_protocol.py` | 新增 | ExecutorProtocol 测试 |
| `tests/test_review_gate.py` | 新增 | ReviewGate 测试 |
| `tests/test_cli.py` | 可能修改 | 如果 event 结构变化需要适配 |
