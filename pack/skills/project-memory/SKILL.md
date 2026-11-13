---
name: project-memory
description: Protocol for reading and maintaining the externalized .supervisor/ project memory store.
---

# Project Memory Protocol

Projects keep durable context in a `.supervisor/` directory at the repository root (or an
externalized mirror linked from `.supervisor/` via `deploy memory externalize`). Never dump
unbounded session logs into `GEMINI.md`; store concise decisions and state here instead.

## Store Layout

```text
.supervisor/
  README.md          # Store rules and file index
  history.md         # Append-only chronological milestone log
  roadmap.md         # Active phases, open items, blockers, next step
  memory/
    decisions/       # YYYY-MM-DD-slug.md architectural decision records
    conventions/     # Project-specific patterns and pitfalls
    drafts/          # In-progress writing state files (optional)
```

## Reading Priority (Start of Work)

Read selectively based on what the task needs:
1. `.supervisor/roadmap.md` — current phase, blockers, immediate next actions
2. `.supervisor/history.md` — recent completed milestones (tail ~60 lines first)
3. Specific files under `.supervisor/memory/` relevant to the active module or domain

## Writing Rules

- Only `curator`, `fixer`, `writer`, or `writer-worker` should mutate `.supervisor/`.
- Write concise, high-signal entries with `date`, `scope`, and concrete file/command
  evidence; never invent unverified test results or speculative architecture claims.
- Use templates and detailed curator procedures in:
  - `./references/curator-procedures.md`
  - `./references/writing.md`
  - `./templates/entry.md`
  - `./templates/draft-state.md`
  - `./templates/store-readme.md`
- Neither `curator` nor `fixer` may run `git commit` after updating `.supervisor/`.
