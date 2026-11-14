# Supervisor for Antigravity — Project Rules

Repository conventions for contributing to or modifying `agy-supervisor`.

## Runtime & Compatibility

- `deploy`, `pack/skills/supervisor-config/scripts/external-critic`, and `tools/audit/audit.py` MUST
  remain **Python 3.9+ stdlib-only** (no third-party imports, no `X | Y` type unions, no
  `match/case`).
- `pack/skills/project-backup/scripts/backup.sh` MUST remain **Bash 3.2+ compatible** using
  parallel indexed arrays (no associative arrays `declare -A`).
- Test suite (`tests/test_*.py`) MUST use stdlib `unittest` only (run via
  `/usr/bin/python3 -m unittest discover -s tests -t . -v`) and MUST isolate filesystem
  state in temporary directories (`AGY_CONFIG_DIR`, `AGY_CLI_DIR`, `--prefix`, `HOME`)
  without mutating real `~/.gemini` or `~/.local`.
- Canonical routing suite (`tests/test_routing_scenarios.py`) runs 28 offline deterministic
  schema and contract checks by default; live Antigravity invocation is strictly opt-in via
  `AGY_LIVE_ROUTING=1`.

## Versioning & Pack Invariants

- Any edit under `pack/` or to `deploy` MUST bump `VERSION` (`X.y` format, e.g. `1.1`), sync
  `pack/plugin.json`, and add a matching `## <version> - YYYY-MM-DD` entry at the top of
  `CHANGELOG.md`.
- Every edit under `pack/` MUST keep:
  - `agy plugin validate --strict --json pack` exiting `0` with `"findings": []`
  - Non-fenced, non-table markdown prose lines `<= 100` characters across pack and docs
  - Tier word caps: `supervisor <= 1000`, leads `<= 700`, critics `<= 600`, workers `<= 400`,
    `curator <= 400`, quick agents `<= 350`, `SKILL.md <= 1380` words and `< 24,000` bytes
    (`residue <= 350` words)
  - Valid Antigravity agent model tiers only:
    - `inherit`: `supervisor`, `writer` (inherits Carbon medium launcher default)
    - `pro`: `planner`, `researcher`, `executor`, `critic`, `scope-critic`, `writer-worker`
    - `flash`: `curator`, `planner-worker`, `researcher-worker`, `executor-worker`
    - `flash_lite`: `scout`, `git-ops`, `fixer`

## Project Memory & Task Cards

- v10 `.supervisor/` store layout:
  - `.supervisor/README.md` (untracked layout guide derived from template)
  - `.supervisor/history.md` (append-only finished task log)
  - `.supervisor/tasks/` (active and open task cards: `YYYY-MM-DD-<slug>.md`)
  - `.supervisor/memory/` (in-force entries across `decisions`, `facts`, `lessons`, `goals`,
    `conventions`)
  - `.supervisor/working/` (short-term state across `plans`, `research`, `writing`, `residue`)
  - `.supervisor/archive/` (mirrors live tree for superseded entries, completed tasks, and plans)
- Do NOT use legacy `roadmap.md`; roadmap state is tracked as atomic task cards under
  `.supervisor/tasks/`.

## Git & Continuity

- Keep durable project rules here in `GEMINI.md` and live session history in `.supervisor/`.
- Local commits should use `Co-Authored-By: Supervisor for Antigravity` only.
- Never push remotely or mutate user global Antigravity config without explicit user approval.
