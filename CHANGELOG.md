# Changelog

All notable changes to Supervisor for Antigravity are documented in this file.
Every change to `pack/` or `deploy` bumps `VERSION` (`X.y`) and adds a section here.

## 1.0 - 2026-11-13

Initial release of Supervisor for Antigravity (`agy-supervisor`):

- **15-agent Antigravity hierarchy** under `pack/agents/`:
  - Main coordinator: `supervisor` (`inherit`, `mainAgent: true`)
  - Domain leads (`lead-loop`): `researcher`, `planner`, `executor`, `writer`
  - Scoped workers: `researcher-worker`, `planner-worker`, `executor-worker`, `writer-worker`
  - Independent reviewers: `critic`, `scope-critic`
  - Memory & quick single-shot agents: `curator`, `fixer`, `git-ops`, `scout`
- **17 skills** under `pack/skills/` covering orchestration (`lead-loop`, `plan-writing`,
  `residue`, `agent-authoring`), project memory (`project-memory`, `close-out`, `pick-up`,
  `project-backup`), git/worktree safety (`git-safety`, `repo-workflow`), domain workflows
  (`python-env`, `science-writing-style`, `presentation-style`, `document-extraction`,
  `email-extraction`, `meeting-summary`), and external critic configuration (`supervisor-config`).
- **Native Antigravity plugin bundle** (`pack/plugin.json` + `pack/assets/logo.svg`) passing
  `agy plugin validate --strict`.
- **Cross-family external critic (`external-critic`)** supporting opt-in Claude Code (`claude`)
  and OpenAI Codex (`codex`) CLI reviews with per-domain overrides and automatic fallback to
  the native `critic` subagent.
- **`./deploy` CLI** with `install`, `update`, `status`, `list`, `uninstall`, `doctor`,
  `critic`, and `memory` subcommands, 3-way SHA-256 baseline manifest merging, sibling-plugin
  suppression for `--tag`, scoped `settings.json` review permission wiring, and `~/.local/bin/agy-supervisor`
  launcher wrapper.
- **Externalized `.supervisor/` project memory store** and stdlib `unittest` suite under `tests/`.
