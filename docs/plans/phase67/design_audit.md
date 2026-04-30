---
author: claude/design-auditor
phase: phase67
slice: design-audit
status: final
depends_on:
  - docs/plans/phase67/kickoff.md
  - docs/plans/phase67/design_decision.md
  - docs/plans/phase67/risk_assessment.md
  - docs/plans/phase67/context_brief.md
  - docs/plans/phase66/audit_index.md
  - docs/plans/phase66/audit_block5_surface_tools.md
  - docs/plans/phase66/closeout.md
  - docs/concerns_backlog.md
---

TL;DR: NEEDS_REVISION_BEFORE_GATE — 3 slices audited, 12 issues found (2 BLOCKER / 6 CONCERN / 4 SUGGESTION)

## Audit Verdict

Overall: NEEDS_REVISION_BEFORE_GATE

Two BLOCKERs affect M1 and M3 directly. Both are resolvable with targeted design text additions — no structural redesign required. The six CONCERNs each require an explicit assumption from Codex if unresolved; the two most impactful (B.1 and C.3) are in the critical M2 path.

---

## Issues by Slice

### Slice S1: Small Hygiene Cleanup (M1)

#### Q6 — SQLite PRAGMA f-string: ambiguous decision

- [BLOCKER] design_decision §S1.3 says: `f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}"` then immediately says "实装时 Codex 选清晰方案" (Codex chooses at implementation time). This is not authoritative. The PRAGMA string is SQL-level and the choice between f-string interpolation, a dedicated helper wrapper, and retaining the literal-with-comment approach has a correctness dimension: SQLite PRAGMA syntax accepts an integer literal directly (`PRAGMA busy_timeout = 5000`), but an f-string produces the same string so both are safe. However, "Codex chooses" creates ambiguity precisely in the one place where the design claims to be authoritative. The design must pick one and declare it. Position: f-string interpolation is the simplest and consistent with the constant-naming intent; the design should make that the explicit decision.
  - Location: design_decision.md §S1.3 line 85

#### Q8 — `models.py` dataclass field default importing from `review_gate.py` creates circular import risk

- [BLOCKER] design_decision §S1.6 says `models.py:641 reviewer_timeout_seconds: int = 60` should be "改为 import + 引用 DEFAULT_REVIEWER_TIMEOUT_SECONDS". However, `models.py` currently imports only stdlib (`dataclasses`, `datetime`, `typing`, `uuid`). `review_gate.py` imports from `.models` (confirmed: `from .models import ExecutorResult, TaskCard, TaskState`). If `models.py` were to import from `.review_gate`, a circular import would result: `models` → `review_gate` → `models`. The design does not acknowledge this constraint.
  - Two resolutions exist: (a) move `DEFAULT_REVIEWER_TIMEOUT_SECONDS` out of `review_gate.py` into a shared constants module (e.g., `constants.py` or `review_constants.py`) that both `models.py` and `review_gate.py` can safely import from; (b) keep `models.py:641` as a literal `60` and add a comment pointing to `review_gate.DEFAULT_REVIEWER_TIMEOUT_SECONDS` without an actual import. The design must choose one before Codex can start S1.6 safely.
  - Location: design_decision.md §S1.6; src/swallow/review_gate.py:10 (imports models); src/swallow/models.py (imports only stdlib)

#### Q5 — `_pricing_for` grep completeness

- [CONCERN] design_decision §S1.2 instructs Codex to run `grep -rn '_pricing_for' src/ tests/`. This misses `getattr(module, "_pricing_for")` dynamic dispatch and `from swallow.cost_estimation import _pricing_for` patterns in config / scripts / docs outside src/ and tests/. The risk_assessment §R2 labels this low probability and notes context_brief already confirmed no non-self callsite. Codex can proceed under the assumption: "run `grep -rn '_pricing_for' .` (full repo, not just src/tests/) before deletion and treat any match as a blocker." This should be stated in the design rather than left implicit.
  - Location: design_decision.md §S1.2 step 1

#### Q4 — `rank_documents_by_local_embedding` third option not evaluated

- [CONCERN] The design evaluates only (a) move to tests/eval/ and (b) keep + annotate, adopting (b). A third option — a dedicated `src/swallow/_eval_support.py` module that is still in src/ but clearly out of the production path — is not mentioned. This matters because adding `# eval-only` to a function in `retrieval_adapters.py` leaves the function importable from production code with no structural barrier. If future Codex authors fail to read the comment, the function may be called in production. The design should explicitly record why option (c) was not chosen (e.g., "insufficient payoff for a one-function extraction" or "eval functions in src/ are acceptable per project convention"). This is a CONCERN rather than BLOCKER because the chosen (b) is implementable immediately.
  - Location: kickoff.md §G1.2; design_decision.md §S1.1

#### Q7 — `[:4000]` semantic divergence fallback not authorized

- [CONCERN] design_decision §S1.4 says "Codex 实装时需读 surrounding 代码判断,不可机械替换。若发现某处其实是不同语义,新增独立常量." The three occurrences at retrieval_adapters.py:267/312/452 all pass `chunk_text=document.text[:4000]` to `score_search_document`, which is the same call in the same function family. The auditor confirmed all three are the same scoring context. However, the design authorization for creating an independent constant is open-ended: Codex might create `RETRIEVAL_EMBEDDING_SCORING_LIMIT` vs `RETRIEVAL_TEXT_SCORING_LIMIT` etc. The design should either (a) confirm that all three `[:4000]` in retrieval_adapters.py can share `RETRIEVAL_SCORING_TEXT_LIMIT`, or (b) explicitly state the fallback naming rule. Codex should not name constants independently without design authorization.
  - Location: design_decision.md §S1.4

#### Q8b — `planner.py:93` double-`60` literal not covered

- [SUGGESTION] `planner.py:93` line 93 reads `semantics.get("reviewer_timeout_seconds", 60)` and line 97 returns `60` as a fallback. Both are the same timeout semantic. If the design selects `DEFAULT_REVIEWER_TIMEOUT_SECONDS` from `review_gate.py` as owner, planner.py would need to import it too — but given the circular import BLOCKER above, the safe resolution (option b) would mean planner.py also gets a comment-only reference. The design should clarify whether planner.py:93 is in scope for S1.6 replacement or is deferred along with the models.py case.
  - Location: design_decision.md §S1.6; src/swallow/planner.py:93, 97

#### Q18a — MPS_POLICY_KINDS is a `set`, not a tuple; argparse `--help` output becomes nondeterministic

- [SUGGESTION] design_decision §S1.5 proposes `choices=MPS_POLICY_KINDS` where `MPS_POLICY_KINDS` is a Python `set` (confirmed: `mps_policy_store.py:15`). Argparse renders `choices` in `--help` by iterating the container. A `set` has nondeterministic iteration order in CPython across processes (even though within one run it is stable). The auditor confirmed empirically that running the help text 5 times produces two different orderings. The current literal tuple `("mps_round_limit", "mps_participant_limit")` has deterministic help output. The design should either (a) wrap: `choices=sorted(MPS_POLICY_KINDS)` or (b) require that `MPS_POLICY_KINDS` be changed to a `tuple` or `frozenset` with a defined order in `mps_policy_store.py`. This is a SUGGESTION because it does not block functionality, but it is a public CLI surface regression.
  - Location: design_decision.md §S1.5; src/swallow/mps_policy_store.py:15

---

### Slice S2: IO + Artifact Ownership (M2)

#### Q10 — §S2.2 table has 3 "Codex grep 验证" entries with no authoritative variant

- [CONCERN] design_decision §S2.2 mapping table lists `canonical_registry.py:65-91`, `staged_knowledge.py:92-104`, and `dialect_data.py:144-153` as "**Codex grep 验证**" with the variant cell "待定" or conditional. This means for these three callsites the design document does not provide authoritative guidance before implementation begins. The comment says "若 malformed → crash,改用 `read_json_strict`"... but `read_json_strict` is not in the variant list; the helper raises `FileNotFoundError` if missing and `JSONDecodeError` if malformed. None of the three "待定" cells specify which variant to use when Codex grep finds "malformed → crash." The design should pre-specify the mapping rule: "if current behavior is malformed → crash, use `read_json_strict`; if malformed → empty, use `read_json_or_empty`" so Codex can apply it autonomously. The current phrasing requires Codex to pause and write back to Claude, which is the R1 mitigation mechanism — but it places a synchronization burden that could delay M2 mid-implementation.
  - Location: design_decision.md §S2.2 table rows for canonical_registry / staged_knowledge / dialect_data

#### Q11 — `cli.py` private helpers have 77 internal callsites; delete-and-reimport scope is under-specified

- [CONCERN] design_decision §S2.4 says "删除 cli.py 私有 `load_json_if_exists` / `load_json_lines_if_exists`; 所有 callsite 改 import `_io_helpers`." The auditor counted 77 occurrences of these two helpers across cli.py (lines 378, 453, 564, 565, 590, 900–901, 1027–1041, 1179, 2400, 2443, 2986–2987, 3169, 3202–3237, 3417–3449, 3570–3572, 3641, 3729–3781 and more). The name mapping is `load_json_if_exists` → `read_json_or_empty` and `load_json_lines_if_exists` → `read_json_lines_or_empty`. However, the existing `load_json_lines_if_exists` in cli.py does NOT skip+warn on malformed lines — it calls `json.loads(stripped)` directly and will raise `JSONDecodeError` on a malformed line. The `read_json_lines_or_empty` helper in `_io_helpers.py` skips+warns instead. This is a **behavior change**: the current cli.py helper is strict on malformed lines; the replacement silently drops them. For read-only display commands this is likely acceptable, but the design should explicitly acknowledge this behavioral delta and confirm it is intentional.
  - Location: design_decision.md §S2.4; src/swallow/cli.py:623-632 (existing load_json_lines_if_exists body)

#### Q9 — `read_json_lines_strict` absence rationale is implicit

- [SUGGESTION] design_decision §S2.1 notes "不引入 `read_json_lines_strict`(JSONL 历史上无 strict 用法)". This is correct per the current callsite survey. However, M2 introduces `_io_helpers.py` as a shared module for future phases. When candidate O or a subsequent ingestion phase needs strict JSONL reading (e.g., a critical ingestion path that must fail on corruption rather than silently skip), it will need to either add `read_json_lines_strict` to `_io_helpers.py` or implement a fourth variant. The design non-decision ("not needed now") is fine, but should note: "if a strict JSONL variant is needed in future, add `read_json_lines_strict` to `_io_helpers.py` following the same pattern." This makes the design decision self-documenting for candidate O.
  - Location: design_decision.md §S2.1

#### Q12 — M3 dispatch table's `path_resolver` signature is inconsistent with real `paths.py` functions

- [CONCERN] design_decision §S3.1 pseudocode shows:
  ```python
  ARTIFACT_PRINTER_DISPATCH: dict[str, tuple[Callable[[Path, str], Path], Callable, Callable]] = {
      "summary": (summary_path, read_json_or_empty, _print_json_indented),
  ```
  Two problems:
  (a) `summary_path` does not exist in `src/swallow/paths.py`. The actual code uses `artifacts_dir(base_dir, task_id) / "summary.md"`. The design invents a function name that Codex cannot use without first creating it.
  (b) Some commands in the target range use `canonical_registry_path(base_dir)` (no `task_id` arg), while the pseudocode's signature is uniformly `Callable[[Path, str], Path]` (takes both `base_dir` and `task_id`). Commands like `canonical-registry`, `canonical-registry-index`, `canonical-reuse`, `canonical-registry-index-json`, and `canonical-reuse-json` call path functions that do not accept `task_id`. A single `Callable[[Path, str], Path]` type cannot accommodate both.
  The design must either (a) confirm the dispatch table uses `artifacts_dir(base_dir, task_id) / "filename.md"` inline tuples rather than function references, or (b) define wrapper lambdas / partial functions, or (c) acknowledge two dispatch tables with different signatures. The pseudocode as written cannot compile against the existing `paths.py` surface.
  - Location: design_decision.md §S3.1; src/swallow/paths.py (no `summary_path` function)

---

### Slice S3: CLI Read-Only Dispatch Tightening (M3)

#### Q13 — M3 scope description uses line range 3640–3830 but the actual read-only printer block starts at 3592

- [CONCERN] design_decision §S3.1 and §S3.2 repeatedly reference `cli.py:3640-3830` as the target range for table-driven dispatch. The auditor found that the block of read-only artifact printers actually begins at line 3592 with a set-membership dispatch block (`if args.task_command in {"summarize", "semantics", ..., "route"}`). This 21-command block (lines 3592–3645) is already partially table-driven (it uses a dict literal at 3615 to map command → filename). It is not in the design_decision's stated scope range (3640–3830), yet it is the largest contiguous read-only artifact printer block. If Codex strictly follows the line range and leaves 3592–3645 untouched, M3 will produce a result where:
  - Lines 3592–3645: already-partial dict dispatch, left as-is
  - Lines 3647–3787: converted to table-driven
  The resulting code will have two separate dispatch mechanisms for the same category of commands, which is worse than the current state. The design should explicitly state whether lines 3592–3645 are in scope for M3 and, if so, how they relate to the new ARTIFACT_PRINTER_DISPATCH table.
  - Location: design_decision.md §S3.1, §S3.2; src/swallow/cli.py:3592–3645

#### Q15 — dispatch table fallback behavior is unresolved

- [SUGGESTION] design_decision §S3.1 pseudocode shows `if handler is None: return None  # 或 raise NotImplementedError`. "或" (or) means Codex must choose. The design should specify which. `return None` is wrong (the caller `main()` returns the result of this function as the process exit code, and `None` is not a valid exit code). `raise NotImplementedError` is safe if the design intent is that M3 is complete and all read-only commands are in the table. If M3 is expected to be partial (some commands still in if-chain), then the fallback must return a sentinel (e.g., `-1` or a custom `_NOT_HANDLED` sentinel) so the caller can fall through to the existing if-chain. The design should state one of: (a) "M3 converts all read-only printers; fallback is `raise NotImplementedError` and can be validated by running all 20+ commands"; (b) "M3 is partial; fallback returns `_NOT_HANDLED = -999`; caller checks before returning." Without this, Codex will introduce a runtime bug.
  - Location: design_decision.md §S3.1 pseudocode comment

#### Q14 — 5 manual validation commands cover < 25% of the target set; `dispatch` command special case is not in the validation list

- [SUGGESTION] design_decision §S3.4 lists 5 validation commands out of 20+. The `dispatch` command (lines 3639–3645) has special conditional logic: `if args.task_command == "dispatch": load_state(...); if is_mock_remote_task(...): print("[MOCK-REMOTE]")`. If this command is included in M3's dispatch table (the design does not explicitly exclude it), its handler is not a simple `path_resolver → loader → formatter` triple; it requires additional state loading and conditional output. The 5 validation commands do not include `dispatch`. This means the most behaviorally complex command in the near-scope range is neither explicitly excluded from M3 nor included in the validation set.
  - Location: design_decision.md §S3.4; src/swallow/cli.py:3639–3645

---

## Cross-Milestone Issues

#### Q16 — M2 review "顺手修订" M1 path undefined

- [SUGGESTION] kickoff §G4 and design_decision §Review 分轮 say reviews are strictly per-milestone and Codex waits for verdict before proceeding. If M2 review discovers a M1 quick-win has a side effect (e.g., the `[:4000]` constant naming introduces a name that conflicts with another module's constant), the design does not specify whether Claude's M2 review can include a M1 retroactive fix directive, or whether a separate "M1 fixup" commit must be created after M2 review passes. The Phase 66 analogue was: "M2 主动接受 M1 review CONCERN-1 把 finding 升级到 high." Phase 67 review design should state the analogous rule: "if M2 review finds a M1 defect, Claude issues the fix directive in review_comments_block_m.md; Codex creates a fixup commit on the same branch before proceeding to M3." Without this, there is a process gap where M1 defects discovered late have no home.
  - Location: kickoff.md §G4; design_decision.md §Review 分轮机制

#### Q17 — Phase 67 closeout should explicitly declare "prepared for candidate O" items

- [SUGGESTION] design_decision §S2.5 says `_io_helpers.py` is designed for easy signature change in candidate O. kickoff §Phase 67 与候选 O 的衔接 explains the intent. However, neither document specifies that the Phase 67 closeout.md should record what was "pre-positioned for candidate O." If candidate O starts with a different team or after a long gap, there will be no artifact that says "Phase 67 made `_io_helpers.py` intentionally thin to support RawMaterialStore; see §S2.5." The design should require the Phase 67 closeout to include a "pre-positioned items" section explicitly naming `_io_helpers.py` signature thinness and the 11 callsites that will need updating in candidate O.
  - Location: kickoff.md §Phase 67 与候选 O 的衔接; design_decision.md §S2.5

---

## Answers to All 20 Audit Focal Questions

1. **三合一形态合理性**: The milestone-isolation-with-independent-review design is a genuine mitigation. The core audit_index warning risk ("design decision mixed with code cleanup in one review") is materially offset by the three separate `review_comments_block_{l,m,n}.md` files. This is the weakest-violation form as stated. However, it only works if the review_comments protocol is strictly enforced — the design relies on Codex waiting for `verdict: APPROVE` before proceeding. If Codex proceeds optimistically, the entire mitigation collapses. The design text should state the blocking condition more explicitly in kickoff §G4 rather than in a prose sentence.

2. **三 milestone 边界**: M1 → M2 is genuinely locked: M2 creates `_io_helpers.py` which M3 uses. M2 → M3 is locked: M3 dispatch table structure depends on M2's artifact name decision (§S2.3, locked to option a). The implicit dependency — that M3's dispatch table entries will call `read_json_or_empty` from `_io_helpers.py` — is only stated in the dependency diagram comment ("M2 IO helper 是 M3 read-only printer 的依赖") but not in M3's acceptance criteria. M3 acceptance criteria should explicitly require that `_io_helpers` is imported rather than inlining `json.loads`.

3. **M2 commit 边界**: kickoff §Branch Advice says "M2 (1-2 commit, IO helper + callsite 可拆)". The split criterion is clear in concept (helper creation vs callsite replacement), but the design should specify: "commit 1 = `_io_helpers.py` creation only, no callsite changes; commit 2 = all 11+ callsite replacements." This removes ambiguity about what constitutes a "clean" M2 commit 1.

4. **`rank_documents_by_local_embedding` option (b) long-term accumulation**: The concern is valid. The design's justification for (b) is sound for Phase 67 scope. The accumulation risk is real but belongs to a future evaluation: if eval-only functions proliferate in production modules, that becomes a Phase 66-style audit finding. For now, option (b) is implementable with `# eval-only` comment annotation and the auditor accepts this.

5. **`_pricing_for` grep completeness**: See Q5 above — CONCERN, not BLOCKER. The missing coverage is `getattr`-style and out-of-src/tests/ usage. The fix is a one-line change in the design: extend the grep scope to `.` instead of `src/ tests/`.

6. **SQLite PRAGMA string**: See Q6 above — BLOCKER. Must specify f-string or literal-with-constant before implementation.

7. **`[:4000]` naming with fallback**: See Q7 above — CONCERN. The three occurrences in retrieval_adapters.py are confirmed same semantic (all `score_search_document` calls). Design should confirm `RETRIEVAL_SCORING_TEXT_LIMIT` applies to all three.

8. **reviewer_timeout owner / circular import**: See Q8 above — BLOCKER. Cannot import `review_gate.DEFAULT_REVIEWER_TIMEOUT_SECONDS` into `models.py` without creating a circular import. Design must specify an alternative resolution.

9. **`read_json_lines_strict` absence**: See Q9 above — SUGGESTION. Not needed for Phase 67 but worth documenting in `_io_helpers.py` module docstring or design_decision for candidate O awareness.

10. **§S2.2 half-authoritative table**: See Q10 above — CONCERN. The three "Codex grep 验证" entries are incomplete without the mapping rule Codex should apply based on grep results.

11. **cli.py `load_json_lines_if_exists` behavior mismatch**: See Q11 above — CONCERN. The existing cli.py version raises `JSONDecodeError` on malformed lines; `read_json_lines_or_empty` silently skips+warns. This is a behavioral delta the design does not acknowledge.

12. **dispatch table pseudocode `path_resolver` mismatch**: See Q12 above — CONCERN, directly impacts M3 implementability. The function `summary_path` does not exist; the uniform signature `Callable[[Path, str], Path]` does not accommodate path functions that take only `base_dir`.

13. **M3 read-only subset completeness**: The design leaves the final list to "Codex in PR body", which means review happens after the fact. Given that `cli.py:3592-3645` (21 commands) is outside the stated line range but is the largest similar block, Codex may produce a half-converted state. The design should either explicitly include or exclude lines 3592–3645.

14. **5 manual validation commands**: See Q14 above — SUGGESTION. The `dispatch` command with its mock-remote conditional is the highest-risk handler in scope and is absent from the validation list.

15. **Fallback behavior**: See Q15 above — SUGGESTION. `return None` is a runtime bug if the fallback is ever reached; design must choose between `raise NotImplementedError` (M3 is complete) or a sentinel value (M3 is partial).

16. **M2 倒灌 M1 mechanism**: See Q16 above — SUGGESTION. Process gap; define in kickoff §G4.

17. **Candidate O closeout gap**: See Q17 above — SUGGESTION. Phase 67 closeout should explicitly list pre-positioned items.

18. **Scope: 8 [low] items / 7 quick-win**: The audit found that audit_index has exactly 8 [low]-severity findings across 5 blocks. The 7 quick-win items in Phase 67 M1 correspond to the quick-win candidates table in audit_index, which includes items of mixed severity (some [low], some [med]). The claim "7 quick-wins out of 8 [low] items, 1 漏掉" is a mischaracterization: the quick-win table and the severity matrix are not 1:1. The 7 quick-win items are drawn from across severity levels (e.g., "Name SQLite timeout/busy-timeout constants" is Block 1 finding 2 which is [low], "run_consensus_review" is Block 2 finding 1 which is [med][dead-code]). No low-severity item that belongs in M1 scope is missing. The non-goal of "not consuming [low] items outside quick-wins" is correctly scoped.

19. **kickoff completion conditions vs design_decision acceptance criteria**: The two documents are consistent. The only minor drift: kickoff §M3 completion says "audit_block5 finding 3 backlog 标 Partial 或 Resolved" but design_decision §S3 acceptance says "audit_block5 finding 3 backlog 标 Partial(M3 内 read-only 子集消化;governance write + task inspect/review 未做)". The design_decision is more specific and tighter. No gap.

20. **risk_assessment R1-R7 coverage in design_decision**: All 7 risks map to design_decision mitigations: R1 → §S2.2 authoritative table; R2 → §S1.2 grep steps; R3 → §S1.4 "三处一致"; R4 → §S3.4 byte-for-byte validation; R5 → §S3.5 "only change handler"; R6 → §S2.3 locked to option (a); R7 → §S2.5 thin interface. Coverage is complete.

---

## Additional Finding (not in the 20 focal questions)

#### A1 — `cli.py:load_json_lines_if_exists` is used in `task inspect` and `task review` blocks (out-of-M3-scope)

- [SUGGESTION] The 77 callsites of `load_json_if_exists` / `load_json_lines_if_exists` in cli.py include callsites inside the `task inspect` (lines 3199–3384) and `task review` (lines 3412–3558) blocks, which are explicitly out of M3 scope. If M2 (option i) deletes the cli.py private helpers and changes all callsites to import from `_io_helpers`, this will touch code in the `task inspect` and `task review` blocks as a side effect. This is functionally correct (same behavior, modulo the malformed-line behavior delta noted in Q11), but the change will surface in a M2 diff review alongside a M3 diff review — complicating the stated "M2 review does not touch CLI dispatch, M3 does" separation. The design should acknowledge that M2 callsite replacement will necessarily include inspect/review block callsites, and state that this is acceptable in the M2 review scope.
  - Location: design_decision.md §S2.4; src/swallow/cli.py:3202–3433

---

## Questions for Claude

1. (BLOCKER — Q6) §S1.3 SQLite PRAGMA: Is the authoritative decision f-string interpolation (`f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}"`)? If so, state it explicitly and remove "Codex 选清晰方案."

2. (BLOCKER — Q8) §S1.6 reviewer_timeout circular import: `review_gate.py` imports from `models.py`; `models.py` cannot import from `review_gate.py`. What is the resolution? Options: (a) move `DEFAULT_REVIEWER_TIMEOUT_SECONDS` to a new shared constants module; (b) keep `models.py:641` as literal `60` with a comment referencing `review_gate.DEFAULT_REVIEWER_TIMEOUT_SECONDS`; (c) other. Design must specify one.

3. (CONCERN — Q10) §S2.2: The three "Codex grep 验证" rows give no authoritative variant. Should the rule be: "if malformed → crash (no try/except around json.loads), use `read_json_strict`; if missing → empty (has FileNotFoundError guard), use `read_json_or_empty`"? Confirm or revise so Codex can apply autonomously without a pause.

4. (CONCERN — Q11) §S2.4: The existing cli.py `load_json_lines_if_exists` raises `JSONDecodeError` on malformed lines; `read_json_lines_or_empty` skips+warns. Is this behavioral delta acceptable for all 77 cli.py callsites, including callsites in `task inspect` and `task review`?

5. (CONCERN — Q12) §S3.1: `summary_path` does not exist in `paths.py`. Does the dispatch table use `artifacts_dir(base_dir, task_id) / "filename"` tuples instead of path function references? And how does the table handle commands whose path functions do not take `task_id` (e.g., `canonical-registry-path(base_dir)`)? The pseudocode's uniform `Callable[[Path, str], Path]` signature is incorrect for these.

6. (CONCERN — Q13) §S3.2: Is the set-membership block at `cli.py:3592-3645` (21 commands, already uses a dict for filename mapping) in scope for M3 table-driven conversion, or should it remain as-is? If in scope, M3 must reconcile two dispatch mechanisms into one.

7. (SUGGESTION — Q15) §S3.1 pseudocode fallback: Is M3 expected to be complete (all read-only printers converted → `raise NotImplementedError` is safe) or partial (some commands left in if-chain → need a sentinel return)? The pseudocode says "return None 或 raise NotImplementedError" and must be resolved.

8. (SUGGESTION — A1) §S2.4: Will M2's callsite replacement of cli.py private helpers necessarily touch `task inspect` and `task review` blocks (lines 3199–3558)? Should the M2 review explicitly note these out-of-scope-but-touched callsites?

---

## Confirmed Ready

The following design elements have no implementation-blocking issues:

- S1.1 `rank_documents_by_local_embedding` → option (b) keep + `# eval-only` annotation: implementable
- S1.2 `_pricing_for` deletion: implementable (pending Q5 grep scope expansion, which is minor)
- S1.4 `[:4000]` three-place replacement: implementable once Q7 is answered (confirm same constant)
- S1.5 MPS_POLICY_KINDS import: implementable (pending Q18a set-ordering fix, which is a one-word change to `sorted(MPS_POLICY_KINDS)`)
- S2.1 `_io_helpers.py` three variants code template: fully authoritative, implementable as written
- S2.2 authoritative table rows (8 of 11): implementable; only the 3 "Codex grep 验证" rows need Q3 answered
- S2.3 artifact name ownership → option (a): decision is locked, no implementation ambiguity
- S2.5 candidate O pre-positioning: no implementation action required
- S3.3 out-of-scope command list: clear and authoritative
- S3.4 5-command manual validation procedure: implementable
- S3.5 parser registration not changed: clear constraint
- Risk coverage R1–R7: complete; no unmitigated high-probability risks
