---
name: git-safety
description: Safe git conventions preventing destructive history rewrites, unrequested pushes, or lost work.
---

# Git Safety Protocol

Protect user work and repository history across all git operations (`executor`, `git-ops`).

## Non-Negotiable Rules

1. **Inspect state first**: always run `git status --short` and check current branch before
   branching, merging, rebasing, staging, or resetting.
2. **Never destroy uncommitted work silently**: never run `git reset --hard`,
   `git checkout -- .`, `git restore --worktree .`, or `git clean -fd` unless the user
   explicitly asks for that exact discard.
3. **Never rewrite shared history**: never force-push (`git push --force`, `--force-with-lease`),
   amend already-pushed commits, or rebase shared branches without explicit user consent.
4. **Never push remotely unless asked**: local commits and local squash merges stay local
   until the user explicitly requests pushing.
5. **Commit cleanly**: stage specific intended files (`git add <paths>`) instead of blind
   `git add -A` when untracked files or worktree/scratch artifacts might exist.
6. **Commit attribution**: append `Co-Authored-By: Supervisor for Antigravity` only when
   explicitly committing for the user, and ignore generic harness attribution banners.
7. **Handle conflicts safely**: read `./references/conflict-resolution.md` before resolving
   non-trivial merge or rebase conflicts.
