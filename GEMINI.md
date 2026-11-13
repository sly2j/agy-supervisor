# Supervisor for Antigravity — Project Rules

Repository conventions for contributing to or modifying `agy-supervisor`.

## Runtime & Compatibility

- `deploy` and `pack/skills/supervisor-config/scripts/external-critic` MUST remain **Python 3.9+
  stdlib-only** (no third-party imports, no `X | Y` type unions, no `match/case`).
- Test suite (`tests/test_*.py`) MUST use stdlib `unittest` only (run via
  `/usr/bin/python3 -m unittest discover -s tests -t . -v`) and MUST isolate filesystem
  state in temporary directories (`AGY_CONFIG_DIR`, `AGY_CLI_DIR`, `--prefix`, `HOME`)
  without mutating real `~/.gemini` or `~/.local`.

## Versioning & Pack Invariants

- Any edit under `pack/` or to `deploy` MUST bump `VERSION` (`X.y` format, e.g. `1.1`) and add
  a matching `## <version> - YYYY-MM-DD` entry at the top of `CHANGELOG.md`.
- Every edit under `pack/` MUST keep:
  - `agy plugin validate --strict --json pack` exiting `0` with `"findings": []`
  - Non-fenced, non-table markdown prose lines `<= 100` characters
  - Tier word caps (`supervisor <= 1000`, leads `<= 700`, critics `<= 600`, workers `<= 400`,
    `curator <= 400`, quick agents `<= 350`, `SKILL.md <= 1380` words and `< 24,000` bytes)
  - Valid Antigravity agent model tiers only (`inherit`, `pro`, `flash`, `flash_lite`)

## Git & Continuity

- Keep durable project rules here in `GEMINI.md` and live session history/roadmap in
  `.supervisor/`.
- Local commits should use `Co-Authored-By: Supervisor for Antigravity` only.
- Never push remotely or mutate user global Antigravity config without explicit approval.
