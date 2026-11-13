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
