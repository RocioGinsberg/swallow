---
author: claude
phase: 56
slice: kickoff
status: draft
depends_on:
  - docs/roadmap.md
  - docs/design/KNOWLEDGE.md
  - docs/design/AGENT_TAXONOMY.md
  - src/swallow/literature_specialist.py
  - src/swallow/quality_reviewer.py
  - src/swallow/executor.py
---

## TL;DR
Phase 56 为 Literature/Quality Agent 接入 LLM 能力，使其从启发式占位升级为真正有用的分析工具。LiteratureSpecialist 新增关系推断建议（operator gate 确认后落库），QualityReviewer 新增语义质量评估。同步统一成本追踪：HTTP executor 和 Agent LLM 调用均从 API response 取真实 usage，替代 `len // 4` 估算。TDD 先行。

# Phase 56 Kickoff: 知识质量与 LLM 增强检索

## 基本信息

| 字段 | 值 |
|------|-----|
| Phase | 56 |
| Primary Track | Knowledge / RAG |
| Secondary Track | Evaluation / Policy |
| 目标 tag | v1.2.0 (LLM-Enhanced Knowledge) |
| 前置 phase | Phase 55 (v1.1.0) |
| 开发方式 | TDD 先行 |

## 战略定位

Phase 55 打通了知识闭环（本地文件 → 双链图谱 → relation-aware retrieval → 任务执行），但暴露了两个痛点：

1. **手动建关系太重**——摄入 5 个文件后要逐对 `swl knowledge link`，operator 成本高
2. **启发式分析质量有限**——LiteratureSpecialist 只做词频/标题提取，QualityReviewer 只做非空/结构检查，对实际知识治理的帮助有限

Phase 56 的使命是**让 Agent 真正有用**：LLM 驱动的深度分析 + 关系推断建议 + 语义质量评估。同时统一成本追踪，消除 `len // 4` 估算与 API 真实 usage 的不一致。

## 当前 Agent 现状

| Agent | 当前能力 | Phase 56 增强 |
|-------|---------|-------------|
| LiteratureSpecialistAgent | 启发式：heading 提取 + 词频 + 交叉比较 | LLM 深度分析 + **关系推断建议** |
| QualityReviewerAgent | 规则式：non_empty / has_structure / has_actionable_content / min_length | LLM 语义质量评估 |

## 当前成本追踪现状

| 路径 | 估算方式 | 问题 |
|------|---------|------|
| `run_http_executor()` | `_attach_estimated_usage()` — `len(text) // 4` | API response 的 `usage` 字段被丢弃 |
| Agent `execute()` | 无估算 | Phase 53 的 Agent 不调 LLM，无成本 |
| `run_cli_agent_executor()` | `_attach_estimated_usage()` — `len(text) // 4` | CLI agent 无法返回 API usage |

## 目标 (Goals)

1. **LiteratureSpecialist LLM 增强**：接入 LLM 做深度文档分析，输出结构化摘要 + 关系推断建议列表。LLM 不可用时 fallback 到启发式。
2. **关系推断建议工作流**：Agent 产出 `relation_suggestions` → `side_effects` 记录 → operator 通过 `swl knowledge apply-suggestions` 确认后落库。符合 P7（Proposal over Mutation）。
3. **QualityReviewer LLM 增强**：接入 LLM 做语义质量评估，输出结构化评分 + 改进建议。LLM 不可用时 fallback 到规则式。
4. **成本追踪统一**：HTTP executor 从 API response 取真实 `usage`，Agent LLM 调用同理，`_attach_estimated_usage()` 降级为 fallback。

## 非目标 (Non-Goals)

- **不做自动关系落库**：关系建议必须经过 operator gate，不跳过确认直接写入。
- **不做 agentic retrieval / 多跳推理**：留待后续 phase。
- **不做降级链路配置化**：留待 Phase 57（router 层关注点）。
- **不改动 CLI agent（aider / claude-code）的成本追踪**：CLI agent 无法返回 API usage，继续用 `len // 4`。
- **不做 Agent prompt 模板的精细调优**：Phase 56 定义最小可行 prompt，后续迭代优化。

## Slice 拆解

### S1: 成本追踪统一

**目标**：HTTP executor 和 Agent LLM 调用使用 API 真实 usage，`_attach_estimated_usage()` 降级为 fallback。

**TDD 契约**：
- `test_http_executor_uses_api_usage_when_available`：mock HTTP response 含 `usage` 字段，验证 `ExecutorResult.estimated_input_tokens` 来自 API
- `test_attach_estimated_usage_skips_when_already_populated`：当 result 已有 usage 时不覆盖
- `test_attach_estimated_usage_falls_back_for_non_http`：mock / local / CLI 路径继续用 `len // 4`

**实现要点**：
- `run_http_executor()` 在 line 1222 解析 `data = response.json()` 后，提取 `data.get("usage", {})`
- 将 `prompt_tokens` / `completion_tokens` 回填到 `ExecutorResult.estimated_input_tokens` / `estimated_output_tokens`
- `_attach_estimated_usage()` 改为：已有值 > 0 时跳过，否则 fallback 到 `len // 4`
- 新增 helper `extract_api_usage(response_data) -> tuple[int, int]`

**验收条件**：
- HTTP executor 成功时 usage 来自 API response
- HTTP executor 失败时（无 usage 字段）fallback 到 `len // 4`
- 非 HTTP executor 行为不变
- 全量 pytest 通过

### S2: LiteratureSpecialist LLM 增强 + 关系推断

**目标**：LiteratureSpecialist 接入 LLM，产出深度分析 + 关系建议。

**TDD 契约**：
- `test_literature_specialist_uses_llm_when_available`：mock LLM response，验证输出含 LLM 分析结果，`analysis_method: llm`
- `test_literature_specialist_falls_back_to_heuristic_on_llm_failure`：LLM 调用失败时，fallback 到 Phase 53 的启发式逻辑，`analysis_method: heuristic`
- `test_literature_specialist_produces_relation_suggestions`：LLM 分析包含 `relation_suggestions` 列表，每项含 `source_object_id` / `target_object_id` / `relation_type` / `confidence` / `context`
- `test_literature_specialist_records_llm_usage_in_side_effects`：`side_effects["llm_usage"]` 包含 `input_tokens` / `output_tokens` / `model`

**实现要点**：
- `LiteratureSpecialistAgent.execute()` 中新增 `_call_llm(prompt) -> dict` 方法
- 使用 `httpx.post()` 直接调用 API（方案 B），endpoint / API key 复用现有 env vars（`SWL_API_BASE_URL` / `SWL_API_KEY`）
- LLM prompt 要求输出 JSON：`{"summary": "...", "key_concepts": [...], "relation_suggestions": [...]}`
- try-except 包裹 LLM 调用，失败时 fallback 到 `self._build_report()`（现有启发式）
- `ExecutorResult.side_effects` 新增 `llm_usage` 和 `relation_suggestions`
- `ExecutorResult.estimated_input_tokens / estimated_output_tokens` 从 API usage 回填

**关系建议格式**（在 `side_effects` 中）：
```python
"relation_suggestions": [
    {
        "source_object_id": "knowledge-0001",
        "target_object_id": "knowledge-0003",
        "relation_type": "cites",
        "confidence": 0.85,
        "context": "Document A references the constraint defined in Document C"
    }
]
```

**验收条件**：
- LLM 可用时输出 `analysis_method: llm`
- LLM 不可用时输出 `analysis_method: heuristic`（无功能退化，与 Phase 53 行为一致）
- 关系建议在 `side_effects` 中，不自动落库
- LLM usage 在 `side_effects["llm_usage"]` 中
- 全量 pytest 通过

### S3: QualityReviewer LLM 增强

**目标**：QualityReviewer 接入 LLM，产出语义质量评估。

**TDD 契约**：
- `test_quality_reviewer_uses_llm_when_available`：mock LLM response，验证输出含 LLM 评分，`analysis_method: llm`
- `test_quality_reviewer_falls_back_to_heuristic_on_llm_failure`：LLM 不可用时 fallback 到 Phase 53 的规则检查
- `test_quality_reviewer_llm_adds_semantic_criteria`：LLM 评估包含 `coherence` / `completeness` / `actionability` 等语义维度
- `test_quality_reviewer_records_llm_usage`：usage 回填到 result 和 side_effects

**实现要点**：
- `QualityReviewerAgent.execute()` 中新增 `_call_llm(prompt) -> dict`，模式与 S2 一致
- LLM prompt 要求对 artifact 做语义质量评估，输出 JSON：`{"verdicts": [{"name": "...", "verdict": "pass|warn|fail", "detail": "..."}]}`
- 规则检查（non_empty / has_structure / min_length）仍在本地执行，LLM 补充语义维度
- LLM 不可用时仅执行规则检查（与 Phase 53 行为一致）

**验收条件**：
- LLM 可用时输出含语义维度的评分
- LLM 不可用时输出仅含规则维度的评分
- LLM usage 正确追踪
- 全量 pytest 通过

### S4: 关系建议应用工作流

**目标**：operator 可通过 CLI 确认 Agent 的关系建议并落库。

**TDD 契约**：
- `test_cli_knowledge_apply_suggestions_creates_relations`：从 task 的 executor output 中提取 relation_suggestions，`swl knowledge apply-suggestions --task-id <id>` 后关系落库
- `test_cli_knowledge_apply_suggestions_skips_duplicates`：已存在的关系不重复创建
- `test_cli_knowledge_apply_suggestions_dry_run`：`--dry-run` 只显示不落库

**实现要点**：
- CLI 新增 `swl knowledge apply-suggestions --task-id <id> [--dry-run]`
- 从 task 的 executor result 中读取 `side_effects.relation_suggestions`
- 逐条调用 `create_knowledge_relation()`，跳过已存在的关系
- 输出应用报告

**验收条件**：
- CLI 命令可执行
- 关系落库正确
- dry-run 不落库
- 重复关系不报错
- 全量 pytest 通过

## 设计边界

- **Agent 内部直接调 API（方案 B）**：不走 executor routing / fallback chain。Agent 自治管理 LLM 调用，失败时 fallback 到启发式。
- **LLM prompt 输出 JSON**：要求 LLM 返回结构化 JSON，便于程序化消费。解析失败视为 LLM 不可用，fallback 到启发式。
- **关系建议是 proposal**：Agent 产出的关系建议存在 `side_effects` 中，不直接写入 `knowledge_relations` 表。operator 通过 `swl knowledge apply-suggestions` 确认后才落库（P7 原则）。
- **成本追踪优先 API usage**：`_attach_estimated_usage()` 变为 fallback-only，有真实 usage 时不覆盖。

## 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| LLM API 不可用导致 Agent 功能退化 | 低 | fallback 到 Phase 53 启发式，无功能断裂 |
| LLM 返回非 JSON 或格式不符 | 中 | JSON 解析失败 → fallback 到启发式 |
| 关系建议质量低（hallucination） | 中 | operator gate 过滤；confidence 字段供参考 |
| HTTP executor usage 字段缺失（某些 API 不返回） | 低 | fallback 到 `len // 4` |
| 成本追踪改动影响现有 event truth | 低 | `_attach_estimated_usage` 仅在未填充时生效 |

**Phase 56 整体风险评级：中**

## 依赖与前置条件

- Phase 53 (v1.0.0)：LiteratureSpecialistAgent / QualityReviewerAgent 启发式实现
- Phase 55 (v1.1.0)：知识图谱 + `knowledge_relations` 表 + `create_knowledge_relation()`
- 环境变量：`SWL_API_BASE_URL` / `SWL_API_KEY` / `SWL_CHAT_MODEL`（Agent LLM 调用复用现有配置）
