# Rules

本文件规定 Codex 在本仓库中进行规划、实现、文档同步与 Git 操作时应遵守的默认规则。

目标：

- 保持 phase、Git、文档节奏一致
- 减少重复文档维护
- 避免历史材料污染当前实现
- 让当前工作上下文始终清晰、可恢复、可提交

---

## 一、默认工作原则

### 1. 先确认当前工作边界，再开始实现

进入新任务时，先确认：

- active_track
- active_phase
- active_slice
- 当前目标
- 当前非目标
- 当前下一步

默认来源：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/plans/<active-phase>/kickoff.md`
4. `docs/plans/<active-phase>/breakdown.md`

如果当前边界不清楚，不要直接进入实现。

---

### 2. 不默认扩大当前 phase 范围

除非当前文档明确要求，否则不要顺手推进：

- 新 intake 宽度
- 自动 promotion
- 大范围 workbench / UX 扩张
- remote ingestion / sync
- 新平台级复杂度
- 历史 `post-phase-*` 的继续扩张

如果一个改动超出当前 slice，应先判断：

1. 它是否只是当前 slice 的局部实现细节
2. 它是否应放入当前 phase 的后续 slice
3. 它是否应延后到下一 phase

---

### 3. 不把 archive 当作当前目标

`docs/archive/*`、旧 phase closeout、旧 `post-phase-*` 仅按需读取。  
除非当前问题明确依赖它们，否则不要把历史归档材料自动视为当前工作边界。

---

## 二、Git 规则

### 1. 不直接在 `main` 上开发

默认工作方式：

- `main`：稳定主线
- `feat/<phase-or-slice>`：当前开发分支
- `fix/<topic>`：修复分支
- `docs/<topic>`：文档分支

当前推荐分支：

- `feat/phase12-knowledge-promotion-review`

---

### 2. 一个 phase 对应一个短生命周期 feature branch

默认节奏：

- 一个 phase = 一个主要 feature branch
- 一个 slice = 一个或多个小步提交
- phase 完成后再合并回 `main`

不要把多个 phase 的目标混在同一条长期开发分支里。

---

### 3. commit 必须是小步、单一语义

提交信息统一使用：

- `type(scope): summary`

推荐类型：

- `feat`
- `fix`
- `refactor`
- `test`
- `docs`
- `chore`

要求：

- 一个 commit 只表达一类变化
- 不要把代码、测试、README、状态同步全部塞进一个大提交
- 文档提交也应有单独语义，而不是“update many files”

---

### 4. 提交应尽量与 slice 对齐

理想状态下，每个 slice 至少能分解为：

1. 功能实现
2. 测试
3. 必要的当前上下文同步
4. 收口文档（如适用）

例如：

- `feat(knowledge): add review queue classification`
- `feat(cli): add knowledge review queue command`
- `test(knowledge): cover review queue output`
- `chore(context): update active context after review queue slice`

---

## 三、文档更新规则

### 1. 高频状态只更新一个地方

当前唯一高频状态入口是：

- `docs/active_context.md`

以下内容变化时，优先更新它：

- 当前 slice 进度
- 当前下一步
- 当前阻塞项
- 当前 active branch
- 当前 active phase / active slice 的推进状态

不要把这些高频状态同时写进：

- `AGENTS.md`
- `current_state.md`
- README
- closeout

---

### 2. `AGENTS.md` 是入口控制面，不是历史总表

`AGENTS.md` 只负责：

- 仓库定位
- 当前 active 方向
- 长期规则
- phase / Git / 文档节奏
- authoritative docs 说明

不要把它写成：

- 完整 phase 历史
- 高频状态板
- 详细恢复日志
- 第二份 README

---

### 3. `current_state.md` 只做恢复入口

`current_state.md` 只负责：

- 当前稳定 checkpoint
- 最近完成的 phase
- 已知问题
- 恢复命令
- 最小验证命令

不要把它继续扩展成完整开发编年史。

---

### 4. `docs/plans/<phase>/` 是 phase 的正式文档层

每个 phase 默认文档为：

- `kickoff.md`
- `breakdown.md`
- `closeout.md`
- `commit_summary.md`（可选）

要求：

- 当前 phase 先读 kickoff 与 breakdown
- closeout 只在接近收口时重点更新
- commit summary 不是强制文件

---

### 5. `.codex/` 是薄控制层

`.codex/` 只应存放：

- 会话读取顺序
- Codex 工作规则
- 模板
- 少量高价值 skills

不应在 `.codex/` 下再复制一套：

- 完整 phase 正文
- 当前状态板
- README 式背景总表
- 长期历史归档

---

## 四、规划规则

### 1. kickoff 必须写清楚边界

在写 `kickoff.md` 时，必须显式写出：

- 当前 phase
- 当前 track
- 当前 slice
- 当前目标
- 当前非目标
- 当前设计边界
- 完成条件

如果这些内容不明确，不要直接写 breakdown。

---

### 2. breakdown 必须可执行

`breakdown.md` 应至少包含：

- slice 列表
- 顺序
- 每个 slice 的目标
- 每个 slice 的验收条件
- 默认不做的工作
- stop / go 信号

不要让 breakdown 只停留在抽象口号层。

---

### 3. 未来不再新增 `post-phase-*`

历史上的 `post-phase-*` 保留为归档材料。  
未来新的方向性工作应组织为：

- 正式 phase
- 明确 track
- 明确 slice

不要再用 `post-phase-*` 作为新命名。

---

## 五、实现规则

### 1. 先做最小闭环，再做边界 tightening

当前 phase 的实现顺序应优先保证：

- 先有 operator 可见入口
- 再有 operator 可执行动作
- 再有决策持久化
- 再做 inspect / report tightening
- 最后做文档和收口

不要一开始就做大范围重构。

---

### 2. 不破坏当前稳定基线

除非当前 phase 明确要求，否则不要破坏：

- 已接受的本地任务循环
- state / events / artifacts 分层
- inspect / review / control / recovery 路径
- task semantics 与 knowledge objects 的边界
- retrieval、routing、validation、memory 的 inspectable 语义

---

### 3. 明确区分“局部 refactor”和“新 phase 目标”

如果出现方向性重构，先判断：

- 它只是当前 slice 内部的局部整理
- 它是当前 phase 的自然子任务
- 它值得成为下一 phase 的正式 slice

不要在实现中隐式打开一个新的大方向。

---

## 六、phase 收口规则

每结束一个 phase，至少应完成：

1. `docs/plans/<phase>/closeout.md`
2. `current_state.md` 的恢复状态更新
3. `docs/active_context.md` 从当前 phase 状态切换到下一轮入口状态
4. Git 分支收口与合并准备
5. 必要时 tag

---

### phase 收口时的规则文件同步检查

每次 phase 结束时，检查以下文件是否需要同步更新。

#### 必查
- `docs/plans/<phase>/closeout.md`
- `current_state.md`
- `docs/active_context.md`

#### 条件更新
- `AGENTS.md`
- `.codex/session_bootstrap.md`
- `.codex/rules.md`
- `README.md`
- `README.zh-CN.md`

---

### 这些文件在什么情况下需要更新

#### 更新 `AGENTS.md`
当以下内容发生变化时更新：

- active_track 改变
- active_phase 改变
- active_slice 改变
- 长期稳定规则发生变化
- phase / Git / 文档节奏规则发生变化
- authoritative docs 路径发生变化

#### 更新 `.codex/session_bootstrap.md`
当以下内容发生变化时更新：

- Codex 默认读取顺序改变
- active phase 改变
- 当前默认读取的 phase 文档路径改变
- 当前默认分支命名规则改变

#### 更新 `.codex/rules.md`
当以下内容发生变化时更新：

- Git 节奏规则改变
- 文档同步规则改变
- phase 收口规则改变
- planning / implementation 的默认操作规则改变

#### 更新 `README.md` / `README.zh-CN.md`
当以下内容发生变化时更新：

- 用户可见命令变化
- 用户可见工作流变化
- 项目整体定位或结构变化
- Quickstart / operator 路径变化

如果只是 phase 内部实现推进，而没有影响对外使用方式，不要顺手重写 README。

#### 更新 `docs/active_context.md`
phase 收口时应：

- 清除已完成的当前推进状态
- 标记当前 phase 已 closeout
- 写明下一轮默认入口
- 不把旧 phase 的高频状态继续挂在 active context 上

#### 更新 `current_state.md`
phase 收口时应：

- 更新最近稳定 checkpoint
- 更新最近完成的 phase
- 更新已知问题
- 更新恢复命令或验证命令（如有变化）

---

## 七、可选规则：commit summary

`docs/plans/<phase>/commit_summary.md` 是可选产物。

仅在以下情况建议写：

- phase 改动较大，手工提交需要统一摘要
- 需要为 PR / release note / phase closeout 准备简洁概述
- 当前 phase 结束后希望快速复用提交说明

不要把 commit summary 当成每个 phase 的强制负担。

---

## 八、当前默认适用对象

当前这些规则默认服务于：

- `Phase 12`
- `Retrieval / Memory`
- `Knowledge Promotion And Reuse Review`

如果后续进入新 phase，应在 phase 收口时同步检查：

- `AGENTS.md`
- `docs/active_context.md`
- `.codex/session_bootstrap.md`

确保它们不继续停留在旧 phase 语义下。

---

## 九、本文件的职责边界

本文件是：

- Codex 在本仓库中的操作规则
- Git / 文档 / phase 节奏的约束说明
- phase 收口时的规则同步检查表

本文件不是：

- 当前高频状态板
- phase 正文
- closeout 文档
- 详细恢复日志