"""Tests for ./deploy memory externalize, link, and status commands."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY = REPO_ROOT / "deploy"

deploy_module = SourceFileLoader("deploy", str(DEPLOY)).load_module()
plan_memory_grant = deploy_module.plan_memory_grant
memory_grant = deploy_module.memory_grant


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

    def test_plan_memory_grant(self) -> None:
        root_path = Path("/mock/shared/memory/project-a")
        dir_g, rule_g = memory_grant(root_path)
        self.assertEqual(dir_g, "/mock/shared/memory/project-a")
        self.assertEqual(rule_g, "Edit(/mock/shared/memory/project-a/**)")

        initial_settings = {
            "trustedWorkspaces": ["/path/to/ws"],
            "permissions": {
                "allow": ["Bash(ls)"],
            },
        }

        new_settings, added = plan_memory_grant(initial_settings, root_path)
        self.assertIsNotNone(new_settings)
        self.assertEqual(new_settings["trustedWorkspaces"], ["/path/to/ws"])
        perms = new_settings["permissions"]
        self.assertIn("/mock/shared/memory/project-a", perms["additionalDirectories"])
        self.assertIn("Edit(/mock/shared/memory/project-a/**)", perms["allow"])
        self.assertIn("Bash(ls)", perms["allow"])
        self.assertEqual(added["additionalDirectories"], ["/mock/shared/memory/project-a"])
        self.assertEqual(added["allow"], ["Edit(/mock/shared/memory/project-a/**)"])

        # Second run with same settings returns None and empty added lists
        noop_settings, noop_added = plan_memory_grant(new_settings, root_path)
        self.assertIsNone(noop_settings)
        self.assertEqual(noop_added["additionalDirectories"], [])
        self.assertEqual(noop_added["allow"], [])

    def test_externalize_wires_settings_grant(self) -> None:
        self.cli_dir.mkdir(parents=True, exist_ok=True)
        (self.cli_dir / "settings.json").write_text(
            json.dumps({"trustedWorkspaces": [str(self.repo)]}), encoding="utf-8"
        )

        ext = self.run_deploy(
            "memory",
            "externalize",
            "--project",
            str(self.repo),
            "--store-root",
            str(self.mem_root),
        )
        self.assertEqual(ext.returncode, 0, ext.stderr)

        settings_path = self.cli_dir / "settings.json"
        self.assertTrue(settings_path.is_file())
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertEqual(settings["trustedWorkspaces"], [str(self.repo)])

        ext_dir = (self.mem_root / "sample-repo").resolve()
        expected_dir = str(ext_dir)
        expected_rule = f"Edit(/{expected_dir.lstrip('/')}/**)"

        perms = settings.get("permissions", {})
        self.assertIn(expected_dir, perms.get("additionalDirectories", []))
        self.assertIn(expected_rule, perms.get("allow", []))

    def test_dry_run_creates_no_grants(self) -> None:
        # With non-existent settings.json
        res1 = self.run_deploy(
            "memory",
            "externalize",
            "--dry-run",
            "--project",
            str(self.repo),
            "--store-root",
            str(self.mem_root),
        )
        self.assertEqual(res1.returncode, 0, res1.stderr)
        self.assertFalse((self.cli_dir / "settings.json").exists())

        # With pre-existing settings.json
        self.cli_dir.mkdir(parents=True, exist_ok=True)
        initial_content = json.dumps({"trustedWorkspaces": ["/tmp/safe"]}) + "\n"
        (self.cli_dir / "settings.json").write_text(initial_content, encoding="utf-8")

        res2 = self.run_deploy(
            "memory",
            "externalize",
            "--dry-run",
            "--project",
            str(self.repo),
            "--store-root",
            str(self.mem_root),
        )
        self.assertEqual(res2.returncode, 0, res2.stderr)
        self.assertEqual((self.cli_dir / "settings.json").read_text(encoding="utf-8"), initial_content)

    def test_dangling_symlink_detection_and_repair(self) -> None:
        # First externalize successfully
        ext = self.run_deploy(
            "memory",
            "externalize",
            "--project",
            str(self.repo),
            "--store-root",
            str(self.mem_root),
        )
        self.assertEqual(ext.returncode, 0, ext.stderr)

        # Break the .supervisor symlink so it dangles
        sup_link = self.repo / ".supervisor"
        sup_link.unlink()
        broken_target = self.root / "nonexistent-memory-target"
        os.symlink(str(broken_target), str(sup_link))

        # Status check must detect the dangling symlink
        stat_fail = self.run_deploy("memory", "status", "--project", str(self.repo))
        self.assertEqual(stat_fail.returncode, 1)
        self.assertIn("dangling symlink", stat_fail.stdout)

        # Repair with memory link --repair
        link_repair = self.run_deploy(
            "memory",
            "link",
            "--project",
            str(self.repo),
            "--store-root",
            str(self.mem_root),
            "--repair",
        )
        self.assertEqual(link_repair.returncode, 0, link_repair.stderr)

        # Status check now reports ok
        stat_ok = self.run_deploy("memory", "status", "--project", str(self.repo))
        self.assertEqual(stat_ok.returncode, 0, stat_ok.stdout + stat_ok.stderr)
        self.assertIn("ok:", stat_ok.stdout)


if __name__ == "__main__":
    unittest.main()
