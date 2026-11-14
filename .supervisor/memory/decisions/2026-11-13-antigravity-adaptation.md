---
domain: code
summary: adapt supervisor orchestration natively to google antigravity
affects: [pack/, deploy, pack/skills/supervisor-config/scripts/external-critic]
verified: 2026-11-13
source: user 2026-11-13
supersedes:
---
The supervisor orchestration pack is adapted natively to Google Antigravity (agy).
Why: Antigravity enforces strict plugin schemas (inherit, pro, flash, flash_lite model tiers,
explicit tools list, and subagent declarations) and avoids third-party dependencies.
Rejected: Retaining Claude Code-specific frontmatter, tools, or dependencies.
Behaviour stays in the `affects:` files; do not restate it.
