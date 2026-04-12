# Codex 专属规则

本文件只包含 Codex 特有的规则。共同规则见 `.agents/shared/rules.md`。

---

## 一、Git 分支规则

### 不直接在 `main` 上开发

- `main`：稳定主线
- `feat/<phase-or-slice>`：当前开发分支
- `fix/<topic>`：修复分支
- `docs/<topic>`：文档分支

### 一个 phase 对应一个短生命周期 feature branch

- 一个 phase = 一个主要 feature branch
- 一个 slice = 一个或多个小步提交
- phase 完成后再合并回 `main`

---

## 二、Commit 规则

### commit 必须是小步、单一语义

格式：`type(scope): summary`

类型：`feat` / `fix` / `refactor` / `test` / `docs` / `chore`

要求：
- 一个 commit 只表达一类变化
- 不要把代码、测试、README、状态同步全塞进一个大提交
- 文档提交也应有单独语义
- git 提交命令由人工执行，Codex 只负责在对话中提供建议命令

### 提交应与 slice 对齐

每个 slice 完成后，Codex 必须立即给出一条建议的 `git commit` 命令。
默认要求：

1. 不把多个 slice 混入同一个 commit
2. 如一个 slice 改动较大，可拆为多个 commit，但仍只服务该 slice
3. 人工执行 commit 后，再做状态同步或进入下一个 slice
4. 如需额外的文档/状态同步 commit，应单独建议，不与功能实现强绑定

---

## 三、实现规则

### 先做最小闭环，再做边界 tightening

优先顺序：

1. 先有 operator 可见入口
2. 再有 operator 可执行动作
3. 再有决策持久化
4. 再做 inspect / report tightening
5. 最后做文档和收口

### 不破坏当前稳定基线

除非当前 phase 明确要求，不要破坏：

- 已接受的本地任务循环
- state / events / artifacts 分层
- inspect / review / control / recovery 路径
- task semantics 与 knowledge objects 的边界

### 区分"局部 refactor"和"新 phase 目标"

出现方向性重构时，先判断：

1. 它只是当前 slice 内部的局部整理
2. 它是当前 phase 的自然子任务
3. 它值得成为下一 phase 的正式 slice

---

## 四、PR 规则

### 创建 PR 前

- 确认 Claude 的 `review_comments.md` 已产出（如 workflow 要求）
- 确认分支上所有 commit 与 slice 对齐
- 确认测试通过
- 提醒人工准备发起 PR

### PR body

使用 `.agents/templates/pr_body.md` 模板，引用各 agent 产出物的 TL;DR，并将结果写入仓库根目录 `./pr.md`。
Codex 只负责维护 `./pr.md` 内容，不执行 PR 创建命令。

### 合并

- 不自行 merge，等待人工审批
- merge 后更新 `docs/active_context.md` 和分支状态

### 对话提醒要求

- 每完成一个可提交 slice，明确提醒人工执行 commit
- 每次进入可开 PR 状态，明确提醒人工检查并使用 `./pr.md`
- 不输出笼统的“可以一起提交了”，必须指明当前对应的 slice 或 PR 阶段

---

## 本文件的职责边界

本文件是：Codex 在本仓库中的专属操作规则。
本文件不是：共同规则（见 shared/rules.md）、角色定义（见 role.md）、状态板。
