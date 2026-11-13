---
name: document-extraction
description: Structured extraction of facts, requirements, schemas, and citations from specs or documents.
---

# Document Extraction Workflow

Extract exact structured facts from PDFs, markdown specs, RFCs, or source files without
paraphrasing away constraints.

## Extraction Protocol

1. **Preserve provenance**: record exact source file path, section heading, line/page number,
   and version/date for every extracted requirement or constraint.
2. **Distinguish normativity**: classify items explicitly as `MUST` / invariant, `SHOULD` /
   recommendation, `EXAMPLE`, or `OPEN QUESTION`.
3. **Capture exact schemas verbatim**: preserve field names, types, enum values, exit codes,
   and defaults verbatim inside fenced blocks or structured tables.
4. **Flag ambiguities & gaps**: list contradictory statements or missing edge-case specs in an
   explicit `Ambiguities & Gaps` section instead of inventing defaults.
5. **No hallucinated synthesis**: if a source document was truncated or unreadable, state the
   exact unread range explicitly.
