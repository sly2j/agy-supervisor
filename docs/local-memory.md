# Externalized Local Memory (`./deploy memory`)

Repositories where `.supervisor/` or `GEMINI.local.md` should stay out of tracked commits
or survive across worktrees can move project memory to an out-of-tree XDG-style directory.

## Commands

```bash
# Move .supervisor/ & GEMINI.local.md out of main checkout and symlink back
agy-supervisor memory externalize --project /path/to/repo

# Re-link a worktree or fresh clone to the existing external store
agy-supervisor memory link --project /path/to/worktree

# Verify symlinks and .git/info/exclude rules
agy-supervisor memory status --project /path/to/repo
```

## Safety Invariants

- Stores live under `$AGY_SUPERVISOR_MEMORY_ROOT/<project-name>/` (default
  `<prefix>/share/agy-supervisor/memory/<project-name>/`).
- Refuses to externalize if `.supervisor` or `GEMINI.local.md` is tracked by git.
- Refuses if the target store path sits inside any checkout or worktree of the repository.
- Records `.supervisor` and `GEMINI.local.md` in `.git/info/exclude` so `git status`
  remains completely clean without editing shared `.gitignore`.
- Stamps `README.md` with `<!-- agy-supervisor external memory -->` so unrelated folders
  are never overwritten.
