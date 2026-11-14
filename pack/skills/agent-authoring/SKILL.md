---
name: agent-authoring
description: Conventions for writing and reviewing Antigravity subagent and skill definitions in the Supervisor for Antigravity pack (tiers, models, tool restrictions, prompt structure, report contracts, scope boundaries). Use when creating, editing, or critiquing files under pack/agents or pack/skills.
---

# Agent And Skill Authoring

## Tiers

| Tier | Agents | Model / effort | Tools |
|---|---|---|---|
| Main | supervisor | inherit (Gemini 4 Carbon) / default | no run_command, no manage_task; writes only its memory files |
| Lead | researcher | pro / default | all; preload `lead-loop` |
| Lead | executor | pro / default | all; preload `lead-loop` |
| Lead | writer | inherit (Carbon) / default | all; preload `lead-loop`, `project-memory` |
| Lead | planner | pro / default | all; preload `lead-loop`, `plan-writing` |
| Worker | researcher-worker, planner-worker, executor-worker | flash / default | no `invoke_subagent` |
| Worker | writer-worker | pro / default | no `invoke_subagent` |
| Review | critic | pro / default | read-only plus run_command; no `invoke_subagent` |
| Review | scope-critic | pro / default | read-only, no run_command, no `invoke_subagent` |
| Memory | curator | flash / default | explicit allowlist; no `invoke_subagent` |
| Quick | fixer, git-ops, scout | flash_lite / default | explicit allowlist; no `invoke_subagent` |

- Depth is main (0) -> lead or curator (1) -> worker or reviewer (2). Nothing below depth 2
  dispatches.
- Antigravity model tiers are `inherit`, `pro`, `flash`, and `flash_lite`.
- Tools must be declared explicitly from the supported Antigravity tools (`read_file`, `write_file`,
  `edit_file`, `run_command`, `manage_task`, `search_web`, `invoke_subagent`, `send_message`,
  `ask_question`). Never use banned agent keys (`disallowedTools`, `effort`, `color`,
  `enableSubagentTools`).
- One critic serves all domains. Add domain criteria to `critic.md` or to a skill it loads, not as a
  new critic agent.

## Word Caps

| Role | Agents | Body Word Cap |
|---|---|---|
| Main | supervisor | 1000 |
| Lead | researcher, planner, executor, writer | 700 |
| Review | critic, scope-critic | 600 |
| Worker | researcher-worker, planner-worker, executor-worker, writer-worker | 400 |
| Memory | curator | 400 |
| Quick | fixer, git-ops, scout | 350 |

Skills have a hard limit of 1380 body words (except `residue` which has a cap of 350 words),
at most 300 lines, and a file size under 24,000 bytes. The linter enforces all caps strictly.
Caps are ceilings, not targets: spend length on load-bearing contracts such as verdict tokens,
output schemas, and routing tables.

## Agent Files

- Frontmatter:
  - `name` (kebab-case, equal to the filename stem)
  - `description` (one sentence that says what and when, driving Antigravity routing)
  - `model` (one of `inherit`, `pro`, `flash`, `flash_lite`)
  - `tools` (explicit list of valid tools)
  - `mainAgent: true` and `subagent: false` for `supervisor`; `mainAgent: false` and
    `subagent: true` for all other agents
  - `agents` (list of subagents that the agent is allowed to invoke; omitted on leaf agents)
- Body: start with `You are ...`, then the sections the role needs: Mission or Scope,
  Rules or Operating, the domain procedure, then Report or Output.
- State scope boundaries with a named destination: "X goes to `executor`". When agent A routes to B,
  B's scope description must accept that work.
- Keep definitions self-contained: behaviour an agent or skill needs is stated in the pack's own
  files, never delegated to external repositories.
- Agents that report upward use a bounded report with explicit size caps.
- Prefer a skill over an agent when the component is a procedure or domain knowledge rather than a
  role with its own model or context needs.

## Skill Files

- `skills/<name>/SKILL.md` with `name` equal to the directory name. Spend effort on the
  `description`, which triggers loading: say what it does and when to use it.
- Never use banned skill keys (`user-invocable`, `context`, `argument-hint`). Use
  `disable-model-invocation: true` for skills that should not be triggered autonomously.
- Keep SKILL.md under 300 lines and 1380 body words (linted). Put bulky references in
  references/ and helpers in scripts/, referencing them via relative paths.

## Reviewing Definitions (for critic)

Judge a definition by its likely operational effect, not its tidiness:
- Will the routing description trigger at the right times?
- Can the agent do its job with the tools it has?
- Are its boundaries reciprocal with its neighbors?
- Are its contracts checkable?
- Does it duplicate rules that live in a preloaded skill?
- Is it self-contained, or does behaviour depend on unavailable files?

## After Changing The Pack

When an agent's name, scope, model, or tools change, run:
- `/usr/bin/python3 -m unittest discover -s tests -t . -v`
- `agy plugin validate --strict --json pack`
- Bump `VERSION` (X.y format) and add an entry at the top of `CHANGELOG.md`.
