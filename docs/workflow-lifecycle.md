# Workflow Lifecycle

This guide follows a task from the opening user prompt to session close-out: how `supervisor`
routes requests, how leads coordinate workers and reviewers, how state is preserved on disk,
and when it is safe to clear the conversation window.

## The Three Task Sizes

`agy-supervisor` adapts its execution path to the scale and risk of the task:

| Size | Dispatched Agents | State on Disk | Close-Out Action |
|---|---|---|---|
| **Small** | Mode 2 (`fixer`, `scout`, `git-ops`) | Changed files | Leftovers checked; no plan |
| **Medium** | Single lead (`planner`, etc.) | Working plan/notes | Purge leftovers; archive plan |
| **Large** | Multi-package program leads | Parent plan & waves | Wave booking; full close-out |

## Lifecycle Stages

### 1. Request Triage & Delegation Brief
The supervisor analyzes the user's prompt to choose Mode 1 (Full Lead Loop) or Mode 2 (Quick Tier).
When dispatching a lead, `supervisor` constructs a formal **Delegation Brief**:
- **Verbatim Request**: Exactly what the user asked.
- **Contract & Scope**: Acceptance criteria, boundaries, and explicit constraints.
- **Input & Output Paths**: Pointers to files; leads read disk, not caller context.
- **Review Setting**: `Review: full` (default), `Review: light` (one round unless BLOCKING),
  or `Review: none`.
- **Path Guard**: `Path: minimal` instructs agents to touch only necessary files.
- **Attribution Trailer**: Standard commit trailer `Co-Authored-By: Supervisor for Antigravity`.

### 2. Lead Execution & Worker Fan-Out
In Mode 1, the assigned lead follows the standard `lead-loop`:
1. **Contract**: Formalize acceptance criteria and bounds.
2. **Fan-Out**: Execute directly if single-unit; dispatch parallel workers (`executor-worker`,
   `planner-worker`, etc.) if disjoint file sets exist.
3. **Integrate**: Collect worker diffs and run unit tests.
4. **Independent Review**: Invoke `critic` (or probed `external-critic`). If findings warrant,
   invoke `scope-critic` to rule `KEEP`, `DOWNGRADE`, or `DROP`.
5. **Fix & Repeat**: Address kept defects up to 3 rounds.

### 3. Program Waves (`## Work Packages`)
Complex initiatives split into a DAG of work packages inside a parent plan:

```markdown
### P1: Database Migration
- Goal: Schema migration scripts and unit tests
- Owns: src/db/**, tests/test_db.py
- Deps: none
- Stages: plan, execute
- Status: open
```

The supervisor runs the program in **waves**: each wave dispatches all unblocked packages whose
dependencies are satisfied. At the completion of each wave, the plan file is updated and committed,
allowing long programs to pause and resume across sessions.

### 4. Residue Ledger & Teardown (`residue`)
Tests and build scripts often leave behind temporary directories, logs, background processes, or
scratch files. Agents record these in `.supervisor/working/residue/<agent>-<id>.md`.
- At task completion, `fixer` tears down all recorded residue.
- If a deletion is blocked by file permissions or active locks, the removal command is preserved
  and surfaced in the `Run yourself:` footer.

### 5. Session Close-Out (`close-out`)
Close-out transitions active work into durable project history:
1. `fixer` performs final residue teardown.
2. `curator` distills key architectural decisions into `.supervisor/memory/decisions/`.
3. Completed task cards under `.supervisor/tasks/` are updated (`met: YYYY-MM-DD`) and moved to
   `.supervisor/archive/tasks/`.
4. Completed plans in `.supervisor/working/plans/` move to `.supervisor/archive/working/plans/`.
5. A milestone entry is appended to `.supervisor/history.md`.
6. `git-ops` commits the memory changes.

## Structured Footers

Every significant supervisor response ends with standardized status blocks:

### 1. `Run yourself:` Block
Actions requiring human authority (such as remote git pushes, secrets input, or blocked residue
cleanup) are isolated at the end of the response:

````markdown
Run yourself:
```bash
git push origin feat/v10-parity
```
````

### 2. `Session state:` Footer
The final line indicates conversational clearance safety:

```text
Session state: closed out; residue removed; store committed; safe to /clear, resume with "next task"
```

If clearing the conversation would lose uncommitted work or pending questions, it signals:

```text
Session state: wave 2 running; not safe to /clear: pending answers to planner questions
```

## Resuming Work (`pick-up`)

Start a new Antigravity session and resume seamlessly using `pick-up`:
- **Resume Plan**: `agy-supervisor` $\to$ `/pick-up .supervisor/working/plans/plan-auth.md` reads
  plan status and suggests the next wave.
- **Pick Task Cards**: `pick-up` lists open cards in `.supervisor/tasks/` with fulfilled
  dependencies. Picking a card atomically claims it (`status: active`) and begins execution.

## Operating in One-Off Directories

A directory is a project when it sits inside a Git repository or contains `.supervisor/`,
`.agents/`, `GEMINI.md`, or `AGENTS.md`. Anywhere else is a one-off:
- No files are written to `.supervisor/` unless the user asks.
- If an agent generates durable insight, it notes:
  `not stored: no project store here; say *remember* or *make this a project* to keep it`.
