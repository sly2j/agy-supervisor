# Architecture

`agy-supervisor` implements a 3-tier hierarchical orchestration graph tailored to Google
Antigravity's native plugin and `invoke_subagent` runtime.

## Agent Hierarchy (15 Agents)

```text
supervisor (mainAgent: true, model: inherit, no shell)
├── Quick / Memory single-shot leaves
│   ├── scout        (flash_lite, read-only repo/web inspect)
│   ├── fixer        (flash_lite, single-file repair, never commits)
│   ├── git-ops      (flash_lite, safe git inspect/commit/worktree ops)
│   └── curator      (flash, maintains .supervisor/ memory, never commits)
├── Independent reviewers (also callable directly by supervisor or leads)
│   ├── critic       (pro, read-only adversarial verifier)
│   └── scope-critic (pro, read_file-only scope & gold-plating auditor)
└── Domain Leads (lead-loop skill, bounded <= 3 review cycles)
    ├── researcher (pro) ──► researcher-worker (flash) + external/native critic
    ├── planner    (pro) ──► planner-worker    (flash, read-only) + critic + scope-critic
    ├── executor   (flash) ─► executor-worker  (flash) + external/native critic + scope-critic
    └── writer     (pro) ──► writer-worker     (pro) + external/native critic + scope-critic
```

## Antigravity Tool & Model Mapping

- Valid Antigravity agent model tiers are `inherit`, `pro`, `flash`, and `flash_lite`.
- `supervisor` omits `run_command` and `manage_task` so heavy command output stays in child
  contexts, keeping the top-level coordination window clean.
- Generic Antigravity built-in subagents (`self`, `research`, `deepagent`, `review-agent`) are
  excluded unless explicitly requested by the user.
- Callers pass explicit `TypeName`, `Role`, self-contained `Prompt`, optional `Model`, and
  `Workspace: "inherit"` on `invoke_subagent`, then continue existing slices with
  `send_message(Recipient=conversationId, Message=...)`.

## Cross-Family External Critic

Leads follow `lead-loop`: probe `external-critic review --domain <domain> --probe` first.
- When disabled (default) or on error/timeout/malformed output, `lead-loop` falls back
  immediately to Antigravity's native `critic` subagent.
- When enabled (with explicit consent via `agy-supervisor critic enable <claude|codex>`),
  `external-critic` runs `claude -p --output-format text` or `codex exec --sandbox read-only`,
  validating `## Verdict` (`APPROVE` or `REQUEST CHANGES`) and `## Findings`.
