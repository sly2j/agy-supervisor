# Git Conflict Resolution Guide

Use this procedure when merging a feature/worktree branch or hitting merge conflicts.

## Safe Recovery Steps

1. **Check status and abort threshold**:
   - Run `git status --short` to list conflicted paths (`UU`, `AA`, `DU`, `UD`).
   - If you are unsure of the intended semantics for business logic or user-edited files,
     stop immediately (or run `git merge --abort`) and ask the lead/supervisor.
2. **Inspect both sides cleanly**:
   - Run `git diff --merge` or inspect `<<<<<<< HEAD` / `=======` / `>>>>>>> <branch>` hunks
     directly with `read_file`.
   - Understand what changed on base (`HEAD`) versus incoming branch before editing.
3. **Resolve and remove markers**:
   - Edit each conflicted file so zero conflict markers remain.
   - Verify with `grep -rn '<<<<<<<\|=======\|>>>>>>>' <paths>` or `git diff --check`.
4. **Re-run verification after resolution**:
   - Conflict merges can compile while breaking invariants; run the targeted test suite
     before finishing the merge commit or squash landing.
