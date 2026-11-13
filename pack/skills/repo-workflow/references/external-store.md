# Externalized Memory Store (`deploy memory`)

Some repositories cannot or should not track `.supervisor/` in git (shared upstream repos,
strict PR policies, or read-only vendor trees).

## How Externalization Works

Use the `deploy memory` subcommand (installed via `agy-supervisor memory` or `./deploy memory`):

```bash
agy-supervisor memory externalize --project /path/to/repo
```

This command:
1. Moves or initializes the store under the prefix memory root
   (`~/.local/share/agy-supervisor/memory/<repo-key>/`).
2. Replaces `<repo>/.supervisor` with a symlink pointing to that external store directory.
3. Adds `.supervisor` to `<repo>/.git/info/exclude` (local git exclude, not tracked
   `.gitignore`), keeping upstream diffs completely clean.

## Linking & Checking Status

- Re-link a fresh clone on the same machine:
  `agy-supervisor memory link --project /path/to/clone`
- Inspect whether a repository uses in-repo or externalized `.supervisor/`:
  `agy-supervisor memory status --project /path/to/repo`

Note: both forms present identical `.supervisor/` paths to agents and skills.
