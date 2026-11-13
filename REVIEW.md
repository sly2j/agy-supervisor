# Review Checklist (`agy-supervisor`)

Check every change against these repository invariants before accepting work:

1. **Antigravity Plugin Validity**:
   - Does `agy plugin validate --strict --json pack` exit `0` with `"findings": []`?
   - Are `model:` fields strictly within `{inherit, pro, flash, flash_lite}`?
   - Do skills omit unsupported keys (`user-invocable`, `context`, `argument-hint`) and use
     relative links instead of `${CLAUDE_SKILL_DIR}` / `$ARGUMENTS`?
2. **Orchestration Boundaries**:
   - Does `supervisor` stay free of `run_command` / `manage_task` and route through the 10
     listed subagents?
   - Do `curator` and `fixer` explicitly forbid `git commit`?
   - Do leaf agents omit `agents:` and `invoke_subagent` / `define_subagent` / `manage_subagents`?
   - Are generic built-in Antigravity subagents (`self`, `research`, `deepagent`,
     `review-agent`) banned unless requested by the user?
3. **Security & Consent**:
   - Is `external-critic` strictly opt-in (`enabled: false` by default) with explicit consent
     gating before enabling?
   - Does `deploy` add ONLY the scoped `Bash(.../external-critic review *)` permission rule to
     `settings.json` (never `enable` or `disable`)?
   - Does `deploy` keep non-manifest `supervisor-config.json` and unrelated keys in
     `config.json` / `settings.json` intact?
4. **Tests & Versioning**:
   - Did `VERSION` and `CHANGELOG.md` update if `pack/` or `deploy` changed after `HEAD`?
   - Do all stdlib `unittest` checks and `py_compile` pass cleanly?
