---
name: lead-loop
description: Shared lead loop connecting subagents, external or native critics, scope checks, and capped reports.
---

# Lead Orchestration Loop

Follow this loop on every non-trivial lead pass (`researcher`, `planner`, `executor`, `writer`).

## Subagent Discipline

Use `invoke_subagent` with `TypeName`, `Role`, `Prompt`, optional `Model`, and
`Workspace: "inherit"`. Send follow-up turns to an active worker using `send_message`
with its returned `conversationId` instead of spawning duplicates for the same slice.

Never invoke Antigravity's built-in generic subagents (`self`, `research`, `deepagent`,
`review-agent`) unless the user explicitly asks for them; stay inside the supervisor
hierarchy (`<lead>-worker`, `critic`, `scope-critic`).

## Worker Before Critic

1. **Frame the slice**: clarify exact inputs, files/modules, verification command, and
   stop criteria before spawning a worker.
2. **Delegate substantive work**: spawn `<lead>-worker` first via `invoke_subagent`. Run
   independent read-only checks or parallel worker slices together when safe.
3. **Verify before trusting**: inspect key modified files, command exit statuses, and
   targeted test output yourself; confirm zero leftover residue.

## Review Gate (External Critic First, Native Fallback)

Before declaring success on any substantive change, plan, analysis, or draft:

1. Locate the external critic script relative to the installed plugin (use
   `skills/supervisor-config/scripts/external-critic` in the plugin root, or locate it in
   the project/plugin directory) and probe whether an external critic is configured for
   your domain (`research`, `plan`, `code`, `prose`):
   `external-critic review --domain <domain> --probe`
2. If the probe exits 0 and prints a backend/model line, write the self-contained review
   prompt and diff/artifact payload into a scratch file (never rely on huge inline args),
   and invoke:
   `external-critic review --domain <domain> --prompt-file <prompt> --output <out>`
   If the repo diff or target files exceed compact prompt size, pass `--diff-file <patch>`
   or target file summaries in the scratch packet so the external critic sees the exact
   change without scanning unrelated files.
3. If the probe fails, outputs `NO_EXTERNAL_CRITIC`, times out, or fails block validation,
   immediately fall back to the native `critic` subagent via `invoke_subagent`.
   Pass the same self-contained context: task goal, changed paths/diff, commands run, and
   exact expected vs observed outputs.
4. For code/config changes or multi-file passes, also invoke `scope-critic` with the
   user ask, plan/task brief, and exact changed file list (`git status` / `git diff --name-only`).
5. **Bounded fix cycle**: if `critic`, external critic, or `scope-critic` returns `REQUEST
   CHANGES` or flags blocking issues, dispatch `<lead>-worker` (or `send_message` to it)
   to fix, re-verify, and re-review. Stop after 3 failed review cycles and report clearly
   to `supervisor` with remaining blockers and diagnostics.

## Output Cap

Return a concise, structured report to `supervisor`:
- **Status**: `DONE` | `BLOCKED` | `PARTIAL`
- **Summary**: what was accomplished and why
- **Files changed**: exact paths edited or created (or `none`)
- **Verification**: commands run and exact observed pass/fail counts
- **Open issues / Review notes**: remaining blockers, critic verdicts, or follow-ups
