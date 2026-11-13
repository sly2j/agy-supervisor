# Workflow Lifecycle

`agy-supervisor` standardizes session startup, multi-phase execution, worktree landing,
and session close-out.

## 1. Pick-Up (`pick-up` skill)

- `supervisor` loads `GEMINI.md` rules and `.supervisor/roadmap.md` + tail of
  `.supervisor/history.md`.
- Dispatches `scout` or `git-ops` for live branch, `git status --short`, and worktree state.
- Summarizes current status and proposes the next slice before making edits.

## 2. Plan & Execute (`planner` -> `executor` -> `critic` + `scope-critic`)

- Non-trivial features pass through `planner` (`planner-worker` read-only grounding,
  `plan-writing` phased breakdown, independent `critic` + `scope-critic` review).
- Multi-file implementation runs in `executor`, isolating risky or concurrent edits in git
  worktrees under `<toplevel>/.agents/worktrees/<slug>` (ignored in `.git/info/exclude`).
- Before landing, `executor` checks tests, runs `external-critic` (or native `critic`) and
  `scope-critic`, sweeps temporary `residue`, and squash-merges locally without pushing unless
  the user asks.

## 3. Close-Out (`close-out` skill)

- `curator` appends verified milestones to `.supervisor/history.md`, updates
  `.supervisor/roadmap.md`, and logs any new ADRs in `.supervisor/memory/decisions/`.
- Neither `curator` nor `fixer` runs `git commit`; `git-ops` handles commits when requested
  with `Co-Authored-By: Supervisor for Antigravity`.
- `supervisor` closes with structured `Session state:` and `Run yourself:` footers.
