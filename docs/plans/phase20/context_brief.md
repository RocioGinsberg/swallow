# Context Brief: Phase 20 - Mock Dispatch & Execution Gating

## 任务概述
本轮任务 (Phase 20) 属于 Track 3: Execution Topology。其核心目标是在 Phase 19 统一 Handoff Contract Schema 的基础上，让交接单（Handoff Note）驱动实质性的调度决策。具体而言，将在 Orchestrator 中引入 Dispatch 拦截器与 Mock Remote Executor，实现基于 Contract 的模拟远端派发与 Execution Gating（不涉及真实 RPC 和网络传输）。

## 变更范围
- `src/swallow/orchestrator.py` 或调度分发逻辑模块：引入基于 `remote_handoff_contract.json` 的 Dispatch 拦截器。
- `src/swallow/executor.py` 或相关执行器：新增 `MockRemoteExecutor`（模拟远端执行的成功/失败边界）。
- `tests/*`：新增 Dispatcher 路由逻辑与 Mock Executor 的单元测试。

## 相关设计文档
- `docs/design/ORCHESTRATION_AND_HANDOFF_DESIGN.md`：核心依赖。规定了“基于状态的异步协同”与 Dispatcher 读取画像并匹配能力的原则。
- `docs/design/STATE_AND_TRUTH_DESIGN.md`：规定了状态流转与单点事实来源。
- `docs/design/HARNESS_AND_CAPABILITIES.md`：明确了工具沙盒隔离与执行层边界。

## 近期变更摘要
- `d3fd25f` Merge branch 'feat/phase19-handoff-schema-unification'
- `d513a32` docs(phase19): phase PR review
- `f41d15f` docs(phase19): close out handoff schema unification
- `a167907` feat(core-loop): unify handoff contract schema
- Phase 19 刚刚完成，确立了 `HandoffContractSchema` 以及 `remote_handoff_contract.json` 的严谨写盘校验。

## 关键上下文
- **上下文依赖**：当前系统已经具备 Staged Knowledge Gate 和 Handoff Contract 的 Schema 校验，但 Orchestrator 还没有“根据交接单做出去哪执行”的能力。
- **目标边界**：这仅是一个 Mock 层的 Execution Topology 扩展。**绝对不要**在此切片中引入实际的网络序列化（如 gRPC、HTTP 等）或 Provider 的能力协商降级（那是后续阶段的职责）。
- **执行状态流转**：模拟派发应具有完整的状态生命周期（如派发成功/拦截打回），并能将结果以符合现有四件套（State Store, Event Log）的方式落盘。

## 风险信号
- **本地执行回归风险**：在 Orchestrator 插入基于 Contract 的 Dispatch 拦截器时，极易对原有的纯本地同步执行工作流造成破坏。需要强化测试覆盖以确保 `Local Execution` 逻辑仍保持畅通。
- **Executor 接口散逸**：新增的 MockRemoteExecutor 必须严格遵循现有的 Executor 抽象接口，不能为了“远端属性”强行修改底层的基础合约，否则后续接入真实的 Remote Executor 时会付出巨大的重构代价。