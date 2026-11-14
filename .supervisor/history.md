# Project History

Append-only log of verified milestones.

## 2026-11-13 — Initial Supervisor for Antigravity Release (`v1.0`)

- Created native Antigravity plugin bundle in `pack/` (`plugin.json`, `assets/logo.svg`,
  15 agents across main/lead/worker/critic/memory/quick tiers, and 17 skills).
- Verified `agy plugin validate --strict --json pack` passed with `"findings": []` (15 agents,
  17 skills).
- Implemented stdlib-only `./deploy` CLI with 3-way SHA-256 manifests, `--tag`, `--workspace`,
  `--target`, launcher wrapper, `doctor`, `critic`, and `memory` externalization.
- Implemented opt-in cross-family `external-critic` script supporting Claude Code (`claude`)
  and OpenAI Codex (`codex`) with per-domain overrides and native `critic` fallback.

## 2026-11-14 — Full claude-agents v10.2 Parity & Model-Tier Alignment (v1.1)

- Aligned 15 agents to Antigravity model tiers (supervisor/writer inherit Carbon; planner,
  researcher, executor, critic, scope-critic, writer-worker on pro; curator and workers on flash;
  fixer, git-ops, scout on flash_lite) and added launcher `--default-model` support.
- Achieved full operational parity with upstream claude-agents v10.2: Mode 1/2 routing, sequential
  critic -> scope-critic meta-review, Work Packages waves, and single-voice writer.
- Upgraded project memory to v10 architecture (.supervisor/tasks/ cards, immutable archive/,
  6-key entry.md and 7-key task.md templates, atomic CAS claims, and idle-plan sweeps).
- Delivered production tooling: deploy backup creation (.bak.<timestamp>), update --all/--from,
  plan_memory_grant; 5-domain external-critic; GFS retention backup.sh; and tools/audit/audit.py.
- Completed 6-doc reference manual under docs/ covering architecture, workflow lifecycle, local
  memory, model tiers, deploy operations, and context engineering.
- Expanded stdlib unittest suite to 78 passing tests, adding 11 pack-lint invariant checks and 28
  canonical routing scenarios with deterministic contract validation and opt-in live execution.
