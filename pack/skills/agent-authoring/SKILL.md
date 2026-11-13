---
name: agent-authoring
description: Authoring and lint conventions for Supervisor for Antigravity agents and skills.
---

# Agent and Skill Authoring Conventions

Use these rules when adding or modifying agents (`pack/agents/*.md`) or skills
(`pack/skills/*/SKILL.md`). Every bundle must pass `agy plugin validate --strict --json`.

## Tiers

| Role | Agents | Model | Flags (`mainAgent` / `subagent`) | Preloaded Skills |
| :--- | :--- | :--- | :--- | :--- |
| Main | `supervisor` | `inherit` | `true` / `false` | `—` |
| Lead | `researcher` | `pro` | `false` / `true` | `lead-loop`, `residue` |
| Lead | `planner` | `pro` | `false` / `true` | `lead-loop`, `plan-writing`, `repo-workflow` |
| Lead | `executor` | `flash` | `false` / `true` | `lead-loop`, `git-safety`, `repo-workflow`, `residue` |
| Lead | `writer` | `pro` | `false` / `true` | `lead-loop`, `project-memory` |
| Worker | `researcher-worker` | `flash` | `false` / `true` | `residue` |
| Worker | `planner-worker` | `flash` | `false` / `true` | `—` |
| Worker | `executor-worker` | `flash` | `false` / `true` | `residue` |
| Worker | `writer-worker` | `pro` | `false` / `true` | `project-memory` |
| Reviewer | `critic` | `pro` | `false` / `true` | `—` |
| Reviewer | `scope-critic` | `pro` | `false` / `true` | `—` |
| Memory | `curator` | `flash` | `false` / `true` | `project-memory` |
| Quick | `fixer` | `flash_lite` | `false` / `true` | `project-memory`, `residue` |
| Quick | `git-ops` | `flash_lite` | `false` / `true` | `git-safety`, `repo-workflow` |
| Quick | `scout` | `flash_lite` | `false` / `true` | `—` |

## Antigravity Frontmatter Rules

Agents accept only valid Antigravity frontmatter fields:
- `name`, `description`, `model` (`inherit`, `pro`, `flash`, or `flash_lite`)
- `mainAgent` (`true` on `supervisor`, `false` on all others) and `subagent` (inverse)
- `tools`: explicit native tool list (`read_file`, `write_file`, `edit_file`, `run_command`,
  `manage_task`, `search_web`, `invoke_subagent`, `define_subagent`, `manage_subagents`,
  `send_message`, `ask_question`)
- `agents`: subagent allowlist on `supervisor` and leads (`—` omit on leaf agents)
- `skills`: preloaded skill names when used regularly

Never emit unsupported fields (`disallowedTools`, `effort`, `color`, `enableSubagentTools`).
At runtime, callers may pass a per-call `Model` (`pro`, `flash`, `flash_lite`, `inherit`)
to `invoke_subagent` to step up or down within a turn.

Skills accept only `name` (must equal parent folder name), `description`, and optional
`disable-model-invocation: true`. Do not emit `user-invocable`, `context: fork`, or
`argument-hint`. Reference bundled files using relative markdown paths such as
`./references/...` or `./scripts/...`.

## Tool Boundaries

- `supervisor`: no `run_command` or `manage_task`; delegates work and git ops to subagents.
- Leads: carry `invoke_subagent`, `define_subagent`, `manage_subagents`, `send_message`, and
  may inspect or verify directly, while delegating substantive edits or multi-file sweeps.
- Workers & leaf agents: never list `agents` and never carry `invoke_subagent`,
  `define_subagent`, or `manage_subagents`.
- `planner-worker`, `critic`: read-only file access (`read_file`, `run_command`, `manage_task`,
  `search_web`); no `write_file` or `edit_file`.
- `scope-critic`: `read_file` only.
- `curator` and `fixer`: must explicitly forbid running `git commit`.

## Size and Line Budgets

Keep non-fenced, non-table `.md` prose lines `<= 100` characters under `pack/`.
Keep skill `SKILL.md` files `<= 300` lines, `<= 1380` body words (`residue` `<= 350`),
and strictly under `24,000` bytes.
Keep agent body word counts within tier caps: Main `1000`, Lead `700`, Review `600`,
Worker `400`, Memory `400`, Quick `350`.
