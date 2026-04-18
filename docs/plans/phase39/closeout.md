---
author: codex
phase: 39
slice: ingestion-specialist
status: final
depends_on:
  - docs/plans/phase39/kickoff.md
  - docs/plans/phase39/risk_assessment.md
  - docs/plans/phase39/review_comments.md
---

> **TL;DR** Phase 39 已完成 3 个 slice：外部会话格式解析、规则式降噪提纯、端到端 ingestion pipeline + `swl ingest` CLI。review 唯一 concern（Open WebUI 空数组误判）已吸收，ingestion 专项测试 22 passed。

# Phase 39 Closeout

## 完成情况

- S1 `Ingestion Parser`：已完成。支持 ChatGPT JSON、Claude Web JSON、Open WebUI JSON、Markdown 四种输入格式，并统一输出 `ConversationTurn`。
- S2 `Ingestion Filter`：已完成。支持连续消息合并、短闲聊过滤、关键词/列表/代码块信号保留与归一化去重。
- S3 `Ingestion Pipeline + CLI`：已完成。支持 parse → filter → `StagedCandidate` 持久化链路，并新增顶层 `swl ingest` 命令，支持 `--format` 与 `--dry-run`。

## Review Follow-up

- C1 `_is_open_webui_export` 对裸空 list 检测过宽：已修复。现在仅在 payload 为非空 list 时才识别为 Open WebUI 裸消息数组，避免把 `[]` 误判为 Open WebUI 导出。
- 对应回归已补入 `tests/test_ingestion_parsers.py::test_detect_ingestion_format_rejects_empty_json_array`。

## 验证

- Ingestion 专项回归：`.venv/bin/python -m pytest tests/test_ingestion_parsers.py tests/test_ingestion_filters.py tests/test_ingestion_pipeline.py`
- 结果：`22 passed`

## 边界确认

- 未引入实时同步、自动晋升、LLM 降噪、PDF/HTML 解析、HandoffContract 自动生成或 Web 控制中心扩张。
- Ingestion 产出仍统一进入 `pending` staged knowledge，由既有 Librarian 审查路径接管后续晋升。

## 合并建议

- 当前实现与 Phase 39 kickoff 边界一致，review follow-up 已吸收，可进入人工提交、push、PR 同步与 merge 决策。
