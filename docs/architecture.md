# Architecture

`agy-supervisor` provides a hierarchical multi-agent orchestration architecture tailored to
Google Antigravity (`agy` CLI, Antigravity IDE, Antigravity 2.0 Desktop).

## Architectural Overview

The coordinator (`supervisor`) forms the main conversation thread. It routes requests, briefs
delegates, and reports results to the user. It never inspects code directly or runs shell
commands.

```text
User
  │
  ▼
supervisor (Coordinator: routes, briefs, integrates; no shell tools)
  │
  ├──► Mode 1 (Full Loop)
  │      └── Lead: researcher | planner | executor | writer
  │            ├── Workers (disjoint file ownership; parallel fan-out)
  │            ├── critic (adversarial quality, tests & contract review)
  │            └── scope-critic (KEEP / DOWNGRADE / DROP & anti-bloat cuts)
  │
  ├──► Mode 2 (Quick Tier)
  │      └── Fast Specialist: scout | fixer | git-ops (single-turn, no review)
  │
  └──► Direct Dispatch
         └── curator (memory management, task-card lifecycle, store audit)
```

## The 15 Agents

| Agent | Model | Operational Focus | Assigned Tools |
|---|---|---|---|
| `supervisor` | `inherit` | Coordinator: routing & synthesis | Files, web, subagent tools |
| `planner` | `pro` | Architecture & DAG plans lead | Files, shell, subagent tools |
| `researcher` | `pro` | Code tracing & research lead | Files, shell, web, subagents |
| `executor` | `pro` | Code, tests & worktrees lead | Files, shell, subagent tools |
| `writer` | `inherit` | Technical prose & doc lead | Files & subagent tools |
| `critic` | `pro` | Quality, contract & test reviewer | `read_file`, `run_command` |
| `scope-critic` | `pro` | Anti-bloat guardian (KEEP/DROP) | `read_file` |
| `curator` | `flash` | Memory store & task-card curator | Files & `run_command` |
| `planner-worker` | `flash` | Repo research for planner lead | `read_file`, `run_command` |
| `researcher-worker` | `flash` | Web/code investigation worker | `read_file`, web, `run_command` |
| `executor-worker` | `flash` | Slice worker for assigned files | Files & `run_command` |
| `writer-worker` | `pro` | Voice-accurate prose worker | Files (`read`, `write`, `edit`) |
| `scout` | `flash_lite` | Fast symbol & task-card lookup | `read_file`, web, `run_command` |
| `fixer` | `flash_lite` | Surgical repair & residue teardown | Files & `run_command` |
| `git-ops` | `flash_lite` | Routine git & safe branch landing | `read_file`, `run_command` |

*Note*: "Files" denotes `read_file`, `write_file`, and `edit_file`. "Shell" denotes `run_command`.
"Subagents" denotes `invoke_subagent`, `define_subagent`, `manage_subagents`, `send_message`,
and `ask_question`. `supervisor` and `writer` omit shell tools to preserve clean context.

## Mode 1: The Full Lead Loop

Every lead (`planner`, `researcher`, `executor`, `writer`) follows the disciplined `lead-loop`:

1. **Contract**: Formalize the objective, explicit scope bounds, and verifiable acceptance checks.
2. **Fan-Out**:
   - If the task is a single unit, the lead implements it directly.
   - If work splits into independent units with disjoint file ownership, the lead dispatches
     parallel workers (`*-worker`).
3. **Integrate**: The lead validates worker deliverables, compiles diffs, and runs automated tests.
4. **Independent Review**:
   - `critic` verifies correctness, test coverage, and edge cases (rated `BLOCKING`, `SHOULD`,
     `NIT`).
   - `scope-critic` adjudicates findings (`KEEP`, `DOWNGRADE`, `DROP`) and flags speculative bloat
     (`CUTS`).
5. **Bounded Loop**: The lead addresses kept defects. Re-reviews evaluate only changed diffs (up
   to 3 rounds maximum).

### Single-Voice Drafting Principle
For documentation and manuscript writing, `writer` authors all central narrative and prose
directly. `writer-worker` gathers facts, inspects sources, and performs accuracy audits. This
guarantees unified authorial voice while retaining parallelized source grounding.

## Mode 2: The Quick Tier

For small, low-risk, fully specified tasks:
- `scout`: Read-only queries, symbol searches, listing open task cards.
- `fixer`: Single-file edits (up to 3 files / 40 lines), typo repairs, residue cleanup.
- `git-ops`: Fast status checks, staging, and commits.
Mode 2 skips worker fan-out and review loops. If a quick specialist discovers hidden complexity,
it escalates back to `supervisor` for Mode 1 re-routing.

## Work Packages & Multi-Session Programs

Plans with `## Work Packages` define a directed acyclic graph (DAG) of packages:

```markdown
### P1: Core Logic Refactor
- Goal: Decouple authentication handler
- Owns: src/auth/**, tests/test_auth.py
- Deps: none
- Stages: plan, execute
- Status: open
```

The supervisor runs the program in **waves**:
- Each wave executes all unblocked packages whose dependencies are complete.
- Plan status and logs are committed after each wave.
- If a lead requires architectural clarification, its package blocks without stalling
  independent branches.
- Sessions can be cleared (`/clear`) safely between waves and resumed via `pick-up`.

## Git Worktrees & Branch Isolation

In git repositories, `executor` creates an isolated worktree under `.agents/worktrees/<slug>`
cut from the default branch.
- Changes are developed and tested within the isolated worktree.
- Upon passing all test and critic checks, `executor` lands changes onto the default branch
  via a local squash merge with `Co-Authored-By: Supervisor for Antigravity`.
- The worktree and branch are automatically cleaned up.
- Code is never pushed to remote remotes without explicit user direction.

## The 17 Built-In Skills

| Skill | Primary Users | Purpose |
|---|---|---|
| `lead-loop` | All domain leads | 5-stage contract, fan-out, review, and reporting |
| `plan-writing` | `planner`, `critic` | Phased DAG plans, work packages, acceptance criteria |
| `project-memory` | `curator`, `fixer`, leads | Store layout, task cards, ADR entries |
| `git-safety` | `executor`, `git-ops` | Guardrails against destructive history rewrites |
| `repo-workflow` | `executor`, `planner` | Versioning (`X.y`), worktree landing, branch rules |
| `residue` | `executor`, `fixer`, workers | Temporary test artifact ledger and cleanup protocol |
| `python-env` | `executor`, workers | Virtualenv detection, uv integration, dependency sync |
| `agent-authoring`| `executor`, `critic` | Guidelines and lint rules for agents and skills |
| `science-writing-style` | `writer`, workers | Tone, precision, and conventions for manuscripts |
| `presentation-style` | `writer`, workers | Slide deck structure, budgets, and arc guidelines |
| `document-extraction` | Workers, `writer` | Structured extraction from reference documents |
| `email-extraction` | Workers, `writer` | Distills email threads into decisions, actions, owners |
| `meeting-summary`| User, `writer-worker` | Converts meeting transcripts into RAID summaries |
| `pick-up` | User, `supervisor` | Re-enters open plans or claims atomic task cards |
| `close-out` | User, `curator`, `fixer` | Tears down residue, distills memory, archives cards |
| `project-backup` | User | Timestamped zip backups with GFS retention |
| `supervisor-config` | User, leads | Configures cross-family external critic vs native critic |

## Antigravity Platform Constraints

- **Subagent Nesting**: Antigravity supports multi-level subagent spawning (`supervisor` $\to$
  `lead` $\to$ `worker`).
- **Tool Scoping**: Shell execution (`run_command`) is intentionally omitted from `supervisor`
  and `writer` to maintain pristine coordinator context.
- **Permissions**: External memory access and external critic review are granted explicit
  whitelisting in `settings.json`.
