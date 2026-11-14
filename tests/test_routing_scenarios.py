"""Tests for canonical routing scenarios in Supervisor for Antigravity.

Ported from upstream canonical routing scenarios, adapted to Antigravity's model-tier system:
- inherit: Gemini 4 Carbon escalation for supervisor, writer, planner (programs, cross-module),
  and executor (hard refactors, subtle debugging, agent design).
- pro: Gemini Pro for leads (planner, researcher, executor, critic, scope-critic, writer-worker)
  and caller override for short, low-stakes prose in writer.
- flash: Gemini Flash for scoped workers (curator, planner-worker, researcher-worker, executor-worker).
- flash_lite: Gemini Flash Lite for fast specialists (fixer, git-ops, scout).
- default: No caller override passed on dispatch (agent runs its frontmatter model).
"""

import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from typing import Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = REPO_ROOT / "pack"
SUPERVISOR_PATH = PACK_DIR / "agents" / "supervisor.md"

SCENARIOS = [
    # 1: Mode 2 fixer - typo fix
    (
        "Fix the typo 'recieve' in README.md.",
        "2",
        "fixer",
        "default",
    ),
    # 2: Mode 2 git-ops - commit staged changes
    (
        "Commit the staged changes with the message 'docs: clarify install steps'.",
        "2",
        "git-ops",
        "default",
    ),
    # 3: Mode 2 scout - symbol lookup
    (
        "Which file in this repo defines the function parse_frontmatter?",
        "2",
        "scout",
        "default",
    ),
    # 4: Direct response - conversational / conceptual question
    (
        "What is the difference between /clear and /compact?",
        "direct",
        "none",
        "default",
    ),
    # 5: Mode 1 researcher - codebase investigation & write-up
    (
        "Find out how deploy registers profiles and write it up.",
        "1",
        "researcher",
        "default",
    ),
    # 6: Mode 1 planner - feature planning
    (
        "Plan a `--json` flag for `deploy status`.",
        "1",
        "planner",
        "default",
    ),
    # 7: Mode 1 executor - implementation with tests
    (
        "Add a `--json` flag to `deploy status` with tests.",
        "1",
        "executor",
        "default",
    ),
    # 8: Mode 1 writer - proposal draft from notes
    (
        "Draft the overview section of our proposal from these notes: goals, budget, timeline.",
        "1",
        "writer",
        "default",
    ),
    # 9: Mode 2 fixer - small multi-file rename
    (
        "Rename the variable `cfg` to `config` across deploy, tests/test_deploy.py and docs/deploy.md.",
        "2",
        "fixer",
        "default",
    ),
    # 10: Mode 1 executor - escalated rename exceeding quick boundary
    (
        "The fixer reported: ESCALATE: the rename touches 12 files and two call sites change signature. What now?",
        "1",
        "executor",
        "default",
    ),
    # 11: Mode 2 git-ops - routine push
    (
        "Push main to origin.",
        "2",
        "git-ops",
        "default",
    ),
    # 12: Mode 1 executor - class refactor with known design
    (
        "Move the four profile-registry functions in deploy into a `ProfileRegistry` class with the same method names and update their three callers.",
        "1",
        "executor",
        "default",
    ),
    # 13: Mode 2 fixer - quick test fix
    (
        "Quick: fix the failing test in tests/test_deploy.py.",
        "2",
        "fixer",
        "default",
    ),
    # 14: Mode 1 executor - behavior change requiring execution & verification
    (
        "Change the default backup directory to ~/backups; existing users' backups will land there from now on.",
        "1",
        "executor",
        "default",
    ),
    # 15: Mode 1 planner - default tier decision plan
    (
        "Plan how to add retry logic to the backup step of `deploy install`; I'm not sure whether a decorator or a loop fits better.",
        "1",
        "planner",
        "default",
    ),
    # 16: Mode 1 planner - program / cross-service migration -> inherit (Carbon escalation)
    (
        "Plan the move of all our services to a new auth provider: the gateway, billing, the web app and the CLI each need changes over the next quarter.",
        "1",
        "planner",
        "inherit",
    ),
    # 17: Mode 1 planner - open cross-module design with trade-offs -> inherit (Carbon escalation)
    (
        "Work out how the deploy tool's profile registry and the test harness's fixture loader should share state; I see a few approaches with real trade-offs and want a plan.",
        "1",
        "planner",
        "inherit",
    ),
    # 18: Mode 1 planner - unfamiliar domain / port -> inherit (Carbon escalation)
    (
        "Plan a port of the deploy tool to Windows; nobody here has done Windows packaging before.",
        "1",
        "planner",
        "inherit",
    ),
    # 19: Mode 1 planner - explicit thoroughness request -> inherit (Carbon escalation)
    (
        "Plan a `--quiet` flag for `deploy status`, and be thorough about it.",
        "1",
        "planner",
        "inherit",
    ),
    # 20: Mode 1 planner - plan annotation updates -> default
    (
        "I left comments in .supervisor/plans/auth-migration.md (the quarter-long program moving the gateway, billing, web app and CLI to a new auth provider); work through my annotations and update the plan.",
        "1",
        "planner",
        "default",
    ),
    # 21: Mode 1 planner - checklist sync -> default
    (
        "Sync the checklist in .supervisor/plans/auth-migration.md (the quarter-long program moving the gateway, billing, web app and CLI to a new auth provider) with what has landed in git.",
        "1",
        "planner",
        "default",
    ),
    # 22: Mode 1 writer - short low-stakes email -> pro override
    (
        "Write a short email to the team saying the deploy window moves to Thursday.",
        "1",
        "writer",
        "pro",
    ),
    # 23: Mode 1 writer - methods paper paragraph -> default
    (
        "Write the methods paragraph for our paper on the detector calibration from these notes.",
        "1",
        "writer",
        "default",
    ),
    # 24: Mode 1 executor - subtle race condition debugging -> inherit (Carbon escalation)
    (
        "tests/test_deploy.py fails intermittently, only when run in parallel; track down the race and fix it.",
        "1",
        "executor",
        "inherit",
    ),
    # 25: Mode 1 executor - agent design in pack/agents -> inherit (Carbon escalation)
    (
        "Write a new agent definition for a security reviewer in pack/agents.",
        "1",
        "executor",
        "inherit",
    ),
    # 26: Mode 1 executor - legacy multi-module split -> inherit (Carbon escalation)
    (
        "Split deploy into a package with cli.py, profiles.py and install.py along its existing sections; I haven't touched that code in years.",
        "1",
        "executor",
        "inherit",
    ),
    # 27: Mode 1 researcher - investigate before changing -> default
    (
        "Why is `deploy install` slow on macOS? Investigate before we change anything.",
        "1",
        "researcher",
        "default",
    ),
    # 28: Mode 1 executor - specific crash fix with repro and review -> default
    (
        "`deploy status` crashes with `KeyError: 'profile'` at deploy:412 when no profile is registered. Fix it and add a regression test, with review.",
        "1",
        "executor",
        "default",
    ),
]

WRAPPER = (
    "Routing check only: do not dispatch or call tools; answer from your routing rules; "
    "reply with exactly one line `MODE: <1|2|direct>; AGENT: <name|none>; MODEL: <tier>`.\n\nRequest: "
)

VALID_MODES = {"1", "2", "direct"}
VALID_MODEL_TIERS = {"default", "inherit", "pro", "flash", "flash_lite"}


def parse_routing_response(text: str) -> Optional[Tuple[str, str, str]]:
    match = re.search(
        r"MODE:\s*`?`?(1|2|direct)`?`?;\s*AGENT:\s*`?(\S+?)`?[`.,;]*\s*;\s*MODEL:\s*`?([a-z_]+)`?[`.,;]*",
        text or "",
        re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).lower(), match.group(2).strip("`.,;").lower(), match.group(3).strip("`.,;").lower()


class RoutingScenariosDeterministicTest(unittest.TestCase):
    """Part A: Deterministic Always-On Suite verifying routing scenario contracts."""

    def test_scenario_count(self) -> None:
        self.assertEqual(len(SCENARIOS), 28, "Canonical routing suite must contain exactly 28 scenarios")

    def test_scenarios_tuple_schema(self) -> None:
        known_agents = {p.stem for p in (PACK_DIR / "agents").glob("*.md")}
        for idx, (prompt, mode, agent, model) in enumerate(SCENARIOS, 1):
            with self.subTest(scenario_index=idx, prompt=prompt[:40]):
                self.assertTrue(prompt.strip(), f"Scenario {idx}: prompt is empty")
                self.assertIn(mode, VALID_MODES, f"Scenario {idx}: invalid mode {mode!r}")
                if mode == "direct":
                    self.assertEqual(agent, "none", f"Scenario {idx}: direct mode must specify agent 'none'")
                else:
                    self.assertIn(agent, known_agents, f"Scenario {idx}: agent {agent!r} not in pack/agents")
                self.assertIn(model, VALID_MODEL_TIERS, f"Scenario {idx}: invalid model tier {model!r}")

    def test_supervisor_agent_documents_all_routing_contract_elements(self) -> None:
        self.assertTrue(SUPERVISOR_PATH.is_file(), "supervisor.md missing")
        text = SUPERVISOR_PATH.read_text(encoding="utf-8")

        # Modes documented
        self.assertIn("Mode 1: full loop", text)
        self.assertIn("Mode 2: quick tier", text)
        self.assertIn("Answer directly", text)

        # Mode 1 leads documented
        for lead in ("researcher", "planner", "executor", "writer"):
            self.assertIn(f"`{lead}`", text)

        # Mode 2 specialists documented
        for specialist in ("fixer", "git-ops", "scout"):
            self.assertIn(f"`{specialist}`", text)

        # Dynamic caller overrides documented
        self.assertIn('Model: "pro"', text)
        self.assertIn('Model: "inherit"', text)
        self.assertIn('Model: "flash"', text)

        # Structured probe output format documented
        self.assertIn("MODE: <1|2|direct>; AGENT: <name|none>; MODEL: <tier>", text)

    def test_parse_routing_response_helper(self) -> None:
        sample = "MODE: 1; AGENT: planner; MODEL: inherit."
        parsed = parse_routing_response(sample)
        self.assertEqual(parsed, ("1", "planner", "inherit"))

        sample_backticks = "MODE: `2`; AGENT: `fixer`; MODEL: `default`"
        parsed_backticks = parse_routing_response(sample_backticks)
        self.assertEqual(parsed_backticks, ("2", "fixer", "default"))

        sample_direct = "MODE: direct; AGENT: none; MODEL: default"
        parsed_direct = parse_routing_response(sample_direct)
        self.assertEqual(parsed_direct, ("direct", "none", "default"))


class RoutingScenariosLiveTest(unittest.TestCase):
    """Part B: Opt-in Live Routing Suite invoking deployed agy/agy-supervisor."""

    @unittest.skipUnless(
        os.environ.get("AGY_LIVE_ROUTING") == "1",
        "set AGY_LIVE_ROUTING=1 to run live agy routing checks",
    )
    def test_live_routing_suite(self) -> None:
        agy_cmd = (
            os.environ.get("AGY_BIN")
            or shutil.which("agy-supervisor")
            or shutil.which("agy")
            or str(Path.home() / ".local" / "bin" / "agy-supervisor")
        )
        if not shutil.which(agy_cmd) and not Path(agy_cmd).is_file():
            self.skipTest(f"Neither agy nor agy-supervisor available at {agy_cmd}")

        for idx, (prompt, expected_mode, expected_agent, expected_model) in enumerate(SCENARIOS, 1):
            with self.subTest(scenario=idx, prompt=prompt[:40]):
                cmd = [
                    agy_cmd,
                    "-p",
                    WRAPPER + prompt,
                    "--agent",
                    "supervisor",
                ]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                self.assertEqual(
                    proc.returncode,
                    0,
                    f"Live routing failed for scenario {idx}: {proc.stderr}\nOutput: {proc.stdout}",
                )
                parsed = parse_routing_response(proc.stdout)
                self.assertIsNotNone(
                    parsed,
                    f"Scenario {idx}: Could not parse routing from output:\n{proc.stdout}",
                )
                expected = (expected_mode, expected_agent, expected_model)
                self.assertEqual(
                    parsed,
                    expected,
                    f"Scenario {idx} mismatch: got {parsed}, expected {expected}",
                )


if __name__ == "__main__":
    unittest.main()
