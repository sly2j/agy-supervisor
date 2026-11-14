---
name: supervisor-config
description: Switch the lead's critic between Claude, Codex, and native critic, or show which is active. Use when the user asks to configure external critic settings or check status.
disable-model-invocation: true
---

# Supervisor Config

Switch the external review backend of this install, configure per-domain models, or inspect status.

Available actions:
- `status`: show current external critic status and configured domain overrides.
- `enable {claude,codex} [model]`: enable Claude Code or OpenAI Codex as external critic.
- `disable`: disable external critic reviews and fall back to the native `critic` subagent.

## Consent Gate

Enabling an external critic sends code diffs, review briefs, and repository excerpts to the
external CLI provider (Anthropic or OpenAI). Never enable silently without explicit user
confirmation. The CLI prompts interactively or requires `--yes` in non-interactive sessions:

```
External critic consent:
- Reviews spend your provider quota / API credits.
- Repository content, review brief, and diffs are sent to the selected external CLI.
```

## Tooling

Commands run via `./scripts/external-critic`:

```bash
./scripts/external-critic status
./scripts/external-critic enable claude [model] --yes
./scripts/external-critic enable codex [model] --yes
./scripts/external-critic disable
```

Subagents without `run_command` (such as `supervisor` main thread) dispatch `fixer` or `git-ops`
with the exact command line to execute.

## Configuration

Settings persist in `supervisor-config.json` at the plugin root or `$AGY_SUPERVISOR_CONFIG`.
Supported domains are `research`, `plan`, `code`, `prose`, and `agent-definition`.
Per-domain overrides can be set with `--domain <domain>=<backend>[:<model>]` or in JSON:

```json
{
  "critic": {
    "enabled": true,
    "backend": "claude",
    "domains": {
      "code": "codex",
      "prose": "claude",
      "plan": {"backend": "codex", "model": "o3", "effort": "high"}
    }
  }
}
```

A domain value may be `"claude"`, `"codex"`, `"off"` (use native critic), or an object with
`backend`, `model`, and/or `effort`.
