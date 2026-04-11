---
author: codex
phase: 19
slice: handoff-contract-schema-unification
status: final
depends_on:
  - docs/plans/phase19/design_decision.md
  - docs/plans/phase19/risk_assessment.md
---

**TL;DR**: Phase 19 进入实现态，primary track 选定为 `Core Loop`，交叉 `Execution Topology`。本轮只做 handoff contract schema 统一与写盘校验，不扩张到真实 remote execution。

# Phase 19 Kickoff

## 基本信息

- phase: `Phase 19`
- track: `Core Loop`
- secondary_tracks:
  - `Execution Topology`
- slice: `Handoff Contract Schema Unification`
- status: `kickoff`
- recommended_branch: `feat/phase19-handoff-schema-unification`

---

## 启动背景

Phase 18 已完成 `Remote Handoff Contract Baseline`，系统已经具备：

- task-local `remote_handoff_contract.json` baseline artifact
- execution-site / dispatch / handoff / control / inspect / review 的 remote handoff surface
- remote candidate 与 local baseline 的 operator-facing 区分

但设计审查已经指出一个新的收敛点：

> “交接单 / handoff note” 在多份设计文档中使用了相近但不一致的术语集合，当前代码里的 `remote_handoff_contract.json` 仍以 operator-facing baseline 为主，尚未把统一的 handoff schema 固化为 authoritative code contract。

如果不先统一 schema，后续无论是 capability negotiation 还是更深的 orchestration slice，都会继续建立在不完全一致的 handoff vocabulary 之上。

---

## 当前问题

当前仓库里已经有 remote handoff contract baseline，但还缺少三件事：

- 一个 authoritative 的 handoff schema，用来统一 `goal` / `constraints` / `done` / `next_steps` / `context_pointers`
- 对 `remote_handoff_contract.json` 的结构化验证，确保写入路径不会落下必填字段或错误类型
- 对当前 phase 的实现边界重新声明，避免把 schema work 误扩张成 remote execution implementation

换句话说：

Phase 19 的目标不是给 remote handoff 增加更多平台能力，而是先让 contract schema 成为可定义、可验证、可复用的代码真相。

---

## 本轮目标

Phase 19 应完成以下闭环：

1. 定义统一的 handoff contract schema dataclass
2. 让 `remote_handoff_contract.json` 在写入时自动携带并校验 schema 字段
3. 让 `orchestrator` 与 `harness` 两条写盘路径共享同一套 schema / validation truth
4. 为后续 slice 保持 clear boundary：仍然只是 contract baseline，不是 remote worker implementation

---

## 本轮非目标

本轮不默认推进以下方向：

- real remote worker execution
- cross-machine transport implementation
- automatic remote dispatch
- provider routing / capability negotiation 扩张
- 新 CLI 命令
- 无边界文档重写

---

## 设计边界

### 应保持稳定的部分

本轮不应破坏：

- Phase 18 已建立的 remote handoff operator-facing surface
- 当前 local execution baseline
- artifacts / reports / inspect / review 的恢复路径
- state / events / artifacts 的分层

### 本轮新增能力应满足

- unified schema 必须在代码里有 authoritative 定义
- schema validation 必须在写盘时自动执行
- 报错必须明确指出缺失字段或类型不匹配
- 现有 contract report 仍保持可读，不退化成纯 schema dump

---

## 影响范围

本轮预计会涉及：

- `src/swallow/models.py`
- `src/swallow/harness.py`
- `src/swallow/store.py`
- `tests/test_cli.py`
- `docs/active_context.md`
- `docs/plans/phase19/*`

---

## 完成条件

Phase 19 可以进入 closeout 的最低条件应包括：

1. unified handoff schema 已在代码中落地
2. `remote_handoff_contract.json` 写入自动校验 schema 与 contract 字段
3. 至少覆盖 local baseline 与 remote candidate 两类 contract 测试
4. `docs/active_context.md` 已切到 Phase 19 实现态

---

## 下一步

本 kickoff 落地后，下一步应完成：

1. `docs/plans/phase19/breakdown.md`
2. Slice 1：统一 schema dataclass
3. Slice 2：写盘校验与失败测试
