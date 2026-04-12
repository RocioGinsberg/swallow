# Gemini 专属规则

本文件只包含 Gemini 特有的规则。共同规则见 `.agents/shared/rules.md`。

---

## 一、Context Brief 规则

### context_brief.md 必须包含

- **任务概述**：当前要做什么（≤3 句话）
- **变更范围**：哪些模块/文件可能受影响
- **相关设计文档**：列出与本次任务直接相关的 `docs/design/*.md` 及其关键约束
- **近期变更摘要**：从 git history 提取最近相关的变更（≤10 条 commit）
- **关键上下文**：其他 agent 需要知道但不容易自行发现的信息
- **风险信号**：发现的潜在冲突或不一致（如有）

### 不要写的内容

- 不写实现建议（那是 Claude 的职责）
- 不写代码片段（那是 Codex 的职责）
- 不写自己的判断或偏好，只提供事实和观察

---

## 二、一致性检查规则

### consistency_report.md 格式

```markdown
## Consistency Report

### 检查范围
- 对比对象: <方案/代码> vs <设计文档列表>

### 一致项
- [CONSISTENT] <描述>

### 不一致项
- [INCONSISTENT] <描述>
  - 来源: <设计文档路径:行号>
  - 当前状态: <实际情况>
  - 期望状态: <设计文档要求>
  - 建议: <修改方案 or 更新设计文档>

### 未覆盖项
- [NOT_COVERED] <描述>
  - 说明: 当前方案涉及但设计文档未提及的部分
```

### 检查时机

- phase kickoff 后、design_decision 产出前：检查任务方向与设计文档的一致性
- Codex 实现完成后、PR review 前：检查实现与设计文档的一致性

---

## 三、长上下文使用原则

### 充分利用长上下文窗口

Gemini 的核心优势是长上下文。应当：

- 一次性读入多个相关设计文档，而不是逐个读取
- 在单次会话中完成完整的一致性比对
- 为其他 agent 压缩信息：把长材料变成短摘要

### 输出必须精炼

虽然输入可以很长，但输出必须精炼：

- context_brief 控制在 300 行以内
- consistency_report 只列不一致项和未覆盖项，一致项概括即可
- TL;DR 必须 ≤3 行

---

## 四、前期规划与 Track 打包原则 (Primary + Secondary Track)

为了避免任务切片过于细碎、增加不必要的上下文交接开销，Gemini 在进行前期阶段规划或推荐时，**默认采用“主赛道 + 强相关的副赛道” (Primary + Strong Secondary Track) 的组合打包模式**。

### 执行标准

- **组合原则**：如果一个底层的逻辑改动（例如在 Track 6 增加验证策略）自然而然地需要一个上层视图（例如在 Track 5 增加 CLI 输出或干预入口）才能闭环，应当将它们合并为同一个 Phase 的任务包。
- **划定绝对边界 (Non-goals)**：在合并任务包时，**必须更加严格地定义“不做什么”**。任务包的扩大仅限于“逻辑上的紧密闭环”，绝不允许跨越到完全不同的架构领域导致范围失控（例如：做 CLI 干预时绝不碰网络序列化）。
- **描述要求**：在产出或协助制定下一步计划时，明确指出这属于哪个 Primary Track 以及附带了哪个 Secondary Track 的内容，阐明打包带来的高闭环价值。

---

## 五、与其他 Agent 的协作边界

- Gemini 产出 context_brief → Claude 读取后产出 design_decision
- Gemini 产出 consistency_report → Claude 在 review 中参考
- Gemini 不直接与 Codex 交互，所有信息经由文件传递

---

## 本文件的职责边界

本文件是：Gemini 在本仓库中的专属操作规则。
本文件不是：共同规则（见 shared/rules.md）、角色定义（见 role.md）、状态板。

