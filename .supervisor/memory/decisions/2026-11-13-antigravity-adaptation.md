# Decision: Adapting Supervisor Orchestration to Antigravity

- **Date**: 2026-11-13
- **Status**: Accepted
- **Scope**: `pack/`, `deploy`, `external-critic`

## Context

`sly2j/claude-supervisor` targets Claude Code's agent/skill schema (`opus`/`sonnet`/`haiku`,
`disallowedTools`, `${CLAUDE_SKILL_DIR}`, `$ARGUMENTS`, `~/.claude/settings.json`). Antigravity
(`agy` 1.4.9) enforces a strict plugin schema verified by `agy plugin validate --strict`.

## Decision

1. Map agent models strictly to Antigravity tiers (`inherit`, `pro`, `flash`, `flash_lite`)
   with explicit `mainAgent`, `subagent`, and native `tools` lists (`read_file`, `write_file`,
   `edit_file`, `run_command`, `manage_task`, `search_web`, `invoke_subagent`, `define_subagent`,
   `manage_subagents`, `send_message`, `ask_question`), using `invoke_subagent(...,
   Workspace="inherit")` plus git worktrees at `<toplevel>/.agents/worktrees/<slug>`.
2. Keep `deploy` and `external-critic` Python 3.9+ stdlib-only and expose both Claude (`claude`)
   and Codex (`codex`) as opt-in cross-family CLI critics with native `critic` fallback.
3. Launch via `~/.local/bin/agy-supervisor` (`exec agy --agent supervisor "$@"`) so plain
   `agy` behavior remains untouched.

## Consequences

- `pack/` passes `agy plugin validate --strict --json` cleanly without warnings or errors.
- All automated checks run standalone via `/usr/bin/python3 -m unittest`.
