---
author: codex
phase: 19
slice: handoff-contract-schema-unification
status: final
depends_on:
  - docs/plans/phase19/kickoff.md
  - docs/plans/phase19/design_decision.md
---

**TL;DR**: Phase 19 按 3 个 slice 推进，但当前只进入代码侧的前 2 个 slice。Codex 本轮先统一 schema、接写盘校验、补测试；设计文档标注仍保留为后续 gated 工作，不在本次实现中越权改动。

# Phase 19 Breakdown

## 基本信息

- phase: `Phase 19`
- track: `Core Loop`
- secondary_tracks:
  - `Execution Topology`
- slice: `Handoff Contract Schema Unification`
- branch: `feat/phase19-handoff-schema-unification`

---

## 总体目标

把 Phase 18 的 remote handoff baseline 从“operator-facing contract summary”推进到“带统一 handoff schema 的可验证 contract truth”。

本轮重点是 schema 收敛与写盘校验，不是扩展新的 dispatch 行为。

---

## Affected Areas

- `src/swallow/models.py`
- `src/swallow/harness.py`
- `src/swallow/store.py`
- `tests/test_cli.py`
- `docs/active_context.md`
- `docs/plans/phase19/*`

---

## 默认实现顺序

本轮建议按以下顺序推进：

1. schema dataclass / serialization
2. remote handoff contract write validation
3. targeted tests
4. 状态同步

这样做的原因是：

- 先把统一 vocabulary 固化为代码对象
- 再保证所有写盘路径共享同一套 contract truth
- 最后用测试锁住 local / remote 两类边界

---

## Slice 列表

### P19-01 unified handoff schema dataclass

#### 目标

定义统一的 handoff schema，收敛设计文档里的术语差异。

#### 建议范围

至少包含：

- `goal`
- `constraints`
- `done`
- `next_steps`
- `context_pointers`

并说明与设计文档术语的映射关系。

#### 验收条件

- authoritative schema dataclass 已存在
- `remote_handoff_contract.json` 包含统一 schema 字段
- local baseline 与 remote candidate 都能生成有效 schema

#### 推荐提交粒度

- `feat(core-loop): add unified handoff contract schema`

---

### P19-02 remote handoff contract validation

#### 目标

让 `remote_handoff_contract.json` 在所有写盘入口自动校验。

#### 建议范围

至少校验：

- 必填字段存在
- schema 字段类型正确
- 关键布尔 / 列表 / 字符串字段不被错误类型覆盖
- 错误信息明确指出具体字段

#### 验收条件

- `orchestrator` 与 `harness` 的 contract 写入共享同一校验逻辑
- 非法 payload 会被拒绝并抛出明确错误
- 有针对性测试覆盖

#### 推荐提交粒度

- `feat(topology): validate remote handoff contract writes`
- `test(cli): cover handoff contract schema validation`

---

### P19-03 docs alignment note

#### 目标

在设计文档中标注统一 schema 与 authoritative code path。

#### 当前处理

由于 Codex 角色规则禁止修改 `docs/design/*.md` 正文，本 slice 保留为后续 gated 工作，由具备对应权限的角色或经人工明确指示后再执行。

#### Stop/Go Signal

- `go`: 人工明确要求同步 `docs/design/*`
- `stop`: 当前实现只收口代码与测试，不越权修改设计文档
