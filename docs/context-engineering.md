# Context Engineering

`agy-supervisor` is architected around a single coordinator agent that accumulates as little
context as possible. The coordinator delegates work to domain leads and fast specialists, and
leads delegate in turn to slice workers. Each runs in a fresh, isolated context window. Agents
maintain state in flat, auditable files under `.supervisor/`.

This document explains the principles and mechanisms behind this design. The operational
mechanics are detailed in [architecture.md](architecture.md).

## The Problem: Context Degradation Over Long Horizons

Context accumulates across two distinct time scales:
1. **Task Horizon**: In a multi-turn task, intermediate tool outputs, logs, diffs, and notes
   steadily consume the context window.
2. **Project History**: Across days or weeks, architectural decisions, conventions, and domain
   facts must inform future work without requiring re-prompting.

Drew Breunig's taxonomy of long-context degradation defines five core failure modes:
1. **Context Poisoning**: An erroneous fact or hallucination enters context and is repeatedly
   referenced in subsequent steps.
2. **Context Distraction**: A context grows so long that the model over-focuses on past context
   history, neglecting its base pre-training.
3. **Context Confusion**: Superfluous tools or extraneous information dilute model attention,
   causing degraded function calling.
4. **Context Clash**: Conflicting pieces of information accrue across turns, creating
   indecision or regression.
5. **Context Inertia**: The model commits to an early hypothesis or subtask and stubbornly
   persists even after contrary evidence emerges.

In agents spanning multi-hour tasks or cross-session programs, unmanaged context growth causes
severe context rot. `agy-supervisor` treats context as a scarce, perishable resource.

## Context Control Tactics

`agy-supervisor` counters context degradation using seven structural tactics:

| Tactic | Antigravity Mechanism | Countered Failure Mode |
|---|---|---|
| **Context Quarantine** | Fresh window per lead, worker, reviewer | Distraction, Inertia |
| **Context Offloading** | File persistence under `.supervisor/` | Information loss, Bloat |
| **Tool Loadout** | Fixed minimal tool definitions declared per role | Confusion, Clash |
| **Capped Summaries** | Bounded reports at every delegation boundary | Distraction in caller |
| **Pruning & Archival** | Curator retiring superseded plans to `archive/` | Strategic forgetting |
| **Plain Retrieval** | Grep-based discovery of targeted memory entries | Attention dilution |
| **Provenance Tracking** | Grounded source citations and critic verification | Poisoning |

## The Architecture of Context Boundaries

Context boundaries protect the main thread and prevent runaway token consumption:

```text
User Request
    │
    ▼
supervisor (Coordinator: one window for session; no shell; lossy summaries only)
    │
    ├──► Mode 2: scout / fixer / git-ops (fresh window; <= 15-line result)
    │
    └──► Mode 1: Domain Lead (researcher / planner / executor / writer)
            │   (fresh window; bounded <= 700-word report with artifact paths)
            │
            ├──► Workers (researcher-worker, planner-worker, executor-worker, writer-worker)
            │       (fresh window per unit; bounded <= 400-word reports)
            │
            ├──► critic (fresh window; quality & test verifier; max 12 findings)
            │
            └──► scope-critic (fresh window; KEEP / DOWNGRADE / DROP; anti-bloat cuts)
```

### 1. A Coordinator That Reads Almost Nothing
The top-level `supervisor` thread persists throughout the session. If it inspected large code
files or ran test suites directly, its window would quickly degrade.
- `supervisor` carries **no shell tool** (`run_command`).
- File reading is reserved for routing triage; deep exploration is delegated to `scout` or
  domain leads.
- In measured sessions, over 85% of total tokens are spent in discardable subagent windows.

### 2. Isolated Windows for Leads and Workers
Each lead agent executes in its own subagent context window. When a task splits into disjoint
units, the lead dispatches parallel workers. Each worker operates in a clean window, writes only
to its assigned files, and returns a bounded summary. A worker's mistakes remain contained
within its window unless explicitly incorporated into the lead's deliverable.

### 3. Decoupled Reviewer Windows
`critic` evaluates the deliverable in an independent context window, checking correctness,
test coverage, and adherence to project rules. In subsequent review rounds, it evaluates only
the delta of changed lines. `scope-critic` rules on each finding from `critic` (`KEEP`,
`DOWNGRADE`, `DROP`) and flags speculative additions (`CUTS`), preventing defensive bloat.

### 4. Capped Reports at Delegation Boundaries
Subagents do not dump raw command output or complete file contents back to their caller.
Instead, they emit structured, capped summaries:
- Leads return a concise status, changed paths, and verification outcomes.
- Workers return diff outlines and unit validation results.
- Reviewers return bounded markdown tables of findings.
Full artifacts live on disk; only references and high-signal summaries re-enter caller context.

### 5. Persistent File Storage Over In-Context Memory
Work spanning multiple sessions cannot reside in context. `agy-supervisor` externalizes durable
state to disk under `.supervisor/`:
- Short-term artifacts: `.supervisor/working/plans/` and `.supervisor/working/research/`
- Long-term memory: `.supervisor/memory/` across five explicit kinds
- Residue ledger: `.supervisor/working/residue/` tracking temporary test artifacts
A new session resumes seamlessly by reading plan files on disk via `pick-up`.

### 6. Role-Specific Tool Loadouts
Exposing every tool to every agent increases function-calling ambiguity. Each agent declares
a minimal toolset in its frontmatter:
- `supervisor` has file and subagent tools, but no shell.
- `writer` has file authoring tools, but no shell.
- `scope-critic` has `read_file` only.
- `git-ops` has git shell execution and `read_file`.
- `fixer` has surgical editing and test verification tools.

### 7. Provenance and Grounding Against Poisoning
To prevent poisoned assumptions from spreading:
- Memory entries are treated as claims to be verified, never unquestioned instructions.
- Research artifacts explicitly separate observed facts from labeled assumptions.
- `writer-worker` is constrained to source files; missing information must be flagged.
- `critic` verifies file paths, symbol names, and command flags against real files.

## Trade-offs & Token Efficiency

This multi-agent architecture introduces trade-offs:
1. **Instruction Overhead**: Strict contracts, schemas, and review protocols require substantial
   prompt instructions across agents and preloaded skills.
2. **Handoff Lossiness**: Summarizing worker outputs risks dropping subtle nuances, mitigated by
   storing complete artifacts on disk.
3. **Model Tiering**: Effective coordination and scope adjudication require capable models
   (Carbon and Pro). Running trivial tasks through cheap quick specialists (`flash_lite`)
   offsets this cost.

For small, one-off scripts, standard single-turn interaction suffices. For durable, multi-session
engineering and research, context engineering guarantees predictability and prevents decay.
