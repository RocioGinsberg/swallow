---
author: codex
phase: 54
slice: closeout
status: implemented_validated
depends_on:
  - docs/plans/phase54/kickoff.md
  - docs/plans/phase54/design_decision.md
  - docs/plans/phase54/risk_assessment.md
  - docs/active_context.md
---

## TL;DR
Phase 54 的命名清理已完成实现与验证。`codex_fim` 已降级为 legacy shim，主路径切到 `fim`，文件名已从 `codex_fim.py` 重命名为 `fim_dialect.py`，相关 router / executor / tests / concerns backlog 已同步收口。

# Phase 54 Closeout

## 结论

本轮围绕 taxonomy 命名清理的最小范围工作已经完成，核心边界保持不变：

- `FIMDialect.spec.name` 现为 `fim`
- `BUILTIN_DIALECTS["fim"]` 为主键，`BUILTIN_DIALECTS["codex_fim"]` 保留为 legacy shim
- `router.py` 的 `http-deepseek` 方言提示已切到 `fim`
- `CodexFIMDialect` alias 继续保留，用于 backward compatibility
- `docs/concerns_backlog.md` 中 Phase 52 的 `codex_fim` concern 已移入 Resolved

## 实现范围

### S1: dialect 命名清理

- `src/swallow/dialect_adapters/codex_fim.py` 重命名为 `src/swallow/dialect_adapters/fim_dialect.py`
- `FIMDialect.spec.name` 从 `codex_fim` 改为 `fim`
- `supported_model_hints` 主路径改为 `fim` / `deepseek` / `deepseek-coder`
- `src/swallow/dialect_adapters/__init__.py` 改为从 `fim_dialect` 导出
- `src/swallow/executor.py` 中 `BUILTIN_DIALECTS` 新增 `fim` 主键并保留 `codex_fim` shim
- `src/swallow/router.py` 中 `http-deepseek` 的 `dialect_hint` 改为 `fim`

### S2: 测试与收口

- `tests/test_dialect_adapters.py`、`tests/test_cli.py`、`tests/test_router.py`、`tests/eval/test_http_executor_eval.py` 的主路径断言改为 `fim`
- 保留一条 `codex_fim` legacy shim 回归测试
- `docs/concerns_backlog.md` 中 Phase 52 concern 已标记为 Resolved

## 验证结果

```text
.venv/bin/python -m pytest tests/test_dialect_adapters.py tests/test_router.py tests/test_cli.py tests/eval/test_http_executor_eval.py -q
→ 239 passed, 2 deselected, 5 subtests passed

.venv/bin/python -m pytest --tb=short
→ 452 passed, 8 deselected
```

## 当前边界

- `codex_fim` 仍保留为兼容 shim，不做 breaking change
- `doctor codex` alias 未移除
- `http-claude` / `http-gemini` 路由名未在本 phase 重命名

## Post-Implementation 状态

- 当前实现已完成，等待 Human 做 slice commit / 后续 PR 收口
- 若后续需要移除 `codex_fim` shim，应单独做一次迁移 phase，并在 SQLite / persisted state 边界上加明确迁移策略
