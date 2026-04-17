---
author: claude
phase: 35
slice: all
status: final
depends_on: [docs/plans/phase35/kickoff.md]
---

> **TL;DR**: Phase 35 实现质量良好，3 个 slice 均满足 kickoff 验收标准。0 BLOCK，2 CONCERN，1 NOTE。测试 249 passed。Phase 29 dialect concern 已消化。

# Phase 35 Review — Event Telemetry + Meta-Optimizer + Dialect Data Layer

## 审查范围

- **分支**: `feat/phase35-meta-optimizer`
- **Commits**: 4 (docs init + S1 telemetry + S2 meta-optimizer + S3 dialect data layer)
- **变更量**: +1680 / -291 lines, 20 files
- **测试结果**: 249 passed, 5 subtests, 6.06s

---

## Slice 完成矩阵

| Slice | Kickoff 标准 | 实际交付 | 状态 |
|-------|-------------|---------|------|
| S1: Event Telemetry | TelemetryFields dataclass；executor 事件注入 task_family/logical_model/physical_route/latency_ms/degraded/error_code | `TelemetryFields` + `build_telemetry_fields()` + `infer_task_family()`；harness.py executor 事件注入；orchestrator.py fallback 事件补齐 latency | **[PASS]** |
| S2: Meta-Optimizer | 只读事件扫描；route 成功率/故障指纹/degradation 趋势；CLI 入口 + markdown 提案产出 | `meta_optimizer.py` 306 行；`swl meta-optimize --last-n N`；`optimization_proposals.md` 全局 artifact；只读验证测试 | **[PASS]** |
| S3: Dialect Data Layer | 抽取公共数据收集层；4 个 dialect 改为消费共享层；Phase 29 concern 消化 | `dialect_data.py` 270 行 + `PromptData` 7 个子 dataclass；executor.py/claude_xml/codex_fim 统一消费；concerns_backlog Phase 29 标记 Resolved | **[PASS]** |

---

## 架构一致性审查

### S1: Event Telemetry

**[PASS] 设计一致性**
- `TelemetryFields` 使用 `slots=True` dataclass，字段与 `SELF_EVOLUTION_AND_MEMORY.md` 规划一致（除 token_cost 明确延后）
- `build_telemetry_fields()` 作为 helper 统一构建，harness.py 和 orchestrator.py 均调用同一入口
- `infer_task_family()` 基于 task_semantics 推断 task 分类，语义合理
- `ExecutorResult.latency_ms` 新增字段默认 0，向后兼容
- latency 测量使用 `time.perf_counter()`，精度合适

**[PASS] 回归安全**
- 遥测字段通过 dict merge (`|`) 注入 payload，不影响既有字段
- fallback 事件补齐 `latency_ms` + `previous_latency_ms`，与 Phase 34 事件结构兼容

### S2: Meta-Optimizer

**[PASS] 设计一致性**
- 严格只读：扫描 events.jsonl，不修改任何 state/event/config
- `RouteTelemetryStats` 提供 success_rate / failure_rate / fallback_rate / average_latency_ms，计算方法正确（除零保护完备）
- `FailureFingerprint` 按 failure_kind + error_code 分组聚类
- 提案生成基于阈值启发式（failure_rate > 0.5 → 建议路由审查等），合理的 MVP 策略
- CLI 入口 `swl meta-optimize` 集成干净，`--last-n` 参数控制扫描范围
- 产出写入 `.swl/meta_optimizer/optimization_proposals.md`，路径通过 paths.py helper

**[PASS] 架构对齐**
- 符合 AGENT_TAXONOMY_DESIGN §7.2 定义：specialist / read-only / workflow-optimization
- 不参与 runtime routing，不修改路由表，不自动采纳提案

### S3: Dialect Data Layer

**[PASS] 设计一致性**
- `collect_prompt_data()` 集中采集 task/route/semantics/knowledge/retrieval 数据
- 7 个子 dataclass（TaskPromptData / RoutePromptData / SemanticsPromptData / KnowledgePromptData / ReusedKnowledgePromptData / PriorRetrievalPromptData / PromptData）结构清晰
- `StructuredMarkdownDialect` 和 `build_executor_prompt()` 改为消费 `PromptData`，消除了信息收集重复
- `ClaudeXMLDialect` 和 `CodexFIMDialect` 同步改用 `collect_prompt_data()`
- executor.py 中 `normalize_executor_name` / `resolve_executor_name` 移至 dialect_data.py（因 prompt 数据层需要），import 路径更新正确

**[PASS] Phase 29 CONCERN 消化**
- concerns_backlog Phase 29 S3 "StructuredMarkdownDialect 与 build_executor_prompt() 信息收集重复" 已标记 Resolved
- 实际消化方式与 kickoff 设计一致

---

## 测试覆盖审查

| 文件 | 新增/修改测试 | 覆盖评价 |
|------|-------------|---------|
| test_meta_optimizer.py | 3 新增 | route health 聚合 + empty task + 只读验证，核心路径覆盖充分 |
| test_dialect_adapters.py | 2 新增 | shared prompt data 聚合 + structured markdown 消费路径 |
| test_binary_fallback.py | telemetry 断言扩展 | fallback 事件 latency_ms / degraded / logical_model 验证 |
| test_cli.py | telemetry payload + help 断言 | lifecycle 事件 telemetry 字段完整验证 |

**总体**: 249 passed，无 skip/xfail，新功能核心路径有覆盖。

---

## CONCERN

### C1: degraded 标志基于 route_reason 字符串匹配 [CONCERN]

**位置**: `src/swallow/harness.py:159`, `src/swallow/orchestrator.py:312`

```python
degraded="fallback route" in str(state.route_reason).lower()
```

判断 executor 是否处于降级状态，使用的是对 `route_reason` 字符串的子串匹配。如果未来 route_reason 措辞变化（或其他原因包含 "fallback route" 字样），会导致 degraded 标志误判。

**当前影响**: 低。route_reason 由 `_run_binary_fallback` 生成，措辞可控。
**建议**: 在 TaskState 或 RouteSpec 上增加显式 `is_fallback: bool` 字段，替代字符串启发式。记入 concerns_backlog，可在下一次触碰 telemetry 路径时消化。

### C2: Meta-Optimizer 事件类型字符串硬编码 [CONCERN]

**位置**: `src/swallow/meta_optimizer.py:125,147`

Meta-Optimizer 通过硬编码字符串 `"executor.completed"` / `"executor.failed"` / `"task.execution_fallback"` 匹配事件类型。如果 orchestrator/harness 中事件类型发生变更，meta_optimizer 不会编译报错，只会静默丢失数据。

**当前影响**: 低。事件类型自 Phase 31 以来稳定，schema freeze 是 Phase 35 前提条件。
**建议**: 抽取事件类型常量到 models.py（如 `EVENT_EXECUTOR_COMPLETED = "executor.completed"`），meta_optimizer 和 harness 共同引用。可作为后续 minor cleanup 消化。

---

## NOTE

### N1: meta-optimize CLI 功能测试覆盖较浅

`test_cli.py` 仅验证 `meta-optimize` 出现在 help 文本中，未测试 `main(["meta-optimize"])` 的实际执行路径。`test_meta_optimizer.py` 覆盖了核心逻辑，但 CLI 入口集成（argparse → run_meta_optimizer → stdout）缺少端到端断言。

非阻塞：核心逻辑已有独立测试，CLI 层非常薄（4 行代码）。

---

## 回归安全确认

- 249 tests passed, 0 skips, 0 xfails（较 Phase 34 的 244 新增 5 个测试）
- `dialect_data.py` 抽取后 executor.py 减少约 200 行，但 prompt 输出等价性通过既有测试验证
- `TelemetryFields` 通过 dict merge 注入 payload，不破坏既有事件消费者
- `meta_optimizer.py` 为纯新增模块，无回归面

---

## 结论

**Merge ready — 0 BLOCK, 2 CONCERN, 1 NOTE**

C1/C2 均为低优先级代码健壮性问题，不影响功能正确性。当前分支已吸收这两个 follow-up：

- C1 已通过 `TaskState.route_is_fallback` 显式字段替代 `route_reason` 字符串匹配
- C2 已通过 `models.py` 中的共享事件类型常量替代 `meta_optimizer.py` / `harness.py` / `orchestrator.py` 的事件类型硬编码

更新后结论保持不变：**Merge ready — 0 BLOCK, 2 CONCERN, 1 NOTE**
