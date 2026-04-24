---
author: claude
phase: 53
slice: risk_assessment
status: draft
depends_on:
  - docs/plans/phase53/kickoff.md
  - docs/plans/phase53/design_decision.md
  - docs/plans/phase53/context_brief.md
---

## TL;DR

Phase 53 的核心风险集中在两处：(1) Literature Specialist / Quality Reviewer 无现有实现，输入/输出契约可能在实装后发现不够用，需要迭代；(2) `resolve_executor` 从 if-chain 迁移到注册表时，现有 librarian / meta-optimizer 的延迟 import 路径可能被意外破坏。其余风险均为低等级，可通过测试覆盖缓解。整体风险评级：**低-中**，工作量约 52h，复用度高。

---

## 风险矩阵（概率 × 影响）

| ID | 风险 | 概率 | 影响 | 等级 | 消化时机 |
|----|------|-----|-----|------|---------|
| R1 | Literature Specialist 启发式实现不够用，输出质量低 | 中 | 中 | **中** | S2 实施时 |
| R2 | Quality Reviewer 与 Validator 职责边界在实践中模糊 | 中 | 中 | **中** | S2 实施时 |
| R3 | `resolve_executor` 注册表迁移破坏现有 Agent 延迟 import | 中 | 高 | **中** | S3 实施时 |
| R4 | ConsistencyReviewerAgent 与 fire-and-forget 路径的输入格式不一致 | 低 | 中 | **低** | S1 实施时 |
| R5 | 5 个新 Agent 文件增加 import 图复杂度 | 低 | 低 | **低** | S1/S2 实施时 |
| R6 | C1 消化不彻底（文档注释不够清晰） | 低 | 低 | **低** | S3 review 时 |
| R7 | 新 Agent 的 taxonomy profile 常量与 AGENT_TAXONOMY.md 不一致 | 低 | 中 | **低** | S1/S2 实施时 |

---

## 中风险详解

### R1 — Literature Specialist 启发式实现不够用

**描述**：Phase 53 的 Literature Specialist 基于正则提取标题 + 词频统计 + 交叉比较。对于非 markdown 文件（PDF、纯文本无标题）、非英文内容、或需要语义理解的场景，启发式输出可能无实际价值。

**触发场景**：
- 输入文档为纯文本无标题结构 → 标题提取返回空
- 输入文档为中文 → 英文 stop words 过滤无效，词频结果噪声大
- operator 期望语义级别的"关键概念提取" → 启发式只能给词频

**缓解**：
- 明确 Phase 53 是"最小可行实现"，输出格式稳定但内容质量有限
- 对无标题文档：fallback 到按段落分割 + 前 N 行摘要
- 对中文内容：词频统计按字符 bigram 或空格分词（粗糙但可用）
- 在 `ExecutorResult.output` 中标注 `analysis_method: heuristic`，后续 LLM 增强时切换为 `analysis_method: llm`
- 验收标准：输出格式正确 + 非空 + 可被 Review Gate 消费，不要求语义准确性

**残留风险**：operator 可能对启发式输出质量不满意。通过文档说明"Phase 53 为最小实现，LLM 增强留待后续"管理预期。

---

### R2 — Quality Reviewer 与 Validator 职责边界模糊

**描述**：两者都做"校验"，在实践中 operator 可能不清楚何时用 Validator、何时用 Quality Reviewer。特别是当 Quality Reviewer 的 `non_empty` criterion 与 Validator 的 `artifacts.missing` 检查重叠时。

**触发场景**：
- operator 对同一 artifact 同时触发 Validator 和 Quality Reviewer → 重复检查
- Quality Reviewer 的 `non_empty` 报 pass，但 Validator 的 `artifacts.missing` 报 fail（因为 Validator 检查的是另一组 artifact）→ 结果看似矛盾

**缓解**：
- 在 CLI help 和文档中明确分工：
  - `swl validate` → Validator → "task 级 artifact 完整性检查"
  - `swl quality-review` → Quality Reviewer → "单个 artifact 内容质量检查"
- Quality Reviewer 的 `non_empty` criterion 检查的是 `artifact_ref` 指向的单个文件，Validator 检查的是 task 级 artifact 集合——输入不同，不会矛盾
- 单元测试覆盖两者对同一 task 的输出，验证不矛盾

**残留风险**：低。正交分工在代码层面清晰，operator 理解成本通过文档管理。

---

### R3 — `resolve_executor` 注册表迁移破坏现有 Agent

**描述**：当前 `resolve_executor` 的 librarian / meta-optimizer 分支使用 `raw_name` 和 `normalized_type` 双重匹配。迁移到注册表时，如果 key 不覆盖所有变体（如 `meta-optimizer` vs `meta_optimizer`），会导致现有 Agent 无法解析。

**触发场景**：
- 注册表只注册 `"meta-optimizer"` 但遗漏 `"meta_optimizer"` → 下划线变体的 TaskState 无法解析
- 注册表查找逻辑从 `raw_name` 改为 `normalized_name` → 大小写或空格处理差异

**缓解**：
- 注册表同时注册所有已知变体（`"meta-optimizer"` + `"meta_optimizer"`）
- 迁移后保留 `resolve_executor` 的 fallback 逻辑（mock / http / CLI agent 仍走 if-chain）
- 回归测试：`test_executor_protocol.py` 的参数化用例覆盖所有 Agent 名称变体
- 分步提交：先引入注册表 + 注册现有 2 个 Agent（commit 1），验证绿灯后再注册新 Agent（commit 2-6）

**残留风险**：低。注册表是纯加法变更，fallback 路径保留。

---

## 低风险

### R4 — ConsistencyReviewerAgent 与 fire-and-forget 路径输入格式不一致

**描述**：Agent 的 `execute()` 接收 `TaskCard.input_context`，fire-and-forget 路径接收 `(base_dir, task_id, auditor_route, sample_artifact_path)`。两者输入格式不同，但底层都调用 `run_consistency_audit()`。

**缓解**：Agent 的 `execute()` 从 `card.input_context` 提取参数后调用同一函数，格式转换在 Agent 内部完成。两条路径的输入差异是预期的（Agent 是结构化入口，fire-and-forget 是内部调度）。

### R5 — 5 个新 Agent 文件增加 import 图复杂度

**描述**：新增 5 个 `.py` 文件，每个有独立的 import 依赖。

**缓解**：延迟 import（`resolve_executor` 中按需加载），与现有 librarian / meta-optimizer 模式一致。启动时间不受影响。

### R6 — C1 消化不彻底

**描述**：文档注释可能不够清晰，reviewer 可能认为消化不到位。

**缓解**：design_decision 已给出具体的注释文本和 taxonomy 表格补充内容，review 时重点检查。

### R7 — taxonomy profile 常量与蓝图不一致

**描述**：新 Agent 的 `system_role` / `memory_authority` 常量可能与 `AGENT_TAXONOMY.md §7.3` 定义不一致（如 Quality Reviewer 误用 `"specialist"` 而非 `"validator"`）。

**缓解**：每个 Agent 的单元测试显式断言 `agent.system_role` 和 `agent.memory_authority` 与蓝图定义一致。

---

## 回归风险监控

| 区域 | 监控指标 | 回归信号 |
|------|---------|---------|
| Executor resolver | `test_executor_protocol.py` 全套 | 新 Agent 名称无法解析 |
| Ingestion pipeline | `tests/test_ingestion*.py` | Agent 包装破坏原函数行为 |
| Consistency audit | `tests/test_consistency_audit.py` | Agent 化影响 fire-and-forget 路径 |
| Validator | `tests/test_validator*.py` 或 orchestrator 集成测试 | Agent 包装破坏原函数行为 |
| 端到端 | 全量 pytest | >5 个 failure → 注册表迁移问题 |

---

## 风险吸收判断

**可以接受的风险**：
- R1（启发式质量）：Phase 53 明确为最小实现，LLM 增强留后续
- R5（import 复杂度）：延迟 import 已验证
- R6（C1 消化深度）：review 时检查
- R7（taxonomy 常量）：单元测试断言

**必须在实施前确认的事项**：
- R3：注册表迁移的 key 覆盖范围——需在 S3 启动前列出所有 Agent 名称变体

**Phase 53 整体风险评级：低-中**

- 无高风险项
- 3 个包装型 Agent 复用度极高，风险集中在 2 个新建 Agent
- 工作量较 Phase 52 小（52h vs 62h）
- 可 staged rollout（S1 → S2 → S3），每步独立可 revert
