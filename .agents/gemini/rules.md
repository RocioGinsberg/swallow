# Gemini 专属规则

本文件只包含 Gemini 特有的规则。共同规则见 `.agents/shared/rules.md`。

---

## 一、Design Preview 与阶段过渡规则

当一个 Phase 正式收官（closeout 完成）后，Gemini 需要负责规划下一阶段的候选方向：

### design_preview.md 必须包含

- **基建现状盘点**：简述系统当前已稳固的核心底座和最新收口的成果。
- **现状与蓝图差距分析 (Reality vs. Blueprint)**：**[强制采用多层锚点分析模式]**
    对比分析必须覆盖以下三个维度，以避免局部最优陷阱：
    1.  **系统级锚点 (The Bedrock)**：对比 `ARCHITECTURE.md`。检查改动是否破坏了核心分层、状态真值语义或 handoff 契约。
    2.  **领域级卫星 (Domain Satellites)**：对比当前 Track 相关的 `docs/design/*.md`。评估功能实现与特定领域设计愿景的契合度。
    3.  **跨界嗅探 (Cross-Cutting Smell Test)**：识别对非活跃 Track 文档（如路由、成本、安全）的潜在负面影响或耦合风险。
- **分析输出要求**：必须包含一个对比表，且包含 **“局部最优风险预警”** 列，用于警示仅满足局部需求可能带来的长期架构债。表格示例：
    | 维度 | 参考源 | 蓝图愿景 | 核心差距 | 局部最优风险预警 |
    | :--- | :--- | :--- | :--- | :--- |
    | 系统级 | `ARCHITECTURE.md` | ... | ... | **[风险描述]** |
    | 领域级 | `docs/design/...` | ... | ... | ... |
- **候选方向评估**：结合 `docs/system_tracks.md`，提供 2-3 个高边际收益（High ROI）的演进方向。
- **优劣势分析**：每个候选方向必须包含设计目标、优势 (Pros)、劣势 (Cons) 以及关联的 Track。
- **推荐结论**：给出作为架构看门人的倾向性建议，并明确向 Human Operator 抛出决策请求。

### 触发与等待机制

- **不可越级**：`design_preview.md` 产出后，**必须停下来等待人工（Human Operator）的明确确认**。
- **触发 Context Brief**：只有在收到人工针对 `design_preview.md` 的明确决策（例如“选择方向 A”）之后，才能据此起草下一阶段的 `context_brief.md`。

---

## 二、Context Brief 规则

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

