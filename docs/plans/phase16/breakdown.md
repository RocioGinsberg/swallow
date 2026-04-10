# Phase 16 Breakdown

## 基本信息

- phase: `Phase 16`
- track: `Evaluation / Policy`
- secondary_tracks:
  - `Retrieval / Memory`
  - `Workbench / UX`
- slice: `Canonical Reuse Regression Baseline`
- branch: `feat/phase16-canonical-reuse-regression`

---

## 总体目标

把当前已经具备 canonical reuse evaluation baseline 的路径，从“可记录、可复查”推进到“可比较、可判断是否退化”的 regression baseline。

本轮重点不是自动调 policy，而是建立显式 regression truth。

---

## Affected Areas

- `src/swallow/canonical_reuse_eval.py`
- `src/swallow/orchestrator.py`
- `src/swallow/cli.py`
- `src/swallow/paths.py`
- `src/swallow/store.py`
- `tests/test_cli.py`
- `docs/active_context.md`
- `docs/plans/phase16/*`

---

## 默认实现顺序

本轮建议按以下顺序推进：

1. regression baseline schema / artifact
2. baseline snapshot generation
3. compare / inspect path
4. docs / help alignment
5. phase closeout

这样做的原因是：

- 先明确 baseline artifact 长什么样
- 再明确 snapshot 如何从现有 evaluation summary 派生
- 再补 operator-facing compare
- 最后收正文档和 closeout

---

## Slice 列表

### P16-01 regression baseline schema / artifact

#### 目标

定义 canonical reuse regression baseline 的最小 artifact 结构。

#### 建议范围

至少包含：

- baseline_generated_at
- task_id
- evaluation_count
- judgment_counts
- resolved / unresolved citation counts
- retrieval_match_count
- latest_judgment snapshot

#### 验收条件

- regression baseline 不再只是临时观察
- baseline 可持久化、可回看
- 结构直接复用现有 evaluation summary 语义

#### 推荐提交粒度

- `feat(policy): add canonical reuse regression baseline artifact`

---

### P16-02 baseline snapshot generation

#### 目标

从已有 canonical reuse evaluation records 生成稳定 regression snapshot。

#### 建议范围

可优先考虑：

- task-local baseline artifact
- 由 existing evaluation summary 派生
- 对空记录场景保持明确表达

#### 验收条件

- snapshot 可重复生成
- judgment vocabulary 保持与 Phase 15 一致
- 不引入 generalized scoring platform

#### 推荐提交粒度

- `feat(knowledge): generate canonical reuse regression snapshot`
- `test(knowledge): cover canonical reuse regression snapshot`

---

### P16-03 compare / inspect path

#### 目标

给 operator 提供一个紧凑的 canonical reuse regression compare path。

#### 建议范围

可优先考虑：

- 新增 `task` 范围内 regression compare / inspect 入口
- 或在现有 inspect / review 中补充 regression snapshot

重点展示：

- baseline summary
- current summary
- delta / mismatch indicators

#### 验收条件

- operator 不打开底层 JSON 也能看出是否发生明显退化
- compare path 不误导为自动 policy learning
- 与现有 inspect / review 语义保持一致

#### 推荐提交粒度

- `feat(cli): add canonical reuse regression inspect path`
- `test(cli): cover canonical reuse regression inspection`

---

### P16-04 docs / help alignment

#### 目标

让 canonical reuse regression baseline 的 operator 语义在文档中可见。

#### 建议范围

同步以下内容中至少必要部分：

- CLI help
- `README.md`
- `README.zh-CN.md`
- `docs/active_context.md`

#### 验收条件

- regression baseline 被描述为显式 comparison truth，而非自动 policy optimizer
- 命令名、artifact 名、summary 名保持一致
- 文档不扩写成更大 evaluation platform 设计

#### 推荐提交粒度

- `docs(readme): document canonical reuse regression workflow`

---

### P16-05 closeout

#### 目标

完成 Phase 16 的 stop/go judgment。

#### 建议范围

收口时更新：

- `docs/plans/phase16/closeout.md`
- `current_state.md`
- 必要时 `AGENTS.md`

#### 验收条件

- 当前 phase 的 stop / go 边界已写清楚
- 下一轮起点明确
- 当前 regression baseline 已能作为稳定 checkpoint 被恢复

#### 推荐提交粒度

- `docs(phase16): add closeout note`
