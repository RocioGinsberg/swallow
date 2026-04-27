# Active Context

## 当前轮次

- active_track: `<填写当前 track>`
- active_phase: `<填写当前 phase>`
- active_slice: `<填写当前 slice>`
- active_branch: `<填写当前分支>`
- status: `<planning | implementation | closeout>`

---

## 当前目标

用 2 到 5 行说明本轮当前最重要的目标。

要求：

- 只写当前轮次
- 不写完整项目历史
- 不写已归档 phase 的长说明
- 不写 README 式背景介绍

---

## 当前问题

用简洁条目说明当前轮次正在解决什么问题。

建议格式：

- 当前系统已经具备什么
- 当前最缺什么
- 为什么这一轮要先补这个缺口

要求：

- 只写和当前 phase / slice 直接相关的问题
- 不默认回顾所有旧 phase

---

## 本轮范围

### 应做

列出当前轮次默认应推进的工作。

建议：

1. `<工作项 1>`
2. `<工作项 2>`
3. `<工作项 3>`

### 不应默认推进

列出当前轮次不应顺手扩张的方向。

例如：

- `<非目标 1>`
- `<非目标 2>`
- `<非目标 3>`

要求：

- 明确写“本轮不做什么”
- 防止实现过程中 scope creep

---

## 当前建议拆解

### Slice 1：`<名称>`

目标：
- `<一句话说明>`

验收要点：
- `<验收点 1>`
- `<验收点 2>`

### Slice 2：`<名称>`

目标：
- `<一句话说明>`

验收要点：
- `<验收点 1>`
- `<验收点 2>`

### Slice 3：`<名称>`

目标：
- `<一句话说明>`

验收要点：
- `<验收点 1>`
- `<验收点 2>`

说明：

- 这里写的是当前 phase 的执行拆解，不是长期路线图
- slice 名称应尽量和 Git commit / phase breakdown 对齐

---

## 当前关键文档

本轮优先读取：

1. `AGENTS.md`
2. `docs/system_tracks.md`
3. `docs/plans/<active-phase>/kickoff.md`
4. `docs/plans/<active-phase>/breakdown.md`

按需再读取：

- `current_state.md`
- `docs/plans/<active-phase>/closeout.md`
- `docs/archive/*`

要求：

- 不默认回读所有历史 phase
- 不默认回读 archive

---

## 当前 Git 节奏

推荐做法：

- 当前 branch：`<填写分支>`
- 每个 milestone 完成后做一次人工审查与提交
- 高频只更新本文件
- phase 收口时再更新：
  - `docs/plans/<active-phase>/closeout.md`
  - `current_state.md`
  - 必要时 `AGENTS.md`
  - 必要时 `README.md`

推荐提交类型：

- `feat(...)`
- `fix(...)`
- `refactor(...)`
- `test(...)`
- `docs(...)`
- `chore(context): update active context ...`

---

## 当前实现约束

列出当前轮次不应破坏的稳定基线。

例如：

- `<稳定边界 1>`
- `<稳定边界 2>`
- `<稳定边界 3>`

要求：

- 这里写“不能破坏什么”
- 不写过宽泛的长期哲学
- 重点写当前实现必须守住的边界

---

## 当前待办

- [ ] `<待办 1>`
- [ ] `<待办 2>`
- [ ] `<待办 3>`
- [ ] `<待办 4>`

要求：

- 待办应是当前短期真实动作
- 不写长期 wishlist
- 不写已经归档的老任务

---

## 下一步

下一步应优先完成：

1. `<下一步 1>`
2. `<下一步 2>`

要求：

- 始终保持这里可执行
- 新会话读到这里时，应能直接知道先做什么
