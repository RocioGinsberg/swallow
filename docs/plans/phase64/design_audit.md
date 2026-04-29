---
author: claude/design-auditor
phase: phase64
slice: design-audit
status: revised-after-model-review
depends_on: ["docs/plans/phase64/design_decision.md", "docs/plans/phase64/model_review.md"]
---

TL;DR: concerns-only — 2 slices audited, 4 issues found (0 BLOCKERs, 4 CONCERNs). Both original BLOCKERs are fully resolved. All 4 GPT-5 BLOCKs are consumed. 4 CONCERNs remain that require explicit assumption-logging by Codex but do not block start of work.

## Audit Verdict

Overall: concerns-only

---

## GPT-5 BLOCK Resolution Status

| BLOCK | Claimed Fix | Verified? |
|-------|-------------|-----------|
| Q1 守卫语义未锁定 | Pivot 2: 守卫 = "executor 不调 selection 函数"; allow-list 和 docstring 明确 | YES — selection function set authoritative in design_decision §S1 line 84 |
| Q2 单跳隐性 invariant | Pivot 1: orchestrator 预解析整条 chain (`tuple[str,...]`) + 环检测 pseudocode | YES — pseudocode is complete and correct; see chain analysis below |
| Q4 helper 破环 Codex decides | 强制中性模块 `_http_helpers.py` + authoritative symbol 清单 | YES — design_decision §S2 table is specific and binding |
| Q9 httpx.post 守卫过宽 | 细化为 chat-completion URL pattern (3段 AST 规则) | YES — pattern is precise and handles the embeddings case explicitly |

Original design_audit BLOCKERs:
- S1-1 (`RouteSpec.from_dict` 不存在): RESOLVED — pivot to `tuple[str,...]` eliminates deserialization entirely.
- S1-2 (`_load_fallback_route` 签名矛盾): RESOLVED — new design uses 3-param signature `(state, current_route_name, visited_routes)`; 2-call-site change documented at design_decision line 47.

---

## Issues by Slice

### Slice S1 — Path B fallback chain plan + lookup_route_by_name

- [READY] Chain plan pivot design is internally consistent. Original BLOCKERs fully resolved.

- [CONCERN] **Chain traversal algorithm produces a correct result for current ROUTE_REGISTRY, but the risk_assessment description of the "互链" scenario contains a factual error that could mislead Codex.** risk_assessment R2 (line 63) states: "ROUTE_REGISTRY 当前 fallback 静态: `http-glm` ↔ `http-qwen` (line 354/378 互链) 实际就是 chain depth 2 + 环". The actual ROUTE_REGISTRY is NOT a symmetric mutual cycle. Verified from source:
  - `router.py:354` `http-claude` → fallback `http-qwen`
  - `router.py:378` `http-qwen` → fallback `http-glm`
  - `router.py:402` `http-glm` → fallback `local-claude-code`
  - `router.py:474` `local-claude-code` → fallback `local-summary`
  - `router.py:282/306` `local-aider`/`local-codex` → fallback `local-summary`

  The `http-glm` → `http-qwen` mutual cycle claimed in the risk assessment does not exist; the actual chain starting from `http-claude` is a 4-hop linear chain with no mutual cycle. Codex must run the chain plan algorithm against the correct ROUTE_REGISTRY graph (not the erroneous description) when writing regression tests. The algorithm itself handles both linear chains and true cycles correctly — the bug is only in the test scenario description, not in the algorithm.

- [CONCERN] **Reentrant fallback path through `_run_executor_for_fallback_route` (executor.py:552) does NOT currently pass `visited_routes` back into `_apply_executor_route_fallback`.** The current code at executor.py:724 calls `_run_executor_for_fallback_route(state, retrieval_items, visited_routes=seen_routes | {fallback_route.name}, ...)` which calls `run_prompt_executor` (executor.py:561), which calls `_apply_executor_route_fallback` again. The key question for the S1 pivot: after S1, when executor re-enters `_apply_executor_route_fallback` on a second-hop failure, it will again call the new `_load_fallback_route(state, current_route_name, visited_routes)`. At that point, `current_route_name` will be the first-hop fallback (e.g., `http-qwen` if starting from `http-claude`), and `visited_routes` will be passed through `run_prompt_executor` → `_apply_executor_route_fallback` via the `visited_routes` parameter (executor.py:701). This means the chain lookup needs to find `http-qwen` in the chain tuple and return the next entry (`http-glm`). This works correctly as long as the chain tuple was pre-resolved starting from the *primary* route name (not the fallback), so the full chain `("http-claude", "http-qwen", "http-glm", "local-claude-code", "local-summary")` is available. However: `state.fallback_route_chain` is written once at `select_route` time based on the primary route. When `_apply_route_spec_for_executor_fallback` mutates `state.route_name` to the fallback name (executor.py:518), the chain in `state.fallback_route_chain` still references the full original chain — so subsequent `_load_fallback_route` calls can still locate the new current position by searching `current_route_name` in the tuple. This logic is sound. **The concern is that design_decision does not explicitly state that `state.fallback_route_chain` must NOT be mutated when `_apply_route_spec_for_executor_fallback` runs.** If Codex naively adds `state.fallback_route_chain = ...` inside `_apply_route_spec_for_executor_fallback`, subsequent hops will break. Codex must treat `fallback_route_chain` as read-only after initial pre-population. The design should make this immutability expectation explicit.

- [READY] `lookup_route_by_name` as single-line forwarder to `route_by_name` is correct. The `-detached` suffix expansion in `route_by_name` (router.py:774-777) will work transparently. No additional design needed.

- [READY] MPS path: `synthesis.py:141 _participant_state_for_call` uses `dataclasses.replace(base_state, ...)`. design_decision §S1 correctly calls for `_apply_route_selection_with_fallback_chain` helper to also populate `fallback_route_chain` based on the participant's resolved route. The synthesis code at line 142-163 does an explicit `replace(base_state, ...)` without `fallback_route_chain`, so after S1, `participant_state.fallback_route_chain` will inherit `base_state.fallback_route_chain` (the primary route's chain, not the participant's). design_decision §S1 line 79 correctly addresses this with the shared helper. This is an implementation requirement, not an open design question — confirmed ready.

- [READY] Guard anti-vacuous anchor: design_decision §S1 line 87 anchor (`assert hasattr(swallow.router, "fallback_route_for")`) confirms the selection function exists so the scan target is non-empty. This is better than the original audit's concern about checking `_load_fallback_route` existence. Acceptable.

---

### Slice S2 — Helper 中性模块 + Provider Router invoke_completion seam

- [READY] `_http_helpers.py` authoritative symbol table is complete and specific. The `clean_output` and `_normalize_http_response_content` conditional-migration approach ("Codex spike to confirm if router.invoke_completion needs them") is the one remaining underdetermined point, but design_decision §S2 table explicitly marks these as "Codex spike 时确认", and the consequence of either path is bounded (move or don't move). This does not block start of S2.

- [CONCERN] **`invoke_completion` template in design_decision §S2 (lines 138-191) references `_resolve_invoke_completion_model(model)` as an internal helper (line 164), but this function is not defined anywhere and is not listed in the `_http_helpers.py` symbol table.** The actual `call_agent_llm` in agent_llm.py:50 calls `resolve_agent_llm_model(model)`, which is defined in agent_llm.py:34-35 as `return resolve_swl_chat_model(explicit_model=explicit_model)`. The design states (risk_assessment R4, line 97) that `invoke_completion` "should maintain the same calling chain" i.e., must call `resolve_agent_llm_model` or an equivalent. But `resolve_agent_llm_model` is defined in `agent_llm.py`, which after S2 should import FROM router (not the other way around). If `invoke_completion` in `router.py` imports `resolve_agent_llm_model` from `agent_llm.py`, it creates a circular import: `agent_llm → router → agent_llm`. The design does NOT specify where `resolve_agent_llm_model` lives after S2, and the `_http_helpers.py` symbol table does not include it. Codex must either (a) inline the one-liner `model or resolve_swl_chat_model(explicit_model=model)` directly in `invoke_completion` (skipping `resolve_agent_llm_model` wrapper entirely, which is acceptable since that wrapper is itself a one-liner), or (b) move `resolve_agent_llm_model` to `_http_helpers.py`. The design is silent on this. Codex will need to make an assumption; it should document the choice in the PR body.

- [CONCERN] **The AST pattern for `test_specialist_internal_llm_calls_go_through_router` has an underspecified node-matching rule for `httpx.AsyncClient(...).post(url, ...)` at executor.py:1320-1321.** design_decision §S2 (lines 213-216) says: "查所有 `httpx.post(url, ...)` 与 `httpx.AsyncClient(...).post(url, ...)` 调用节点." The direct `httpx.post(...)` form is a `Call(func=Attribute(value=Name('httpx'), attr='post'))` node — straightforward to match. The `client.post(...)` form is `Call(func=Attribute(value=<client-expr>, attr='post'))` where the value is NOT `Name('httpx')` directly. The design does not give an AST pattern for how to identify `httpx.AsyncClient().post(...)` as distinct from any other `.post()` call (e.g., a requests session). Since the guard's URL-pattern matching (step 2) would still reject this call if the URL doesn't contain `/chat/completions`, the practical risk is low for the current codebase (executor.py:1321 uses `resolve_new_api_chat_completions_url()` which IS a `Call(Name("resolve_new_api_chat_completions_url"))` — it would be caught by step 2 rule 2 if it were in a non-allow-list file). executor.py IS in the allow-list. But the guard implementation needs a concrete decision on whether to match `AsyncClient().post` at all for the url-pattern check. Codex needs to decide this and document it.

- [READY] `route_hint` is dropped entirely. No behavior contract needed. Verified in kickoff non-goals (line 82) and design_decision §S2 signature (line 224). This is clean.

- [READY] `call_agent_llm` thin-caller pattern at design_decision §S2 (lines 194-204) is correct. The signature matches agent_llm.py:38-44 exactly. Test mock transparency is maintained because `patch("swallow.agent_llm.call_agent_llm")` still intercepts at the module boundary.

- [READY] Integration smoke test requirement (design_decision §S2 line 208) is a hard requirement for S2 PR body. This adequately addresses the original design_audit CONCERN about test fixture coverage.

---

## Questions for Claude

1. **[for CONCERN S1-2 immutability] Should `state.fallback_route_chain` be explicitly documented as "do not mutate after pre-population"?** design_decision §S1 does not say this anywhere. Suggest adding one sentence to the `_apply_route_spec_for_executor_fallback` description noting that `fallback_route_chain` is intentionally NOT updated in that function. Otherwise Codex may symmetrically update it alongside other `state.route_*` fields.

2. **[for CONCERN S2-1 model resolution] Where does `resolve_agent_llm_model` (currently in `agent_llm.py:34`) live after S2?** Options: (a) inline the single line `model or resolve_swl_chat_model(explicit_model=model)` directly in `invoke_completion` — no import needed; (b) move to `_http_helpers.py` and add to symbol table. The template at design_decision line 164 references `_resolve_invoke_completion_model(model)` which does not exist — this name needs to be resolved before Codex implements.

---

## GPT-5 CONCERN Resolution Status

| CONCERN | Claimed Fix | Verified? |
|---------|-------------|-----------|
| Q3 route_hint 契约 | route_hint dropped entirely (YAGNI) | YES |
| Q5 retrieval scope-in 守卫名 | 守卫 docstring 显式注明 retrieval 包含理由 | YES — kickoff line 68-70 |
| Q6 RouteSpec.from_dict 工程化 | Pivot eliminates serialization entirely | YES |
| Q7 拆 Phase 64.5 | 不拆,理由明确 | YES |
| Q8 测试 mock blind spot | S2 PR body 强制 grep 清单 + integration smoke test | YES — design_decision line 206-208 |
| Q10 router god-module | Provider Router 概念边界声明 = 三合一 | YES — kickoff §设计边界 |
| Q11 dependency rule | dependency rule 表 in kickoff §设计边界 and risk_assessment | YES |

---

## Confirmed Ready

- S1 core algorithm: chain plan pseudocode is correct, `lookup_route_by_name` design is correct, 2-callsite change is documented.
- S2 symbol migration table: complete and authoritative.
- S2 `call_agent_llm` thin-caller: pattern is correct and test-transparent.
- S2 guard chat-completion AST pattern: 3-rule design handles embeddings correctly.
- Both guards anti-vacuous anchors: adequate.
- MPS participant path: design covers it with `_apply_route_selection_with_fallback_chain` shared helper.

**Codex can start S1 immediately.** The two CONCERNs in S1 are:
- S1-C1: Treat `fallback_route_chain` as read-only in `_apply_route_spec_for_executor_fallback`; document in PR body.
- S1-C2: Use the correct ROUTE_REGISTRY chain graph for regression tests (linear `http-claude → http-qwen → http-glm → local-claude-code → local-summary`, not the erroneous mutual-cycle description in risk_assessment R2).

**Codex can start S2 after S1 is merged.** The two CONCERNs in S2 are:
- S2-C1: Resolve `_resolve_invoke_completion_model` naming — either inline or move `resolve_agent_llm_model` to `_http_helpers.py`; document decision in PR body.
- S2-C2: Decide AsyncClient `.post()` AST matching strategy and document in PR body.
