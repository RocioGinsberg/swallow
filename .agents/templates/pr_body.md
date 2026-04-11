# PR Body 模板

创建 PR 时，Codex 使用以下模板组装 PR body。
各节内容从对应 agent 的产出物中提取 TL;DR 或摘要。

---

```markdown
## Context
<!-- 来源: docs/plans/<phase>/context_brief.md 的 TL;DR -->
<!-- 由 Gemini 产出 -->

{context_brief TL;DR}

## Design Decision
<!-- 来源: docs/plans/<phase>/design_decision.md 的 TL;DR + slice 列表 -->
<!-- 由 Claude 产出 -->

{design_decision TL;DR}

### Slices
{slice 列表及其完成状态}

### Risk
<!-- 来源: docs/plans/<phase>/risk_assessment.md 的高风险项 -->
{高风险 slice 列表，如无则写"无高风险项"}

## Implementation Notes
<!-- 由 Codex 填写 -->

{实现要点、技术选型说明、注意事项}

### Test Coverage
{测试覆盖情况}

## Review
<!-- 来源: docs/plans/<phase>/review_comments.md 的 [CONCERN] 和 [BLOCK] 项 -->
<!-- 由 Claude 产出 -->

{review 要点，如全部 PASS 则写"评审通过，无 concern 或 block 项"}

## Human Decision
<!-- 留空，由人工在 PR 上填写合并理由或打回原因 -->
```
