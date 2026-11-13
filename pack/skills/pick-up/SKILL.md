---
name: pick-up
description: Resume an existing project quickly by loading .supervisor/ state, git status, and open blockers.
disable-model-invocation: true
---

# Session Pick-Up Protocol

Orient quickly at the start of a resumed session without reading the entire repository blind.

## Steps

1. **Read project rules & status**:
   - Inspect `GEMINI.md` (if present) and `.supervisor/roadmap.md`.
   - Read the last ~60 lines of `.supervisor/history.md`.
2. **Inspect live repo state**:
   - Dispatch `scout` or `git-ops` to inspect `git status --short`, current branch,
     `git log -n 5 --oneline`, and `git worktree list` (without modifying files).
3. **Load targeted domain memory**:
   - Open relevant files under `.supervisor/memory/decisions/` or `conventions/` matching
     the user's next goal.
4. **Confirm active direction**:
   - Present a crisp 4–8 line status brief: current branch, clean/dirty files, open
     roadmap item, any blockers, and proposed first step.
   - Ask the user for confirmation if multiple roadmap tracks compete for priority.
