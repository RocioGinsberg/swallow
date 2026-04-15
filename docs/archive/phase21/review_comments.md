---
author: claude
phase: 21
slice: dispatch-policy-gate-and-mock-topology-visibility
status: draft
depends_on:
  - docs/plans/phase21/design_decision.md
  - docs/plans/phase21/risk_assessment.md
---

**TL;DR**: 三个 slice 全部实现且通过测试（146 passed）。整体 PASS，可合并。一个 CONCERN 关于 acknowledge 硬编码 route_mode="summary"，不阻塞本轮。

# Review Comments: Phase 21

## 测试结果

```
146 passed, 5 subtests passed in 5.55s
```

全部通过，无 failure。

---

## Slice 1: Dispatch Policy — 语义校验层

### [PASS] dispatch_policy.py 模块设计
- 独立模块，职责单一：校验 context_pointers 指向的 artifact 是否存在
- `PolicyResult` dataclass 干净，`validate_handoff_semantics()` 逻辑清晰
- `_candidate_pointer_paths()` 支持相对路径（task_dir + artifacts 子目录）和绝对路径两种查找策略，覆盖合理

### [PASS] orchestrator 集成
- 仅对 `remote_candidate=True` 的 contract 执行语义校验，不影响 local 路径
- 校验失败直接生成 blocked verdict，与 Phase 20 已有的 blocked 处理路径复用
- 不改变 `evaluate_dispatch_verdict()` 原有逻辑，只在其前方增加一道过滤

### [PASS] 测试覆盖
- `test_dispatch_policy.py` 覆盖了：有效指针 pass、无效指针 blocked、空指针 pass、端到端 orchestrator 拦截
- 端到端测试通过注入 `artifact_paths["task_semantics_json"] = "missing-artifact.md"` 触发 remote_candidate → 语义校验失败 → blocked，验证链路完整

---

## Slice 2: CLI acknowledge 命令

### [PASS] acknowledge_task() 实现
- 状态前置校验正确：非 dispatch_blocked 任务 raise ValueError
- 状态转换设计合理：`dispatch_blocked → running (phase=retrieval, dispatch_status=acknowledged)`
- 完整重新选择 local route（通过 `select_route()`），不残留 mock-remote 路由信息
- event payload 记录了 previous_status / previous_phase，便于审计

### [PASS] CLI 集成
- `swl task acknowledge <task_id>` 命令注册正确
- 成功时输出 `dispatch_acknowledged` + 状态摘要
- 失败时输出 `acknowledge_blocked` + 当前状态 + 原因，返回 exit code 1

### [PASS] resume/retry 对 acknowledged 任务的处理
- `is_acknowledged_dispatch_reentry()` 检测 acknowledged 状态，直接走 `execute_task_run()` 跳过正常的 resume/retry 前置检查
- 这避免了 acknowledged 任务因 checkpoint 不满足 resume_ready 而卡死
- 端到端测试验证了 acknowledge → resume → completed 全链路

### [CONCERN] route_mode 硬编码为 "summary"
- `acknowledge_task()` 中 `state.route_mode = "summary"` 是硬编码值
- 当前这是合理的默认选择（acknowledged = 强制 local，summary 是最安全的模式）
- 但未来如果需要支持 operator 选择 route_mode，这里需要参数化
- **不阻塞本轮**，记录为后续可选改进

---

## Slice 3: [MOCK-REMOTE] 可视化标识

### [PASS] is_mock_remote_task() 判断逻辑
- 基于 `transport_kind` 和 `dispatch_status` 双条件判断
- 排除了 `blocked` 和 `acknowledged` 状态（这些不应标记为 mock-remote）
- 同时支持从 state 属性和 topology dict 两种来源读取，兼容 inspect 和 review 的不同数据加载方式

### [PASS] inspect 命令集成
- Route And Topology 区域新增 `route_label: [MOCK-REMOTE]` 行
- local 任务显示 `route_label: -`，不干扰

### [PASS] review 命令集成
- Handoff 区域同样新增 `route_label: [MOCK-REMOTE]`

### [PASS] dispatch 报告命令
- mock-remote 任务的 dispatch 报告输出前添加 `[MOCK-REMOTE]` 标签行

### [PASS] 测试覆盖
- mock-remote 任务 inspect → 包含 `[MOCK-REMOTE]`
- local 任务 inspect → 不包含 `[MOCK-REMOTE]`
- blocked 任务 inspect → 不包含 `[MOCK-REMOTE]`
- dispatch 报告 → mock-remote 包含标签

---

## 与 design_decision 的一致性检查

| 设计要求 | 实现状态 |
|----------|---------|
| 新建 dispatch_policy.py | PASS — 已创建 |
| orchestrator 入口前置校验 | PASS — remote_candidate 条件触发 |
| CLI acknowledge 子命令 | PASS — 完整实现 |
| 状态流转 blocked→running(retrieval) | PASS — 与设计一致 |
| topology_dispatch_status="acknowledged" 新值 | PASS — 已实现 |
| event: task.dispatch_acknowledged | PASS — 已记录 |
| inspect/review [MOCK-REMOTE] 标签 | PASS — 三处输出均有 |
| 不触及真实 remote/RPC | PASS — 无越界 |

## Phase-Guard 检查

- [x] 未越出 Phase 21 scope
- [x] 未触及 non-goals（无 RPC、无 provider negotiation、无 auto-promotion）
- [x] 已有 local-path 行为未被修改

## 结论

**PASS, mergeable.** 三个 slice 全部符合设计，测试通过，无 BLOCK 项。唯一 CONCERN（acknowledge route_mode 硬编码）不影响当前功能正确性。
