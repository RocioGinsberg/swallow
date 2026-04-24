---
author: claude
phase: 54
slice: risk_assessment
status: draft
depends_on:
  - docs/plans/phase54/kickoff.md
  - docs/plans/phase54/design_decision.md
  - docs/plans/phase54/context_brief.md
---

## TL;DR

Phase 54 风险极低。唯一需要关注的是 `BUILTIN_DIALECTS["codex_fim"]` 查找键重命名的序列化兼容性——通过双键注册（shim）完全消除。`http-claude` 持久化字段风险已通过"本 phase 不动"决策规避。整体风险评级：**低**，工作量约 6h。

---

## 风险矩阵

| ID | 风险 | 概率 | 影响 | 等级 | 消化时机 |
|----|------|-----|-----|------|---------|
| R1 | `"codex_fim"` 键重命名破坏持久化 TaskState | 低 | 高 | **低** | S1 实施时（shim 消除） |
| R2 | 文件重命名遗漏 import 路径 | 低 | 中 | **低** | S1 实施时（全量 pytest 验证） |
| R3 | `CodexFIMDialect` alias 被外部依赖直接 import | 极低 | 中 | **低** | S1 实施时（alias 保留） |
| R4 | 测试 fixture 字符串未全部更新 | 低 | 低 | **低** | S2 实施时 |

---

## 低风险详解

### R1 — `"codex_fim"` 键重命名破坏持久化 TaskState

**描述**：`TaskState.route_dialect` 可能持久化了 `"codex_fim"` 字符串。若 `BUILTIN_DIALECTS` 中删除该键，`resolve_dialect("codex_fim")` 将失败。

**缓解**：双键注册——`BUILTIN_DIALECTS["fim"]` 为主键，`BUILTIN_DIALECTS["codex_fim"]` 保留为 shim，两者指向同一 lazy factory。持久化数据无需迁移。

**残留风险**：无。shim 永久保留直到显式决定移除（届时需要 SQLite 迁移，不在本 phase 范围）。

### R2 — 文件重命名遗漏 import 路径

**描述**：`codex_fim.py` → `fim_dialect.py` 重命名后，若有 import 路径未更新，会导致 `ImportError`。

**缓解**：全量 pytest 在 S1 完成后立即运行，任何遗漏的 import 都会在测试阶段暴露。变更文件清单已列出所有需要更新的 import 路径（`__init__.py`、`executor.py`）。

### R3 — `CodexFIMDialect` alias 被外部依赖直接 import

**描述**：若有外部代码（用户脚本、插件）直接 `from swallow.dialect_adapters import CodexFIMDialect`，移除 alias 会破坏它们。

**缓解**：`CodexFIMDialect = FIMDialect` alias 在 `fim_dialect.py` 末尾保留，`__init__.py` 继续 re-export。不移除，仅加 deprecation 注释。

### R4 — 测试 fixture 字符串未全部更新

**描述**：测试中硬编码的 `"codex_fim"` 字符串若未更新，会导致测试断言失败（但不影响功能）。

**缓解**：S2 专门处理测试更新，全量 pytest 验证。保留一条 `"codex_fim"` shim 回归测试，其余改为 `"fim"`。

---

## 回归风险监控

| 区域 | 监控指标 | 回归信号 |
|------|---------|---------|
| Dialect 解析 | `resolve_dialect("fim")` + `resolve_dialect("codex_fim")` | 任一返回 None |
| Router | `http-deepseek` 路由 dialect 解析 | dialect_hint 无法解析 |
| 全量回归 | `pytest --tb=short` | 任何 ImportError 或 KeyError |

---

## 风险吸收判断

**可以接受的风险**：
- R1：shim 完全消除
- R2：pytest 即时验证
- R3：alias 保留
- R4：S2 专门处理

**Phase 54 整体风险评级：低**

- 无中高风险项
- 纯重构，无功能变化
- 工作量极小（6h）
- 可单步提交，每步独立可 revert
