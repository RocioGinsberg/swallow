# Claude 专属规则

本文件只包含 Claude 特有的规则。共同规则见 `.agents/shared/rules.md`。

---

## 一、方案拆解规则

### design_decision.md 必须包含

- 方案总述（≤5 句话概括做什么、为什么这么做）
- slice 拆解（每个 slice 的目标、影响范围、风险评级）
- 依赖说明（哪些 slice 有顺序依赖）
- 明确的非目标（当前方案刻意不做什么）
- 验收条件（每个 slice 怎么算完成）

### 风险评级标准

每个 slice 标注以下三个维度，各 1-3 分：

- **影响范围**：1=单文件 2=单模块 3=跨模块
- **可逆性**：1=轻松回滚 2=需要额外工作 3=难以回滚
- **依赖复杂度**：1=无外部依赖 2=依赖内部模块 3=依赖外部系统

总分 ≥7 的 slice 必须标注为高风险，建议拆分或增加人工 gate。

---

## 二、评审规则

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

## 三、分支建议规则

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

## 四、phase-guard 规则

每次产出 design_decision 或 review_comments 时，同时检查：

1. 当前方案是否越出 kickoff.md 的 goals
2. 当前方案是否触及 kickoff.md 的 non-goals
3. 当前 slice 数量是否合理（单 phase 建议 ≤5 个 slice）

如果发现越界，在产出物中显式标注 `[SCOPE WARNING]` 并说明原因。

---

## 本文件的职责边界

本文件是：Claude 在本仓库中的专属操作规则。
本文件不是：共同规则（见 shared/rules.md）、角色定义（见 role.md）、状态板。
