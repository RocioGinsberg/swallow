---
author: claude
phase: 55
slice: risk_assessment
status: draft
depends_on:
  - docs/plans/phase55/kickoff.md
  - docs/plans/phase55/design_decision.md
---

## TL;DR

Phase 55 风险集中在检索管线改造（S3）——`retrieve_context()` 是核心路径，插入 Relation Expansion 需要确保不破坏现有检索行为。其余 slice 风险低。整体风险评级：**中**，TDD 先行是主要缓解手段。

---

## 风险矩阵

| ID | 风险 | 概率 | 影响 | 等级 | 消化时机 |
|----|------|-----|-----|------|---------|
| R1 | Relation Expansion 改动 `retrieve_context()` 破坏现有检索行为 | 中 | 高 | **中** | S3 实施时 |
| R2 | `knowledge_relations` 表 schema 不够用，后续需要 ALTER TABLE | 低 | 中 | **低** | S2 实施时 |
| R3 | 本地文件 markdown 分段策略对非标准 markdown 效果差 | 低 | 低 | **低** | S1 实施时 |
| R4 | object_id 跨表引用无 FK 约束，孤儿关系累积 | 低 | 低 | **低** | S2 实施时 |
| R5 | Relation Expansion 在大图谱上性能退化 | 极低 | 中 | **低** | S3 实施时 |

---

## 中风险详解

### R1 — Relation Expansion 改动 `retrieve_context()` 破坏现有检索行为

**描述**：`retrieve_context()` 是任务执行的核心检索入口，被 `run_task()` / `run_task_async()` 调用。S3 在其中插入 Relation Expansion 阶段，如果实现有误（如 score 计算错误、重复项、异常未捕获），会影响所有任务的检索质量。

**触发场景**：
- Relation Expansion 抛出异常 → `retrieve_context()` 整体失败
- 扩展结果的 score 过高 → 挤掉直接命中的高质量结果
- 扩展结果与 seed 重复 → 结果列表膨胀

**缓解**：
- TDD 先行：S3 的测试覆盖正常路径、空关系、深度限制、去重、score 衰减
- Relation Expansion 作为 **additive** 操作：不修改 seed items 的 score，只追加新 items
- 异常隔离：`expand_by_relations()` 内部 try-except，失败时返回空列表（降级为无扩展），不阻塞检索
- 无关系时退化为 no-op：如果 `knowledge_relations` 表为空，`expand_by_relations()` 立即返回空列表，零开销
- 全量 pytest 回归：现有 452 个测试覆盖检索路径

**残留风险**：低。TDD + 异常隔离 + 全量回归三重保护。

---

## 低风险详解

### R2 — schema 不够用

**缓解**：最小 schema（7 列），后续可通过 `ALTER TABLE ADD COLUMN` 扩展。不做过度设计。

### R3 — markdown 分段策略

**缓解**：按 `#` heading 分段是成熟模式，与 `retrieval_adapters.py` 的 `build_markdown_chunks()` 一致。非标准 markdown（无 heading）退化为单段，不丢失内容。

### R4 — 孤儿关系

**缓解**：应用层在创建关系时验证 object_id 存在性。后续可加 `swl knowledge doctor` 清理孤儿关系。

### R5 — 大图谱性能

**缓解**：深度限制默认 2（最多 2 跳），置信度阈值 0.3，本地知识库规模有限（百到千级对象）。BFS 在此规模下为毫秒级。

---

## 回归风险监控

| 区域 | 监控指标 | 回归信号 |
|------|---------|---------|
| 检索管线 | `retrieve_context()` 返回结果 | 现有测试中检索结果数量或 score 变化 |
| 知识存储 | `knowledge_evidence` / `knowledge_wiki` 读写 | 新表 DDL 影响现有表 |
| CLI | `swl ingest` / `swl knowledge` 命令 | 新命令与现有命令冲突 |
| 全量回归 | `pytest --tb=short` | 任何 failure |

---

## 风险吸收判断

**可以接受的风险**：
- R1：TDD + 异常隔离 + 全量回归
- R2：最小 schema + ALTER TABLE 可扩展
- R3：成熟分段模式
- R4：应用层验证
- R5：深度限制 + 规模有限

**Phase 55 整体风险评级：中**

- 1 个中风险（检索管线改造），缓解措施充分
- 4 个低风险，均可接受
- TDD 先行是核心风险控制手段
- 工作量约 40h，与 Phase 53 相当
