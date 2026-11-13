---
name: close-out
description: Cleanly wrap up a session by verifying work, updating .supervisor/ memory via curator, and confirming git state.
disable-model-invocation: true
---

# Session Close-Out Checklist

Run this workflow when wrapping up a working session so the next session starts cleanly.

## Steps

1. **Sweep residue**: ensure temporary scratch files, debug logs, and dead edits are removed
   from modified files (`residue` checklist).
2. **Verify changed work**: ensure all relevant tests and linters ran after the final edit,
   recording exact commands and pass counts. Never mark unverified work as tested.
3. **Update `.supervisor/` memory**: invoke `curator` (never directly committing) to:
   - Append a concise verified entry to `.supervisor/history.md`
   - Refresh `.supervisor/roadmap.md` with completed items, active blockers, and next step
   - Record any new architectural decisions under `.supervisor/memory/decisions/`
4. **Inspect git state**: invoke `git-ops` (or inspect `git status --short` and worktrees) to
   confirm no dangling `.agents/worktrees/*` remain unless intentionally kept open, and ask
   the user before creating commits if uncommitted changes remain.
5. **Emit close-out footers**: end with clear `Session state:` and `Run yourself:` lines
   summarizing branch, clean/dirty state, test status, and the exact next pickup command.
