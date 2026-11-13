"""Tests for ./deploy memory externalize, link, and status commands."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY = REPO_ROOT / "deploy"


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


class DeployMemoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="agy-mem-test-")
        self.root = Path(self.tmp.name)
        self.cfg_dir = self.root / "gemini-config"
        self.cli_dir = self.root / "gemini-cli"
        self.prefix = self.root / "prefix"
        self.mem_root = self.root / "memory-store"
        self.repo = self.root / "sample-repo"
        self.repo.mkdir()
        self.env = os.environ.copy()
        self.env["AGY_CONFIG_DIR"] = str(self.cfg_dir)
        self.env["AGY_CLI_DIR"] = str(self.cli_dir)
        self.env["AGY_SUPERVISOR_PREFIX"] = str(self.prefix)
        self.env["AGY_SUPERVISOR_MEMORY_ROOT"] = str(self.mem_root)

        self.assertEqual(git(self.repo, "init", "-b", "main").returncode, 0)
        self.assertEqual(git(self.repo, "config", "user.name", "Tester").returncode, 0)
        self.assertEqual(git(self.repo, "config", "user.email", "tester@example.com").returncode, 0)
        (self.repo / "README.md").write_text("# Sample\n", encoding="utf-8")
        self.assertEqual(git(self.repo, "add", "README.md").returncode, 0)
        self.assertEqual(git(self.repo, "commit", "-m", "init").returncode, 0)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_deploy(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(DEPLOY), *args],
            capture_output=True,
            text=True,
            env=self.env,
            timeout=20,
            check=False,
        )

    def test_externalize_status_and_worktree_link(self) -> None:
        sup = self.repo / ".supervisor"
        sup.mkdir()
        (sup / "roadmap.md").write_text("# Roadmap\n- Next task\n", encoding="utf-8")
        (self.repo / "GEMINI.local.md").write_text("# Local notes\n", encoding="utf-8")

        ext = self.run_deploy(
            "memory",
            "externalize",
            "--project",
            str(self.repo),
            "--store-root",
            str(self.mem_root),
        )
        self.assertEqual(ext.returncode, 0, ext.stderr)

        ext_dir = self.mem_root / "sample-repo"
        self.assertTrue((self.repo / ".supervisor").is_symlink())
        self.assertTrue((self.repo / "GEMINI.local.md").is_symlink())
        self.assertTrue((ext_dir / ".supervisor" / "roadmap.md").is_file())
        self.assertTrue((ext_dir / "README.md").is_file())
        self.assertIn("<!-- agy-supervisor external memory -->", (ext_dir / "README.md").read_text())

        # git status must remain clean thanks to .git/info/exclude
        st_git = git(self.repo, "status", "--short")
        self.assertEqual(st_git.stdout.strip(), "")

        stat_cmd = self.run_deploy("memory", "status", "--project", str(self.repo))
        self.assertEqual(stat_cmd.returncode, 0, stat_cmd.stdout + stat_cmd.stderr)
        self.assertIn("ok:", stat_cmd.stdout)

        # Linked worktree can attach to the same external store.
        wt = self.root / "wt-feature"
        self.assertEqual(
            git(self.repo, "worktree", "add", str(wt), "-b", "feature/test").returncode, 0
        )
        link_cmd = self.run_deploy(
            "memory",
            "link",
            "--project",
            str(wt),
            "--store-root",
            str(self.mem_root),
        )
        self.assertEqual(link_cmd.returncode, 0, link_cmd.stderr)
        self.assertTrue((wt / ".supervisor").is_symlink())
        self.assertTrue((wt / "GEMINI.local.md").is_symlink())
        self.assertEqual(
            self.run_deploy("memory", "status", "--project", str(wt)).returncode, 0
        )

    def test_refuses_tracked_supervisor_or_nested_store(self) -> None:
        sup = self.repo / ".supervisor"
        sup.mkdir()
        (sup / "roadmap.md").write_text("# Tracked\n", encoding="utf-8")
        git(self.repo, "add", ".supervisor/roadmap.md")
        git(self.repo, "commit", "-m", "track sup")

        fail_tracked = self.run_deploy(
            "memory", "externalize", "--project", str(self.repo), "--store-root", str(self.mem_root)
        )
        self.assertEqual(fail_tracked.returncode, 1)
        self.assertIn("tracked by git", fail_tracked.stderr)

        # Untrack and test nested store rejection.
        git(self.repo, "rm", "-r", "--cached", ".supervisor")
        git(self.repo, "commit", "-m", "untrack sup")
        nested = self.repo / "nested-store"
        fail_nested = self.run_deploy(
            "memory", "externalize", "--project", str(self.repo), "--store-root", str(nested)
        )
        self.assertEqual(fail_nested.returncode, 1)
        self.assertIn("lies inside checkout", fail_nested.stderr)


if __name__ == "__main__":
    unittest.main()
