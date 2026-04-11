---
author: claude
phase: 19
slice: handoff-contract-schema-unification
status: draft
depends_on:
  - docs/plans/phase19/design_review.md
---

**TL;DR**: Phase 19 选择 Orchestration（Core Loop + Execution Topology 交叉）作为 primary track，聚焦统一 Handoff Contract Schema，将三处文档中不一致的交接单术语固化为单一代码 Schema，并补充验证逻辑。共 3 个 slice，预计改动集中在 models.py 和 harness.py。

---

# Design Decision — Phase 19

## Track 选择建议

### 推荐 Primary Track: Core Loop（交叉 Execution Topology）

**理由**：

Gemini 审查报告（`design_review.md`）明确指出三个演进方向中，**统一交接契约 Schema** 优先级最高——它是 Phase 18 Remote Handoff Contract Baseline 的自然延续，且 Gemini 发现了跨文档的术语不一致（KNOWLEDGE_AND_RAG_DESIGN vs ORCHESTRATION_AND_HANDOFF_DESIGN vs INTERACTION_AND_WORKBENCH），这是一个必须在进一步扩展前解决的基础问题。

**排除的候选 track**：
- Capabilities（能力协商/降级）：Gemini 建议逐个落地，但当前 Schema 不统一会导致后续能力协商的契约基础不稳，应先统一再扩展
- Retrieval/Memory：Phase 12-17 已大量投入，当前不是瓶颈
- Workbench/UX：无新的 operator 需求驱动

### Slice 命名

`Handoff Contract Schema Unification`

---

## 方案拆解

### Slice 1: Schema 术语统一与定义

**目标**：将三处文档中的交接单字段统一为单一术语集，写入代码层 Schema。

统一方案（基于 Gemini 审查建议）：

| 统一字段 | 来源 1 (Orchestration) | 来源 2 (RAG/Knowledge) | 来源 3 (Interaction) |
|----------|----------------------|----------------------|---------------------|
| `goal` | Goal | Goals | Goal |
| `constraints` | — | Constraints | Constraints |
| `done` | Done | — | — |
| `next_steps` | Next_Steps | — | — |
| `context_pointers` | Context_Pointers | Context | Context Ref |

最终统一 Schema 字段：`goal`, `constraints`, `done`, `next_steps`, `context_pointers`

**影响范围**：`src/swallow/models.py`（TaskState 或新增 HandoffContract dataclass）
**验收条件**：新 Schema dataclass 存在，字段定义清晰，有 docstring 说明与各设计文档的映射关系
**风险评级**：影响 1 / 可逆 1 / 依赖 1 = **总分 3（低风险）**

---

### Slice 2: remote_handoff_contract.json 验证逻辑

**目标**：基于统一 Schema，为 `remote_handoff_contract.json` 添加标准验证逻辑。

**具体内容**：
- 验证 handoff contract record 是否包含所有必填字段
- 验证字段值是否符合预期类型/格式
- 在 harness 写入 artifact 时自动执行验证
- 验证失败时产出明确错误信息（不静默跳过）

**影响范围**：`src/swallow/harness.py`（artifact 写入路径），可能新增 `src/swallow/validation.py` 或在现有 validators 中扩展
**验收条件**：写入 handoff contract 时自动验证，不合规记录被拒绝并报错，有对应测试
**风险评级**：影响 2 / 可逆 1 / 依赖 2 = **总分 5（中风险）**

---

### Slice 3: 设计文档术语对齐标注

**目标**：在三份设计文档中标注术语已统一至代码 Schema，不修改设计文档正文结构，只添加对齐说明。

**具体内容**：
- 在 `ORCHESTRATION_AND_HANDOFF_DESIGN.md`、`KNOWLEDGE_AND_RAG_DESIGN.md`、`INTERACTION_AND_WORKBENCH.md` 中各添加一个 "Schema Alignment Note" 小节
- 说明各文档原始术语与统一 Schema 的对应关系
- 标注统一 Schema 的 authoritative 定义位置（代码文件路径）

**影响范围**：`docs/design/` 下三个文件（只添加标注，不改正文）
**验收条件**：三份文档均有 alignment note，指向同一个 authoritative Schema 定义
**风险评级**：影响 1 / 可逆 1 / 依赖 1 = **总分 3（低风险）**

---

## 实现顺序

Slice 1 → Slice 2 → Slice 3（严格顺序，每个依赖前一个）

## 非目标

- 不实现真实 remote execution
- 不改动 provider routing / 能力协商
- 不扩展 handoff contract 的业务语义（如自动 dispatch）
- 不修改设计文档的正文结构或章节组织
- 不引入新的 CLI 命令

---

## Branch Advice

- **建议分支名**：`feat/phase19-handoff-schema-unification`
- **建议操作**：从 `main` 切出新分支
- **PR 策略**：3 个 slice 合并为一个 PR（改动范围小且内聚）
