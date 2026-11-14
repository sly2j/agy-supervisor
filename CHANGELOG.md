# Changelog

All notable changes to Supervisor for Antigravity are documented in this file.
Every change to `pack/` or `deploy` bumps `VERSION` (`X.y`) and adds a section here.

## 1.1 - 2026-11-14

Major release achieving full upstream v10.2 operational and architectural parity for Google
Antigravity:

- **Model-Tier Alignment & Architecture**:
  - Main coordinator `supervisor` and writing lead `writer` run on `inherit` (Gemini 4 Carbon).
  - Deep leads and reviewers (`planner`, `researcher`, `executor`, `critic`, `scope-critic`,
    `writer-worker`) run on `pro`.
  - Scoped workers (`curator`, `planner-worker`, `researcher-worker`, `executor-worker`) run
    on `flash`.
  - Quick specialists (`fixer`, `git-ops`, `scout`) run on `flash_lite`.
  - Dynamic caller overrides: `supervisor` escalates `planner` (programs, cross-module designs,
    unfamiliar domains) and `executor` (hard refactors, race condition debugging, agent definitions)
    to `inherit` (Carbon); passes `pro` to `writer` for short, low-stakes prose; passes `flash` to
    `executor` for mechanical edits.
  - Launcher `--default-model` flag and `AGY_SUPERVISOR_MODEL` runtime environment override
    support.

- **Full v10.2 Agent & Skill Operational Port**:
  - Two-mode routing architecture: Mode 1 full loop (`researcher`, `planner`, `executor`,
    `writer`) and Mode 2 quick tier (`fixer`, `git-ops`, `scout`) with strict 4-point gating.
  - Sequential two-stage review: primary `critic` (6-column finding table, severity invariant
    `VERDICT: REVISE` iff `BLOCKING`, round 2+ delta reviews) followed by meta-reviewer
    `scope-critic` (`KEEP`, `DOWNGRADE`, `DROP` rulings and up to 8 material cuts).
  - Program execution with `## Work Packages` DAG waves, `Deps: done` dependency tracking,
    and `fixer` status advancement.
  - Single-voice drafting invariant in `writer` with subordinate worker research and audit.
  - Strict line-length (<= 100 chars), word caps (1000 main, 700 leads, 600 critics, 400
    workers, 350 quick), and Antigravity tool boundaries.

- **v10 Project Memory Architecture & Task Cards**:
  - Structured `.supervisor/` memory hierarchy: `tasks/`, `memory/` (5 core kinds), `working/`,
    and immutable `archive/`.
  - Standardized task card lifecycle in `pack/skills/project-memory/templates/task.md` (7 YAML
    frontmatter keys) and CAS atomic claims in `pick-up`.
  - Streamlined `entry.md` template (6 frontmatter keys, concise 3-part body) and `draft-state.md`
    tracking.
  - Procedural lifecycle operations in `curator` and `close-out` (`task`, `drop task`, `close-out`,
    `migrate`).

- **Tooling Enhancements**:
  - `./deploy` upgrades: backup creation (`.bak.<timestamp>`) on `--force` / `--overwrite-local`,
    multi-profile `update --all`, remote git source updates via `--from`, workspace permissions
    grant `plan_memory_grant`, and launcher generation.
  - `external-critic` expansion: 5 supported review domains (`research`, `plan`, `code`, `prose`,
    `agent-definition`), structured 6-column review parser, and non-interactive consent guards.
  - Project backup tool `backup.sh`: GFS grandfather-father-son retention algorithm (7 recent,
    4 weekly, monthly, bi-yearly, safety floor >= 3) and disk space guards.
  - Offline session audit CLI `tools/audit/audit.py`: hierarchical transcript reconstruction from
    `~/.gemini/antigravity-cli/brain/`, metric reporting, and privacy guardrails.

- **Expanded Verification & Canonical Routing Suite**:
  - Deterministic and opt-in live routing suite `tests/test_routing_scenarios.py` covering all 28
    canonical upstream routing cases mapped to Antigravity model tiers.
  - 11 new pack-lint invariant checks in `tests/test_pack_lint.py` validating models, template keys,
    attribution trailers, origin rebase rules, and script AST compatibility.
  - Expanded unit test coverage in `tests/test_backup.py`, `tests/test_audit.py`,
    `tests/test_deploy.py`, and `tests/test_version.py`.

## 1.0 - 2026-11-13

Initial release of Supervisor for Antigravity (`agy-supervisor`):

- **15-agent Antigravity hierarchy** under `pack/agents/`:
  - Main coordinator: `supervisor` (`inherit`, `mainAgent: true`)
  - Domain leads (`lead-loop`): `researcher`, `planner`, `executor`, `writer`
  - Scoped workers: `researcher-worker`, `planner-worker`, `executor-worker`, `writer-worker`
  - Independent reviewers: `critic`, `scope-critic`
  - Memory & quick single-shot agents: `curator`, `fixer`, `git-ops`, `scout`
- **17 skills** under `pack/skills/` covering orchestration (`lead-loop`, `plan-writing`,
  `residue`, `agent-authoring`), project memory (`project-memory`, `close-out`, `pick-up`,
  `project-backup`), git/worktree safety (`git-safety`, `repo-workflow`), domain workflows
  (`python-env`, `science-writing-style`, `presentation-style`, `document-extraction`,
  `email-extraction`, `meeting-summary`), and external critic configuration (`supervisor-config`).
- **Native Antigravity plugin bundle** (`pack/plugin.json` + `pack/assets/logo.svg`) passing
  `agy plugin validate --strict`.
- **Cross-family external critic (`external-critic`)** supporting opt-in Claude Code (`claude`)
  and OpenAI Codex (`codex`) CLI reviews with per-domain overrides and automatic fallback to
  the native `critic` subagent.
- **`./deploy` CLI** with `install`, `update`, `status`, `list`, `uninstall`, `doctor`,
  `critic`, and `memory` subcommands, 3-way SHA-256 baseline manifest merging, sibling-plugin
  suppression for `--tag`, scoped `settings.json` review permission wiring, and `~/.local/bin/agy-supervisor`
  launcher wrapper.
- **Externalized `.supervisor/` project memory store** and stdlib `unittest` suite under `tests/`.
