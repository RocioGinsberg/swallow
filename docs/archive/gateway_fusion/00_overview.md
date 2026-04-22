# Gateway 设计融合方案总览

> 来源：`docs/design_gateway.md` 内化至长期设计蓝图
> 作者：Claude (方案拆解)
> 日期：2026-04-16
> 状态：已执行

---

## 背景

`docs/design_gateway.md` 是一份架构哲学层面的 gateway 定位论述，核心主张：

1. Gateway 是**任务语义与外部供应商波动之间的稳定边界**（volatility absorber）
2. **策略与执行必须分离**——上游讲意图与约束，下游讲路由与通道
3. Gateway 不是模型选择器，是让模型选择变得**可治理、可观测、可替换**的操作层

现有蓝图的问题：第 2 层的 Router（策略路由）和第 6 层的能力协商器（执行路由）之间职责重叠、边界模糊。降级矩阵中混入了策略判断（如"禁止弱模型做架构规划"），违背策略/执行分离原则。

---

## 变更清单

| # | 动作 | 目标文件 |
|---|---|---|
| 1 | 第6层重命名 + Mermaid图调整 + §3.5重写 | `ARCHITECTURE.md` |
| 2 | 新增 §0 Gateway 设计哲学 | `docs/design/PROVIDER_ROUTER_AND_NEGOTIATION.md` |
| 3 | §4.1 降级矩阵拆分，策略约束移出 | `docs/design/PROVIDER_ROUTER_AND_NEGOTIATION.md` |
| 4 | §2.1 Router 扩充为 Strategy Router | `docs/design/ORCHESTRATION_AND_HANDOFF_DESIGN.md` |
| 5 | §2.4 Review Gate 补充降级联动 | `docs/design/ORCHESTRATION_AND_HANDOFF_DESIGN.md` |
| 6 | §3.2 Meta-Optimizer 补充遥测消费 | `docs/design/SELF_EVOLUTION_AND_MEMORY.md` |
| 7 | 新建 GATEWAY_PHILOSOPHY.md | `docs/design/GATEWAY_PHILOSOPHY.md` |

---

## 核心设计决策

- **职责归属修正**：策略性降级约束（如"禁止弱模型做架构规划"）从网关层回归编排层
- **第6层重命名**：`模型接入与路由层 (Provider Router)` → `模型网关层 (Model Gateway)`
- **Strategy Router 显式化**：编排层的 Router 扩充为 Strategy Router，承接能力下限断言
- **遥测接口契约**：网关层路由遥测 → Meta-Optimizer 的数据流转显式定义
- `docs/design_gateway.md` 原文保留为参考，精华提炼入 `GATEWAY_PHILOSOPHY.md`
