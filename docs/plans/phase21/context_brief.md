# Context Brief: Phase 21 - Dispatch Policy Gate & Mock Topology Visibility

## 任务概述
本轮任务 (Phase 21) 采用打包模式：**Primary Track: 6 (Evaluation / Policy) + Secondary Track: 5 (Workbench / UX)**。
其核心目标是在 Phase 20 (Mock Dispatch) 的基础上，首先在调度前引入真正的语义验证策略 (Policy Gate)，拦截非法的交接单；其次在 CLI 层面补充拦截任务的人工放行命令 (`acknowledge`) 与可视化的 `[MOCK-REMOTE]` 区分标识，形成逻辑与交互的完整闭环。

## 变更范围
- **Track 6 (逻辑层)**：在 `src/swallow/orchestrator.py` 的 Dispatch 前置环节，或新增 `dispatch_policy.py`，实现 `validate_handoff_semantics()`。主要检查 `context_pointers` 指向的知识点或 Git Hash 是否实际存在/可访问。
- **Track 5 (交互层)**：
  - `src/swallow/cli.py`：新增命令或子命令，允许操作员手动将状态从 `dispatch_blocked` 疏通 (acknowledge)。
  - CLI `inspect / review` 的输出渲染器：确保 `MockRemoteExecutor` 产生的路由在终端输出时带有显式的 `[MOCK-REMOTE]` 前缀/标签，不再与真实的 remote execution 混淆。
- `tests/*`：补充策略验证和新增 CLI 命令的端到端测试。

## 相关设计文档
- `docs/design/ORCHESTRATION_AND_HANDOFF_DESIGN.md`：强调了交接单必须经过严格提纯（不传递大块代码，只传递指针）。本次增加的验证就是为了确保这些“指针”不是幻觉产生的死链。
- `docs/design/INTERACTION_AND_WORKBENCH.md`：规定了“中断与接管机制 (Handoff & Interrupt)”和“权限阻断墙”。本次新增的 `acknowledge` 动作正是此机制的 CLI 落地。
- `.agents/gemini/rules.md`：依据新增加的“前期规划与 Track 打包原则”进行的主副赛道合并规划。

## 近期变更摘要
- Phase 20 完成了 `DispatchVerdict` 与 `mock-remote` 路径的打通。
- Phase 20 `review_comments.md` 提出了遗留的 UI 混淆问题：Mock-remote 当前在视图层与真实 remote 无法区分，亟待解决。
- `d3fd25f` (Phase 19 收口)
- Phase 20 尚未合入 main，目前在 `feat/phase20-mock-dispatch-gating` 上，但这不影响我们先规划下一阶段的基线。

## 关键上下文
- **合并打包的价值**：仅仅做拦截 (Track 6)，任务卡住了操作员无能为力；仅仅做 UI 标识 (Track 5)，又缺乏底层的防守意义。将“语义验证”与“可视化/手动疏通”结合，恰好闭环了**“发现问题 -> 拦截 -> 提示人 -> 人工接管”**的标准工作流。
- **绝对非目标 (Non-goals)**：
  1. 绝不碰网络传输、跨进程通信或真实的 RPC 序列化。
  2. 绝不在此阶段做 Provider 能力降级（Capability Negotiator 不在这个包里）。

## 风险信号
- **生命周期状态循环死锁**：在实现 `acknowledge` 疏通阻塞时，需要极其小心地定义下一个流转状态（例如：是从 `dispatch_blocked` 回到 `pending`，还是直接转入某种强制放行的 `mock_remote`）。处理不当可能导致状态机在拦截和放行间死循环。