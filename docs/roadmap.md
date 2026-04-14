---
author: claude
status: living-document
---

## TL;DR
跨 phase 蓝图对齐活文档。记录各 track 的"现状 vs 蓝图"差距、推荐 phase 队列、已消化条目。Gemini 每次 phase closeout 时增量更新，新 phase 启动时直接读取本文件选方向，无需重复蓝图全量对齐。

---

# Roadmap

## 一、蓝图差距总表

按 track 组织，每条记录"蓝图愿景 → 当前现状 → 核心差距 → 风险等级"。

### Track 2: Retrieval / Memory

| ID | 蓝图愿景 | 当前现状 | 核心差距 | 风险 | 来源 |
|:---|:---------|:---------|:---------|:-----|:-----|
| R2-1 | Staged → Canonical 显式晋升路径 | **已消化 (P28)**：`task staged` + `knowledge stage-promote --text/--force` | — | — | `ARCHITECTURE.md` — Self-Evolution |
| R2-2 | Graph RAG & 混合图谱：知识具备实体关系和引用链 | 知识对象缺乏跨任务关联审计 | 晋升过程无精炼/去重策略（P28 补齐了基础精炼） | 中 | `KNOWLEDGE_AND_RAG_DESIGN.md` |
| R2-3 | 单一事实源：Canonical 记录具备完整溯源 | **已消化 (P28)**：晋升时 `decision_note` + `[refined]` 审计标记 | — | — | `STATE_AND_TRUTH_DESIGN.md` |
| R2-4 | 执行中动态检索 (Mid-flight Retrieval) | 仅支持 pre-execution retrieval | 无 agentic mid-flight retrieval 工具 | 中 | `KNOWLEDGE_AND_RAG_DESIGN.md` |
| R2-5 | 向量/语义检索 | 仅关键词匹配 | 无 embedding 或语义搜索 | 低(非近期) | `ARCHITECTURE.md` |

### Track 3: Execution Topology

| ID | 蓝图愿景 | 当前现状 | 核心差距 | 风险 | 来源 |
|:---|:---------|:---------|:---------|:-----|:-----|
| E3-1 | Provider Dialect & Negotiation (Layer 6) | **已消化 (P29)**：dialect adapter 层、plain_text + structured_markdown、route dialect 持久化与可观测性 | — | — | `ARCHITECTURE.md` |
| E3-2 | 真实 remote execution boundary | Handoff contract baseline 已建 (P18) | 无真实 transport / remote worker | 低(非近期) | `ARCHITECTURE.md` |

### Track 1: Core Loop

| ID | 蓝图愿景 | 当前现状 | 核心差距 | 风险 | 来源 |
|:---|:---------|:---------|:---------|:-----|:-----|
| C1-1 | 更成熟的 stop / resume / retry 语义 | **已消化 (P30)**：phase-level checkpoint、`retry/rerun --from-phase`、checkpoint 可观测性 | — | — | `STATE_AND_TRUTH_DESIGN.md` |

### Track 4-6

暂无紧迫差距。后续 phase 按需补充。

---

## 二、推荐 phase 队列

按优先级排序。每条含 track、slice 名、一句话理由、依赖的差距 ID。

| 优先级 | Phase | Track | Slice 名 | 理由 | 风险批注 | 差距 ID |
|:-------|:------|:------|:---------|:-----|:---------|:--------|
| 1 | 31 | Retrieval / Memory (Primary) + Core Loop (Secondary) | Initial Agentic RAG Exploration | 执行中动态检索工具；依赖 canonical 知识库有足够内容积累 | 前置条件：canonical 库需有实际使用数据，否则效果难验证；P29 structured_markdown dialect 可能影响 mid-flight retrieval prompt 格式 | R2-4 |
| 2 | 32 | Execution Topology (Primary) | Provider-Specific Dialect Expansion | 在 P29 adapter 层基础上实现 Claude XML / OpenAI Chat 等 provider-specific dialect | 依赖 P29 baseline 稳定运行一段时间后的反馈 | E3-1(扩展) |

注：队列仅为建议顺序，每轮 phase 启动前由 Human 最终决定。Phase 28-30 已完成，从队列移除。

---

## 三、已消化差距

Phase closeout 时将已解决的条目从总表移至此处。

| 差距 ID | 消化于 | 说明 |
|:--------|:-------|:-----|
| R2-1 | Phase 28 | Knowledge Promotion Baseline: `task staged` + `knowledge stage-promote --text/--force` |
| R2-3 | Phase 28 | 晋升时 `decision_note` + `[refined]` 审计标记，溯源链完整 |
| E3-1 | Phase 29 | Provider Dialect Baseline: dialect adapter 层、plain_text + structured_markdown、route 持久化与可观测性 |
| C1-1 | Phase 30 | Operator Checkpoint & Selective Retry: phase-level checkpoint、`retry/rerun --from-phase`、checkpoint 可观测性 |
| _(Phase 27)_ | Phase 27 | Grounding baseline: canonical retrieval → grounding evidence artifact → task state 锁定 |

---

## 维护规则

- **维护者**：Gemini（差距总表）+ Claude（推荐队列优先级与风险批注）
- **Gemini 更新时机**：每次 phase closeout 时增量更新差距总表
- **Claude 更新时机**：Gemini 更新差距总表后，评审并调整推荐队列排序与风险批注
- **新 phase 启动流程**：读 roadmap → Claude 评审优先级 → Human 选方向 → context_brief（跳过蓝图全量重读）
- **全量刷新**：仅在架构蓝图文档 (`ARCHITECTURE.md`, `docs/design/*.md`) 发生重大变更时触发
