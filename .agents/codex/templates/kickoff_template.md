# Phase Kickoff

> Legacy template. 新 phase 默认使用 `.agents/codex/templates/plan_template.md` 产出 `docs/plans/<phase>/plan.md`;只有 Human 明确要求或 phase 复杂到单文件计划不可审查时,才单独产出 kickoff。

## 基本信息

- phase: `<填写 phase 名称>`
- track: `<填写当前 track>`
- slice: `<填写当前 slice>`
- status: `kickoff`
- recommended_branch: `<填写推荐分支名>`

---

## 启动背景

说明当前为什么进入这个 phase。

建议回答：

- 当前仓库已经完成了什么基线
- 哪些历史阶段已视为稳定 checkpoint
- 当前缺口是什么
- 为什么这一轮应该优先补这个缺口，而不是继续扩张其他方向

要求：

- 只写与当前 phase 直接相关的背景
- 不要回顾完整项目编年史
- 不要把 archive 材料整体复制进来

---

## 当前问题

用条目写清楚当前 phase 试图解决的问题。

建议格式：

- 当前系统已经能做什么
- 当前系统还缺什么
- 当前 operator / implementation path 在哪里不够清晰
- 当前为什么需要这个 phase

要求：

- 问题必须具体
- 问题必须能映射到后续 breakdown
- 不要写成过宽泛的愿景口号

---

## 本轮目标

明确写出本轮 phase 要完成什么。

建议：

1. `<目标 1>`
2. `<目标 2>`
3. `<目标 3>`

要求：

- 目标必须可落到实现与验收
- 目标必须和当前 track 一致
- 不要把多个 track 的目标混在同一个 kickoff 中

---

## 本轮非目标

明确写出本轮不默认做什么。

例如：

- `<非目标 1>`
- `<非目标 2>`
- `<非目标 3>`

要求：

- 非目标必须显式写出
- 用来约束 scope creep
- 尽量覆盖最容易“顺手做掉”的扩张方向

---

## 设计边界

### 应保持稳定的部分

列出当前 phase 不应破坏的已有基线。

例如：

- `<稳定边界 1>`
- `<稳定边界 2>`
- `<稳定边界 3>`

### 本轮新增能力应满足

列出本轮新增能力必须满足的约束。

例如：

- `<新增约束 1>`
- `<新增约束 2>`
- `<新增约束 3>`

要求：

- 边界要能指导实现
- 不要只写抽象哲学
- 应能帮助判断某项改动是否越界

---

## 本轮建议方向

按方向列出当前 phase 应优先围绕哪些问题组织实现。

### 1. `<方向 1>`
说明：
- `<一句话描述>`

### 2. `<方向 2>`
说明：
- `<一句话描述>`

### 3. `<方向 3>`
说明：
- `<一句话描述>`

要求：

- 建议方向不等于详细 breakdown
- 这里只做 phase 级指导，不替代 breakdown 的 slice 列表

---

## 完成条件

写清楚本 phase 可以 closeout 的最低条件。

建议格式：

1. `<完成条件 1>`
2. `<完成条件 2>`
3. `<完成条件 3>`

要求：

- 条件必须可检查
- 条件必须与目标对应
- 不能写成“感觉差不多完成了”

---

## Git 节奏要求

说明当前 phase 默认采用的 Git 节奏。

建议包括：

- 推荐 branch 名
- 一个 phase 对应一个短生命周期 feature branch
- 一个 slice 对应一个或多个小步提交
- 高频状态只更新 `docs/active_context.md`
- 收口时再更新 closeout / current_state / 必要规则文件

推荐提交类型：

- `feat(...)`
- `fix(...)`
- `refactor(...)`
- `test(...)`
- `docs(...)`
- `chore(context): update active context ...`

---

## 下一步

kickoff 落地后，下一步应优先完成：

1. `docs/plans/<phase>/breakdown.md`
2. 明确最小 slice 顺序
3. 切出推荐 feature branch
4. 从第一个最小闭环 slice 开始实现

要求：

- 这里必须可执行
- 新会话读到这里时，应能立刻知道下一步做什么
