# Workflow: Hotfix

紧急修复流程。跳过完整的 context analysis 和 design decomposition，快速修复并合并。

---

## 适用场景

- 线上/测试环境发现阻塞性 bug
- 修复范围明确（单文件或单模块）
- 不涉及架构变更

**如果修复涉及多模块或架构调整，使用 feature workflow。**

---

## 流程

```
Claude: Quick Assessment + branch-advise
        ↓
 Human: Approve Fix Scope ⛔
        ↓
 Codex: Fix + Test
        ↓
 Human: Merge ⛔
```

---

## Step 1: Claude — Quick Assessment

**输入**：bug 描述 / 报错信息

**产出**：
- 口头（对话中）的修复范围评估 + 风险判断
- branch-advise：建议 `fix/<topic>` 分支名

**不产出正式 design_decision.md**（除非人工要求）。

---

## Step 2: Human — Approve Fix Scope ⛔

确认修复范围合理，授权 Codex 开始。

---

## Step 3: Codex — Fix + Test

- 创建 `fix/<topic>` 分支
- 修复 + 测试
- 创建 PR

---

## Step 4: Human — Merge ⛔

审查 PR，合并。

---

## 收口

hotfix merge 后，在 `docs/active_context.md` 记录：
- 修复了什么
- 是否需要后续跟进（如果是，创建正式 phase/slice）
