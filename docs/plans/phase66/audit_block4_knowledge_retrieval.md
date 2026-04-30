---
author: codex
phase: phase66
slice: audit-block4-knowledge-retrieval
status: review
depends_on:
  - docs/plans/phase66/kickoff.md
  - docs/plans/phase66/design_decision.md
  - docs/plans/phase66/risk_assessment.md
  - docs/plans/phase66/context_brief.md
  - docs/plans/phase66/review_comments_block1_3.md
  - docs/concerns_backlog.md
---

TL;DR: Block 4 audited 25 files / 5827 LOC with 12 findings: 1 high / 10 med / 1 low. Known retrieval/parser backlog items were skipped; `tests/` was used only as callsite oracle.

## Coverage

Audited files:

- `src/swallow/retrieval.py` - 913 LOC
- `src/swallow/retrieval_config.py` - 43 LOC
- `src/swallow/knowledge_objects.py` - 128 LOC
- `src/swallow/knowledge_partition.py` - 59 LOC
- `src/swallow/knowledge_policy.py` - 233 LOC
- `src/swallow/knowledge_review.py` - 243 LOC
- `src/swallow/knowledge_store.py` - 389 LOC
- `src/swallow/staged_knowledge.py` - 161 LOC
- `src/swallow/ingestion/__init__.py` - 41 LOC
- `src/swallow/ingestion/filters.py` - 232 LOC
- `src/swallow/ingestion/parsers.py` - 542 LOC
- `src/swallow/ingestion/pipeline.py` - 406 LOC
- `src/swallow/dialect_adapters/__init__.py` - 4 LOC
- `src/swallow/dialect_adapters/claude_xml.py` - 62 LOC
- `src/swallow/dialect_adapters/fim_dialect.py` - 59 LOC
- `src/swallow/dialect_data.py` - 276 LOC
- `src/swallow/canonical_audit.py` - 95 LOC
- `src/swallow/canonical_registry.py` - 222 LOC
- `src/swallow/canonical_reuse.py` - 66 LOC
- `src/swallow/canonical_reuse_eval.py` - 377 LOC
- `src/swallow/knowledge_index.py` - 113 LOC
- `src/swallow/knowledge_relations.py` - 121 LOC
- `src/swallow/knowledge_suggestions.py` - 191 LOC
- `src/swallow/grounding.py` - 84 LOC
- `src/swallow/retrieval_adapters.py` - 767 LOC

Block total: 5827 LOC.

Note: Phase 66 revised kickoff says block 4 includes parent globs. The actual audited set is 25 files, including `ingestion/__init__.py` and `dialect_adapters/__init__.py`.

## Skip List Applied

Loaded the Phase 66 skip list from `design_decision.md` and `docs/concerns_backlog.md`: 13 pre-Phase-65 Open items plus 3 Phase-65 known gaps, 16 total.

Block-specific skipped items:

- Phase 45: `_select_chatgpt_primary_path()` same-depth / same-create-time leaf heuristic in `ingestion/parsers.py`; already tracked, not counted.
- Phase 49: `retrieval.py` `_sqlite_vec_warning_emitted` global warning flag race; already tracked, not counted.
- Phase 57: `retrieval_adapters.py` `VECTOR_EMBEDDING_DIMENSIONS = resolve_swl_embedding_dimensions()` import-time fixed value; already tracked, not counted.
- Phase 58: `_is_open_webui_export` auto-detect semantic change; already tracked, not counted.
- Phase 64 M2-2: embedding HTTP calls in `retrieval_adapters.py` were not treated as chat-completion guard findings.

`tests/` was not audited as a subject. It was used only as a callsite oracle for dead-code checks, per Phase 66 design.

## Method

- File inventory: `wc -l` for the 25 block files.
- Symbol inventory: `rg -n '^def |^class |^[A-Z][A-Z0-9_]+\\s*='`.
- Dead-code check: two-pass grep per design, with `src/swallow/` as production callsite source and `tests/` as oracle only.
- Literal / helper checks: targeted `rg` for `json.loads`, `read_text`, `FileNotFoundError`, ingestion format strings, embedding/vector defaults, markdown heading regexes, chunk sizes, preview limits, and canonical reuse policy strings.

## Finding Summary

| Severity | dead-code | hardcoded-literal | duplicate-helper | abstraction-opportunity | Total |
|---|---:|---:|---:|---:|---:|
| high | 0 | 0 | 1 | 0 | 1 |
| med | 1 | 6 | 0 | 3 | 10 |
| low | 0 | 1 | 0 | 0 | 1 |
| **Total** | **1** | **7** | **1** | **3** | **12** |

The count is inside the design expectation for block 4(12-20 findings).

## Findings

### [high][duplicate-helper] JSON / JSONL loader patterns repeat across knowledge, canonical, retrieval, and surface paths

- **位置**:
  - `src/swallow/knowledge_store.py:123-143`
  - `src/swallow/staged_knowledge.py:92-104`
  - `src/swallow/canonical_registry.py:65-91`
  - `src/swallow/knowledge_suggestions.py:22-31`
  - `src/swallow/retrieval.py:588-600`
  - `src/swallow/retrieval.py:678-690`
  - `src/swallow/dialect_data.py:144-153`
- **判定依据**:
  - `rg -n 'json\\.loads|read_text|FileNotFoundError|except \\(OSError|except OSError|except json\\.JSONDecodeError'` across block 4 files shows multiple file-exists guard + `read_text` + `json.loads` + empty-fallback readers.
  - The JSONL registry readers in `staged_knowledge.py` and `canonical_registry.py` repeat the same loop shape as the M1 `_load_json_lines` finding, while JSON object readers in `knowledge_suggestions.py`, `retrieval.py`, and `dialect_data.py` repeat the same fallback contract.
  - This is broader than a single-file readability issue: the same IO contract is implemented in block 1, block 4, and block 5.
- **建议处理**:
  - In a later cleanup phase, centralize JSON object and JSONL loading helpers with explicit error-policy variants: strict, empty-on-missing, and empty-on-malformed.
  - Preserve current behavior differences; several callsites intentionally swallow malformed JSON while others should fail fast.
- **影响范围**:cross-block / cross-module.
- **关联**:M1 review CONCERN-1 asked M3 `audit_index.md` to consider upgrading `_load_json_lines` severity because the duplication crosses blocks.

### [med][dead-code] `rank_documents_by_local_embedding(...)` is eval-only and has no production callsite

- **位置**:`src/swallow/retrieval_adapters.py:249-292`
- **判定依据**:
  - `rg -n 'rank_documents_by_local_embedding\\(' src/swallow tests`
  - Production hits: only `src/swallow/retrieval_adapters.py:249` definition.
  - Test/eval hits: `tests/eval/test_vector_retrieval_eval.py:82`.
  - Per Phase 66 two-pass dead-code rule, test-only callsite = production-dead, marked med.
- **建议处理**:
  - In a later cleanup phase, either move the local embedding ranker under eval/test support or connect it to a production adapter path.
  - If removed from production, keep eval coverage by importing from a test helper.
- **影响范围**:single-file plus eval import.
- **关联**:none.

### [med][hardcoded-literal] Ingestion format names are embedded in parser dispatch and CLI surface

- **位置**:
  - `src/swallow/ingestion/parsers.py:10-15`
  - `src/swallow/ingestion/parsers.py:63`
  - `src/swallow/ingestion/parsers.py:84-92`
  - `src/swallow/ingestion/parsers.py:278-286`
  - `src/swallow/cli.py:1520` (cross-block consumer)
- **判定依据**:
  - `rg -n 'SUPPORTED_INGESTION_FORMATS|chatgpt_json|claude_json|open_webui_json|generic_chat_json' src/swallow/ingestion/parsers.py src/swallow/cli.py`
  - The same format taxonomy lives as `SUPPORTED_INGESTION_FORMATS`, parser branch literals, detector return values, and CLI `choices=...`.
  - Phase 66 hardcoded-literal rules count dialect / provider / format names as externalization candidates even when each appears in a controlled set.
- **建议处理**:
  - In a later cleanup phase, export a single tuple or enum-like data object from the parser layer and let CLI choices consume it.
  - Keep the Phase 58 `_is_open_webui_export` semantic concern skipped; this finding is only about duplicate spelling ownership.
- **影响范围**:cross-block parser / CLI surface.
- **关联**:Phase 58 auto-detect semantic change skipped, not counted.

### [med][abstraction-opportunity] Markdown heading parsing is implemented in three knowledge/retrieval paths

- **位置**:
  - `src/swallow/ingestion/parsers.py:17`
  - `src/swallow/ingestion/parsers.py:236-265`
  - `src/swallow/ingestion/parsers.py:299-312`
  - `src/swallow/ingestion/pipeline.py:30`
  - `src/swallow/ingestion/pipeline.py:388-406`
  - `src/swallow/retrieval_adapters.py:35`
  - `src/swallow/retrieval_adapters.py:551-688`
- **判定依据**:
  - `rg -n 'MARKDOWN_HEADING_PATTERN|LOCAL_MARKDOWN_HEADING_PATTERN|MARKDOWN_HEADING_RE|parse_markdown_text|_split_local_markdown|build_markdown_chunks' src/swallow/ingestion src/swallow/retrieval_adapters.py`
  - The parser, ingestion pipeline, and retrieval adapter all own heading regexes and section-splitting behavior.
  - The structures are not identical enough for a mechanical duplicate-helper finding, but they clear the N>=3 abstraction-opportunity threshold.
- **建议处理**:
  - Mark design-needed. A later phase can decide whether markdown heading parsing should be shared or remain deliberately context-specific.
  - Preserve the retrieval adapter's 0-3 leading-space tolerance if centralized.
- **影响范围**:cross-module.
- **关联**:none.

### [med][abstraction-opportunity] Conversation content extraction repeats list/dict text-normalization logic

- **位置**:
  - `src/swallow/ingestion/parsers.py:339-386`
  - `src/swallow/ingestion/parsers.py:390-413`
  - `src/swallow/ingestion/parsers.py:416-475`
- **判定依据**:
  - `rg -n '_extract_chatgpt_content|_extract_claude_content|_extract_open_webui_content|_extract_generic_chat_content|_normalize_generic_chat_content' src/swallow/ingestion/parsers.py`
  - ChatGPT, Claude, Open WebUI, and generic chat parsing each repeat "accept string, accept list of strings/dicts, pull text field, strip, join fragments" logic with format-specific wrappers.
  - The repetition is format-sensitive and should not be collapsed without tests, but it meets the N>=3 abstraction-opportunity threshold.
- **建议处理**:
  - In a later cleanup phase, consider a shared `_extract_text_fragments(...)` helper with explicit allowed dict fields / content type policy passed by caller.
  - Keep format-specific error messages and metadata behavior at callsites.
- **影响范围**:single block / ingestion parser.
- **关联**:none.

### [low][hardcoded-literal] Retrieval preview and scoring truncation limits are raw numbers

- **位置**:
  - `src/swallow/retrieval.py:423`
  - `src/swallow/retrieval.py:645`
  - `src/swallow/retrieval.py:875`
  - `src/swallow/retrieval.py:883`
  - `src/swallow/retrieval_adapters.py:267`
  - `src/swallow/retrieval_adapters.py:312`
  - `src/swallow/ingestion/pipeline.py:292`
- **判定依据**:
  - `rg -n '\\[:4000\\]|\\[:220\\]|> 80' src/swallow/retrieval.py src/swallow/retrieval_adapters.py src/swallow/ingestion/pipeline.py`
  - `4000`, `220`, and `80` are content-window / preview limits, but only some chunk limits are named constants.
  - Phase 66 hardcoded-literal rules count magic numbers when not named.
- **建议处理**:
  - In a later cleanup phase, introduce named constants such as `RETRIEVAL_SCORING_TEXT_LIMIT`, `RETRIEVAL_PREVIEW_LIMIT`, and `INGESTION_PREVIEW_LIMIT`.
  - Keep values unchanged unless a retrieval quality phase revisits them.
- **影响范围**:single block.
- **关联**:none.

### [med][hardcoded-literal] Embedding API endpoint shape and adapter names are code-level policy data

- **位置**:
  - `src/swallow/retrieval_adapters.py:186-214`
  - `src/swallow/retrieval_adapters.py:255`
  - `src/swallow/retrieval_adapters.py:331-332`
  - `src/swallow/retrieval_adapters.py:460`
- **判定依据**:
  - `rg -n '/v1/embeddings|timeout_seconds: int = 20|local_embedding|sqlite_vec|api_embedding' src/swallow/retrieval_adapters.py`
  - `build_api_embedding(...)` bakes the OpenAI-compatible embeddings path suffix, request fields, header shape, and a raw `20` second timeout into the adapter.
  - Adapter names / backend metadata strings are also embedded in code and consumed by retrieval telemetry.
- **建议处理**:
  - In a later cleanup phase, move endpoint suffix and timeout to runtime config or named constants and document adapter-name ownership.
  - This is not the Phase 57 embedding-dimension import-time concern and not the Phase 64 chat-completion guard concern.
- **影响范围**:single block / retrieval adapter policy.
- **关联**:Phase 57 and Phase 64 M2-2 skipped.

### [med][hardcoded-literal] Canonical reuse policy and evaluation judgments are embedded as code strings

- **位置**:
  - `src/swallow/canonical_reuse.py:7-8`
  - `src/swallow/canonical_reuse_eval.py:7`
  - `src/swallow/canonical_reuse_eval.py:99-111`
  - `src/swallow/cli.py:2109-2113` (cross-block CLI choice)
- **判定依据**:
  - `rg -n 'CANONICAL_REUSE_POLICY_NAME|CANONICAL_REUSE_SUPERSEDED_RULE|CANONICAL_REUSE_EVAL_JUDGMENTS|useful|noisy|needs_review' src/swallow/canonical_reuse.py src/swallow/canonical_reuse_eval.py src/swallow/cli.py`
  - Policy name, supersede rule, and judgment taxonomy are source-level strings, with CLI repeating the judgment choices.
  - These are user/operator-facing governance values, not transient display text.
- **建议处理**:
  - In a later cleanup phase, give canonical reuse evaluation one owner for policy/judgment constants and import from it in CLI.
  - Keep the current values stable for existing artifacts.
- **影响范围**:cross-block canonical / CLI surface.
- **关联**:none.

### [med][hardcoded-literal] `dialect_data.py` still defaults executor identity to `"aider"`

- **位置**:
  - `src/swallow/dialect_data.py:18-20`
  - `src/swallow/dialect_data.py:117-126`
- **判定依据**:
  - `rg -n 'DEFAULT_EXECUTOR|EXECUTOR_ALIASES|aider' src/swallow/dialect_data.py src/swallow/doctor.py src/swallow/cli.py`
  - `DEFAULT_EXECUTOR = "aider"` and alias normalization live in prompt data collection, not the executor registry / route metadata layer.
  - Phase 66 hardcoded-literal rules count executor/provider/model brand names as findings even on single occurrence.
- **建议处理**:
  - In a later design/cleanup phase, decide whether prompt dialect data should consume executor identity from route metadata rather than owning a default brand.
  - Do not change the default in an audit-only phase.
- **影响范围**:cross-module prompt formatting.
- **关联**:none.

### [med][hardcoded-literal] Retrieval artifact allow-lists duplicate task artifact names in code

- **位置**:
  - `src/swallow/retrieval.py:64-79`
  - `src/swallow/paths.py:61-165` (cross-block path owner)
  - `src/swallow/cli.py:3592-3637` (cross-block surface)
- **判定依据**:
  - `rg -n 'memory.json|retrieval.json|route.json|summary.md|route_report.md|validation_report.md|executor_output.md' src/swallow/retrieval.py src/swallow/paths.py src/swallow/cli.py`
  - Retrieval hardcodes which task artifact files are eligible retrieval sources, while path helpers and CLI artifact printers maintain overlapping names.
  - Artifact filenames are public workflow surface; duplicating them increases stale artifact risk as new reports are added.
- **建议处理**:
  - In a later cleanup phase, consider deriving retrieval-eligible artifact names from a shared artifact registry or path-owner table.
  - Preserve the current allow-list semantics; not every artifact should become retrievable by default.
- **影响范围**:cross-block retrieval / surface.
- **关联**:none.

### [med][abstraction-opportunity] RetrievalItem assembly repeats across knowledge, canonical reuse, and file retrieval paths

- **位置**:
  - `src/swallow/retrieval.py:423-443`
  - `src/swallow/retrieval.py:645-665`
  - `src/swallow/retrieval.py:883-902`
- **判定依据**:
  - The three paths all build `RetrievalItem(...)` from a document/chunk match, with preview construction, score breakdown, matched terms, citation, and metadata assembly.
  - The first two paths also repeat `knowledge_priority_bonus` score handling.
  - The shape appears in N>=3 places, but source-type and metadata differences make it an abstraction opportunity rather than a direct duplicate-helper finding.
- **建议处理**:
  - In a later cleanup phase, evaluate a small `_retrieval_item_from_match(...)` helper with explicit source-type and score-policy parameters.
  - Avoid hiding source-type-specific metadata decisions inside a generic builder.
- **影响范围**:single block / retrieval readability.
- **关联**:none.

### [med][hardcoded-literal] Ingestion staged-candidate defaults encode authority and source-kind strings in pipeline code

- **位置**:
  - `src/swallow/ingestion/pipeline.py:24-30`
  - `src/swallow/ingestion/pipeline.py:43-90`
  - `src/swallow/ingestion/pipeline.py:117-170`
- **判定依据**:
  - `rg -n 'EXTERNAL_SESSION_SOURCE_KIND|LOCAL_FILE_SOURCE_KIND|OPERATOR_NOTE_SOURCE_KIND|DEFAULT_INGESTION_SUBMITTED_BY|staged-knowledge|swl_ingest' src/swallow/ingestion/pipeline.py`
  - Source kinds, default submitter, and memory-authority strings are operational metadata but live as local constants in the ingestion pipeline.
  - Related taxonomy strings also appear in block 5 specialist modules.
- **建议处理**:
  - In a later cleanup phase, decide whether ingestion source-kind and authority defaults belong in a shared specialist/ingestion metadata module.
  - Keep `staged-knowledge` semantics aligned with INVARIANTS §5 before any refactor.
- **影响范围**:cross-block ingestion / specialist metadata.
- **关联**:none.

## Checked But Not Counted

- `_select_chatgpt_primary_path(...)` was inspected but skipped as Phase 45 backlog.
- `_sqlite_vec_warning_emitted` was inspected but skipped as Phase 49 backlog. `_embedding_api_warning_emitted` follows the same warning-once pattern, but Phase 66 finding taxonomy has no concurrency category; it is left as index-level calibration material rather than counted here.
- `VECTOR_EMBEDDING_DIMENSIONS` was skipped as Phase 57 backlog.
- `_is_open_webui_export(...)` was skipped as Phase 58 backlog.
- `store.py` JSON helper production callsites were not re-audited in block 4; M1 review requested that note for M3 `audit_index.md`.
