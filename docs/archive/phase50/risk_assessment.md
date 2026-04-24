---
author: claude
phase: 50
slice: risk-assessment
status: draft
depends_on: ["docs/plans/phase50/design_decision.md"]
---

TL;DR: 三个 slice 均为中低风险。最高风险点是 S2 的 orchestrator 触发插入（跨模块，需确认 async 上下文）和 S1 的返回类型变更（可能破坏现有 eval 测试断言）。无高风险 slice（总分均 < 7）。

# Phase 50 Risk Assessment

## 风险矩阵

评分维度：影响范围（1=单文件 2=单模块 3=跨模块）× 可逆性（1=轻松回滚 2=需额外工作 3=难以回滚）× 依赖复杂度（1=无外部依赖 2=依赖内部模块 3=依赖外部系统）

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 风险等级 |
|-------|---------|--------|-----------|------|---------|
| S1: Meta-Optimizer 结构化提案 | 2 | 1 | 2 | **5** | 中 |
| S2: 一致性审计自动触发 | 3 | 2 | 2 | **7** | 中高（边界） |
| S3: 路由质量权重 | 2 | 1 | 2 | **5** | 中 |

---

## S1 风险详情（总分 5）

**主要风险：返回类型变更破坏现有测试**

`build_optimization_proposals()` 从返回 `list[str]` 改为 `list[OptimizationProposal]`，现有 `test_meta_optimizer.py` 中的断言需要同步更新。eval 测试（`test_eval_meta_optimizer_proposals.py`）可能依赖文本格式。

**缓解措施**：
- Codex 在修改前先运行 `pytest tests/test_meta_optimizer.py` 确认当前基线
- 同步更新所有断言，不保留旧接口
- `build_meta_optimizer_report()` 保持 markdown 输出格式不变，确保 artifact 向后兼容

**残余风险**：低。类型变更是局部的，回滚只需还原 `models.py` 和 `meta_optimizer.py`。

---

## S2 风险详情（总分 7，边界高风险）

**主要风险 1：orchestrator 触发插入引入 async 竞态**

在 `run_task_async()` 或 `AsyncSubtaskOrchestrator` 完成后插入 `asyncio.create_task()` 触发审计，如果 event loop 已关闭或任务已被 GC，fire-and-forget task 可能静默失败或产生 RuntimeWarning。

**缓解措施**：
- 使用 `asyncio.ensure_future()` 并在触发前检查 loop 状态
- 审计失败不影响主任务结果（已设计为 fire-and-forget）
- 添加 try/except 包裹触发调用，失败时只记录 warning

**主要风险 2：verdict 正则解析误判**

LLM 输出格式不固定，正则关键词匹配可能产生误判（false pass / false fail）。

**缓解措施**：
- 默认 `verdict = "inconclusive"`，只有明确匹配才设为 pass/fail
- verdict 仅写入 artifact，不影响任务 state 或路由决策
- 测试覆盖边界情况（空输出、混合关键词）

**主要风险 3：policy 文件不存在时的行为**

首次运行时 `.swl/audit_policy.json` 不存在，需要优雅降级（默认 `enabled=False`）。

**缓解措施**：policy 加载时文件不存在则使用默认值，不抛异常。

**建议**：S2 总分 7，建议 Codex 在实现后单独运行集成测试验证 async 触发路径，再进入 S3。

---

## S3 风险详情（总分 5）

**主要风险：`candidate_routes()` 排序改变现有路由行为**

加入 `quality_weight` 排序后，原本确定性的候选列表顺序可能改变，影响依赖特定顺序的测试。

**缓解措施**：
- 默认 `quality_weight = 1.0`，所有 route 权重相同时排序稳定（保持原有顺序）
- 只在多候选时排序，单候选路径不变
- 运行 `pytest tests/test_router.py` 确认无回归

**主要风险 2：`.swl/route_weights.json` 文件格式错误**

手动编辑或 apply 命令写入格式错误的 JSON，导致 RouteRegistry 初始化失败。

**缓解措施**：
- 加载时 try/except，格式错误则忽略权重文件并记录 warning
- `apply` 命令写入前验证 JSON 格式

**残余风险**：低。权重文件独立于 swallow.db，删除文件即可回滚到默认权重。

---

## Phase Guard 检查

对照 `kickoff.md` 的 goals 和 non-goals：

- ✓ S1/S2/S3 均在 kickoff goals 范围内
- ✓ 无自动路由切换（S3 的 apply 需人工执行）
- ✓ 无 Web UI 扩展
- ✓ 无 SQLite 主 schema 变更（route_weights.json 独立）
- ✓ Slice 数量 = 3，在 ≤5 限制内

**[IN-SCOPE]** 所有 slice 均在 phase scope 内。

## 建议执行顺序

1. **S1** — 无依赖，风险低，先做建立结构化基础
2. **S2** — 独立，但总分 7，建议单独验证 async 触发后再继续
3. **S3** — 依赖 S1 的 `OptimizationProposal`，S1 完成后可开始
