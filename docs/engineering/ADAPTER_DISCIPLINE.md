---
author: claude
status: living-document
---

> **Document discipline**
> Owner: Human
> Updater: Human / Claude / Codex
> Trigger: 新 adapter 类型加入(driving 或 driven)、framework 升级导致原语行为变化、违反纪律的实战案例需归档为 worked example
> Anti-scope: 不维护 phase 状态、不替代 `INVARIANTS.md` / `CODE_ORGANIZATION.md` / `ARCHITECTURE_DECISIONS.md`、不维护具体 framework API 用法手册

TL;DR:
本文档把 LTO-13 audit Round 1-3 + post-merge follow-up 暴露的 16 项 framework-rejection 与 boundary 教训编纂为长期 adapter 实施纪律。
核心规则一句话:**"使用 framework 提供的能力 是默认选择,自写 helper 才需要书面理由"**。
六条规则 + 强制模块布局 + LTO-13 worked examples。任何新 adapter phase(MCP / desktop / 另一个 HTTP 实例 / 重写已有 adapter)开始前,起草人必须读完本文。

# Adapter Discipline

> 本文档与 `docs/engineering/ARCHITECTURE_DECISIONS.md`(架构身份)、`docs/engineering/CODE_ORGANIZATION.md`(目标分层)、`docs/engineering/GOF_PATTERN_ALIGNMENT.md`(模式词汇)并列。
> `INVARIANTS.md` 仍是宪法;本文不增加新不变量,只把 adapter 边界的实施纪律写明确。

适用范围:**所有 driving adapter**(`adapters/cli/`、`adapters/http/`、未来 MCP / desktop / 第二个 HTTP 实例),以及未来 **driven adapter** 的引入(SQLite / 文件系统 / LLM provider / HTTP client 等);见 `ARCHITECTURE_DECISIONS.md §1.1` 的 Hexagonal vocabulary。

---

## 1. Framework-Default Principle

**规则**:对 framework(FastAPI / Pydantic / click / uvicorn / 未来 MCP framework / httpx / SQLAlchemy 等)提供的任何能力 —— 请求/响应 schema、依赖注入、异常处理、错误响应格式、后台任务、OpenAPI / 等价 schema 自动生成、TestClient / 等价测试客户端 —— **默认使用 framework 原语**。自写 helper 需要在 adapter 模块顶部 docstring 或本文 §6 worked examples 区写明放弃 framework 原语的理由。

**理由**:不使用 framework 原语 = 自写一个 mini framework。每个不使用都是个体小决策,叠在一起就是一整套与 framework 平行的"我们自己的方案"。LTO-13 R3 audit 找到 6 处此类绕开,collectively re-implemented ~80% of what FastAPI already provides;每条单独看都"轻",叠加后 plan_audit 14 个 concerns 一半与此相关。

**不算违反的情况**:

- framework 原语**确实不能表达**当前需求(罕见;先通过本文 §6 worked example 论证)
- framework 行为与项目 INVARIANTS 冲突(此时 INVARIANTS 优先,记录在 `INVARIANTS.md`)
- adapter 启动期(`create_*_app(...)`)无法 lazy-evaluate 的硬约束(如 `api.py` 顶层 import 不能 hard-import FastAPI;但内部已经允许 use FastAPI 一切)

**算违反的情况(LTO-13 实例)**:

- 自写 response 转换器替代 `response_model=` Pydantic envelope(R3-1)
- 自写 try/except 错误 ladder 替代 `@app.exception_handler`(R3-2)
- 自定义 `WebRequestError` 复刻 `HTTPException`(R3-3)
- 用 `message.startswith(...)` 字符串匹配决定 HTTP status,替代 typed exception + handler(R3-4)
- `globals().update({...})` 给测试桥接 lazy-imported 模型,替代 `Depends` 注入(R3-5)
- 闭包捕获 `base_dir` 替代 `Depends(get_base_dir)`(R3-6)

---

## 2. Adapter Forbidden Zone

**规则**:driving adapter **不许做的事**(无书面例外;违反在 plan_audit 阶段必须 [BLOCKER]):

1. **不许编 state machine 规则**。Task / proposal / knowledge state transition 决策属于 application 层或 domain 层(见 `CODE_ORGANIZATION.md §2`);adapter 只能调用 application command 或 query。如需在 UI 渲染"是否可点"等条件,application 层必须暴露 backend-derived eligibility(见 LTO-13 R2-2 / `application/queries/control_center.py` `build_task_action_eligibility` 实例)。
2. **不许动 module global**。`globals().update({...})`、修改其他模块的属性、动态注入符号 —— 一律不允许。adapter 内的状态通过 `Depends` 或 `app.state` 传递,不通过 module 命名空间。
3. **不许在 schema 默认值编码"我是哪个 surface"**。`planning_source: str = Field(default="web", ...)` 这种是边界 leak —— "我是 web / cli / mcp" 应在 `OperatorToken(source="web")` 构造时由 adapter 显式声明,不在 request schema 里 hardcode(见 §4)。
4. **不许实现 domain validation**。请求 shape 校验(类型 / 必填 / 正则 / Literal 枚举 / `Field(min_length=...)` / `extra="forbid"` 等)由 framework 原语(Pydantic / click)处理 —— **这些都属于 shape 校验,不是 domain validation**。**领域校验**(staged candidate 是否存在、proposal path 是否在 workspace 内、task 是否处于可执行状态)由 application command 或 domain 层 raise typed exception,adapter 只 catch + 映射 HTTP status。
5. **不许直接 import domain / persistence / orchestrator 内部**。adapter 的 import 链应只到 `application/{commands,queries}/`(driving)或 `application/ports/`(driven),不能 reach `orchestration.*`、`knowledge_retrieval.*` 子模块、`truth_governance.sqlite_store`、`provider_router/` 内部 focused 模块等。LTO-13 C1 即此类违规(`schemas.py:12` 直接 import `knowledge_retrieval.staged_knowledge.StagedCandidate`,已在 review-fix 提交修复)。
6. **不许重新声明 application 字段集**。如果 application command 接收 N 个参数,adapter 的请求 schema 不应该独立维护"几乎相同但少一个字段"或"几乎相同但默认值不同"的版本 —— 这种 drift 在 application 改签名时无法被静态发现。如果差异确实存在(例如 `workspace_root` 不允许从 web 接收),用 schema `extra="forbid"` + 明确测试覆盖记录这一点(见 LTO-13 `tests/integration/http/test_web_write_routes.py:68` 实例)。

---

## 3. Adapter 模块布局(强制)

每个 driving adapter 的目录必须遵循以下文件分工。文件可以为空(early-stage),但**不允许把不同职责揉进一个文件**:

```
adapters/<surface>/
  api.py            # 仅 @app.post / @app.get 等路由声明 + 静态 mount + 启动期 @app.exception_handler 注册;每条路由 ≤10 行,无 try/except
  schemas.py        # 请求 + 响应 Pydantic 模型(同一个文件,对称);如规模过大,请拆为 schemas/{request,response}.py
  dependencies.py   # Depends 工厂(get_base_dir / get_operator_token / resolve_workspace_relative_file 等)
  exceptions.py     # adapter-内部的 typed exception(如 TaskActionBlockedError 携带结构化 detail);application 层 typed exception 不在此处定义
  server.py         # 进程启动入口(uvicorn.run / 信号处理 / host guard 等);可选,小项目放在 cli 或外部
  static/           # 仅 driving HTTP adapter 需要;静态资源
  __init__.py
```

**handler 注册位置**:`@app.exception_handler(...)` 在 `api.py` 的 `create_<surface>_app()` 启动期集中声明(见 LTO-13 `api.py:104-122` 实例),不必单独成文件。如果 handler 数量超过 ~10 个或带复杂逻辑,可拆出 `errors.py` 集中放 handler 实现 —— 但本文不强制此拆分,因为典型 adapter 的 handler 数量在 5-8 个,内联在 `api.py` 启动期更易读。

**禁止的命名**:

- `http_models.py`(LTO-13 用过此名,后已删除)—— 它实际上是 schemas.py 与 errors.py 的混合桶,违反单一职责
- `helpers.py` / `utils.py` —— 这是 dump-everything-here 的信号;每个 helper 应有明确归属
- `models.py` 在 adapter 下(与 `orchestration/models.py` / Pydantic 模型混淆)—— 用 `schemas.py`

**driven adapter 的对应布局**(D6 之后会用到):

```
adapters/<driven>/
  client.py         # 与外部资源交互的具体实现(httpx.Client 持有者 / SQLite connection / etc.)
  config.py         # adapter 配置 dataclass(timeout / retry / endpoint 等)
  port.py           # Protocol 声明(本来该在 application/ports/ 下,但 driven adapter 也可以 co-locate)
```

---

## 4. Surface-identity 规则

**规则**:"我是 web / cli / mcp / desktop" 这件事,**只能在 adapter 调用 application command 时作为参数显式传递**,通常通过 `OperatorToken(source="<surface>", actor=...)`。

- ❌ 不允许在 request schema 里编码:`planning_source: str = Field(default="web", ...)` 不是 surface identity 的位置
- ❌ 不允许在 application command 内部根据某些字段值"猜测"自己被哪个 adapter 调用
- ✅ adapter 在 `dependencies.py` 提供 `get_operator_token() -> OperatorToken`,返回硬编码的 `source="web"`
- ✅ application command 接收 `OperatorToken` 参数,据此填 audit / governance 字段

**当前 source 值快照**(下面这段是带日期的 snapshot,会随时间漂移;读时务必 grep 当前代码):

> 截至 **2026-05-03**,`OperatorToken.source` 合法值 = `cli / system_auto / librarian_side_effect`;**没有 `web` / `mcp` 值**。LTO-13 决定与 `cli` 共用(单用户本地工具,真实 actor 一致)。
>
> 权威来源:`src/swallow/truth_governance/governance_models.py` `OperatorToken.source` Literal 类型。

**何时需要新增 source 值**:

- 出现真实区分需求(audit log 需要按 surface 过滤、governance 决策依赖来源)
- 引入第三方 actor(MCP server 代表外部 LLM 行动,与本地 cli 用户身份不同)

新增 source 值需要修改 `truth_governance/governance_models.py` 的 `OperatorToken.source` Literal 并加测试,**不属于 adapter 单边动作**。

---

## 5. 错误映射规则

**规则**:领域 error 的 HTTP / CLI / MCP 状态映射,**必须基于 typed exception 派发**,不能基于 exception message 字符串匹配。

**实施**:

1. application command 在领域错误时 raise typed exception(`UnknownStagedCandidateError(ValueError)` / `StagePromotePreflightError(ValueError)` / 未来更多)
2. adapter 在 `errors.py` 用 `@app.exception_handler(...)` / click 错误回调 / MCP 错误响应 等 framework 原语,集中映射 typed exception → 该 surface 的状态码
3. **禁止**:`if message.startswith("Unknown ..."):` 这类反模式(LTO-13 R3-4 实例,已删除)
4. **禁止**:每条路由/命令 try/except ladder(LTO-13 R3-2 11 处实例,已删除)

**好处**:

- 上游修改 error message 文案不会静默改变状态码
- 新增领域 exception 类型 = 新增一个 handler,不需要触碰 N 处路由
- 多 adapter 之间映射规则各自定义但 application 层 typed exception 是共享的

---

## 6. Worked Examples(LTO-13 plan_audit 14 concerns 索引)

LTO-13 audit Round 1-3(`docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan_audit.md`)的 14 项 concerns 全部映射到本文规则。新 adapter phase 的 plan_audit 阶段应当**直接对照本表自查**:

| Concern ID | 违规规则 | 一句话教训 | 修复实例(可参照) |
|---|---|---|---|
| R1-1 | §2 #6(不许重新声明 application 字段集) | `workspace_root` 是 Truth 层 invariant,adapter 不能从 client 接收;用 `extra="forbid"` 拒绝 | `surface_tools/web/schemas.py` `WebRequestModel` `extra="forbid"` |
| R1-2 | §2 #5(不许直接 reach domain) | proposal `Path` 参数桥接走 application 公共 helper(workspace-relative path resolve),不能让 adapter 自己拼路径 | `dependencies.py` `resolve_workspace_relative_file()` |
| R1-3 | §1(framework-default) | dev 依赖必须在 `pyproject.toml` 声明,否则测试环境 ImportError 静默 skip | `pyproject.toml [project.optional-dependencies] dev` 加 `fastapi` |
| R1-4 | §2 #5 + §1 | guard test 必须**显式列出** application boundary 之外的禁止 import / call;`apply_proposal` / `create_task` / `run_task` 都加进去 | `tests/test_invariant_guards.py` `UI_FORBIDDEN_WRITE_CALLS` |
| R1-5 | §4(surface-identity) | `OperatorToken.source` 暂时与 `cli` 共用;新增 `web` 值是单独 phase | `application/commands/*.py` 调用 governance 时硬编码 `source="cli"`(2026-05-03 状态) |
| R1-Pyd | §1(framework-default) | "禁用 Pydantic" 把硬约束(顶层 import)与工具选型(schema 校验)耦合;Pydantic 随 FastAPI dev extras 自动装,实际不省依赖,只换来手写 coercion;请求体 schema 用 Pydantic | `surface_tools/web/schemas.py` Pydantic models |
| R2-1 | §1 + §2 #4 | 长跑路由必须**显式选择** sync 阻塞 vs fire-and-poll;LTO-13 选择 accept-long-request,UI 显示 pending 状态防重复提交;不能默认沉默 | `surface_tools/web/static/index.html` `pendingTaskAction` 状态 |
| R2-2 | §2 #1(不许编 state machine) | UI 按钮可见性必须由 backend `action_eligibility` 字段驱动,不能在 JS 里 if/else 判 status/phase | `application/queries/control_center.py` `build_task_action_eligibility()` |
| R2-3 | §1(framework-default,response_model) | 所有写路由必须声明 `response_model=`,响应 schema 在 OpenAPI 中可见;统一 envelope `{"ok": true, "data": ...}` | `surface_tools/web/schemas.py` `TaskEnvelope` 等 |
| R2-4 | §2 #1 + §3 | 安全相关 bypass(force / admin override / etc.)默认不暴露在 HTTP / MCP 等远端表面;CLI 保留逃生口;UI 想暴露需独立 confirmation UX phase | `surface_tools/web/schemas.py` `StageDecisionRequest` 不含 `force` 字段 + `extra="forbid"` |
| R2-5 | §3(adapter 模块布局,server.py) | 无认证写表面**必须在进程启动前**强制 loopback-only;非 loopback host 抛 RuntimeError | `surface_tools/web/server.py` `validate_loopback_host()` |
| R2-6 | §1 + §5(error 映射) | command result dataclass 字段不对称是 application 层事实(理想状态 application 应该 raise typed exception 而非返回 blocked field);adapter 用 typed exception 同化两类 blocked,不依赖 result 字段对称。**长期看 application 层应该统一 raise**,LTO-13 选择在 adapter 层吸收作为权宜 | `surface_tools/web/api.py` `_task_acknowledge_or_raise` 合成 `blocked_kind="acknowledge"` |
| R3-1 | §1 + §3 | 删除自写 response 转换器(`http_models.py`);Pydantic envelope + `response_model=` 唯一路径 | LTO-13 final 实现;`http_models.py` 已删 |
| R3-2 | §1 + §5 | `@app.exception_handler` 集中映射;每路由 ≤10 行,无 try/except | `api.py:104-122` 5 个集中 handler |
| R3-3 | §1(framework-default) | 不重复发明 `HTTPException`;adapter-内部 typed exception 仅用于"无法直接表达 HTTP 语义"的领域级阻断(如 `TaskActionBlockedError` 携带结构化 detail) | `exceptions.py` 仅保留 `TaskActionBlockedError` |
| R3-4 | §5(typed exception) | 删除 `_status_for_value_error` message 匹配;新增 `UnknownStagedCandidateError(ValueError)` typed | `application/commands/knowledge.py` |
| R3-5 | §2 #2(不许动 module global) | 删除 `globals().update`;`app.state.base_dir = base_dir` + `Depends(get_base_dir)` 是正解 | `api.py:100` + `dependencies.py:8` |
| R3-6 | §1 + §3(dependencies.py) | 所有 per-request 上下文走 `Depends`,不走闭包捕获 | `api.py` 每条路由 `Depends(get_base_dir)` |
| C1 (post-merge follow-up) | §2 #5(不许直接 reach domain) | adapter `schemas.py` 不能 import `knowledge_retrieval.*`;application 层补公共导出 | `application/commands/knowledge.py` 公共导出 `StagedCandidate`,`schemas.py` 改从此导入 |
| N1 (post-merge follow-up) | §3(adapter 模块布局) | `_static_dir()` 用 `Path.cwd()` 是 dead-arg;adapter 内部 path 解析应当显式从 `__file__` 推导 | `api.py:35-36` 已简化 |

---

## 7. 与已有文档的关系

- `INVARIANTS.md` —— 宪法。本文不增加新 invariant,只把 adapter 边界的实施细则写明。任何 adapter 决策与 INVARIANTS 冲突时 INVARIANTS 优先。
- `CODE_ORGANIZATION.md` —— 目标分层(`§2 Layer Duties` / `§3 Interface Standard`)。本文是 §3 Interface Standard 的施工标准。
- `ARCHITECTURE_DECISIONS.md` —— 架构身份(Hexagonal)+ 6 项偏离 D1-D6。本文是 D5(adapter discipline 编纂)的产出物。
- `GOF_PATTERN_ALIGNMENT.md` —— pattern 词汇。adapter 实施使用的 facade / strategy / repository 等命名仍走那份词汇。
- `TEST_ARCHITECTURE.md` —— 分层测试。adapter 测试归在 `tests/integration/<surface>/` 与 `tests/unit/adapters/<surface>/`。

---

## 8. 维护与触发

- 新 adapter phase 的 `plan.md` 起草前,起草人(Codex / Claude)必须读完本文。
- `plan_audit` 阶段 design-auditor 对照本文 6 条规则 + 模块布局逐项 check,违规默认 [BLOCKER]。
- 实战中若发现新的 framework-rejection 模式或新的 boundary leak 模式,作为 worked example 加进 §6,并同步更新对应规则(§1-§5)。
- 如果 framework 升级带来新原语(例如 FastAPI `lifespan` events 替代 startup/shutdown handler),issue 一个本文修订 phase,把新原语加入 §1 默认列表。
- LTO-13 是本文的诞生 case;后续 adapter phase 完成后,把它们的 audit 教训以同样格式追加到 §6,本文持续 living-document。
