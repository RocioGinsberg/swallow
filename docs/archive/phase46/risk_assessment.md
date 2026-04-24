---
author: claude
phase: 46
slice: all
status: draft
depends_on:
  - docs/plans/phase46/design_decision.md
  - docs/plans/phase46/kickoff.md
---

> **TL;DR**: Phase 46 整体风险 24/36（中-高）。S2（HTTP 执行器 + CLI 去品牌化）和 S4（降级矩阵 + Cline 兜底）为高风险 slice，需要 Human gate 和充分的 mock 测试覆盖。最大系统性风险是 new-api 基础设施就绪假设。

---

# Phase 46 Risk Assessment: 模型网关物理层实装

## 风险矩阵

### 维度说明

- **影响范围**：1=单文件 2=单模块 3=跨模块
- **可逆性**：1=轻松回滚 2=需要额外工作 3=难以回滚
- **依赖复杂度**：1=无外部依赖 2=依赖内部模块 3=依赖外部系统

总分 ≥7 标注为高风险。

### 逐 Slice 风险

#### S1: 基础设施就绪验证

| 维度 | 分数 | 说明 |
|------|------|------|
| 影响范围 | 1 | 仅 `pyproject.toml`、`doctor.py`、`tests/eval/` |
| 可逆性 | 1 | 添加依赖和测试骨架，轻松回滚 |
| 依赖复杂度 | 2 | 依赖 new-api Docker 栈可用 |
| **总分** | **4** | **低风险** |

**主要风险**：new-api 容器未启动或端口配置不一致。
**缓解**：`swl doctor` 检查项会在 S1 中落地，后续 slice 可据此判断 stop/go。

---

#### S2: HTTP 执行器核心 + CLI 去品牌化

| 维度 | 分数 | 说明 |
|------|------|------|
| 影响范围 | 3 | 跨 `executor.py`、`router.py`、`cost_estimation.py`、`models.py`、测试文件 |
| 可逆性 | 2 | HTTP 执行器可独立回滚，但 CLI 重构涉及现有测试的断言变更 |
| 依赖复杂度 | 3 | 依赖 new-api 外部服务 + httpx 新依赖 + 现有 320+ 测试的兼容性 |
| **总分** | **8** | **高风险** |

**风险 R1: CLI 重构破坏现有路径**
- 描述：将 `run_codex_executor` 重构为 `CLIAgentExecutor` 时，可能破坏现有的 Codex 执行路径和依赖它的测试
- 影响：320+ 现有测试中涉及 executor 的部分可能失败
- 概率：中
- 缓解：先写 `CLIAgentExecutor` 的 Codex 配置实例，确保行为与 `run_codex_executor` 完全一致后再删除旧函数。分两步提交：先新增并行路径，再移除旧路径

**风险 R2: `run_executor_inline` else 兜底移除的连锁影响**
- 描述：将 `else: run_codex_executor(...)` 改为 `UnknownExecutorError` 后，任何未正确注册的 executor name 都会报错而非静默降级
- 影响：如果存在隐式依赖默认 Codex 路径的代码或测试，会立即暴露
- 概率：中
- 缓解：在重构前先 grep 全仓库确认所有 executor name 的使用点，确保每个都有显式注册

**风险 R3: new-api 响应格式不符预期**
- 描述：new-api 的 OpenAI-compatible 端点可能在某些边缘情况下（如 streaming 字段、tool_calls 结构）与标准 OpenAI 格式有差异
- 影响：HTTP 执行器解析响应失败
- 概率：低-中
- 缓解：S1 中先用手动请求验证响应格式，S2 中对响应解析做防御性编码

---

#### S3: 方言对齐与多模型路由

| 维度 | 分数 | 说明 |
|------|------|------|
| 影响范围 | 2 | `router.py`、`executor.py`、可能 `dialect_adapters.py` |
| 可逆性 | 1 | 新增路由注册，不修改现有路由，轻松回滚 |
| 依赖复杂度 | 2 | 依赖 S2 的 HTTPExecutor 已就绪 |
| **总分** | **5** | **中风险** |

**风险 R4: 模型族方言匹配不准确**
- 描述：`resolve_dialect_name` 的 substring 匹配可能在新增模型（qwen/glm）时产生误匹配
- 影响：模型收到错误格式的 prompt
- 概率：低
- 缓解：为每个新增模型族编写方言正确性 eval 测试

---

#### S4: 降级矩阵 + Cline 兜底

| 维度 | 分数 | 说明 |
|------|------|------|
| 影响范围 | 2 | `executor.py`、`router.py`、测试文件 |
| 可逆性 | 2 | fallback 链配置可回滚，但 Cline 集成涉及新的 CLI 交互协议 |
| 依赖复杂度 | 3 | 依赖 Cline CLI 外部二进制 + 其 headless 模式的稳定性 |
| **总分** | **7** | **高风险** |

**风险 R5: Cline CLI headless 模式不稳定**
- 描述：Cline CLI 2.0 较新，`-y` headless 模式和 JSON 输出的行为可能在版本间变化
- 影响：降级到 Cline 时输出解析失败
- 概率：中
- 缓解：Cline 作为可选软依赖，未安装时自动跳过。降级链中 Cline 之后还有 `local-summary` 兜底。测试中使用 mock 而非真实 Cline 二进制

**风险 R6: 降级链循环或死锁**
- 描述：`fallback_route_name` 链式配置如果出现循环引用，会导致无限降级
- 影响：系统挂起
- 概率：低
- 缓解：在降级逻辑中加入已访问路由集合检测，遇到循环立即终止并降级到 `local-summary`

---

## 系统性风险

### SR1: new-api 基础设施就绪假设（最大风险）

整个 Phase 46 建立在 `localhost:3000` (new-api) 可用的假设上。如果 Docker Compose 栈未部署或配置有误，S1 之后所有 slice 都会阻塞。

**缓解**：S1 的首要任务就是验证这个假设。如果不成立，S1 产出中应包含部署指南，由 Human 确认基础设施就绪后再进入 S2。

### SR2: Eval 覆盖缺口

Phase 45 的 eval 基线覆盖的是 ingestion 降噪和 meta-optimizer 提案质量，不直接覆盖"执行器替换后模型输出质量不降级"。Phase 46 需要在 S1 中建立新的 eval 场景，但这些场景本身的基线值需要在 S2 完成后才能确定。

**缓解**：S1 先建 eval 骨架（测试结构 + fixture），S2 完成后补充基线阈值，S4 中做全量 eval 验证。

### SR3: 测试回归风险

S2 的 CLI 重构会触及 `executor.py` 的核心分发逻辑，这是 320+ 测试中被间接依赖最多的模块之一。

**缓解**：S2 采用"先并行后替换"策略——新增 `CLIAgentExecutor` 与旧 `run_codex_executor` 并行存在，全量测试通过后再移除旧路径。

---

## 风险总览

| ID | 风险 | Slice | 概率 | 影响 | 缓解策略 |
|----|------|-------|------|------|----------|
| R1 | CLI 重构破坏现有路径 | S2 | 中 | 高 | 先并行后替换 |
| R2 | else 兜底移除连锁影响 | S2 | 中 | 中 | 全仓库 grep 确认 |
| R3 | new-api 响应格式差异 | S2 | 低-中 | 中 | S1 手动验证 + 防御性解析 |
| R4 | 方言 substring 误匹配 | S3 | 低 | 中 | eval 测试覆盖 |
| R5 | Cline headless 不稳定 | S4 | 中 | 低 | 可选软依赖 + mock 测试 |
| R6 | 降级链循环 | S4 | 低 | 高 | 已访问集合检测 |
| SR1 | new-api 基础设施不就绪 | 全局 | 中 | 阻塞 | S1 验证 + Human gate |
| SR2 | Eval 覆盖缺口 | 全局 | 确定 | 中 | 分阶段建立基线 |
| SR3 | 测试回归 | S2 | 中 | 高 | 先并行后替换 |

## 建议的 Human Gate 时机

1. **S1 完成后**：确认 new-api 可达，决定是否进入 S2
2. **S2 完成后**：验证 HTTP 执行器真实调用 LLM 成功，确认 CLI 重构无回归
3. **S4 完成后**：全量测试 + eval 通过，准备 PR
