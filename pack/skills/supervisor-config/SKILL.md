---
name: supervisor-config
description: Manage optional cross-family external critic settings (Claude Code and OpenAI Codex) and consent.
---

# Supervisor External Critic Configuration

Supervisor supports an **optional, opt-in** cross-family external critic (`claude` or
`codex` CLI) to review code, plans, research, and prose from an independent model family.
External critics are **off by default** and fall back automatically to the native
`critic` subagent if disabled, missing, or unauthenticated.

## Tooling (`./scripts/external-critic`)

Resolve `external-critic` from `./scripts/external-critic` relative to this skill (or via
`agy-supervisor critic ...` / `deploy critic ...`):

- **Inspect status**:
  `./scripts/external-critic status`
- **Enable with explicit consent** (prompts interactively unless `--yes` is given):
  `./scripts/external-critic enable <claude|codex> [model] [--effort low|medium|high|max]`
  Add per-domain overrides with repeatable `--domain <domain>=<backend>[:<model>]`
  where `<domain>` is one of `research`, `plan`, `code`, `prose`.
- **Disable external critic**:
  `./scripts/external-critic disable`
- **Probe / run review** (used by leads inside `lead-loop`):
  `./scripts/external-critic review --domain code --probe`
  `./scripts/external-critic review --domain code --prompt-file <p> [--diff-file <d>]`

## Privacy & Consent Gate

Enabling an external critic sends prompts, specs, diffs, or file snippets to an external
CLI provider outside Antigravity. Never enable silently without explaining this data flow
and obtaining explicit user confirmation (interactive prompt or `--yes` after consent).
