---
author: claude
phase: 39
slice: ingestion-specialist
status: final
depends_on:
  - docs/roadmap.md
  - docs/plans/phase36/closeout.md
  - docs/plans/phase38/closeout.md
---

> **TL;DR** Phase 39 引入 Ingestion Specialist，支持导入外部对话记录（ChatGPT JSON / Claude Web JSON / Open WebUI JSON / 通用 Markdown），经降噪提纯后转化为 `StagedCandidate` 进入 Staged-Knowledge 暂存区，由 Librarian 审查晋升。3 个 slice，低-中风险。

# Phase 39 Kickoff: Ingestion Specialist — 外部会话摄入

## Track

- **Primary Track**: Retrieval / Memory
- **Secondary Track**: Workbench / UX

## 目标

打通人类在外部大模型 UI（ChatGPT / Claude Web）及主机侧探索面板（Open WebUI :3002）中沉淀的探索上下文与 Swallow 内部规范记忆之间的桥梁。

具体目标：

1. 实现 **Ingestion Specialist** 模块：解析 ChatGPT JSON 导出、Claude Web JSON 导出、Open WebUI JSON 导出，以及通用 Markdown 文件
2. 实现 **降噪提纯**：从聊天记录中剥离闲聊、重复、无效内容，提取有效结论、架构约束与被否方案
3. 将提纯后的记录转化为标准 `StagedCandidate`，自动进入 Staged-Knowledge 暂存区，对接 Phase 36 已收口的 Librarian 审查晋升防线
4. 提供 CLI 入口 `swl ingest` 供 operator 触发摄入

## 非目标

- **不做实时同步**：不监听外部 API，不做 WebSocket / polling，仅支持本地文件导入（含 Open WebUI 导出文件；Open WebUI API 自动拉取留待 Provider Connector 层落地后的后续 phase）
- **不做自动晋升**：摄入产出一律进入 `pending` 状态的 StagedCandidate，晋升由 Librarian 防线控制
- **不做 LLM 调用降噪**：本阶段降噪使用规则式提取（关键词/结构匹配），不引入 LLM 二次处理
- **不做 PDF / HTML / 图片解析**：仅支持 JSON + Markdown 输入格式
- **不做 HandoffContractSchema 自动生成**：摄入产出为 StagedCandidate，不直接生成 HandoffContract（后续 phase 可扩展）
- **不扩展 Web 控制中心**：摄入入口仅为 CLI

## 设计边界

### 输入格式

| 格式 | 来源 | 解析方式 |
|------|------|---------|
| ChatGPT JSON | `conversations.json` 导出 | 解析 `mapping` 结构，提取 assistant 与 user message pairs |
| Claude Web JSON | Claude 导出 JSON | 解析 `chat_messages` 数组，提取 content blocks |
| Open WebUI JSON | Open WebUI (:3002) 导出 | 解析 `messages` 数组（OpenAI 兼容格式），提取 role + content pairs |
| Markdown | 通用笔记 | 按 heading 分段，每段作为独立知识片段 |

**Open WebUI 定位说明**：Open WebUI 是部署在主机侧 VPS 上的探索性对话面板（见 `PROVIDER_ROUTER_AND_NEGOTIATION.md` §5.4），属于 Swallow 生态的半内部组件。本阶段通过文件导入摄入其对话记录；未来 Provider Connector 层落地后，可演进为通过 Open WebUI API 自动拉取，实现更短的知识回流路径。

### 降噪策略（规则式）

- 过滤纯问候/确认/致谢等闲聊轮次（基于短文本 + 关键词匹配）
- 合并连续同角色消息
- 去重：对提取片段做文本归一化后去重
- 保留含代码块、列表、关键词（"决定"/"约束"/"方案"/"结论"/"不做"等）的轮次

### 产出路径

```
外部文件 → IngestionParser (格式解析)
         → IngestionFilter (降噪)
         → StagedCandidate[] (标准化)
         → staged_knowledge registry (持久化)
         → Librarian review queue (已有路径)
```

### 与现有模块的接口

- **`staged_knowledge.py`**：复用现有 `StagedCandidate` dataclass 与 `register_staged_candidate()` / `load_staged_candidates()`
- **`librarian_executor.py`**：不修改。摄入产出进入 staged registry 后，Librarian 的 review/promote 路径已在 Phase 36 收口
- **`cli.py`**：新增 `ingest` 子命令
- **`paths.py`**：新增 ingestion 相关路径 helper

## Slice 拆解

### S1: Ingestion Parser — 格式解析层

**目标**：实现 ChatGPT JSON、Claude Web JSON、Open WebUI JSON、Markdown 四种格式的解析器，输出统一的中间表示 `ConversationTurn` 列表。

**影响范围**：新增 `src/swallow/ingestion/` 包，新增 `parsers.py`

**风险评级**：
- 影响范围: 1 (新增独立模块)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 1 (无外部依赖)
- **总分: 3** — 低风险

**验收条件**：
- ChatGPT JSON 导出解析通过：正确提取 role + content + timestamp
- Claude Web JSON 导出解析通过：正确提取 sender + text blocks
- Open WebUI JSON 导出解析通过：正确提取 role + content（OpenAI 兼容 messages 格式）
- Markdown 解析通过：按 heading 分段，每段含 heading + body
- 解析器对畸形输入返回有意义的错误而非崩溃

### S2: Ingestion Filter — 降噪提纯层

**目标**：对 `ConversationTurn` 列表执行规则式降噪，输出 `ExtractedFragment` 列表（有效知识片段）。

**影响范围**：新增 `src/swallow/ingestion/filters.py`

**风险评级**：
- 影响范围: 1 (新增独立模块)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 1 (无外部依赖)
- **总分: 3** — 低风险

**验收条件**：
- 闲聊轮次被过滤（"好的"/"谢谢"/"明白了" 等）
- 含代码块/列表/关键词的轮次被保留
- 连续同角色消息被合并
- 重复片段被去重
- 空输入返回空列表，不报错

### S3: Ingestion Pipeline + CLI — 端到端集成

**目标**：将 Parser → Filter → StagedCandidate 转化串联为完整 pipeline，新增 `swl ingest` CLI 入口，将摄入结果写入 staged_knowledge registry。

**影响范围**：新增 `src/swallow/ingestion/pipeline.py`，修改 `cli.py`、`paths.py`

**风险评级**：
- 影响范围: 2 (跨模块：ingestion + cli + paths + staged_knowledge)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 2 (依赖内部 staged_knowledge 模块)
- **总分: 5** — 中风险

**验收条件**：
- `swl ingest <file>` 正确识别格式并执行完整 pipeline
- 产出的 `StagedCandidate` 出现在 staged_knowledge registry 中
- `source_kind` 标记为 `"external_session_ingestion"`
- `swl ingest --dry-run` 仅输出提取结果，不写入 registry
- 全量 pytest 通过

## Slice 依赖

```
S1 (Parser) → S2 (Filter) → S3 (Pipeline + CLI)
```

严格顺序依赖。

## 风险总评

| Slice | 影响 | 可逆 | 依赖 | 总分 | 评级 |
|-------|------|------|------|------|------|
| S1 | 1 | 1 | 1 | 3 | 低 |
| S2 | 1 | 1 | 1 | 3 | 低 |
| S3 | 2 | 1 | 2 | 5 | 中 |
| **合计** | | | | **11/27** | **低-中** |

主要风险集中在 S3 的跨模块集成。S1/S2 为纯新增独立代码，风险极低。

## 完成条件

1. 四种格式（ChatGPT JSON / Claude Web JSON / Open WebUI JSON / Markdown）均可成功解析并提取知识片段
2. 降噪规则有效过滤闲聊、合并重复
3. `swl ingest <file>` 端到端可用，产出进入 staged_knowledge registry
4. 全量 pytest 通过，无回归
5. 摄入产出不触发 Librarian 自动晋升（仅进入 pending 暂存区）

## Branch Advice

- 当前分支: `main`
- 建议操作: 人工审批 kickoff 后，从 `main` 切出 `feat/phase39-ingestion-specialist`
- 理由: Phase 39 为新功能开发，应在 feature branch 上进行
- 建议 PR 范围: S1 + S2 + S3 合并为单 PR（模块独立，总体量可控）
