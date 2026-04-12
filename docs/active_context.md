# Active Context

## 当前轮次

- latest_completed_track: `Evaluation / Policy` (Primary) + `Workbench / UX` (Secondary)
- latest_completed_phase: `Phase 21`
- latest_completed_slice: `Dispatch Policy Gate & Mock Topology Visibility`
- active_track: `Architecture Refinement`
- active_phase: `Documentation Update`
- active_slice: `Agent Taxonomy Integration`
- active_branch: `main`
- status: `documentation_updated`

---

## 当前目标

将 `refine.md` 中定义的 **智能体分类学 (Agent Taxonomy)** 正式融入到系统的核心设计文档中，以取代过去模糊的模型品牌定位（如 Claude Agent），明确区分 General Executor、Specialist Agent 和 Validator 的职责与边界。

---

## 当前要解决的问题

当前系统已经具备：

- staged knowledge 的显式 review / promote / reject gate
- canonical registry / index / inspect baseline
- canonical promotion write-through、dedupe、trace-based supersede
- canonical reuse policy / retrieval integration / traceability baseline
- Handoff Contract Schema 在代码层的统一与写盘校验验证
- 基于 Handoff Contract 的 DispatchVerdict 和 Mock Remote 执行路径
- dispatch 前 `context_pointers` 语义校验
- `dispatch_blocked` -> `acknowledge` -> 本地恢复执行路径
- `[MOCK-REMOTE]` CLI 视图区分
- **基于分类学的 Agent Taxonomy 设计原则 (已合入核心文档)**

当前待解决的是：
下一轮应选择哪个 active track / phase / slice，继续推进系统能力的演进。

---

## 当前关键文档

当前优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/system_tracks.md`
4. `current_state.md`
5. `ARCHITECTURE.md`

---

## 当前产出物

- README.md (已更新 Agent Taxonomy 概述)
- ARCHITECTURE.md (已更新 7层模型与 Agent 分野解析)
- docs/design/ORCHESTRATION_AND_HANDOFF_DESIGN.md (已更新分类学路由与隐藏编排器护栏)

## 当前推进

已完成：

- **[Gemini]** 已理解并应用 `refine.md` 核心思想，对系统文档进行了同步修改：
  - `README.md` 中修正了 Executor Layer 的描述，添加了相关术语定义。
  - `ARCHITECTURE.md` 中更新了架构图中的 Agent 角色，并新增了 3.7 智能体分类学章节。
  - `docs/design/ORCHESTRATION_AND_HANDOFF_DESIGN.md` 中强调了智能调度器基于分类学而非模型品牌进行路由，并增加了对隐藏编排器的防御原则。

## 下一步

- 从 `docs/system_tracks.md` 重新选择下一轮 active track / phase / slice
- 为下一轮工作编写 fresh kickoff。
