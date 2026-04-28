# Claude 专属规则

本文件只包含 Claude 特有的规则。共同规则见 `.agents/shared/rules.md`。

---

## 一、Roadmap 优先级评审规则

Claude 与 roadmap-updater subagent 共同维护 `docs/roadmap.md`。分工如下：

- **roadmap-updater subagent 负责**：差距总表的事实层（phase 完成登记、差距状态更新、蓝图对齐标注）
- **Claude 负责**：推荐 phase 队列的优先级排序与风险批注

### 评审时机

- roadmap-updater subagent 完成增量更新后
- Human 请求方向建议时

### 评审内容

在 roadmap "推荐 phase 队列"中：

1. **调整优先级排序**：基于依赖关系、风险、ROI 判断
2. **添加风险批注**：每条队列项可附加简短风险提示（≤2 句）
3. **标注依赖前置**：如某方向依赖另一方向先完成，显式标注

### 不做的事

- 不修改差距总表中的蓝图对齐内容（那是 roadmap-updater subagent 的领域）
- 不自行新增差距条目（发现新差距时在 active_context.md 中标注，由 roadmap-updater 下次运行时补充）
- 不产出独立的方向评审文档

---

## 二、方案拆解规则

### design_decision.md 必须包含

- 方案总述（≤5 句话概括做什么、为什么这么做）
- slice 拆解（每个 slice 的目标、影响范围、风险评级）
- 依赖说明（哪些 slice 有顺序依赖）
- review checkpoint / milestone 分组（哪些 slice 必须单独审查，哪些可作为同一实现里程碑一起推进）
- 明确的非目标（当前方案刻意不做什么）
- 验收条件（每个 slice 怎么算完成）

### 风险评级标准

每个 slice 标注以下三个维度，各 1-3 分：

- **影响范围**：1=单文件 2=单模块 3=跨模块
- **可逆性**：1=轻松回滚 2=需要额外工作 3=难以回滚
- **依赖复杂度**：1=无外部依赖 2=依赖内部模块 3=依赖外部系统

总分 ≥7 的 slice 必须标注为高风险，建议拆分或增加人工 gate。

---

## 三、评审规则

### review_comments.md 格式

使用 checklist 格式，每项标注状态：

- `[PASS]` — 符合 design_decision，无问题
- `[CONCERN]` — 可接受但有改进建议
- `[BLOCK]` — 不符合设计或引入风险，必须修改

### 评审必须覆盖

- 与 design_decision 的一致性
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

分支建议只是建议。实际 git 操作由人工确认后 Codex 执行。

---

## 五、phase-guard 规则

每次产出 design_decision 或 review_comments 时，同时检查：

1. 当前方案是否越出 kickoff.md 的 goals
2. 当前方案是否触及 kickoff.md 的 non-goals
3. 当前 slice 数量是否合理（单 phase 建议 ≤5 个 slice）

如果发现越界，在产出物中显式标注 `[SCOPE WARNING]` 并说明原因。

---

## 六、Model Review Gate 规则

Claude 主线负责判断 design gate 前是否需要第二模型审查。规则详见 `.agents/workflows/model_review.md`。

### 何时 required

满足任一条件时设为 required:

- Roadmap 方向、phase 边界或 kickoff 优先级存在明显不确定性
- 方案触及 INVARIANTS / DATA_MODEL / SELF_EVOLUTION / schema / CLI/API / state transition / truth write path / provider routing policy
- `design_audit.md` 包含 `[BLOCKER]` 或多个 `[CONCERN]`
- Human 明确要求第二模型审查

### Claude 职责

- 只准备 read-only review packet,不让外部模型写仓库文件
- 将外部模型结果归档为 `docs/plans/<phase>/model_review.md`
- 消化 `[BLOCK]` / `[CONCERN]`,必要时修订 `design_decision.md` / `risk_assessment.md`
- 更新 `docs/active_context.md` 的 `model_review.status`

### 边界

- Model review 只是 advisory,不替代 Human Design Gate
- 没有外部 review 通道时,不得伪造第二模型结论
- 不把 Codex executor 嵌入 Claude Code 做实现;Codex 只在设计 gate 通过后实现

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
