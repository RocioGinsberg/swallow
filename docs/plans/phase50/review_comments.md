---
author: claude
phase: 50
slice: review
status: draft
depends_on:
  - docs/plans/phase50/design_decision.md
  - docs/plans/phase50/risk_assessment.md
---

TL;DR: 0 BLOCK / 2 CONCERN / 可以合并。实现与 design_decision 高度一致，406 tests passed。两个 CONCERN 均为可接受的设计取舍，不阻塞合并。

# Phase 50 PR Review

## 测试结果

`.venv/bin/python -m pytest --tb=short -q` → **406 passed, 8 deselected, 5 subtests passed**（全量通过，较 Phase 49 基线 395 tests 新增 11 个测试）

---

## S1: Meta-Optimizer 结构化提案

- [PASS] `OptimizationProposal` dataclass 结构与 design_decision 完全一致，`proposal_type / severity / route_name / description / suggested_action / suggested_weight` 字段齐全
- [PASS] `build_optimization_proposals()` 返回 `list[OptimizationProposal]`，原有启发式规则全部保留并结构化
- [PASS] workflow 类提案已实现：debate retry rate ≥ 30% 和 task_family 成本离群（≥ 2x 中位数）两个触发条件均落地
- [PASS] `TaskFamilyTelemetryStats` 新增 dataclass 正确追踪 debate retry 与成本，`total_attempt_count()` 逻辑清晰
- [PASS] `build_meta_optimizer_report()` 从结构化提案渲染，markdown 格式向后兼容
- [PASS] `extract_route_weight_proposals_from_report()` 正则解析 route_weight 提案，供 CLI apply 使用
- [PASS] eval 测试已更新，全量通过

**[CONCERN-1]** `extract_route_weight_proposals_from_report()` 从 markdown 文本反向解析 `route_weight` 提案，而不是直接消费 `list[OptimizationProposal]`。这意味着 CLI `apply` 命令依赖 `build_meta_optimizer_report()` 的文本格式稳定性——如果将来 report 格式变更，apply 会静默失败（正则不匹配，返回空列表）。

当前可接受：`apply` 命令的输入是 operator 手动指定的文件路径，失败时会抛出 `ValueError("No route_weight proposals found")`，不会静默损坏状态。但未来若需要程序化消费提案，应改为直接序列化 `list[OptimizationProposal]` 到 JSON artifact。

---

## S2: 一致性审计自动触发

- [PASS] `AuditTriggerPolicy` dataclass 与 design_decision 一致，`from_dict()` 有完善的类型强制转换和边界处理
- [PASS] `parse_consistency_audit_verdict()` 实现了 design 中的三级 verdict（pass/fail/inconclusive），优先精确匹配 `- verdict:` 行，fallback 到关键词扫描
- [PASS] `schedule_consistency_audit()` 使用 `threading.Thread(daemon=True)` 而非 `asyncio.create_task()`——这是正确的选择，因为触发点在同步的 `_maybe_schedule_consistency_audit()` 中，避免了 design 中预警的 event loop 竞态问题
- [PASS] `_maybe_schedule_consistency_audit()` 在 `run_task_async()` 的 `else` 分支（任务成功完成）后触发，不影响失败路径，符合 fire-and-forget 语义
- [PASS] `task.consistency_audit_scheduled` 事件记录了完整的触发上下文（trigger_reasons、policy 参数、observed 值），可追溯
- [PASS] `swl audit policy show/set` CLI 完整，`--auditor-route` 会验证 route 是否存在
- [PASS] `ConsistencyAuditResult.verdict` 字段在所有失败路径均正确设为 `"inconclusive"`

**[CONCERN-2]** `_FAIL_SIGNAL_PATTERNS` 包含 `\bfail(?:ed|ure)?\b`，这个模式会匹配 LLM 输出中描述"过去失败"的上下文句子（如 "the previous attempt failed but current state is consistent"），可能产生 false fail verdict。

当前可接受：verdict 仅写入 artifact，不影响任务 state 或路由决策，误判的代价低。`- verdict:` 精确匹配优先级高于关键词扫描，如果 LLM 输出包含结构化 verdict 行则不走关键词路径。建议后续 phase 在 audit prompt 中明确要求 LLM 输出 `- verdict: pass/fail/inconclusive` 行，减少对关键词扫描的依赖。

---

## S3: 路由质量权重

- [PASS] `RouteSpec.quality_weight: float = 1.0` 字段位置正确，默认值保证向后兼容
- [PASS] `_sort_routes_by_quality()` 在 `candidate_routes()` 的所有多候选返回路径均已插入排序，单候选路径不受影响
- [PASS] `build_detached_route()` 正确传递 `quality_weight`，detached route 不会丢失权重
- [PASS] `load_route_weights()` / `save_route_weights()` 有完善的错误处理（文件不存在、JSON 格式错误均优雅降级）
- [PASS] `apply_route_weights()` 在 `create_task()`、`acknowledge_task()`、`run_task_async()`、`main()` 四个入口均已调用，覆盖完整
- [PASS] `swl route weights show/apply` CLI 完整，apply 会验证 route 存在性，只持久化非默认权重（`abs(weight - 1.0) > 1e-9`）
- [PASS] `route_weights.json` 路径通过 `paths.py` 统一管理，与 `audit_policy.json` 一致

---

## 架构一致性检查

- [PASS] 三个模块均保持只读/operator-confirmed 原则：Meta-Optimizer 不直接修改路由状态，audit 触发不影响任务 state，权重变更需 CLI apply 确认
- [PASS] 无 SQLite 主 schema 变更，`route_weights.json` 和 `audit_policy.json` 独立于 `swallow.db`
- [PASS] 无新的 LLM 调用引入（verdict 解析用正则，权重提案用启发式规则）
- [PASS] 与 `ARCHITECTURE.md` 的 Truth Layer / Retrieval Layer 分层无冲突，本 phase 改动在 Policy / Routing 层

## Phase Scope 检查

- [PASS] 无 Web UI 扩展
- [PASS] 无自动路由切换（apply 需人工执行）
- [PASS] 无跨任务并发审计
- [PASS] 3 个 slice，在 ≤5 限制内

---

## 结论

**0 BLOCK / 2 CONCERN / 可以合并**

两个 CONCERN 均为已知设计取舍，不阻塞合并：
- CONCERN-1（apply 依赖文本格式）：operator 工具，失败有明确报错，不损坏状态
- CONCERN-2（verdict 关键词误判）：verdict 不影响任务 state，误判代价低

建议 CONCERN-1 和 CONCERN-2 登记 backlog，在后续 phase 中自然消化。
