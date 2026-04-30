---
author: claude/design-auditor
phase: phase66
slice: design-audit
status: draft
depends_on:
  - docs/plans/phase66/kickoff.md
  - docs/plans/phase66/design_decision.md
  - docs/plans/phase66/risk_assessment.md
  - docs/plans/phase66/context_brief.md
  - docs/roadmap.md
  - docs/concerns_backlog.md
  - docs/plans/phase65/closeout.md
  - docs/plans/phase64/review_comments.md
---

TL;DR: NEEDS_REVISION_BEFORE_GATE — 3 slices audited, 9 issues found (1 BLOCKER, 5 CONCERN, 3 OK).

The BLOCKER is a self-contradictory dead-code algorithm that cannot be resolved by Codex assumption alone. Five CONCERNs cover file-count mismatches in validation criteria, an off-by-one skip-list count, a missing report-length cap, an ambiguous review handoff trigger, and the "tests/ role duality" that is never disambiguated. None of these are scope or design-direction problems — they are precision gaps that will cause Codex to make conflicting assumptions or fail self-verification steps.

---

## Audit Verdict

Overall: NEEDS_REVISION_BEFORE_GATE

The design's goal decomposition, finding taxonomy, finding template, hotspot guidance, read-only enforcement strategy, milestone sequencing, and risk categorisation are all well-specified for a first-time audit phase. The issues below are surgical text fixes, not redesign. The BLOCKER requires a one-sentence resolution to the test-callsite ambiguity. The CONCERNs can each be resolved with a sentence or a corrected number.

---

## Issues by Slice

### Slice S1: 块 1 + 块 3 audit (M1 — calibration + warm-up)

#### Focus 1 — 5-block split and 70-file attribution

- [OK] All 70 non-`__init__.py` files are covered. The context_brief §1 attribution tables correctly distributed all 29 previously unassigned non-`__init__` files into blocks 2, 4, and 5. No named file is missing or double-assigned.

- [CONCERN-1] The four subdir `__init__.py` files (`truth/__init__.py`, `ingestion/__init__.py`, `dialect_adapters/__init__.py`, `web/__init__.py`) are never explicitly assigned to a block in either context_brief §1 or design_decision. `find src/swallow -name '*.py'` returns 75 files, not 70. The design consistently says "70 個 .py 文件全部歸入某一塊" but the actual `find` count is 75. The top-level `__init__.py` is explicitly named in block 1. The four subdir `__init__.py` files are implicitly covered by the glob expressions `truth/*.py`, `ingestion/*.py`, `dialect_adapters/*.py`, `web/*.py` in the kickoff G1 block lists, but they appear in none of the context_brief §1 assignment tables and are not reflected in the validation-criteria file counts.

  Practical consequence for Codex: The S2 validation criterion "块4:18文件 / 块5:14文件" is wrong. The actual non-`__init__` file counts per block are: Block 4 = 23 files (18 named + ingestion/parsers.py + ingestion/filters.py + ingestion/pipeline.py + dialect_adapters/claude_xml.py + dialect_adapters/fim_dialect.py); Block 5 = 16 files (14 named + web/api.py + web/server.py). Codex running a self-check against "18 files" for block 4 will pass incorrectly. The four subdir `__init__.py` files will also be audited or silently skipped with no design guidance on which.

  This is implementable with the assumption "glob expressions supersede explicit counts," but Codex will need to make that assumption explicitly and the validation criteria will then be self-contradictory.

#### Focus 2 — finding 4-category criteria thresholds

- [BLOCKER-1] The dead-code algorithm at design_decision §S1 is internally contradictory and cannot be resolved by Codex assumption.

  Step 2 of the algorithm states: `grep -rn "<symbol>" src/swallow/ tests/` — both directories combined — and flags the symbol as dead when the combined hit count equals 1 (self-definition only). Step 3 then states: "测试覆盖但生产无调用(此条**算 dead**,因为生产路径不可达)." These two rules are mutually exclusive. If a function is called only by tests, the combined grep hits at least 2 (the definition in `src/` plus the call in `tests/`), so Step 2's "count = 1" condition does not trigger. Step 3 then says the same function IS dead. Codex cannot satisfy both rules simultaneously.

  The risk_assessment R1 section compounds this: the "over-loose tendency" example describes `callsite = 1 但 self-test 唯一 caller` as the over-loose direction, which is inconsistent with Step 3 (which declares test-only callsite = dead, meaning that detection is correct, not over-loose).

  To proceed Codex would have to silently choose one interpretation:
  - Option A: run separate greps — first `grep src/swallow/` only for production callsites; if production callsites = 0, grep `tests/` separately to confirm test-only usage and still flag as dead.
  - Option B: ignore Step 3 and treat any function called by tests as alive.
  
  These produce materially different finding counts in blocks where test coverage exists but production paths are absent. Codex cannot choose without a design fix.

- [CONCERN-2] The "9-line vs 10-line" edge case for duplicate-helper detection is not resolved. The design gives the threshold as "≥ 10 行高度相似" but provides no guidance for 9-line matches or for 10-line matches where 1 of 10 lines is semantically non-equivalent. The R1 risk acknowledges Codex subjective drift but treats this as mitigated by M1 calibration. At M1, Codex will encounter this edge before Claude has had a chance to calibrate. Codex will need to make an assumption (round down = don't report; round up = report). The assumption should be stated explicitly in the block report so Claude can calibrate it.

#### Focus 3 — skip list item count accuracy

- [CONCERN-3] The skip list count is off by one, and design_decision double-counts one item.

  Actual Open items in `concerns_backlog.md` as of audit date: 16 rows. These comprise 13 pre-Phase-65 Open items plus 3 Phase-65 known gaps. The context_brief §4 lists exactly 13 pre-Phase-65 items (Phase 45, 49, 50×2, 57, 58, 59, 61/63×2, 63 M2-1, 63 M2-5, 63 M3-1, 64 M2-2) yet states the total as "14 項." The missing 14th item does not exist; the count is a counting error that propagated from context_brief §4 into kickoff G4, design_decision §S1 skip list, risk_assessment R6, and design_decision TL;DR.

  Additionally, design_decision's total of 18 skip items is computed as "14 backlog + 3 Phase65 known gap + 1 Phase64 M2-2 = 18." But Phase 64 M2-2 is already one of the 13 (or claimed 14) backlog items, so it is double-counted. The correct unique skip total is 13 + 3 = 16.

  The kickoff TL;DR uses a different total (17 = 14 + 3, omitting the separate M2-2 term), creating a three-way inconsistency across kickoff / design_decision / risk_assessment.

  Practical consequence: when Codex lists "本块跳过的 backlog 编号," it will either list 14 (using the stated count) or 13 (using the actual Open table). When audit_index.md writes "18 項跳過 ✓," the number is incorrect. The mismatch is cosmetic in that all actual Open items ARE named in context_brief §4 and can be looked up by Codex, but the total is wrong and will fail any numerical audit check.

#### Focus 4 — finding template "建议处理" field

- [OK] The "建议处理" field does not create a real risk of Codex crossing the read-only boundary. The template examples ("推荐立刻删 / 推荐外部化到 routes.default.json / 推荐抽到 _http_helpers.py") are framed as recommendations Codex writes INTO the audit report for Claude to review, not as instructions for Codex to act on. The parenthetical "(Codex 给初判,Claude review 时核可)" makes the direction clear. The mention of `_http_helpers.py` as a suggested destination is a concrete recommendation within a finding, not an instruction to create a file. No revision needed.

#### Focus 5 — read-only boundary hardness

- [OK] The read-only boundary is hard and well-specified. Kickoff TL;DR explicitly states "不动任何代码/测试/文档(audit report 与 backlog 自身除外)," making audit reports and backlog the only writable files. Kickoff non-goals §1 repeats the prohibition including typos. risk_assessment R3 requires `git diff main -- src/ tests/ docs/design/` to be empty as a closeout gate. Codex auditing a typo in its own audit report draft is permitted (audit reports are the output product); Codex fixing a typo in `src/` is not. This distinction is clear.

---

### Slice S2: 块 4 + 块 5 audit (M2 — large files, multi-era)

#### Focus 6 — cli.py and orchestrator.py practical feasibility

- [CONCERN-4] A report-length cap for single-block audit reports is missing. context_brief §关键上下文 (final paragraph) explicitly recommended that design_decision "明确每块允许的 finding report 最长行数上限,避免块 2 audit report 失控膨胀." design_decision §S2 does not contain this guidance. The design does say Codex should scan cli.py "分段" by subcommand group and build a segment index, which mitigates the scan-complexity problem. However, there is no stopping condition for report length. If block 5 produces 30 findings with full template entries (each ~12-15 lines), the block 5 report grows to ~450 lines; block 2 could reach 600+ lines. Without a cap, Claude's per-milestone review has no committed surface bound.

  This is implementable but Codex will have to choose a report structure on its own. The assumption should be stated when Codex starts M2.

- [CONCERN-5] The scope statement "tests/ 不进 scope" is never disambiguated from the dead-code algorithm's use of `grep tests/`. Codex reading the non-goal ("不审 tests/ 目录") will correctly understand it as "do not generate findings about test code." But reading the dead-code algorithm ("grep -rn ... src/swallow/ tests/"), Codex might wonder whether it is allowed to grep `tests/` at all given the non-goal. These are two different roles: tests/ is excluded as an audit subject but used as a callsite oracle. Design_decision §S1 does not contain a sentence making this distinction explicit. When Codex explains the dead-code judgment basis in a finding, it will be unclear whether citing "grep tests/ shows 0 hits" is allowed.

#### Focus 7 — milestone 5-file coverage check for blocks 4 and 5

The file-count validation criteria error from Focus 1 / CONCERN-1 applies directly here. S2 validation criterion states "块4:18文件 / 块5:14文件." The actual non-`__init__` file counts are 23 and 16 respectively (see CONCERN-1 above for full derivation). Codex performing a self-check will get a false pass.

---

### Slice S3: 块 2 audit + audit_index (M3 — largest LOC, cross-block summary)

#### Focus 9 — review inter-milestone trigger

- [CONCERN-6] The 3-round milestone review model deviates from the standard feature.md workflow (Step 4 → all milestones → Step 5 Claude review once), and the deviation is not formally documented. More importantly, the trigger for Codex to start M2 after M1 review is undefined.

  In the standard workflow, Claude's review trigger is "Codex 实现完成,所有 milestones 代码由人工完成提交." In Phase 66's model, Claude reviews after M1 commit before M2 starts. design_decision §S3 says "Claude review 後 Codex 才進入下一 milestone," but does not specify:
  - What artifact or file signals "M1 review is complete"? A `review_comments_block1.md` file? A `review_comments.md` segment?
  - The review_comments file naming is left as "review_comments_block<n>.md (或合并到一個 review_comments.md 内分段)" — the "or" means Codex does not know which file to poll. If Claude writes `review_comments.md` with an M1 section, Codex cannot distinguish "M1 review complete, start M2" from "file exists but incomplete."

  This is implementable with the assumption "Human will signal Codex verbally when M1 review is committed," but the design should state this assumption explicitly rather than leaving Codex to infer the handoff convention.

#### Focus 10 — scope integrity: tests/ absence and tool ban

- [OK] The scope decisions are defensible and implementable as stated. Excluding `tests/` from audit findings is explained in kickoff (Phase 65 just added 21 tests, signal is not clean) and context_brief. The no-new-tools constraint (no vulture / pyflakes / radon / ruff) is stated as a Phase 66 constraint, leaving the tool evaluation to a future design phase. These are tight but consistent. The "architectural vs hygienic dead code" boundary (e.g., store.py JSON write paths dead because Phase 65 migrated to SQLite) is resolved by the dead-code rule itself: if callsite = 0, it is dead regardless of why. Codex citing "Phase 65 migration made this dead" as context is permitted and encouraged by the R5 mitigation ("强制标注 (Phase 65 new code)").

---

## Questions for Claude

1. **Dead-code algorithm — test callsite contradiction (BLOCKER-1):** Should Codex run two separate grep passes — first `grep src/swallow/` for production callsites (= 0 → candidate dead), then `grep tests/` to confirm test-only usage — rather than the single combined grep that makes Step 2 and Step 3 irreconcilable? Please specify the authoritative two-step process or pick one of the two interpretations.

2. **Skip list count (CONCERN-3):** The actual Open table in `concerns_backlog.md` has 13 pre-Phase-65 items (not 14), and Phase 64 M2-2 is one of those 13 (not an additional 14th+1). Please correct the skip-list count across kickoff G4 / design_decision TL;DR and §S1 / risk_assessment R6. The corrected unique skip total is 16 (13 pre-Phase65 + 3 Phase65 known gaps), and Phase 64 M2-2 should not appear as a separate addend.

3. **Validation criteria file counts (CONCERN-1):** Please update the S2 acceptance criterion from "块4:18文件 / 块5:14文件" to the correct counts that match the actual file system: Block 4 = 23 non-`__init__` files, Block 5 = 16 non-`__init__` files. Also please decide whether the 4 subdir `__init__.py` files (truth, ingestion, dialect_adapters, web) are assigned to their parent block (via the glob expression) or explicitly excluded as trivial (like the top-level `__init__.py` in block 1).

4. **tests/ role duality (CONCERN-5):** Please add one sentence to design_decision §S1's dead-code algorithm clarifying that `tests/` is excluded as an audit subject (per non-goal) but is used as a callsite oracle in grep commands. Without this, Codex may refrain from grepping `tests/` due to the non-goal.

5. **Milestone review handoff trigger (CONCERN-6):** Please specify the inter-milestone trigger convention. Options: (a) Claude commits `review_comments_block<n>.md` (named file per milestone, no "or"); (b) Human verbally signals Codex. Either is fine but should be the single authoritative answer so Codex knows what to wait for.

6. **Report length cap (CONCERN-4):** The context_brief explicitly flagged this as a needed addition to design_decision. Please add a max-line guidance for single-block reports (e.g., "block 2 audit report target ≤ 400 lines; if finding count requires more, create a summary section and move full entries to an appendix sub-section within the same file"). This is advisory but without it Codex has no stopping condition.

7. **9-line edge case for duplicate helper (CONCERN-2):** If Codex encounters 9-line high-similarity code across 2 files (just under the 10-line threshold), the design gives no ruling. Please confirm: strict threshold means 9 lines = NOT a finding, OR Codex may use judgment and flag it as [low] with explicit note "9-line, below threshold, flagged for calibration." This should be resolved before M1 calibration starts to avoid M1 becoming the calibration of the calibration.

---

## Confirmed Ready

- **S1 / Finding template field semantics:** The "建议处理" field is correctly scoped as Codex-authored recommendation for Claude review. The template examples do not constitute instructions to modify code. No revision needed.

- **S3 / Read-only boundary hardness:** The boundary is hard and self-consistent across kickoff, non-goals, and risk_assessment R3. The audit report self-correction exception (Codex may fix typos in its own audit output because audit reports are the Phase 66 output product) is implied by the parenthetical in kickoff TL;DR and is unambiguous.

- **S3 / Scope integrity — tests/ absence and tool ban:** Both decisions are explained, consistent with kickoff non-goals, and implementable without further clarification. The architectural vs. hygienic dead code boundary resolves automatically via the callsite = 0 rule.

- **S1 / Phase 65 new code tagging:** The requirement to tag findings in sqlite_store / truth/ with `(Phase 65 new code)` and add a tradeoff note is clear and actionable. The list of Phase 65 new files is named (sqlite_store.py, truth/route.py, truth/policy.py, truth/knowledge.py, truth/proposals.py).

- **S3 / audit_index Codex-recommendation section:** The "Codex 推薦下一阶段優先項" section in the audit_index template is bounded by "1-3 條" and explicitly says "Human 在新 Direction Gate 決定;Codex 不替決." This is not a scope drift into design work; it is structured advisory output.

- **S2 / cli.py segment scan strategy:** The design's instruction to scan cli.py by subcommand group and embed a segment index in audit_block5 is sufficient to make the 3832-line file tractable. No timeline cap is required for audit work.
