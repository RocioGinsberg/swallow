# Claude 专属规则

本文件只包含 Claude 特有的规则。共同规则见 `.agents/shared/rules.md`。

---

## 一、Roadmap 维护规则

Roadmap 由 Human / Codex / roadmap-updater subagent 共同维护，Claude 主线只承担复核与评审相关的轻量职责。

- **roadmap-updater subagent 负责**：phase 完成事实登记（已有差距条目的状态更新、phase 完成标注、蓝图对齐自动同步）
- **Codex 主线负责**：Human 要求时新增候选方向、维护推荐队列、把真实使用 / 实现反馈转化为后续 phase planning 输入
- **Claude 主线负责**：PR review / tag evaluation 过程中发现 roadmap 风险时写入简短批注，或在 Human 明确要求时做方向复核

### 触发时机

- roadmap-updater subagent 完成增量更新后（评审与微调）
- Human 请求方向建议时
- 会话讨论中浮现新方向时，默认由 Codex 写入；Claude 只在当前会话由 Claude 承接时直接写入
- Phase 拆分（如 Phase 63 → 63 + 63.5）发生时

### Claude 可写内容

在 `docs/roadmap.md` 中，Claude 可以直接：

1. 为 review / tag evaluation 中发现的风险添加简短批注（≤2 句）
2. 修正 roadmap-updater 造成的事实性错漏
3. Human 明确要求时，给出方向复核并更新推荐顺序
4. 发现 PR review concern 已经影响后续候选时，同步 `docs/concerns_backlog.md` 并在 roadmap 中加引用

### 不做的事

- **不修改差距条目的"已消化"状态标注**（那是 roadmap-updater subagent 的事实层职责，phase 完成时由 subagent 自动同步；Claude 手动改容易破坏 subagent 下次同步）
- 不修改 §一 当前实现基线 / §二 Era 演进锚点（这两节的更新也属于 subagent 事实层）
- 不产出独立的方向评审文档（直接写 roadmap，不另开 brainstorm 文件）
- 不默认替 Codex 产出 phase plan 或长篇方案拆解

### 与 active_context 的边界

- `docs/roadmap.md` 承载**跨 phase 蓝图**（差距、候选、长期方向）
- `docs/active_context.md` 承载**当前 phase 高频状态**（active_slice、当前下一步、阻塞项）
- 讨论中浮现的新方向 → 直接写 roadmap §三 / §四
- 当前 phase 内的状态变化 → 写 active_context

---

## 二、方案审查规则

### 默认审查对象

新 phase 默认审查 Codex 产出的：

- `docs/plans/<phase>/plan.md`
- `docs/plans/<phase>/plan_audit.md`

旧 phase 可兼容读取 `kickoff.md` / `design_decision.md` / `risk_assessment.md` / `breakdown.md`，但不再默认要求这些文件存在。

### `plan.md` 审查重点

- 目标 / 非目标是否足以约束 scope creep
- slice / milestone 是否可执行，是否保留人工 commit gate
- 高风险项是否有单独 milestone、验证方式和降级路径
- 是否遵守 `docs/design/INVARIANTS.md` 与相关设计 / 工程文档
- 是否存在明显遗漏的测试、guard、eval 或 smoke 检查
- 是否有不必要的冗余文档拆分

---

## 三、评审规则

### review_comments.md 格式

使用 checklist 格式，每项标注状态：

- `[PASS]` — 符合 `plan.md`，无问题
- `[CONCERN]` — 可接受但有改进建议
- `[BLOCK]` — 不符合设计或引入风险，必须修改

### 评审必须覆盖

- 与 `plan.md` 的一致性（旧 phase 兼容 `design_decision.md`）
- 与 `docs/design/*.md` 架构原则的一致性
- 测试覆盖是否充分
- 是否越出 phase scope

### 不做的事

- 不审查代码风格（留给 linter）
- 不审查 commit message 格式（Codex 自行遵守）
- 不提出超出当前 phase 范围的改进建议

---

## 四、分支建议规则

### 何时提供 branch-advise

- phase 开始时：建议分支名
- 准备 PR 时：评估是否该开 PR、PR 范围是否合理
- slice 切换时：评估是否需要新分支

### branch-advise 输出格式

```markdown
## Branch Advice

- 当前分支: <branch-name>
- 建议操作: 继续 / 新建分支 / 开 PR
- 理由: <一句话>
- 建议分支名（如适用）: <name>
- 建议 PR 范围（如适用）: <slice 列表>
```

### 最终执行

分支建议只是建议。实际 git 操作由人工执行；Codex 可提供建议命令和状态同步。

---

## 五、phase-guard 规则

每次产出 plan audit / model review / review_comments 时，同时检查：

1. 当前方案是否越出 `plan.md` 的 goals
2. 当前方案是否触及 `plan.md` 的 non-goals
3. 当前 slice 数量是否合理（单 phase 建议 ≤5 个 slice）

如果发现越界，在产出物中显式标注 `[SCOPE WARNING]` 并说明原因。

---

## 六、Model Review Gate 规则

Claude 主线负责判断 plan gate 前是否需要第二模型审查。规则详见 `.agents/workflows/model_review.md`。

### 何时 required

满足任一条件时设为 required:

- Roadmap 方向、phase 边界或 `plan.md` 优先级存在明显不确定性
- 方案触及 INVARIANTS / DATA_MODEL / SELF_EVOLUTION / schema / CLI/API / state transition / truth write path / provider routing policy
- `plan_audit.md` 包含 `[BLOCKER]` 或多个 `[CONCERN]`
- Human 明确要求第二模型审查

### Claude 职责

- 只准备 read-only review packet,不让外部模型写仓库文件
- 将外部模型结果归档为 `docs/plans/<phase>/model_review.md`
- 消化 `[BLOCK]` / `[CONCERN]`,必要时要求 Codex 修订 `plan.md` 并重新进入 audit / gate
- 更新 `docs/active_context.md` 的 `model_review.status`

### 边界

- Model review 只是 advisory,不替代 Human Plan Gate
- 没有外部 review 通道时,不得伪造第二模型结论
- 不把 Codex executor 嵌入 Claude Code 做实现;Codex 只在 plan gate 通过后实现

---

## 七、Review 阶段测试规则

PR review 时应尽量运行测试验证实现正确性：

- 使用 `.venv/bin/python -m pytest` 执行测试
- 如果 `.venv` 环境不存在，跳过自动测试，并在 `review_comments.md` 中标注 `[NOTE] 测试环境未就绪，未执行自动测试`
- 不要临时安装系统级包（`pip install --break-system-packages` 等）来替代

---

## 八、CONCERN 追踪规则

Review 中产出的 `[CONCERN]` 项必须同步登记到 `docs/concerns_backlog.md`。

### 登记时机

每次产出 `review_comments.md` 且包含 `[CONCERN]` 项时，在同一轮中更新 backlog。

### 登记内容

每条记录包含：Phase、Slice、CONCERN 描述、预期消化时机。

### 分类

- **Open**：待后续 phase 自然消化或专项修复
- **Won't Fix / By Design**：经评估属于设计意图，不需要修改
- **Resolved**：已在后续 phase 中修复，注明修复 phase

### 回顾节奏

每 3-5 个 phase 回顾一次 backlog：
- 清理已过时的 Open 条目
- 将已自然解决的移入 Resolved
- 不主动将 Open 项塞入当前 phase scope（除非人工决定优先级）

---

## 本文件的职责边界

本文件是：Claude 在本仓库中的专属操作规则。
本文件不是：共同规则（见 shared/rules.md）、角色定义（见 role.md）、状态板。
