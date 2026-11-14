# Model Tiers & Antigravity Alignment

`agy-supervisor` aligns Google Antigravity's model tiers with upstream orchestration roles to
balance reasoning depth, context durability, execution speed, and token cost.

## Antigravity Model Tiers Overview

Antigravity strictly validates agent frontmatter against four model identifiers (`agy plugin
validate --strict`):

| Antigravity Tier | Runtime Identity | Characteristics | Upstream Analog |
|---|---|---|---|
| `inherit` | Carbon medium | Top-level coordinator & natural prose lead | `fable` |
| `pro` | Gemini Pro | Deep architectural reasoning, review rigor | `opus` |
| `flash` | Gemini Flash | Parallel slices, task curation, worker units | `sonnet` |
| `flash_lite` | Gemini Flash Lite | Rapid lookups, surgical fixes, git checks | `haiku` |

## 15-Agent Model Assignment Matrix

Every agent declares an explicit `model:` field in its frontmatter (`pack/agents/<name>.md`):

| Agent Role | File Name | Frontmatter `model:` | Default Engine | Invocable Tools |
|---|---|---|---|---|
| `supervisor` | `supervisor.md` | `inherit` | Carbon medium | Files, web, subagents |
| `writer` | `writer.md` | `inherit` | Carbon medium | Files & subagent tools |
| `planner` | `planner.md` | `pro` | Gemini Pro | Files, shell, subagents |
| `researcher` | `researcher.md` | `pro` | Gemini Pro | Files, shell, web, subagents |
| `executor` | `executor.md` | `pro` | Gemini Pro | Files, shell, subagents |
| `critic` | `critic.md` | `pro` | Gemini Pro | `read_file`, `run_command` |
| `scope-critic` | `scope-critic.md` | `pro` | Gemini Pro / Carbon | `read_file` |
| `writer-worker`| `writer-worker.md` | `pro` | Gemini Pro | `read`, `write`, `edit_file` |
| `curator` | `curator.md` | `flash` | Gemini Flash | Files & `run_command` |
| `planner-worker` | `planner-worker.md` | `flash` | Gemini Flash | `read_file`, `run_command` |
| `researcher-worker` | `researcher-worker.md` | `flash` | Flash | `read`, web, `run_command` |
| `executor-worker` | `executor-worker.md` | `flash` | Gemini Flash | Files & `run_command` |
| `scout` | `scout.md` | `flash_lite` | Gemini Flash Lite | `read_file`, web, `run_command` |
| `fixer` | `fixer.md` | `flash_lite` | Gemini Flash Lite | Files & `run_command` |
| `git-ops` | `git-ops.md` | `flash_lite` | Gemini Flash Lite | `read_file`, `run_command` |

*Note*: "Files" denotes `read_file`, `write_file`, and `edit_file`. "Shell" denotes `run_command`.
"Subagents" denotes Antigravity subagent delegation tools (`invoke_subagent`, `define_subagent`,
`manage_subagents`, `send_message`, `ask_question`). `supervisor` and `writer` omit shell tools.

## Rationale for Tier Assignments

### 1. Orchestrator and Lead Prose (`inherit` / Gemini 4 Carbon)
The main coordinator (`supervisor`) and writing lead (`writer`) run on the session's default
model (`gemini-4-carbon-medium`). Carbon excels at high-level routing, concise briefing, and
synthesizing natural, voice-accurate prose. `supervisor` carries no shell tools (`run_command`),
ensuring heavy execution context stays isolated in child subagents.

### 2. High Reasoning Leads and Independent Reviewers (`pro`)
`planner`, `researcher`, and `executor` handle complex decision-making, dependency tracking,
and multi-file refactoring. They require Gemini Pro's rigorous analytical capabilities.
`writer-worker` also runs on `pro` (rather than `flash`) so that drafted sections or source
extractions faithfully adhere to established tone and formatting conventions.

### 3. Reviewer Decoupling & `scope-critic` Ceiling
`critic` evaluates code, plan, and research artifacts for correctness, testing, and edge cases.
A single reviewer drifts toward defensive over-engineering. To counteract bloat, `scope-critic`
serves as a meta-reviewer, ruling on each finding (`KEEP`, `DOWNGRADE`, `DROP`) and listing
unnecessary additions to cut (`CUTS`).
- `scope-critic` declares `model: pro` in frontmatter as a quality floor.
- When dispatched by Carbon callers (`supervisor`, `writer`), the caller passes
  `Model: "inherit"`, granting `scope-critic` Carbon's superior anti-bloat discrimination.

### 4. Bounded Workers and Memory Curator (`flash`)
Workers perform concrete, single-unit tasks within strict file boundaries. They return bounded
summaries and diffs. Running workers on Gemini Flash provides high throughput and parallelism
at low token cost. `curator` runs on `flash` to maintain the `.supervisor/` memory store,
perform close-out migrations, and summarize task status cleanly.

### 5. Quick Leaf Specialists (`flash_lite`)
Mode 2 specialists (`scout`, `fixer`, `git-ops`) handle trivial reads, atomic single-file edits,
and routine git operations. Gemini Flash Lite delivers near-instant turnarounds while consuming
minimal context. If a quick specialist encounters ambiguity, conflicts, or broad scope, it
escalates immediately back to `supervisor`.

## Dynamic Caller Override Rules

Callers adjust subagent model tiers dynamically via `invoke_subagent(Model=...)`:

- **`planner` Escalation**: `supervisor` invokes `planner` with `Model: "inherit"` (Carbon) for
  multi-work-package programs, cross-module architecture designs, unfamiliar domains, or when the
  user requests "thorough" or "full" planning.
- **`writer` Downgrade**: `supervisor` invokes `writer` with `Model: "pro"` when drafting short,
  low-stakes text (e.g. status emails, internal meeting notes, single-paragraph updates).
- **`executor` Adjustment**: `supervisor` invokes `executor` with `Model: "inherit"` (Carbon)
  for subtle race conditions, distributed bugs, or agent definition changes; it passes
  `Model: "flash"` for purely mechanical, repetitive, or strictly specified tasks.
- **`scope-critic` Inheritance**: Carbon callers pass `Model: "inherit"` so `scope-critic`
  operates at Carbon reasoning levels.

## Launcher Model Configuration

The deployed launcher wrapper (`agy-supervisor`) resolves models hierarchically:

1. **User CLI Flag**: Explicit `--model <id>` or `-m <id>` passed on the command line always takes
   precedence.
2. **Environment Variable**: `AGY_SUPERVISOR_MODEL` overrides the installed default:
   ```bash
   export AGY_SUPERVISOR_MODEL="gemini-4-carbon-medium"
   agy-supervisor
   ```
3. **Installed Default**: Configured during `./deploy install --default-model <id>` (stored in the
   registry and recorded in `.agy-supervisor-manifest.json`).

## Antigravity IDE & Desktop Model Selection

When operating inside Antigravity IDE or Antigravity 2.0 Desktop:
- Select the active profile from the model selector dropdown (default: Gemini 4 Carbon).
- Child subagents launched via `invoke_subagent` will respect the frontmatter declarations and
  dynamic caller overrides automatically.
- Antigravity's native subagent spawn depth permits nested delegations (`supervisor` $\to$ `lead`
  $\to$ `worker`), ensuring Mode 1 full loops operate without depth restriction warnings.
