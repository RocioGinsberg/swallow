# Active Context

## 当前轮次

- active_track: `Retrieval / Memory`
- active_phase: `Phase 12`
- active_slice: `Knowledge Promotion And Reuse Review`
- active_branch: `feat/phase12-knowledge-promotion-review`（建议）
- status: `in_progress`

---

## 当前目标

本轮工作的目标是把已存在的 imported knowledge / staged knowledge，从“已记录”推进到“可审查、可决策、可复用”的显式 operator 流程。

当前 Phase 12 重点不是扩张 intake，也不是继续扩大 workbench 宽度，而是补齐 intake 之后的 review / promotion / reuse review 闭环。

---

## 本轮要解决的问题

当前系统已经具备：

- planning handoff 进入 task semantics
- staged knowledge capture 进入 knowledge objects
- intake / inspect / review 的基础 operator 入口
- retrieval 中对 reusable knowledge 的部分显式边界
- knowledge stage / evidence / reuse / canonicalization 相关字段与报告

当前最缺少的是：

- staged knowledge 的显式 review queue
- promote / reject 的 operator entrypoints
- promotion decision record
- reuse-readiness 的更直接 inspection 入口
- intake 之后如何进入后续 reusable path 的清晰工作流

---

## 本轮范围

### 应做

本轮默认应推进以下内容：

1. knowledge review queue
2. knowledge promote entrypoint
3. knowledge reject entrypoint
4. promotion decision record / artifact
5. reuse-readiness inspection tightening
6. help / README alignment
7. phase closeout

### 不应默认推进

本轮不默认推进以下方向：

- 扩大 planning / knowledge intake 宽度
- 自动 knowledge promotion
- 隐式全局记忆
- remote ingestion / sync
- 大范围 Workbench / UX 扩张
- 让 imported planning 自动驱动 run preparation 或执行主循环
- 重新打开旧 `post-phase-*` 过渡方向

---

## 当前建议拆解

### Slice 1：review queue baseline
目标：
- 给 staged knowledge 建立 compact review queue 入口
- 能区分待 review、可 promote、blocked 的对象

验收要点：
- operator 能直接看到哪些 knowledge objects 需要处理
- queue 输出中体现 stage / evidence / reuse-readiness 的关键边界

### Slice 2：promote / reject entrypoints
目标：
- 给 operator 提供显式 promote / reject 命令或等价入口
- 不依赖 create-time flags 作为唯一控制点

验收要点：
- knowledge objects 的状态变化是显式操作结果
- promote / reject 不会隐式修改无关对象

### Slice 3：decision record / artifact
目标：
- 记录谁在何时对哪个 object 做了 promote / reject 决策
- 让后续 inspect / review 能看到决策链

验收要点：
- 决策结果可持久化
- inspect / review 路径能看到 promotion 记录

### Slice 4：reuse-readiness inspection tightening
目标：
- 更直接看出哪些 imported knowledge 已具备复用条件
- 更直接看出哪些对象仍被 stage / evidence / policy 卡住

验收要点：
- inspect / review / report 至少有一条紧凑路径能看 reuse readiness
- 不要求引入新的自动化复用逻辑

### Slice 5：docs/help alignment
目标：
- 更新 operator 文档，让 intake 之后的 review / promotion / reuse review 流程可见

验收要点：
- CLI help、README、phase 文档不互相打架
- 当前 phase 的收口材料完整

---

## 当前关键文档

本轮优先读取：

1. `AGENTS.md`
2. `docs/system_tracks.md`
3. `docs/plans/phase12/kickoff.md`
4. `docs/plans/phase12/breakdown.md`

需要恢复历史上下文时再读取：

- `current_state.md`
- `docs/archive/*`
- 旧 phase closeout
- 旧 `post-phase-*` 归档文档

---

## 当前 Git 节奏

推荐做法：

- 从 `main` 切出 `feat/phase12-knowledge-promotion-review`
- kickoff / breakdown 先落地
- 每完成一个 slice 做小步提交
- 高频只更新本文件
- phase 收口时再更新：
  - `docs/plans/phase12/closeout.md`
  - `current_state.md`
  - 必要时 `AGENTS.md`
  - 必要时 `README.md` / `README.zh-CN.md`

推荐提交类型：

- `feat(...)`
- `fix(...)`
- `refactor(...)`
- `test(...)`
- `docs(...)`
- `chore(context): update active context ...`

---

## 当前实现约束

- 不破坏已接受的本地任务循环
- 不破坏已有 artifact 语义
- 不破坏 inspect / review / control 相关工作台路径
- 不引入新的大范围 phase 外架构改造
- 不为了“看起来完整”而提前加入平台型复杂度

---

## 当前推进

已完成：

- `Phase 12` kickoff / breakdown 文档已确认
- review queue baseline 已落地，新增 `swl task knowledge-review-queue`
- promote / reject entrypoints 已落地，新增：
  - `swl task knowledge-promote`
  - `swl task knowledge-reject`
- decision record 已落地：
  - `knowledge_decisions.jsonl`
  - `artifacts/knowledge_decisions_report.md`
- operator 可通过 `swl task knowledge-decisions` / `knowledge-decisions-json` 检查决策记录
- reuse-readiness 已更直接纳入 `swl task inspect` / `swl task review`
- knowledge review 摘要已接入 `swl task queue` / `swl task control`
- 相关 CLI 测试已补齐并通过
- README / README.zh-CN 已补充 intake 之后的 review / promotion 流程

## 当前待办

- [x] 确认 `Phase 12` 的 kickoff 文档
- [x] 确认 `Phase 12` 的 breakdown 文档
- [x] 确认 review queue 的最小输出形态
- [x] 确认 promote / reject 的命令边界
- [x] 确认 decision record 应落在哪类 artifact / record
- [x] 确认 reuse-readiness 应优先进入哪个 inspect 路径
- [ ] 开始 feature branch 开发
- [x] 把 reuse-readiness 更直接纳入 `inspect` / `review`
- [x] 同步 README / CLI help 的 Phase 12 工作流说明
- [x] 评估是否需要把 review queue 摘要进一步纳入 `task queue` 或 `control` 视图

---

## 下一步

下一步应优先完成：

1. 基于当前 queue / control 集成，判断是否要继续把 knowledge review 引入更细粒度的 operator 优先级排序
2. 视需要补 Phase 12 closeout 所需的收口文档
