---
author: claude
phase: 54
slice: design
status: draft
depends_on:
  - docs/plans/phase54/kickoff.md
  - docs/plans/phase54/context_brief.md
  - src/swallow/executor.py
  - src/swallow/dialect_adapters/codex_fim.py
  - src/swallow/router.py
---

## TL;DR

Phase 54 的核心设计决策只有两个：(1) `codex_fim` 如何降级为 legacy alias——选择"双键注册 + spec.name 更新"而非"删除旧键"；(2) `http-claude` 路由名是否重命名——选择本 phase 不动，原因是持久化边界风险超出低风险定位。文件重命名（`codex_fim.py` → `fim_dialect.py`）是纯机械操作，无设计争议。

---

## 核心设计决策

### 决策 1：`codex_fim` dialect 降级策略

**问题**：`BUILTIN_DIALECTS["codex_fim"]` 是活跃查找键，`FIMDialect.spec.name = "codex_fim"` 是 dialect 身份标识。如何在不破坏现有 `TaskState.route_dialect = "codex_fim"` 的前提下完成去品牌化？

**候选方案**：
- A. 直接重命名：`"codex_fim"` → `"fim"`，删除旧键
- B. 双键注册：新增 `"fim"` 键，保留 `"codex_fim"` 作为 shim，`spec.name` 改为 `"fim"`
- C. 仅更新 `spec.name`，不动 `BUILTIN_DIALECTS` 键

**选择方案**：B（双键注册）

**理由**：
- A 会破坏任何持久化了 `route_dialect = "codex_fim"` 的 `TaskState`（SQLite 存储）
- C 造成 `spec.name`（`"fim"`）与 `BUILTIN_DIALECTS` 键（`"codex_fim"`）不一致，增加认知负担
- B 是最安全的迁移路径：新代码使用 `"fim"`，旧数据通过 shim 继续工作

**实现**：

```python
# executor.py — BUILTIN_DIALECTS
def _lazy_fim() -> DialectProtocol:
    from .dialect_adapters.fim_dialect import FIMDialect
    return FIMDialect()

BUILTIN_DIALECTS: dict[str, Callable[[], DialectProtocol]] = {
    "fim": _lazy_fim,
    "codex_fim": _lazy_fim,  # legacy alias — deprecated, use "fim"
    # ... 其他 dialect
}
```

```python
# fim_dialect.py — spec.name 更新
class FIMDialect:
    spec = DialectSpec(
        name="fim",  # was "codex_fim"
        description="FIM (fill-in-the-middle) format for code completion models.",
        supported_model_hints=["fim", "deepseek", "qwen-coder"],
    )
```

注意：`supported_model_hints` 中的 `"codex"` 也应移除（`"codex"` 是已废弃的 OpenAI 产品名，不是当前支持的 model hint）。

---

### 决策 2：`http-claude` / `http-gemini` 路由名处置

**问题**：`http-claude` 是 `AuditTriggerPolicy.auditor_route` 的持久化默认值，`http-gemini` 是路由注册键。是否在本 phase 重命名？

**候选方案**：
- A. 重命名为描述性名称（如 `http-claude-api`、`http-gemini-api`），`from_dict()` 加 fallback
- B. 本 phase 不动，留待后续 phase 处理
- C. 仅更新 `AuditTriggerPolicy` 默认值，不动路由键

**选择方案**：B（本 phase 不动）

**理由**：
- `http-claude` 描述的是 transport（http）+ backend（claude），是合理的描述性名称，不是纯品牌名（不同于 `codex` 这种已废弃产品名）
- `AuditTriggerPolicy.auditor_route` 是持久化字段，重命名需要 SQLite 迁移或 `from_dict()` fallback，风险超出本 phase 的低风险定位
- Phase 54 的主要驱动力是消化 Phase 52 CONCERN（`codex_fim`），`http-claude` 不在该 CONCERN 范围内

**残留**：`http-claude` 和 `http-gemini` 保留现状，不登记为新 CONCERN（它们是合理的描述性名称）。

---

### 决策 3：`codex_fim.py` 文件重命名策略

**问题**：文件名 `codex_fim.py` 含品牌名，是否重命名？如何处理 import？

**候选方案**：
- A. 重命名为 `fim_dialect.py`，更新所有 import
- B. 保留文件名，仅更新内容
- C. 新建 `fim_dialect.py`，`codex_fim.py` 改为纯 re-export shim

**选择方案**：A（重命名 + 更新 import）

**理由**：
- 文件名是最直观的品牌残留，重命名成本低（纯机械操作）
- B 造成文件名与内容不一致（文件叫 `codex_fim.py` 但内容是 `FIMDialect`）
- C 引入额外文件，增加复杂度

**实现**：
- `git mv src/swallow/dialect_adapters/codex_fim.py src/swallow/dialect_adapters/fim_dialect.py`
- 更新 `dialect_adapters/__init__.py` 的 import 路径
- 更新 `executor.py` 的 lazy import 路径
- 保留 `CodexFIMDialect = FIMDialect` alias（在 `fim_dialect.py` 末尾）
- 保留 `__init__.py` 中的 `CodexFIMDialect` re-export

---

### 决策 4：`doctor codex` CLI alias 处置

**问题**：`cli.py` 中 `doctor codex` 已标注为 deprecated alias。是否在本 phase 移除？

**候选方案**：
- A. 移除 alias
- B. 保留，不动

**选择方案**：B（保留）

**理由**：
- `doctor codex` 是 CLI 用户可能在脚本中使用的命令，移除是 breaking change
- 本 phase 定位是"低风险纯重构"，不做 breaking change
- 该 alias 已标注 deprecated，用户有足够提示

---

### 决策 5：`supported_model_hints` 中的 `"codex"` 处置

**问题**：`FIMDialect.spec.supported_model_hints` 包含 `"codex"`。是否移除？

**候选方案**：
- A. 移除 `"codex"`，保留 `"fim"`、`"deepseek"`、`"qwen-coder"`
- B. 保留 `"codex"` 作为 legacy hint

**选择方案**：A（移除）

**理由**：
- `supported_model_hints` 用于 dialect 选择路由，`"codex"` 作为 model hint 已无实际对应的 executor（`LEGACY_MODEL_HINT_ALIASES["codex"] = "fim"` 在 `cost_estimation.py` 中已是 legacy alias）
- 移除不影响任何现有路由（没有 `model_hint="codex"` 的活跃路由）
- 保留会误导开发者认为 `"codex"` 是当前支持的 model hint

---

## 变更文件清单

| 文件 | 变更类型 | 内容 |
|------|---------|------|
| `dialect_adapters/codex_fim.py` → `fim_dialect.py` | 重命名 | `spec.name` 改为 `"fim"`，移除 `"codex"` from `supported_model_hints` |
| `dialect_adapters/__init__.py` | 更新 import | `from .fim_dialect import FIMDialect`，保留 `CodexFIMDialect` re-export |
| `executor.py` | 更新 | `BUILTIN_DIALECTS` 新增 `"fim"` 键，保留 `"codex_fim"` shim；lazy import 路径更新 |
| `router.py` | 更新 | `dialect_hint="codex_fim"` → `"fim"` |
| `tests/` | 更新 | 主路径断言改为 `"fim"`，保留一条 `"codex_fim"` shim 回归测试 |
| `concerns_backlog.md` | 更新 | Phase 52 `codex_fim` CONCERN 移至 Resolved |

---

## 验收条件

| Slice | 验收条件 |
|-------|---------|
| **S1** | ✓ `FIMDialect.spec.name == "fim"` ✓ `BUILTIN_DIALECTS["fim"]` 可解析 ✓ `BUILTIN_DIALECTS["codex_fim"]` 仍可解析（shim）✓ `router.py` 不再引用 `"codex_fim"` ✓ 文件重命名完成，所有 import 更新 |
| **S2** | ✓ 测试主路径使用 `"fim"` ✓ shim 回归测试保留 ✓ `concerns_backlog.md` Phase 52 条目 Resolved ✓ 全量 pytest 通过 |

---

## 提交序列建议

1. `refactor(dialect): rename codex_fim.py to fim_dialect.py and update spec.name` — 文件重命名 + spec 更新
2. `refactor(executor): add "fim" as primary dialect key, keep "codex_fim" as legacy shim` — BUILTIN_DIALECTS 双键
3. `refactor(router): update dialect_hint from codex_fim to fim` — router 引用更新
4. `test(dialect): update fixtures to use fim as primary key, add codex_fim shim regression` — 测试更新
5. `docs(concerns): resolve phase52 codex_fim concern` — backlog 收口

## 实现时间估算

| 任务 | 估算工时 |
|------|---------|
| S1 - 文件重命名 + spec + BUILTIN_DIALECTS + router | 4h |
| S2 - 测试更新 + concerns_backlog | 2h |
| **总计** | **6h** |
