---
author: claude
phase: 57
slice: risk-assessment
status: draft
depends_on:
  - docs/plans/phase57/design_decision.md
---

## TL;DR

Phase 57 总体风险可控。唯一中风险 slice 是 S1（Neural Embedding），因为引入外部 API 依赖；但 graceful degradation 设计使其可逆性保持在最高级。其余 slice 均为低风险。最大系统性风险是 embedding API 可用性对检索主链路的影响。

# Phase 57 Risk Assessment

## 风险矩阵总览

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 风险级别 |
|-------|---------|--------|-----------|------|---------|
| S1: Neural Embedding | 2 | 1 | 3 | **6** | 中 |
| S2: LLM Rerank | 1 | 1 | 2 | **4** | 低 |
| S3: Chunking 优化 | 1 | 1 | 1 | **3** | 低 |
| S4: Specialist CLI | 1 | 1 | 1 | **3** | 低 |

所有 slice 总分 < 7，无高风险 slice。无需额外拆分或增加人工 gate。

## S1: Neural Embedding — 详细风险分析

### R1.1 Embedding API 可用性引入网络依赖

**风险**：当前 `VectorRetrievalAdapter` 是纯本地路径。引入 API embedding 后，检索主链路将依赖网络连通性。

**缓解**：
- graceful degradation: API 不可用时 fallback 到 `build_local_embedding()`
- fallback 路径与当前行为完全一致，不引入新的失败模式
- `swl doctor` 新增 embedding API 探针，提前暴露配置问题

**残余风险**：fallback 触发时检索质量退回到 blake2b 级别，但不会比 Phase 56 差。

### R1.2 sqlite-vec 维度迁移

**风险**：64 维向量和 1536 维向量不能混存于同一 virtual table。维度变化需要重建索引。

**缓解**：
- 向量索引是辅助召回结构，不是 truth。重建不丢失任何知识真值数据
- 策略：检测维度不匹配时自动 drop + recreate vector table
- 首次 API embedding 写入时触发重建，不需要显式迁移命令

**残余风险**：首次重建时有一次性延迟；旧 local embedding 的已 index 向量全部失效（预期行为）。

### R1.3 Embedding 模型名硬编码

**风险**：如果写死 `text-embedding-3-small` 而不走 `runtime_config.py`，后续切换模型困难。

**缓解**：
- 设计要求通过 `SWL_EMBEDDING_MODEL` 环境变量配置
- 默认值在 `runtime_config.py` 统一管理
- pre-kickoff 已验证 `text-embedding-3-small` 在当前 provider 可用

### R1.4 `iter_canonical_reuse_items` 路径对齐

**风险**：将 canonical reuse 路径从 term-frequency-only 改为 vector 路径，可能改变已有 canonical 对象的 retrieval 排序。

**缓解**：
- 这是修正既有行为不一致，不是功能退化
- canonical 对象已有 `KNOWLEDGE_PRIORITY_BONUS = 50` 加持
- 测试覆盖将验证 canonical 对象在 vector 路径下仍被优先召回

## S2: LLM Rerank — 详细风险分析

### R2.1 Rerank 调用增加延迟和成本

**风险**：每次 `retrieve_context()` 多一次 LLM 调用。

**缓解**：
- rerank 只对 top-N（10-15 条）做，token 用量有限
- `RERANK_ENABLED` 开关可关闭
- 复用 `call_agent_llm()`，无新增 API 依赖
- 使用 `gpt-4o-mini` 等成本低廉模型

**残余风险**：p99 延迟增加 1-3 秒（可接受）。

### R2.2 LLM 输出不可解析

**风险**：LLM 返回的排序结果格式不稳定。

**缓解**：
- 格式解析失败时 fallback 到原始排序
- prompt 明确要求 JSON 格式的 index 列表
- 不需要 100% 解析成功率，失败只是退回到无 rerank 状态

## S3: Chunking 优化 — 详细风险分析

### R3.1 Score 分布变化

**风险**：overlap 改变 chunk 边界，影响已有知识对象的 retrieval score。

**缓解**：
- canonical 对象的 text 字段不变（来自 knowledge truth layer）
- score 变化方向是正面的（overlap 减少边界信息丢失）
- 参数化设计（`overlap_lines`、`max_chunk_size`）可调至 0 回滚

### R3.2 性能影响

**风险**：overlap 增加 chunk 数量，检索时间可能增加。

**缓解**：
- overlap 2-3 行，chunk 数量增加有限
- max_chunk_size 限制反而可能减少超长 chunk 的 scoring 成本

## S4: Specialist CLI — 无风险

新增 CLI 参数，不影响已有行为。最低风险 slice。

## 系统性风险评估

### 网络依赖扩散

Phase 57 后，检索主链路将有两个可选网络调用点（embedding + rerank）。所有网络调用都有本地 fallback，但连续触发 fallback 时用户体验退化明显。

**建议**：`swl doctor` 应在一个检查项中同时验证 chat / embedding API 连通性，给出整体健康状态。

### 向后兼容性

Phase 57 不改变任何公共 API / CLI 语义（S4 仅新增参数），不破坏已有 knowledge truth 数据，不改变 state / event / artifact 结构。不需要显式迁移步骤。

## 结论

Phase 57 风险可控，所有 slice 总分 < 7。主要风险点（API 可用性）已通过 graceful degradation 充分缓解。建议按设计顺序实施，无需增加额外人工 gate。
