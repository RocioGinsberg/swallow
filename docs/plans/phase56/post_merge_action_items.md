---
author: claude
phase: 56
slice: post_merge_action_items
status: draft
---

## TL;DR

Phase 56 merge 后的操作清单：真实数据验证 → 观察结论 → 决定 Phase 57 方向。

# Phase 56 Post-Merge Action Items

## 1. Merge & Tag

- [ ] 合并 Phase 56 到 main
- [ ] 打 tag `v1.2.0`
- [ ] 更新 `docs/roadmap.md`：Phase 56 标记 ✅ Done

## 2. 环境确认

- [ ] 确认 `SWL_API_KEY` 已配置
- [ ] 确认 API provider 是否支持 `/v1/embeddings`：
  ```bash
curl "$SWL_API_BASE_URL/v1/embeddings" \
  -H "Authorization: Bearer $SWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "text-embedding-v1", "input": "test"}'
  ```
- [ ] 如果支持 embedding API，记录模型名和维度，后续可替换 `build_local_embedding()` 的 64-dim hash 投影

## 3. 真实数据验证（LLM 增强 Agent）

用设计文档跑一轮完整的 LLM 增强知识闭环：

```bash
# 3.1 摄入
swl knowledge ingest-file docs/design/KNOWLEDGE.md
swl knowledge ingest-file docs/design/AGENT_TAXONOMY.md
swl knowledge ingest-file docs/design/ARCHITECTURE.md

# 3.2 Promote（挑 2-3 个有价值的 candidate）
swl knowledge stage-list
swl knowledge stage-promote <candidate_id>

# 3.3 创建 literature-specialist 任务（LLM 增强）
swl task create --title "Analyze knowledge architecture" \
  --goal "Deep analysis of KNOWLEDGE.md and AGENT_TAXONOMY.md" \
  --workspace-root . --executor literature-specialist
swl task run <task_id> --executor-name literature-specialist

# 3.4 检查 LLM 分析结果
swl task inspect <task_id>
# 确认：analysis_method 是 "llm" 还是 "heuristic"？
# 确认：relation_suggestions 是否合理？有没有 hallucination？

# 3.5 应用关系建议
swl knowledge apply-suggestions --task-id <task_id> --dry-run
# 觉得合理就去掉 --dry-run

# 3.6 创建普通任务，验证检索整合
swl task create --title "Summarize agent taxonomy" \
  --goal "Explain the relationship between knowledge truth and agent roles" \
  --workspace-root .
swl task run <task_id>
# 检查 .swl/tasks/<task_id>/retrieval.json：
#   - canonical knowledge 是否排在前面（KNOWLEDGE_PRIORITY_BONUS 效果）
#   - expansion_source=relation 是否出现
#   - 检索结果是否比 Phase 55 更有用
```

## 4. 观察记录

跑完后记录以下观察项（用于决定 Phase 57 方向）：

| 观察维度 | 要关注什么 | 结论模板 |
|---------|----------|---------|
| **LLM 分析质量** | relation_suggestions 是否合理、是否有 hallucination、confidence 是否有参考价值 | "LLM 建议 X 条关系，其中 Y 条合理" |
| **检索排序** | canonical knowledge 是否排在 repo 文件前面、KNOWLEDGE_PRIORITY_BONUS=50 够不够 | "canonical 排名第 N，repo 文件排名第 M" |
| **召回覆盖度** | relation expansion 是否补充了直接检索漏掉的有价值知识 | "expansion 补充了 X 条，其中 Y 条有用" |
| **Chunking 粒度** | heading 分段是否合理，有没有太粗或太细 | "## 级别合适 / 需要按 ### 再分" |
| **成本追踪** | `swl task inspect` 中 estimated_input_tokens / estimated_output_tokens 是否来自 API（不是 len//4） | "HTTP 路径：API usage / Agent 路径：API usage" |

建议在执行前显式导出当前测试模型：

```bash
export SWL_CHAT_MODEL="gpt-4o-mini"
```

## 5. Phase 57 方向决策

基于观察结论，从以下方向中选择：

| 条件 | 推荐方向 |
|------|---------|
| 检索排序差、该找到的排不上来 | **检索增强**：rerank + hybrid search + embedding 升级 |
| LLM 分析好但任务拆分不好 | **编排增强**：Planner 显式化 + DAG |
| 检索和分析都够用，路由不够精准 | **能力画像**：遥测驱动 capability profiles |
| chunking 粒度不对 | 先调 chunking 策略，不需要一个完整 phase |

## 6. 遗留改进项（非阻塞，可随时做）

| 改进 | 来源 | 优先级 |
|------|------|--------|
| 降级链路配置化（route fallback → YAML） | Phase 56 讨论 | Phase 57 方向 |
| `resolve_knowledge_object_id()` 已提取到 `canonical_registry.py` | Phase 55 follow-up | ✅ 已完成 |
| `KNOWLEDGE_PRIORITY_BONUS` 已移入 `retrieval_config.py` | Phase 55 follow-up | ✅ 已完成 |
