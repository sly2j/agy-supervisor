"""Tests for cross-family external-critic configuration, invocation, and fallback."""

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
print("## Verdict\\nAPPROVE — clean implementation.\\n\\n## Findings\\nNone.\\n\\n## Verification\\nChecked.")
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
print("## Verdict\\nREQUEST CHANGES — missing edge guard.\\n\\n## Findings\\n- file.py:1 add guard\\n\\n## Verification\\nInspected diff.")
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
        self.assertIn("REQUEST CHANGES", out_file.read_text(encoding="utf-8"))
        c_call = json.loads(codex_log.read_text(encoding="utf-8"))
        self.assertEqual(c_call["argv"], ["exec", "--sandbox", "read-only", "-m", "gpt-5"])
        self.assertIn("+x = 1", c_call["stdin"])

        rev_plan = self.run_critic("review", "--domain", "plan", "--prompt-file", str(prompt_file))
        self.assertEqual(rev_plan.returncode, 0, rev_plan.stderr)
        cl_call = json.loads(claude_log.read_text(encoding="utf-8"))
        self.assertEqual(
            cl_call["argv"],
            ["-p", "--output-format", "text", "--model", "claude-sonnet", "--effort", "high"],
        )

        dis = self.run_critic("disable")
        self.assertEqual(dis.returncode, 0)
        probe_after = self.run_critic("review", "--domain", "code", "--probe")
        self.assertEqual(probe_after.returncode, 2)

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
