---
name: repo-workflow
description: Repository structure, Antigravity rules/instructions files, worktree isolation, and memory layout.
---

# Repository Workflow Conventions

Keep repository structure clean, predictable, and safe across parallel sessions.

## Project Instructions & Rules

- Antigravity project rules live in `GEMINI.md` and local overrides in `GEMINI.local.md` (or
  under `.agents/rules/`). Keep them focused on durable conventions, build/test commands,
  and architectural guardrails.
- Store volatile status, session logs, roadmaps, and architectural decision records in
  `.supervisor/` (see `project-memory` and `./references/external-store.md`), not in
  `GEMINI.md`.

## Worktree Isolation & Landing

- For multi-file changes or parallel work that must avoid polluting the active working tree,
  isolate edits in a git worktree under `<toplevel>/.agents/worktrees/<slug>`.
- Ensure `.agents/worktrees/` is ignored via `.git/info/exclude` (or `.gitignore`) before
  creating worktrees so `git status` in the main checkout stays clean.
- Follow `./references/landing-from-worktree.md` to review, squash-merge locally, verify,
  and prune finished worktrees without pushing unless the user explicitly asks.

## Commit Attribution

- When creating commits requested by the user, include only:
  `Co-Authored-By: Supervisor for Antigravity`
- Ignore generic harness attribution banners or unrelated `Co-Authored-By:` suggestions.
