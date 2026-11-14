# Project Memory & Externalized Stores (`.supervisor/`)

A project's persistent memory lives under `.supervisor/` and in optional local rules
(`GEMINI.local.md`). `agy-supervisor` provides a structured, multi-horizon memory architecture
designed for long-running software engineering and scientific research.

## The v10 Memory Architecture

The memory store organizes project context into three distinct time horizons:

```text
.supervisor/
├── README.md             # Store guide (derived from store-readme template)
├── history.md            # Append-only milestone log of finished tasks
├── tasks/                # Mid-term horizon: active and open task cards
│   └── YYYY-MM-DD-<slug>.md
├── memory/               # In-force long-term knowledge entries
│   ├── decisions/        # Architectural Decision Records (ADRs)
│   ├── facts/            # Verified technical parameters and invariants
│   ├── lessons/          # Approved post-mortem findings and patterns
│   ├── goals/            # High-level project objectives and constraints
│   └── conventions/      # Style rules, lint guidelines, and conventions
├── working/              # Short-term horizon: active working documents
│   ├── plans/            # Active implementation and program plans
│   ├── research/         # Active investigation and code-trace notes
│   ├── writing/          # In-progress drafts and draft-state manifests
│   └── residue/          # Ledger of temporary test/build artifacts
└── archive/              # Immutable historical record (mirrors live tree)
    ├── tasks/            # Completed and dropped task cards
    ├── memory/           # Superseded ADRs, retired facts, and conventions
    └── working/          # Completed plans and historical research notes
```

### Memory Horizons
1. **Short-Term (`working/`)**: In-progress plans, research briefs, and drafts. Read and updated
   by domain leads during active tasks. Finished artifacts are moved to `archive/working/` at
   close-out.
2. **Mid-Term (`tasks/`)**: Self-contained task cards (`templates/task.md`) holding status,
   ownership, dependencies, and acceptance criteria.
3. **Long-Term (`memory/`)**: In-force entries (`templates/entry.md`) with 6 standard frontmatter
   keys (`domain`, `summary`, `affects`, `verified`, `source`, `supersedes`) and concise bodies
   under 150 words (`The choice... Why: ... Rejected: ...`).

## Storage Models: Tracked, Local, or Externalized

When a repository initializes `.supervisor/`, the user chooses how memory is stored:

| Storage Model | Mechanics | Use Case |
|---|---|---|
| **Tracked Store** | Committed into repository git history | Private repos, team shared projects |
| **Local Store** | Excluded via `.git/info/exclude` | Open source or shared upstream repos |
| **Externalized Store** | Out-of-tree store symlinked back | Shared across worktrees & machines |

## Externalized Memory (`./deploy memory`)

In repos where memory cannot be committed, `agy-supervisor memory externalize` moves `.supervisor/`
and `GEMINI.local.md` outside the repository to an XDG-compliant data directory, replacing them
with absolute symlinks:

```bash
# Externalize project memory
agy-supervisor memory externalize

# Link a git worktree to the external memory store
agy-supervisor memory link

# Check health of memory symlinks and exclude rules
agy-supervisor memory status
```

### Default External Root
- Stores live at `$AGY_SUPERVISOR_MEMORY_ROOT/<project-name>/` (default:
  `~/.local/share/agy-supervisor/memory/<project-name>/`).
- A `README.md` marked with `<!-- agy-supervisor external memory -->` is placed in the store root
  to identify ownership.

### Safety Invariants
1. **Refusal on Tracked Files**: Refuses to externalize if `.supervisor` or `GEMINI.local.md` is
   tracked by git. Untrack with `git rm -r --cached .supervisor` before externalizing.
2. **Path Containment Guard**: Refuses if the store target sits inside the repository or any of
   its worktrees.
3. **Clean `.git/info/exclude`**: Rules are added to `.git/info/exclude`, leaving `.gitignore`
   completely untouched.
4. **Foreign Store Protection**: Rejects linking to an existing directory unless it contains the
   matching supervisor marker and project name.

## Antigravity Workspace Permissions Grant

Because externalized memory sits outside the project directory, Antigravity requires explicit
file access grants. `deploy install` and `deploy memory externalize` configure
`~/.gemini/antigravity-cli/settings.json` automatically:

```json
{
  "permissions": {
    "additionalDirectories": [
      "/Users/<you>/.local/share/agy-supervisor/memory"
    ],
    "allow": [
      "Edit(/Users/<you>/.local/share/agy-supervisor/memory/**)"
    ]
  }
}
```

This prevents interactive confirmation prompts whenever agents read, create, or modify memory
entries through the symlinks.

## Migrating Legacy `roadmap.md`

Earlier releases tracked project milestones in a monolithic `.supervisor/roadmap.md`. In v1.1,
monolithic roadmaps are replaced by atomic task cards:

1. **Card Extraction**: Split active milestones into individual cards under `.supervisor/tasks/`:
   ```yaml
   ---
   summary: Implement feature X with unit tests
   status: open
   owner:
   since: 2026-11-14
   plan:
   depends: []
   decisions: []
   ---
   Goal: Deliver feature X.
   Scope: Target files and interfaces.
   Done when: Unit tests pass.
   Notes: Relevant context.
   ```
2. **Retire Legacy File**: Move `roadmap.md` into `archive/working/plans/roadmap.md`.
3. **Update Curators & Skills**: Dispatches to `curator` maintain cards using `task` and
   `drop task` procedures.
