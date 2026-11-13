"""Version consistency tests."""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class VersionTest(unittest.TestCase):
    def test_version_format_and_sync(self) -> None:
        version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^\d+\.\d+$")

        plugin = json.loads((REPO_ROOT / "pack" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["version"], version)

        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "deploy"), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), f"agy-supervisor {version}")

    def test_version_bumped_when_pack_or_deploy_changed(self) -> None:
        git_dir = REPO_ROOT / ".git"
        if not git_dir.exists():
            self.skipTest("git repository not initialized yet")
        head = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--verify", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if head.returncode != 0:
            self.skipTest("no HEAD commit yet")

        diff = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "HEAD", "--", "pack", "deploy"],
            capture_output=True,
            text=True,
            check=False,
        )
        if not diff.stdout.strip():
            return
        head_ver = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "show", "HEAD:VERSION"],
            capture_output=True,
            text=True,
            check=False,
        )
        cur_ver = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertNotEqual(
            cur_ver,
            head_ver.stdout.strip(),
            "pack/ or deploy changed relative to HEAD without bumping VERSION",
        )


if __name__ == "__main__":
    unittest.main()
