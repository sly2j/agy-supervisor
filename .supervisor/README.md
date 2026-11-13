# Project Memory Store (`.supervisor/`)

This directory holds durable, session-spanning project context managed by Supervisor for
Antigravity (`curator` and `writer` agents).

## Files

- `roadmap.md` — current milestone state, active phases, blockers, and immediate next steps
- `history.md` — append-only chronological log of verified milestones
- `memory/decisions/` — concise architectural decision records (`YYYY-MM-DD-<slug>.md`)
- `memory/conventions/` — durable project patterns, gotchas, and tooling notes
- `memory/drafts/` — optional writing/draft progress trackers

## Reading Order

1. Start sessions with `roadmap.md` and the tail of `history.md`.
2. Pull specific files from `memory/` only when touching the matching subsystem.
3. Update via `curator` on milestone boundaries or close-out (`close-out` skill).
