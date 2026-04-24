---
author: claude
phase: 54
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase54/context_brief.md
  - docs/roadmap.md
  - docs/design/AGENT_TAXONOMY.md
---

## TL;DR
Phase 54 是纯重构阶段，目标是清理 `codex` 品牌残留（dialect key、文件名、alias）并评估 `http-claude` 等路由名的去品牌化可行性。无功能变化，无新 Agent，无新 LLM 调用。核心风险集中在两处序列化边界：`BUILTIN_DIALECTS["codex_fim"]` 查找键与 `AuditTriggerPolicy.auditor_route` 持久化字段。

# Phase 54 Kickoff: Taxonomy 命名与品牌残留清理

## 基本信息

| 字段 | 值 |
|------|-----|
| Phase | 54 |
| Primary Track | Agent Taxonomy |
| Secondary Track | Provider Routing |
| 目标 tag | v1.0.0 (Naming Cleanup) |
| 前置 phase | Phase 53 (v1.0.0) |

## 战略定位

Phase 53 完成了 Specialist Agent 体系的全面落地，系统进化逻辑已完全显式化。Phase 54 的使命是**清理历史品牌名残留**，使代码库的命名语义与 `AGENT_TAXONOMY.md §6` 定义的 `[role]/[site]/[authority]/[domain]` 格式对齐，同时消化 Phase 52 遗留的 CONCERN（`codex_fim` dialect 未去品牌化）。

完成后，代码库中不再有 `codex`（已废弃的 OpenAI 产品名）作为活跃标识符出现在非 legacy/backward-compat 上下文中。

## 品牌残留清单与处置策略

### 主要目标：`codex_fim` dialect 清理

| 位置 | 当前状态 | 处置 |
|------|---------|------|
| `BUILTIN_DIALECTS["codex_fim"]` in `executor.py` | 活跃查找键 | 重命名为 `"fim"`，保留 `"codex_fim"` shim |
| `FIMDialect.spec.name = "codex_fim"` in `codex_fim.py` | dialect 身份标识 | 改为 `"fim"` |
| `dialect_adapters/codex_fim.py` 文件名 | 文件名含品牌 | 重命名为 `fim_dialect.py` |
| `CodexFIMDialect` alias in `__init__.py` | backward-compat alias | 保留，加 deprecation 注释 |
| `router.py` line 428 `dialect_hint="codex_fim"` | http-deepseek 路由引用 | 更新为 `"fim"` |
| `LEGACY_MODEL_HINT_ALIASES: {"codex": "fim"}` in `cost_estimation.py` | 已是 legacy alias | 保留不动（已是迁移机制） |

### 次要目标：`http-claude` 路由名评估

`http-claude` 是 `AuditTriggerPolicy.auditor_route` 的持久化默认值，重命名需要 `from_dict()` fallback。评估后**本 phase 不重命名**，原因：
- `http-claude` 描述的是 transport（http）+ backend（claude），是合理的描述性名称，不是纯品牌名
- 重命名需要 SQLite 迁移，风险超出本 phase 的"低风险纯重构"定位
- `http-gemini` 同理，保留

### 低优先级：`doctor codex` CLI alias

`cli.py` 中 `doctor codex` 已标注为 deprecated alias。本 phase 可选择移除或保留，不影响功能。

## 目标 (Goals)

1. **`codex_fim` → `fim` dialect 重命名**：更新 `DialectSpec.name`、`BUILTIN_DIALECTS` 键、`router.py` 引用，保留 backward-compat shim。
2. **`codex_fim.py` → `fim_dialect.py` 文件重命名**：更新所有 import 路径，保留 `CodexFIMDialect` alias。
3. **测试更新**：更新引用 `"codex_fim"` 字符串的测试 fixture 和断言，保留 shim 路径的回归测试。
4. **消化 Phase 52 CONCERN**：`codex_fim` 去品牌化完成后，在 `concerns_backlog.md` 中标记该条目为 Resolved。

## 非目标 (Non-Goals)

- **不重命名 `http-claude` / `http-gemini` 路由**：持久化字段风险超出本 phase 定位。
- **不移除 `LEGACY_ROUTE_ALIASES`**：`local-codex → local-aider` 等已是迁移机制，不是残留。
- **不修改 `"gemini"` model hint**：这是具体 API 模型标识符，不是 taxonomy 品牌名。
- **不引入新功能、新 Agent、新 LLM 调用**。
- **不做 `[role]/[site]/[authority]/[domain]` 格式的全面推行**：路由名不在 taxonomy 命名格式的强制范围内（taxonomy 格式适用于实体身份，不适用于路由注册键）。

## Slice 拆解

### S1: `codex_fim` dialect 重命名

**目标**：将 `codex_fim` 从活跃标识符降级为 legacy alias。

**变更清单**：
- `dialect_adapters/codex_fim.py` → `dialect_adapters/fim_dialect.py`（文件重命名）
- `FIMDialect.spec.name` 改为 `"fim"`
- `BUILTIN_DIALECTS` 键从 `"codex_fim"` 改为 `"fim"`，保留 `"codex_fim": _lazy_fim` shim
- `router.py` `dialect_hint="codex_fim"` 改为 `"fim"`
- `dialect_adapters/__init__.py` 更新 import 路径，保留 `CodexFIMDialect` alias
- 所有 `from .codex_fim import` 改为 `from .fim_dialect import`

**验收条件**：
- `FIMDialect.spec.name == "fim"`
- `BUILTIN_DIALECTS["fim"]` 可解析，`BUILTIN_DIALECTS["codex_fim"]` 仍可解析（shim）
- `resolve_dialect("codex_fim")` 返回 `FIMDialect` 实例（backward compat）
- 全量 pytest 通过

### S2: 测试与 concerns_backlog 收口

**目标**：更新测试引用，标记 Phase 52 CONCERN 为 Resolved。

**变更清单**：
- 更新 `tests/` 中引用 `"codex_fim"` 字符串的 fixture 和断言（主路径改为 `"fim"`，shim 路径保留一条回归测试）
- `concerns_backlog.md`：将 Phase 52 `codex_fim` CONCERN 移至 Resolved 区

**验收条件**：
- 无测试引用 `"codex_fim"` 作为主路径（仅 shim 回归测试保留）
- `concerns_backlog.md` Phase 52 条目状态更新
- 全量 pytest 通过

## 设计边界

- **只降级，不删除**：`"codex_fim"` 键和 `CodexFIMDialect` alias 保留为 shim，不立即删除，避免破坏外部依赖。
- **文件重命名使用 git mv**：保留 git history，不是新建文件。
- **不触碰序列化边界**：`AuditTriggerPolicy.auditor_route` 默认值不变，`LEGACY_MODEL_HINT_ALIASES` 不变。

## 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| `BUILTIN_DIALECTS["codex_fim"]` 查找键重命名破坏现有 TaskState | 低 | 保留 shim，`resolve_dialect_name()` 两个键均可解析 |
| 文件重命名破坏 import | 低 | 更新所有 import，`__init__.py` 保留 `CodexFIMDialect` alias |
| 测试 fixture 字符串未全部更新 | 低 | S2 专门处理，全量 pytest 验证 |

**Phase 54 整体风险评级：低**

## 依赖与前置条件

- Phase 53 (v1.0.0)：Specialist Agent 体系稳定，`EXECUTOR_REGISTRY` 已落地
- Phase 52 CONCERN：`codex_fim` 去品牌化是本 phase 的主要驱动力
