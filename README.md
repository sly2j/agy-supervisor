# Supervisor for Antigravity (`agy-supervisor`)

Multi-agent hierarchical orchestration plugin and deployment CLI for **Google Antigravity**
(`agy` CLI, Antigravity 2.0 Desktop, Antigravity IDE), inspired by and architecturally
aligned with [`sly2j/claude-supervisor`](https://github.com/sly2j/claude-supervisor).

## What It's For

`agy-supervisor` is designed for long-horizon software engineering and scientific research:
complex, multi-session tasks that require iterative investigation, structured planning,
rigorous execution, independent review, and durable project memory.

- **Parallel Work Packages**: Break large tasks into directed acyclic graph (DAG) programs
  executed in waves with isolated file ownership.
- **Context Quarantine**: Keep the main conversation thread clean. The coordinator reads
  almost nothing directly; leads, workers, and reviewers operate in fresh, discardable context
  windows.
- **Persistent Project Memory**: Maintain project decisions, invariants, conventions, active task
  cards, and research notes in `.supervisor/`, surviving across session boundaries.

## Architecture: Mode 1 & Mode 2

`agy-supervisor` routes requests based on scope, risk, and complexity:

```text
User Request
    │
    ▼
supervisor (Coordinator: routes, briefs, integrates; no shell tools)
    │
    ├──► Mode 1: Full Lead Loop (researcher | planner | executor | writer)
    │      ├── Workers: researcher-worker | planner-worker | executor-worker | writer-worker
    │      ├── critic: adversarial quality, correctness & test coverage reviewer
    │      └── scope-critic: KEEP / DOWNGRADE / DROP adjudicator & anti-bloat cuts
    │
    ├──► Mode 2: Quick Tier (scout | fixer | git-ops)
    │      └── Atomic, single-turn tasks with no review loop
    │
    └──► Direct Dispatch: curator (memory store lifecycle, task cards, close-out)
```

- **Mode 1 (Full Lead Loop)**: The lead formalizes a contract, splits disjoint files across
  parallel workers, integrates changes, runs `critic` and `scope-critic`, and fixes defects up
  to 3 review rounds.
- **Mode 2 (Quick Tier)**: Fast, cheap leaf specialists handle atomic tasks. `scout` performs
  read-only lookups; `fixer` makes surgical edits (up to 3 files / 40 lines); `git-ops` handles
  safe staging, committing, and branching.
- **Single-Voice Lead Drafting**: In `writer`, the lead directly authors all prose to preserve
  a coherent voice; `writer-worker` performs source extraction, fact gathering, and audits.

## Model-Tier Alignment

Antigravity strictly validates agent definitions against four native model tiers:

| Tier | Runtime Engine | Characteristics & Role Assignment |
|---|---|---|
| `inherit` | Carbon medium | Top-level orchestrator (`supervisor`) & prose lead (`writer`) |
| `pro` | Gemini Pro | High reasoning leads (`planner`, `executor`, `researcher`, critics) |
| `flash` | Gemini Flash | High-throughput parallel workers & memory `curator` |
| `flash_lite` | Gemini Flash Lite | Rapid read-only lookups & quick leaf specialists |

See [docs/model-tiers.md](docs/model-tiers.md) for full assignment tables, dynamic caller overrides,
and IDE model selection.

## Quickstart

Requirements:
- Python 3.9+ (`/usr/bin/python3` or virtualenv)
- Google Antigravity CLI (`agy`) installed and available on `PATH`
- Git (for repository tracking and worktree management)

### 1. Installation

Install the plugin globally into `~/.gemini/config/plugins/agy-supervisor` and link the launcher
to `~/.local/bin/agy-supervisor`:

```bash
# Preflight environment check
./deploy doctor

# Install globally
./deploy install
```

Ensure `~/.local/bin` is in your `PATH` (`export PATH="$HOME/.local/bin:$PATH"` in `~/.zshrc` or
`~/.bashrc`).

### 2. Launching Supervisor

```bash
# Start an interactive supervisor session (plain agy remains untouched)
agy-supervisor

# Pass model overrides on demand
agy-supervisor --model gemini-4-carbon-medium
```

## The 15 Agents

| Agent Role | Model Tier | Operational Focus |
|---|---|---|
| `supervisor` | `inherit` | Main thread coordinator; routing, delegation brief, and synthesis |
| `planner` | `pro` | Architecture, technical specifications, and phased DAG plans |
| `planner-worker` | `flash` | Bounded repository research and symbol mapping for plans |
| `researcher` | `pro` | Deep code tracing, literature review, and domain synthesis |
| `researcher-worker` | `flash` | Bounded web, documentation, or code investigations |
| `executor` | `pro` | Code refactoring, implementation, automated tests, worktrees |
| `executor-worker` | `flash` | Concrete change slices within assigned file boundaries |
| `writer` | `inherit` | Technical documentation, manuscripts, and presentation slides |
| `writer-worker` | `pro` | Source fact extraction and tone-accurate section drafting |
| `critic` | `pro` | Read-only quality, test coverage, and specification reviewer |
| `scope-critic` | `pro` | Adjudicates findings (`KEEP`/`DROP`) and identifies bloat |
| `curator` | `flash` | Memory lifecycle: close-out, task cards, and store audits |
| `fixer` | `flash_lite` | Surgical single-file repair, status edits, residue teardown |
| `git-ops` | `flash_lite` | Safe git operations: status, staging, commits, and worktrees |
| `scout` | `flash_lite` | Fast read-only symbol lookups, grep queries, and task listing |

## The 17 Skills

| Skill | Primary Users | Purpose |
|---|---|---|
| `lead-loop` | Domain leads | 5-stage contract, fan-out, review, and reporting loop |
| `plan-writing` | `planner`, `critic` | DAG plan spec, work packages, acceptance criteria |
| `project-memory` | `curator`, `fixer`, leads | Store layout, task cards, ADR entries |
| `git-safety` | `executor`, `git-ops` | Guardrails preventing history rewrites and secret leaks |
| `repo-workflow` | Leads, `git-ops` | Semantic versioning (`X.y`), worktree landing, branch rules |
| `residue` | Leads, `fixer`, workers | Temporary test artifact ledger and teardown protocol |
| `python-env` | `executor`, workers | Virtualenv detection, uv integration, dependency sync |
| `agent-authoring`| `executor`, `critic` | Authoring conventions and lint rules for agents/skills |
| `science-writing-style` | `writer`, workers | Style, precision, and voice for manuscripts |
| `presentation-style` | `writer`, workers | Slide deck structure, narrative arc, budgets |
| `document-extraction` | Workers, `writer` | Structured fact extraction from reference documents |
| `email-extraction` | Workers, `writer` | Distills email threads into decisions, actions, owners |
| `meeting-summary`| User, `writer-worker` | Converts meeting transcripts into structured minutes |
| `pick-up` | User, `supervisor` | Resumes active plans or atomically claims task cards |
| `close-out` | User, `curator`, `fixer` | Tears down residue, distills memory, archives cards |
| `project-backup` | User | Timestamped zip backups with Grandfather-Father-Son retention |
| `supervisor-config` | User, leads | Configures cross-family external critic vs native critic |

## Deployment & CLI Commands

`./deploy` provides full lifecycle management:

```bash
# Diagnostics and status
agy-supervisor doctor              # Preflight diagnostic checks
agy-supervisor status              # Active install status and manifest hashes
agy-supervisor list                # List registered supervisor profiles

# Updating
agy-supervisor update              # Update current profile from upstream
./deploy update --all              # Update all registered supervisor profiles
agy-supervisor update --from <dir> # Update from a local directory or Git repository

# Custom installs
./deploy install --workspace .     # Install into <repo>/.agents/plugins/
./deploy install --tag dev         # Install parallel tagged profile (agy-dev)
./deploy install --default-model gemini-4-carbon-medium

# Uninstallation
agy-supervisor uninstall           # Cleanly removes launcher, pack, and rules
```

See [docs/deploy.md](docs/deploy.md) for full deployment details.

## Project Memory & Task Cards

Project state is preserved in `.supervisor/`:
- `tasks/`: Mid-term task cards (`YYYY-MM-DD-<slug>.md`) with YAML frontmatter.
- `memory/`: Long-term ADRs (`decisions/`), facts, lessons, goals, conventions.
- `working/`: Active DAG plans (`plans/`), research briefs, and drafts.
- `archive/`: Immutable archive of completed tasks, retired ADRs, and finished plans.

### Externalized Memory (`./deploy memory`)
In repositories where memory cannot be committed directly to git:

```bash
# Externalize memory to ~/.local/share/agy-supervisor/memory/<project>
agy-supervisor memory externalize

# Link a git worktree to the external store
agy-supervisor memory link

# Check health of symlinks and git exclude rules
agy-supervisor memory status
```

Externalized stores are automatically granted permissions in `settings.json`. See
[docs/local-memory.md](docs/local-memory.md).

## Workflow: From Pick-Up to Close-Out

1. **Pick-Up**: User initiates work or resumes an existing plan via `pick-up`. Open task cards
   are claimed atomically via compare-and-set (`status: active`).
2. **Worktree Isolation**: Code modifications execute in dedicated git worktrees under
   `.agents/worktrees/<slug>`.
3. **Residue Tracking**: Temporary directories and test sockets are recorded in
   `.supervisor/working/residue/`.
4. **Close-Out**: `close-out` triggers `fixer` to clean up residue, prompts `curator` to distill
   decisions, archives finished task cards (`met: YYYY-MM-DD`), and commits memory updates.
5. **Session Safety**: Every turn ends with a `Session state:` line indicating whether `/clear`
   is safe, plus a `Run yourself:` block for human-only actions (such as remote pushes).

See [docs/workflow-lifecycle.md](docs/workflow-lifecycle.md) for complete walkthroughs.

## Cross-Family External Critic (`external-critic`)

By default, reviews are performed by Antigravity's native `critic` subagent (`pro`). Users may
optionally route reviews to external CLI engines with explicit consent:

```bash
# Route reviews to Claude Code CLI
agy-supervisor critic enable claude

# Route reviews to OpenAI Codex CLI
agy-supervisor critic enable codex

# Route code reviews to Codex while keeping Claude for plans
agy-supervisor critic enable claude --domain code=codex

# Inspect critic status
agy-supervisor critic status
```

If the external engine fails or times out, `lead-loop` falls back to native `critic` automatically.

## Offline Session Audit Tool (`tools/audit/`)

The audit tool scans local Antigravity session transcripts (`~/.gemini/antigravity-cli/brain`) to
measure token costs, critic pass rates, scope cuts, and worker efficiency:

```bash
# Run audit and emit Markdown tables
python3 -I tools/audit/audit.py > tools/audit/out/run.md

# Emit structured JSON
python3 -I tools/audit/audit.py --json > tools/audit/out/run.json
```

The audit tool includes strict privacy guards: it refuses execution (code 2) if user home
directories or workspace paths leak into output.

## Verification & Testing

Run the test suite using standard Python `unittest`:

```bash
# Offline verification (includes 28 deterministic routing contract tests)
/usr/bin/python3 -m unittest discover -s tests -t . -v

# Strict Antigravity plugin schema validation
agy plugin validate --strict --json pack

# Optional: live Antigravity routing tests against real CLI
AGY_LIVE_ROUTING=1 /usr/bin/python3 -m unittest discover -s tests -t . -v
```

## Documentation Reference

- [Architecture & 15 Agents](docs/architecture.md)
- [Context Engineering Rationale](docs/context-engineering.md)
- [Deployment, Launchers & Updates](docs/deploy.md)
- [Model Tiers & Antigravity Alignment](docs/model-tiers.md)
- [Project Memory & External Stores](docs/local-memory.md)
- [Workflow Lifecycle & Close-Out](docs/workflow-lifecycle.md)
