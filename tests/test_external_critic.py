"""Tests for cross-family external-critic configuration, invocation, and fallback."""

import importlib.util
from importlib.machinery import SourceFileLoader
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "pack" / "skills" / "supervisor-config" / "scripts" / "external-critic"

loader = SourceFileLoader("external_critic", str(SCRIPT))
spec = importlib.util.spec_from_loader("external_critic", loader)
assert spec is not None
ext_critic = importlib.util.module_from_spec(spec)
loader.exec_module(ext_critic)


def write_fake_cli(bin_dir: Path, name: str, body: str) -> Path:
    path = bin_dir / name
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    os.chmod(str(path), stat.S_IRWXU)
    return path


class ExternalCriticTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ext-critic-test-")
        self.root = Path(self.tmp.name)
        self.cfg_path = self.root / "supervisor-config.json"
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.env = os.environ.copy()
        self.env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"
        self.env["AGY_SUPERVISOR_CONFIG"] = str(self.cfg_path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_critic(self, *args: str, env=None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            env=env or self.env,
            timeout=15,
            check=False,
        )

    def test_disabled_by_default_and_probe_exits_2(self) -> None:
        st = self.run_critic("status", "--json")
        self.assertEqual(st.returncode, 0, st.stderr)
        data = json.loads(st.stdout)
        self.assertFalse(data["enabled"])

        probe = self.run_critic("review", "--domain", "code", "--probe")
        self.assertEqual(probe.returncode, 2)
        self.assertEqual(probe.stdout.strip(), "NO_EXTERNAL_CRITIC")

    def test_enable_requires_yes_when_non_tty(self) -> None:
        write_fake_cli(self.bin_dir, "claude", "import sys\nprint('{}')\n")
        res = self.run_critic("enable", "claude")
        self.assertEqual(res.returncode, 1)
        self.assertFalse(self.cfg_path.exists())

    def test_enable_claude_with_codex_domain_override_and_review(self) -> None:
        claude_log = self.root / "claude_args.json"
        codex_log = self.root / "codex_args.json"
        write_fake_cli(
            self.bin_dir,
            "claude",
            f"""
import json, sys
if sys.argv[1:4] == ["auth", "status", "--json"]:
    print(json.dumps({{"loggedIn": True}}))
    sys.exit(0)
stdin_text = sys.stdin.read()
open({str(claude_log)!r}, "w").write(json.dumps({{"argv": sys.argv[1:], "stdin": stdin_text}}))
print('''VERDICT: PASS
ROUND: 1

| ID | Severity | Location | Finding | Evidence | Minimal fix |
|---|---|---|---|---|---|

VALIDATION: checked
NOTES: all clean''')
""",
        )
        write_fake_cli(
            self.bin_dir,
            "codex",
            f"""
import json, sys
if sys.argv[1:3] == ["login", "status"]:
    print("Logged in")
    sys.exit(0)
stdin_text = sys.stdin.read()
open({str(codex_log)!r}, "w").write(json.dumps({{"argv": sys.argv[1:], "stdin": stdin_text}}))
print('''VERDICT: REVISE
ROUND: 1

| ID | Severity | Location | Finding | Evidence | Minimal fix |
|---|---|---|---|---|---|
| C1 | BLOCKING | file.py:1 | missing guard | quote | add guard |

VALIDATION: inspected diff
NOTES: needs fix''')
""",
        )

        en = self.run_critic(
            "enable",
            "claude",
            "claude-sonnet",
            "--effort",
            "high",
            "--domain",
            "code=codex:gpt-5",
            "--yes",
        )
        self.assertEqual(en.returncode, 0, en.stderr)
        saved = json.loads(self.cfg_path.read_text(encoding="utf-8"))
        self.assertTrue(saved["enabled"])
        self.assertEqual(saved["backend"], "claude")
        self.assertEqual(saved["domains"]["code"], {"backend": "codex", "model": "gpt-5"})

        probe_plan = self.run_critic("review", "--domain", "plan", "--probe")
        self.assertEqual(probe_plan.returncode, 0)
        self.assertEqual(probe_plan.stdout.strip(), "claude claude-sonnet")

        probe_code = self.run_critic("review", "--domain", "code", "--probe")
        self.assertEqual(probe_code.returncode, 0)
        self.assertEqual(probe_code.stdout.strip(), "codex gpt-5")

        prompt_file = self.root / "prompt.md"
        prompt_file.write_text("Review the diff.", encoding="utf-8")
        diff_file = self.root / "change.patch"
        diff_file.write_text("+x = 1\n", encoding="utf-8")
        out_file = self.root / "review.md"

        rev_code = self.run_critic(
            "review",
            "--domain",
            "code",
            "--prompt-file",
            str(prompt_file),
            "--diff-file",
            str(diff_file),
            "--output",
            str(out_file),
        )
        self.assertEqual(rev_code.returncode, 0, rev_code.stderr)
        self.assertIn("VERDICT: REVISE", out_file.read_text(encoding="utf-8"))
        self.assertIn("missing guard", out_file.read_text(encoding="utf-8"))
        c_call = json.loads(codex_log.read_text(encoding="utf-8"))
        self.assertEqual(c_call["argv"], ["exec", "--sandbox", "read-only", "-m", "gpt-5"])
        self.assertIn("+x = 1", c_call["stdin"])

        rev_plan = self.run_critic("review", "--domain", "plan", "--prompt-file", str(prompt_file))
        self.assertEqual(rev_plan.returncode, 0, rev_plan.stderr)
        self.assertIn("VERDICT: PASS", rev_plan.stdout)
        cl_call = json.loads(claude_log.read_text(encoding="utf-8"))
        self.assertEqual(
            cl_call["argv"],
            ["-p", "--output-format", "text", "--model", "claude-sonnet", "--effort", "high"],
        )

        dis = self.run_critic("disable")
        self.assertEqual(dis.returncode, 0)
        probe_after = self.run_critic("review", "--domain", "code", "--probe")
        self.assertEqual(probe_after.returncode, 2)

    def test_all_five_domains_supported_including_agent_definition(self) -> None:
        write_fake_cli(self.bin_dir, "claude", "import sys\nsys.exit(0)\n")
        write_fake_cli(self.bin_dir, "codex", "import sys\nsys.exit(0)\n")

        en = self.run_critic(
            "enable",
            "claude",
            "--domain",
            "agent-definition=codex:gpt-5",
            "--yes",
            "--skip-auth-check",
        )
        self.assertEqual(en.returncode, 0, en.stderr)

        for d in ("research", "plan", "code", "prose", "agent-definition"):
            probe = self.run_critic("review", "--domain", d, "--probe")
            self.assertEqual(probe.returncode, 0, f"probe failed for domain {d}: {probe.stderr}")
            if d == "agent-definition":
                self.assertEqual(probe.stdout.strip(), "codex gpt-5")
            else:
                self.assertEqual(probe.stdout.strip(), "claude default")

    def test_review_valid_structured_block(self) -> None:
        block = (
            "VERDICT: REVISE\n"
            "ROUND: 2\n\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n"
            "| C1 | BLOCKING | main.py:10 | null pointer | crash log | add null check |\n\n"
            "VALIDATION: ran unit tests\n"
            "NOTES: see log for details\n"
        )
        ok, msg = ext_critic.validate_block(block, round_no=2)
        self.assertTrue(ok, msg)
        self.assertEqual(msg, "ok")

    def test_review_zero_finding_pass(self) -> None:
        block = (
            "VERDICT: PASS\n"
            "ROUND: 1\n\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n\n"
            "VALIDATION: thoroughly checked all files\n"
            "NOTES: no issues found\n"
        )
        ok, msg = ext_critic.validate_block(block, round_no=1)
        self.assertTrue(ok, msg)

    def test_review_should_and_nit_finding_pass(self) -> None:
        block = (
            "VERDICT: PASS\n"
            "ROUND: 1\n\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n"
            "| S1 | SHOULD | helper.py:5 | improve docstring | missing args | add doc |\n"
            "| N1 | NIT | helper.py:12 | rename var | foo -> count | rename |\n\n"
            "VALIDATION: syntax and types checked\n"
            "NOTES: suggestions are non-blocking\n"
        )
        ok, msg = ext_critic.validate_block(block, round_no=1)
        self.assertTrue(ok, msg)

    def test_review_verdict_disagrees_with_rows(self) -> None:
        revise_zero = (
            "VERDICT: REVISE\n"
            "ROUND: 1\n\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n\n"
            "VALIDATION: checked\n"
            "NOTES: none\n"
        )
        ok, msg = ext_critic.validate_block(revise_zero, round_no=1)
        self.assertFalse(ok)
        self.assertEqual(msg, "verdict disagrees with rows (REVISE iff a BLOCKING row)")

        revise_non_blocking = (
            "VERDICT: REVISE\n"
            "ROUND: 1\n\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n"
            "| S1 | SHOULD | test.py:1 | comment | none | fix |\n\n"
            "VALIDATION: checked\n"
            "NOTES: none\n"
        )
        ok, msg = ext_critic.validate_block(revise_non_blocking, round_no=1)
        self.assertFalse(ok)
        self.assertEqual(msg, "verdict disagrees with rows (REVISE iff a BLOCKING row)")

        pass_blocking = (
            "VERDICT: PASS\n"
            "ROUND: 1\n\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n"
            "| C1 | BLOCKING | test.py:1 | fatal flaw | bug | patch |\n\n"
            "VALIDATION: checked\n"
            "NOTES: none\n"
        )
        ok, msg = ext_critic.validate_block(pass_blocking, round_no=1)
        self.assertFalse(ok)
        self.assertEqual(msg, "verdict disagrees with rows (REVISE iff a BLOCKING row)")

    def test_review_fenced_block_unwrapped(self) -> None:
        fenced_md = (
            "```markdown\n"
            "VERDICT: PASS\n"
            "ROUND: 1\n\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n\n"
            "VALIDATION: all checks passed\n"
            "NOTES: good job\n"
            "```\n"
        )
        ok, msg = ext_critic.validate_block(fenced_md, round_no=1)
        self.assertTrue(ok, msg)

        fenced_plain = (
            "```\n"
            "VERDICT: PASS\n"
            "ROUND: 1\n\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n\n"
            "VALIDATION: all checks passed\n"
            "NOTES: good job\n"
            "```\n"
        )
        ok, msg = ext_critic.validate_block(fenced_plain, round_no=1)
        self.assertTrue(ok, msg)

    def test_review_cli_fenced_block_unwrapped(self) -> None:
        write_fake_cli(
            self.bin_dir,
            "claude",
            """
import sys
if sys.argv[1:4] == ["auth", "status", "--json"]:
    print('{"loggedIn": true}')
    sys.exit(0)
print('''```markdown
VERDICT: PASS
ROUND: 1

| ID | Severity | Location | Finding | Evidence | Minimal fix |
|---|---|---|---|---|---|

VALIDATION: wrapped review
NOTES: unwrapped cleanly
```''')
""",
        )
        en = self.run_critic("enable", "claude", "--yes")
        self.assertEqual(en.returncode, 0, en.stderr)
        p_file = self.root / "prompt.md"
        p_file.write_text("inspect", encoding="utf-8")
        out_file = self.root / "out.md"
        res = self.run_critic("review", "--prompt-file", str(p_file), "--output", str(out_file))
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("VERDICT: PASS", res.stdout)
        self.assertFalse(res.stdout.startswith("```"))
        self.assertFalse(out_file.read_text(encoding="utf-8").startswith("```"))

    def test_review_prompt_includes_domain_skill(self) -> None:
        p_plan = ext_critic.build_review_prompt("plan", "check plan", None, round_no=1)
        self.assertIn("## Skill: pack/skills/plan-writing/SKILL.md", p_plan)
        self.assertIn("# Plan Writing", p_plan)
        self.assertNotIn("name: plan-writing", p_plan)

        p_agent = ext_critic.build_review_prompt(
            "agent-definition", "check agent", None, round_no=1
        )
        self.assertIn("## Skill: pack/skills/agent-authoring/SKILL.md", p_agent)
        self.assertTrue(
            "# Agent And Skill Authoring" in p_agent
            or "# Agent and Skill Authoring Conventions" in p_agent
        )
        self.assertNotIn("name: agent-authoring", p_agent)

        p_prose = ext_critic.build_review_prompt("prose", "check prose", None, round_no=1)
        self.assertIn("## Skill: pack/skills/science-writing-style/SKILL.md", p_prose)
        self.assertIn("## Skill: pack/skills/presentation-style/SKILL.md", p_prose)
        self.assertTrue(
            "# Science writing style" in p_prose
            or "# Scientific & Technical Writing Style" in p_prose
        )
        self.assertTrue(
            "# Presentation style" in p_prose
            or "# Presentation & Slide Design Style" in p_prose
        )
        writing_ref = REPO_ROOT / "pack" / "skills" / "project-memory" / "references" / "writing.md"
        if writing_ref.is_file():
            self.assertIn("## Skill: pack/skills/project-memory/references/writing.md", p_prose)
            self.assertIn("# Writing procedures", p_prose)

        p_code = ext_critic.build_review_prompt("code", "check code", None, round_no=1)
        self.assertNotIn("## Skill:", p_code)

    def test_malformed_block_rejections(self) -> None:
        base = (
            "VERDICT: PASS\n"
            "ROUND: 1\n\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n\n"
            "VALIDATION: checked\n"
            "NOTES: clean\n"
        )
        self.assertTrue(ext_critic.validate_block(base, 1)[0])

        # Invalid severity
        bad_sev = base.replace(
            "|---|---|---|---|---|---|",
            "|---|---|---|---|---|---|\n| C1 | LOW | f:1 | x | y | z |",
        )
        ok, msg = ext_critic.validate_block(bad_sev, 1)
        self.assertFalse(ok)
        self.assertIn("invalid severity", msg)

        # Missing round
        no_round = (
            "VERDICT: PASS\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n\n"
            "VALIDATION: checked\n"
            "NOTES: clean\n"
        )
        ok, msg = ext_critic.validate_block(no_round, 1)
        self.assertFalse(ok)

        # Wrong round
        ok, msg = ext_critic.validate_block(base, 2)
        self.assertFalse(ok)
        self.assertIn("round mismatch", msg)

        # Missing or invalid headers
        bad_header = (
            "VERDICT: PASS\n"
            "ROUND: 1\n\n"
            "| Bad | Headers | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n\n"
            "VALIDATION: checked\n"
            "NOTES: clean\n"
        )
        ok, msg = ext_critic.validate_block(bad_header, 1)
        self.assertFalse(ok)
        self.assertIn("missing findings table header", msg)

        no_table_at_all = (
            "VERDICT: PASS\n"
            "ROUND: 1\n\n"
            "VALIDATION: checked\n"
            "NOTES: clean\n"
        )
        ok, msg = ext_critic.validate_block(no_table_at_all, 1)
        self.assertFalse(ok)
        self.assertIn("missing findings table header", msg)

        # Missing validation
        no_val = (
            "VERDICT: PASS\n"
            "ROUND: 1\n\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n\n"
            "NOTES: clean\n"
        )
        ok, msg = ext_critic.validate_block(no_val, 1)
        self.assertFalse(ok)
        self.assertIn("VALIDATION", msg)

        # Missing notes
        no_notes = (
            "VERDICT: PASS\n"
            "ROUND: 1\n\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n\n"
            "VALIDATION: checked\n"
        )
        ok, msg = ext_critic.validate_block(no_notes, 1)
        self.assertFalse(ok)
        self.assertIn("NOTES", msg)

    def test_malformed_critic_output_and_timeout_fallback(self) -> None:
        write_fake_cli(
            self.bin_dir,
            "codex",
            """
import sys, time
if sys.argv[1:3] == ["login", "status"]:
    sys.exit(0)
if "sleep" in sys.stdin.read():
    time.sleep(2)
print("No headings at all.")
""",
        )
        en = self.run_critic("enable", "codex", "--yes")
        self.assertEqual(en.returncode, 0, en.stderr)

        prompt_file = self.root / "p.md"
        prompt_file.write_text("check", encoding="utf-8")
        bad = self.run_critic("review", "--prompt-file", str(prompt_file))
        self.assertEqual(bad.returncode, 3)
        self.assertIn("EXTERNAL_CRITIC_FALLBACK", bad.stderr)

        prompt_file.write_text("sleep", encoding="utf-8")
        timed = self.run_critic("review", "--prompt-file", str(prompt_file), "--timeout", "1")
        self.assertEqual(timed.returncode, 3)
        self.assertIn("timed out", timed.stderr)


if __name__ == "__main__":
    unittest.main()
