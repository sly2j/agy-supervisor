# Supervisor for Antigravity (`agy-supervisor`)

Multi-agent hierarchical orchestration plugin and deployment CLI for **Google Antigravity**
(`agy` CLI, Antigravity 2.0 Desktop, Antigravity IDE), inspired by
[`sly2j/claude-supervisor`](https://github.com/sly2j/claude-supervisor).

## Highlights

- **15-Agent Hierarchy**: `supervisor` coordinator (`inherit`) delegates across 4 domain leads
  (`researcher`, `planner`, `executor`, `writer`), 4 slice workers (`*-worker`), 2 independent
  read-only reviewers (`critic`, `scope-critic`), memory `curator`, and 3 quick single-shot
  specialists (`fixer`, `git-ops`, `scout`).
- **17 Modular Skills**: covers orchestration (`lead-loop`, `plan-writing`, `residue`,
  `agent-authoring`), persistent `.supervisor/` memory (`project-memory`, `pick-up`, `close-out`,
  `project-backup`), safe git/worktree isolation (`git-safety`, `repo-workflow`), domain skills,
  and external critic configuration (`supervisor-config`).
- **Native Antigravity Plugin (`pack/`)**: validated with `agy plugin validate --strict --json`
  with zero errors, warnings, or notes.
- **Safe Deployment (`./deploy`)**: Python 3.9+ stdlib-only installer supporting global,
  tagged (`--tag`), `--workspace`, and `--target` installs, SHA-256 3-way baseline manifests,
  `~/.local/bin/agy-supervisor` launcher, `doctor` diagnostics, and externalized `.supervisor/`
  memory linking.
- **Opt-In Cross-Family External Critic (`external-critic`)**: off by default (native `critic`
  subagent active); optionally routes code, plan, research, or prose reviews to Claude Code
  (`claude`) or OpenAI Codex (`codex`) with explicit consent and automatic native fallback.

## Quickstart

```bash
# 1. Inspect preflight environment without modifying anything
./deploy doctor
./deploy install --dry-run

# 2. Install globally (~/.gemini/config/plugins/agy-supervisor + ~/.local/bin/agy-supervisor)
./deploy install

# 3. Launch an interactive Supervisor session (leaves plain `agy` untouched)
agy-supervisor

# 4. Run diagnostics or inspect install status anytime
agy-supervisor doctor
agy-supervisor status
```

Workspace-only install (no global launcher):

```bash
./deploy install --workspace /path/to/repo
```

Optional cross-family external critic (off by default):

```bash
agy-supervisor critic enable claude
# or
agy-supervisor critic enable codex
# with per-domain override:
agy-supervisor critic enable claude --domain code=codex
```

## Verification

```bash
/usr/bin/python3 -m py_compile deploy pack/skills/supervisor-config/scripts/external-critic
/Users/sjoosten/.local/bin/agy plugin validate --strict --json pack
/usr/bin/python3 -m unittest discover -s tests -t . -v
```

## Documentation

- [Architecture](docs/architecture.md)
- [Workflow Lifecycle](docs/workflow-lifecycle.md)
- [Context Engineering](docs/context-engineering.md)
- [Deployment & Launcher](docs/deploy.md)
- [Externalized Local Memory](docs/local-memory.md)
