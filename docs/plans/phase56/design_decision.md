---
author: claude
phase: 56
slice: design
status: draft
depends_on:
  - docs/plans/phase56/kickoff.md
  - src/swallow/literature_specialist.py
  - src/swallow/quality_reviewer.py
  - src/swallow/executor.py
---

## TL;DR

Phase 56 有 4 个核心设计决策：(1) Agent 内部 LLM 调用通过共享 helper 统一管理（endpoint / key / timeout / usage 提取），不经过 executor routing；(2) LLM 失败时 fallback 到现有启发式，Agent 始终返回有效 result；(3) 关系建议存在 `side_effects` 中，通过 CLI 命令确认后落库；(4) 成本追踪改为"API usage 优先，`len // 4` fallback"。

---

## 核心设计决策

### 决策 1：Agent LLM 调用方式

**问题**：LiteratureSpecialist 和 QualityReviewer 如何调用 LLM？

**候选方案**：
- A. 通过 orchestrator 派发（走 executor routing + fallback chain）
- B. Agent 内部直接调 API（httpx.post）
- C. 新建一个 AgentLLMClient 中间层

**选择方案**：B + 共享 helper

**理由**：
- A 需要构造完整的 TaskState / TaskCard 只为做一次 LLM 调用，过重
- C 引入新的抽象层，Phase 56 只有两个 Agent 需要，不值得
- B 最直接，但两个 Agent 的 LLM 调用逻辑（endpoint 解析、header 构建、timeout、usage 提取、错误处理）完全相同，应该提取为共享 helper 避免重复

**实现**：

```python
# agent_llm.py — 共享 LLM 调用 helper

@dataclass(frozen=True, slots=True)
class AgentLLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    model: str

def call_agent_llm(
    prompt: str,
    *,
    system: str = "",
    model: str | None = None,
    timeout_seconds: int = 30,
) -> AgentLLMResponse:
    """Direct LLM call for specialist agents. Not routed through executor."""
    endpoint = resolve_new_api_chat_completions_url()
    headers = _http_request_headers()
    # ... httpx.post, parse response, extract usage
```

Agent 的 `execute()` 调用 `call_agent_llm()`，成功时用 LLM 结果，失败时 fallback 到启发式。

---

### 决策 2：LLM 失败 fallback 策略

**问题**：LLM 不可用时（API key 未配置、网络超时、JSON 解析失败），Agent 怎么办？

**候选方案**：
- A. 返回 failed 状态
- B. fallback 到启发式，返回 completed 状态
- C. 返回 degraded 状态（介于 completed 和 failed 之间）

**选择方案**：B（fallback 到启发式）

**理由**：
- A 会导致依赖 Agent 输出的下游流程中断——operator 可能只是没配 API key，不应该阻塞
- C 需要引入新的状态语义，增加复杂度
- B 最稳健：Agent 始终返回有效结果，LLM 增强是"锦上添花"。通过 `analysis_method` 字段（`"heuristic"` vs `"llm"`）让 operator 知道是否用了 LLM

**实现**：

```python
def execute(self, base_dir, state, card, retrieval_items):
    # ... resolve inputs
    try:
        llm_response = call_agent_llm(prompt, system=self._system_prompt())
        output = self._build_llm_report(llm_response)
        analysis_method = "llm"
        usage = {"input_tokens": llm_response.input_tokens, ...}
    except AgentLLMUnavailable:
        output = self._build_report(analyses, goal=goal)  # existing heuristic
        analysis_method = "heuristic"
        usage = {}
    return ExecutorResult(..., side_effects={"analysis_method": analysis_method, "llm_usage": usage})
```

---

### 决策 3：关系建议工作流

**问题**：LiteratureSpecialist 推断出的关系建议如何落库？

**候选方案**：
- A. 自动落库（Agent 直接调 `create_knowledge_relation()`）
- B. 存入 `side_effects`，operator 通过 CLI 确认后落库
- C. 存入独立的 `relation_proposals` 表，operator 逐条 approve/reject

**选择方案**：B（side_effects + CLI 确认）

**理由**：
- A 违反 P7（Proposal over Mutation）——Agent 不应该直接改知识图谱
- C 过重——引入新表和新的 approve/reject 工作流，Phase 56 不需要这么复杂
- B 最简洁：关系建议存在 `ExecutorResult.side_effects["relation_suggestions"]` 中，operator 看完分析报告后 `swl knowledge apply-suggestions --task-id <id>` 一键确认

**CLI 工作流**：

```bash
# 1. 运行 literature-specialist 任务
swl task run <task_id> --executor-name literature-specialist

# 2. 查看分析结果（含关系建议）
swl task inspect <task_id>

# 3. 确认建议（or --dry-run 先预览）
swl knowledge apply-suggestions --task-id <task_id>
```

---

### 决策 4：成本追踪统一

**问题**：如何统一 HTTP executor 和 Agent LLM 调用的成本追踪？

**候选方案**：
- A. 全部改用 API usage，删除 `_attach_estimated_usage()`
- B. API usage 优先，`_attach_estimated_usage()` 作为 fallback
- C. 保持现状，两套并存

**选择方案**：B（API usage 优先 + fallback）

**理由**：
- A 会破坏 mock / local / CLI agent 路径（它们无法返回 API usage）
- C 造成混乱——同一个 `estimated_input_tokens` 字段有时是估算有时是真实值，无法区分
- B 最稳健：有真实 usage 就用，没有就 fallback。通过字段值是否 > 0 判断

**实现**：

```python
# executor.py

def _extract_api_usage(response_data: dict) -> tuple[int, int]:
    usage = response_data.get("usage", {})
    return (
        int(usage.get("prompt_tokens", 0)),
        int(usage.get("completion_tokens", 0)),
    )

def _attach_estimated_usage(result: ExecutorResult) -> ExecutorResult:
    input_tokens = result.estimated_input_tokens
    output_tokens = result.estimated_output_tokens
    if input_tokens <= 0:
        input_tokens = estimate_tokens(result.prompt)
    if output_tokens <= 0:
        output_tokens = estimate_tokens(result.output)
    return replace(result, estimated_input_tokens=input_tokens, estimated_output_tokens=output_tokens)
```

`run_http_executor()` 在解析 response 后，将 usage 填入 `ExecutorResult`。`_attach_estimated_usage()` 检测到已有值时跳过。

---

## 与蓝图的对齐

| 蓝图要点 | Phase 56 实现 | 对齐度 |
|---------|-------------|--------|
| **KNOWLEDGE.md 远期方向：LLM 增强检索** | LiteratureSpecialist + QualityReviewer 接入 LLM | ✅ 落地 |
| **AGENT_TAXONOMY.md §7.3 Literature Specialist** | 从启发式升级为 LLM 深度分析 | ✅ 增强 |
| **AGENT_TAXONOMY.md §7.3 Quality Reviewer** | 从规则式升级为 LLM 语义评估 | ✅ 增强 |
| **SELF_EVOLUTION.md P7 Proposal over Mutation** | 关系建议走 operator gate | ✅ 完全对齐 |

---

## 验收条件

| Slice | 验收条件 |
|-------|---------|
| **S1** | ✓ HTTP executor 使用 API usage ✓ fallback 到 `len // 4` ✓ 非 HTTP 路径不变 |
| **S2** | ✓ LiteratureSpecialist LLM 可用时输出 `analysis_method: llm` ✓ LLM 不可用时 fallback ✓ 关系建议在 `side_effects` 中 ✓ LLM usage 正确追踪 |
| **S3** | ✓ QualityReviewer LLM 可用时输出语义评分 ✓ LLM 不可用时 fallback ✓ usage 正确追踪 |
| **S4** | ✓ `swl knowledge apply-suggestions` 命令可执行 ✓ 关系落库 ✓ dry-run ✓ 重复跳过 |

---

## 提交序列建议

1. `refactor(executor): extract API usage from HTTP response, make _attach_estimated_usage fallback-only` — S1
2. `feat(agent): add shared agent_llm helper for direct LLM calls` — S2 基础设施
3. `feat(agent): upgrade LiteratureSpecialist with LLM analysis and relation suggestions` — S2
4. `feat(agent): upgrade QualityReviewer with LLM semantic evaluation` — S3
5. `feat(cli): add swl knowledge apply-suggestions command` — S4
6. `test(agent): add TDD tests for LLM-enhanced agents and cost tracking` — S1-S4 测试

## 实现时间估算

| 任务 | 估算工时 |
|------|---------|
| S1 - 成本追踪统一 | 4h |
| S2 - LiteratureSpecialist LLM + 关系推断 + agent_llm helper | 16h |
| S3 - QualityReviewer LLM | 8h |
| S4 - apply-suggestions CLI + 测试 | 6h |
| **总计** | **34h** |
