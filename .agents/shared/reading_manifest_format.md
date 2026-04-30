---
applies_to: all_agents
status: stable
---

# Reading Manifest Format

> Agent 进入新会话、读完启动文件后,必须输出 reading manifest 作为会话第一句正式输出(允许之前有简短问候)。Human 通过 manifest 即时验证 agent 是否读到了关键文件,避免"agent 漏读关键文档就开始干活"。

---

## 标准格式

```
Reading manifest:
  ✓ <file_path> (<one-line summary>)
  ✓ <file_path> (<one-line summary>)
  ⚠ <file_path> (<异常说明>)
  ✗ <file_path> (<未读 / 跳过原因>)
Ready to: <这一轮准备做什么>
```

字段约定:

| 标记 | 含义 |
|------|------|
| `✓` | 已成功读取,且内容符合预期 |
| `⚠` | 读取了但有异常(版本不一致 / 内容缺失 / 引用断链 / 文件不存在但本次会创建) |
| `✗` | 显式跳过(理由必须明示,例如"本轮工作不涉及" / "已在上次会话读过且未变化") |

`(<one-line summary>)` 不是文件全文摘要,只是**让 human 看一眼就知道 agent 抓到了关键 anchor**。例如:

- `docs/design/INVARIANTS.md` 的 summary 应该是 "constitution v1.x" 或包含具体的 §X 锚点
- active_context.md 的 summary 应该是 "current: Phase 60 S2 in progress"
- closeout.md 的 summary 应该是 "Phase 59 closed, no open BLOCK"

---

## Claude 启动 manifest 示例

```
Reading manifest:
  ✓ .agents/shared/read_order.md (read order v2)
  ✓ .agents/shared/rules.md (5 rules acknowledged)
  ✓ .agents/shared/state_sync_rules.md (state sync section 1 ready)
  ✓ .agents/shared/document_discipline.md (5 disciplines acknowledged)
  ✓ .agents/claude/role.md (role: plan auditor / PR reviewer / tag evaluator)
  ✓ .agents/claude/rules.md (no codegen / no commit / no PR)
  ✓ docs/design/INVARIANTS.md (constitution loaded; 4 inviolable rules)
  ✓ AGENTS.md (collaboration rules; 2-agent + human)
  ✓ docs/active_context.md (current: Phase 60 plan audit pending)
  ✓ docs/plans/phase60/plan.md (retrieval policy slices identified)
  ⚠ docs/plans/phase60/plan_audit.md (does not exist yet, will coordinate subagent)
Ready to: audit plan.md and prepare PR/review gates for Phase 60
```

---

## Codex 启动 manifest 示例

```
Reading manifest:
  ✓ .agents/shared/read_order.md
  ✓ .agents/shared/rules.md
  ✓ .agents/shared/state_sync_rules.md
  ✓ .agents/shared/document_discipline.md
  ✓ .agents/codex/role.md (role: plan / implement / test / commit suggestions)
  ✓ .agents/codex/rules.md
  ✓ docs/design/INVARIANTS.md (constitution loaded)
  ✓ AGENTS.md (collaboration rules)
  ✓ docs/active_context.md (current: Phase 60 S2 implementation pending)
  ✓ docs/plans/phase60/plan.md (approved; retrieval source policy)
  ✓ docs/plans/phase60/plan_audit.md (ready; no blockers)
  ✗ docs/plans/phase59/closeout.md (skipped; Phase 59 already merged, no relevance)
Ready to: implement S2 (HTTP path default retrieval sources tightening) per plan
```

---

## Subagent 启动 manifest 示例

Subagent 的 manifest 更短,只列与其职责相关的输入/输出文件:

```
Reading manifest (consistency-checker):
  ✓ docs/design/INVARIANTS.md
  ✓ docs/plans/phase60/plan.md
  ✓ swallow/retrieval/__init__.py (latest commit on feat/phase-60-s2)
  ⚠ docs/plans/phase60/consistency_report.md (will produce, output_path)
Ready to: compare implementation against plan.md and produce consistency_report.md
```

---

## 异常处理

### 读取失败

如果某个**启动顺序内的必读文件**读取失败,agent 必须:

1. 在 manifest 中以 `⚠` 标记并附原因
2. **不能继续向后操作**——先报告 human,等 human 决定如何处理
3. 不允许在 manifest 中谎称读到了但实际没读

### 版本不一致

如果发现文档之间引用断链或版本不一致(例如 INVARIANTS 引用了 DATA_MODEL 中已删除的章节),agent 必须:

1. 在 manifest 中以 `⚠` 标记
2. 在 "Ready to" 之前先报告这个问题
3. 由 human 决定:本会话内修正 / 创建 concerns_backlog 条目 / 暂停会话

### 跳过文件

只允许在以下情况跳过:

- 文件不属于本轮工作范围(例如 codex 实现 phase 60 时跳过 phase 59 的 closeout)
- 文件已在上次会话中读过,且 git log 显示未变化(需在 summary 中标注 "unchanged since last session")

不允许仅因为"文件太长"或"我大概知道内容"就跳过。

---

## 何时输出 manifest

| 场景 | 是否需要 manifest |
|------|------------------|
| 新会话首次启动 | ✅ 必须 |
| 同一会话内的延续操作 | ❌ 不需要(避免噪音) |
| 切换到新 phase / 新任务时 | ✅ 必须重新输出 |
| 仅回答简短澄清问题 | ❌ 不需要 |
| 涉及修改非启动顺序中的文档 | ✅ 在动手前补充该文档的读取 |

---

## 与其他纪律的关系

reading manifest 是 `document_discipline.md §纪律 5` 的具体格式定义。

它不替代:
- `state_sync_rules.md` 中的状态校验(那是读完 manifest **后**的第一件事)
- 各 agent 自己的 `rules.md` 中的行为约束

它是 agent **进入会话工作状态前的最后一步**——manifest 输出后,agent 才被认为"准备好开始工作"。

---

## 本文件的职责边界

本文档是:
- reading manifest 的格式契约
- agent 启动时的输出标准

本文档不是:
- 各 agent 的具体读取顺序定义(→ `.agents/shared/read_order.md` 与各自的 `rules.md`)
- 状态同步规则(→ `.agents/shared/state_sync_rules.md`)
- 异常处理 SOP(→ 各 agent 的 `rules.md`)
