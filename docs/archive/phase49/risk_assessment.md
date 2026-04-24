---
author: claude
phase: 49
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase49/kickoff.md
  - docs/plans/phase49/design_decision.md
---

## TL;DR
Phase 49 全部四个 slice 均达到高风险边界（总分 ≥ 6），其中 S2/S3/S4 总分为 7，需要人工 gate。最大风险集中在 sqlite-vec 外部二进制依赖（S4）和 LibrarianAgent 写入权限边界（S3）。

# Risk Assessment: Phase 49 - 知识真值归一与向量 RAG

## 风险矩阵

| Slice | 名称 | 影响范围 (1-3) | 可逆性 (1-3) | 依赖复杂度 (1-3) | 总分 | 风险等级 |
|-------|------|--------------|------------|----------------|------|----------|
| S1 | Knowledge SQLite Schema & Store Extension | 2 | 2 | 2 | **6** | 中 |
| S2 | Knowledge Migration Tool | 3 | 2 | 2 | **7** | **高** |
| S3 | Librarian Agent Entity | 3 | 2 | 2 | **7** | **高** |
| S4 | sqlite-vec RAG Pipeline | 2 | 2 | 3 | **7** | **高** |

> 评分标准：影响范围 1=单文件 2=单模块 3=跨模块；可逆性 1=轻松回滚 2=需要额外工作 3=难以回滚；依赖复杂度 1=无外部依赖 2=依赖内部模块 3=依赖外部系统。总分 ≥7 为高风险。

---

## 逐 Slice 风险详析

### S1: Knowledge SQLite Schema & Store Extension（总分 6，中风险）

**主要风险**：Schema 设计不当导致后续 S4 向量存储需要再次重构。

**缓解策略**：
- Schema 设计时预留 `embedding_blob` 列（nullable），避免 S4 再次 ALTER TABLE
- 在 `models.py` 中明确 `Evidence` 类定义（当前探索发现可能缺失），确保与 `KnowledgeObject` / `WikiEntry` 的继承关系清晰
- 新增 pytest 覆盖 Schema 边界（空值、重复 ID、事务回滚）

---

### S2: Knowledge Migration Tool（总分 7，高风险）

**主要风险**：
1. **数据丢失**：文件系统知识对象格式不一致，迁移时解析失败导致静默跳过
2. **幂等性失效**：重复迁移产生重复数据，污染 SQLite 知识库
3. **迁移中断**：大量知识对象迁移时进程中断，导致部分迁移状态

**缓解策略**：
- `--dry-run` 模式必须先于实际迁移验证，输出解析失败的对象列表
- 幂等检查基于知识对象的唯一 ID（而非内容 hash），避免重复写入
- 迁移进度写入 SQLite 迁移状态表，支持断点续传
- 迁移完成后 `swl doctor` 输出知识层健康检查，包含迁移对象数量对比

**人工 gate 要求**：迁移工具实现后，Human 应先在测试环境执行 `--dry-run`，确认输出无误后再执行实际迁移。

---

### S3: Librarian Agent Entity（总分 7，高风险）

**主要风险**：
1. **写入权限溢出**：`LibrarianAgent` 写入边界失控，导致知识库被污染或覆盖
2. **接口兼容性破坏**：升级 `LibrarianExecutor` 时改变了 orchestrator 的触发接口，导致现有任务链路中断
3. **冲突检测误判**：冲突检测逻辑过于激进，将合法的知识更新误判为冲突并拒绝写入

**缓解策略**：
- 写入边界通过 `canonical_write_guard` 机制强制执行（复用 Phase 48 已有的 guard 模式）
- `LibrarianAgent` 保持与 `LibrarianExecutor` 相同的外部触发接口，升级为内部实现变更
- 冲突检测基于显式规则（ID 重复、内容 hash 相同），不做语义级冲突判断（语义冲突留给 Phase 50）
- 新增 pytest 覆盖写入边界拒绝场景（非 LibrarianAgent 路径写入应抛出明确异常）

**人工 gate 要求**：S3 实现后，Human 应验证现有任务链路（`swl run` / `swl review`）不受影响。

---

### S4: sqlite-vec RAG Pipeline（总分 7，高风险）

**主要风险**：
1. **二进制依赖失败**：`sqlite-vec` 在目标环境无法加载（平台不兼容、缺少 .so 文件），导致整个检索模块崩溃
2. **降级机制失效**：降级逻辑存在 bug，`sqlite-vec` 不可用时仍尝试调用向量接口并抛出异常
3. **向量质量不达标**：本地 embedding 方案（TF-IDF 或轻量模型）向量质量过低，RAG 结果无实际价值
4. **索引构建性能**：大量知识对象的向量索引构建时间过长，阻塞主任务链路

**缓解策略**：
- `sqlite-vec` 作为可选依赖（`extras_require["vec"]`），import 失败时捕获 `ImportError` 并记录 WARN 日志，自动切换到 `TextFallbackAdapter`
- 降级路径在 pytest 中通过 mock `sqlite_vec` 模块为 `None` 强制触发，确保降级逻辑被测试覆盖
- 向量化方案优先选择无外部 API 依赖的本地方案（如 `sentence-transformers` 轻量模型或 TF-IDF），并在 eval 测试中验证质量基线（precision ≥ 0.7 / recall ≥ 0.6）
- 向量索引构建异步化，不阻塞主任务链路；索引构建失败时降级到文本匹配，不中断任务执行

**人工 gate 要求**：S4 实现后，Human 应在无 `sqlite-vec` 环境下验证降级路径正常工作。

---

## 全局风险汇总

| 风险类别 | 影响 Slice | 严重程度 | 缓解状态 |
|----------|-----------|---------|---------|
| 数据迁移完整性 | S2 | 高 | 通过 dry-run + 幂等检查缓解 |
| 写入权限边界失控 | S3 | 高 | 通过 canonical_write_guard 缓解 |
| 外部二进制依赖 | S4 | 高 | 通过可选依赖 + 强制降级缓解 |
| Schema 设计不前瞻 | S1 | 中 | 通过预留 embedding_blob 列缓解 |
| 接口兼容性破坏 | S3 | 中 | 通过保持外部接口不变缓解 |
| 向量质量不达标 | S4 | 中 | 通过 eval 测试质量基线缓解 |

---

## Phase 级风险结论

Phase 49 整体风险等级为**高**，主要来源于三个方向：知识数据迁移的完整性、LibrarianAgent 写入权限的边界控制、sqlite-vec 外部二进制依赖的环境鲁棒性。三个方向均有明确的缓解策略，但均需要人工 gate 验证。

建议执行顺序：S1 → (S2 ‖ S3) → S4，每个 slice 完成后由 Human 执行验证再推进下一个。
