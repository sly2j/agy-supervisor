"""Integration tests for ./deploy install, update, tag, launcher, doctor, and uninstall."""

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY = REPO_ROOT / "deploy"


def make_stub_bin(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    os.chmod(str(path), stat.S_IRWXU)
    return path


class DeployTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="agy-deploy-test-")
        self.root = Path(self.tmp.name)
        self.cfg_dir = self.root / "gemini-config"
        self.cli_dir = self.root / "gemini-cli"
        self.prefix = self.root / "prefix"
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.env = os.environ.copy()
        self.env["AGY_CONFIG_DIR"] = str(self.cfg_dir)
        self.env["AGY_CLI_DIR"] = str(self.cli_dir)
        self.env["AGY_SUPERVISOR_PREFIX"] = str(self.prefix)
        self.env.pop("AGY_BIN", None)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_deploy(self, *args: str, env=None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(DEPLOY), *args],
            capture_output=True,
            text=True,
            env=env or self.env,
            timeout=30,
            check=False,
        )

    def test_dry_run_creates_nothing(self) -> None:
        res = self.run_deploy("install", "--dry-run", "--skip-agy-validate")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("[dry-run] Installed agy-supervisor", res.stdout)
        self.assertFalse(self.cfg_dir.exists())
        self.assertFalse(self.cli_dir.exists())
        self.assertFalse(self.prefix.exists())

    def test_global_install_launcher_status_doctor_and_uninstall(self) -> None:
        fake_agy = make_stub_bin(
            self.root / "bin" / "fake-agy",
            """
import json, sys
if sys.argv[1:3] == ["plugin", "validate"]:
    print(json.dumps({"findings": []}))
    sys.exit(0)
if sys.argv[1:] == ["--version"]:
    print("1.4.9")
    sys.exit(0)
print("ARGS:" + json.dumps(sys.argv[1:]))
""",
        )
        env = dict(self.env, AGY_BIN=str(fake_agy))

        # Pre-seed unrelated user keys in config.json and settings.json to verify preservation.
        self.cfg_dir.mkdir(parents=True)
        (self.cfg_dir / "config.json").write_text(
            json.dumps({"plugins": {"science": {"enabled": True}}, "custom": 42}),
            encoding="utf-8",
        )
        self.cli_dir.mkdir(parents=True)
        (self.cli_dir / "settings.json").write_text(
            json.dumps({"agentMode": "accept-edits", "trustedWorkspaces": ["/tmp/work"]}),
            encoding="utf-8",
        )

        inst = self.run_deploy("install", env=env)
        self.assertEqual(inst.returncode, 0, inst.stderr)

        target = self.cfg_dir / "plugins" / "agy-supervisor"
        self.assertTrue((target / ".agy-supervisor-manifest.json").is_file())
        self.assertTrue((target / "plugin.json").is_file())
        self.assertTrue((target / "agents" / "supervisor.md").is_file())

        cfg = json.loads((self.cfg_dir / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["custom"], 42)
        self.assertTrue(cfg["plugins"]["science"]["enabled"])
        self.assertTrue(cfg["plugins"]["agy-supervisor"]["enabled"])

        settings = json.loads((self.cli_dir / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["agentMode"], "accept-edits")
        allow = settings["permissions"]["allow"]
        self.assertEqual(len(allow), 1)
        self.assertIn("external-critic review *)", allow[0])
        self.assertNotIn("enable", allow[0])

        launcher = self.prefix / "bin" / "agy-supervisor"
        self.assertTrue(launcher.is_file())

        # Launcher forwards management subcommands and -v, and passes chat args to agy --agent supervisor.
        l_ver = subprocess.run([str(launcher), "-v"], capture_output=True, text=True, env=env, check=False)
        self.assertEqual(l_ver.returncode, 0, l_ver.stderr)
        self.assertTrue(l_ver.stdout.strip().startswith("agy-supervisor "))

        l_stat = subprocess.run(
            [str(launcher), "status", "--json"], capture_output=True, text=True, env=env, check=False
        )
        self.assertEqual(l_stat.returncode, 0, l_stat.stderr)
        st_data = json.loads(l_stat.stdout)
        self.assertTrue(st_data["installed"])
        self.assertTrue(st_data["launcher_ok"])
        self.assertTrue(st_data["critic_rule_present"])

        l_run = subprocess.run(
            [str(launcher), "-p", "hello"], capture_output=True, text=True, env=env, check=False
        )
        self.assertEqual(l_run.returncode, 0, l_run.stderr)
        self.assertIn('["--agent", "supervisor", "-p", "hello"]', l_run.stdout)

        doc = self.run_deploy("doctor", "--json", env=env)
        self.assertEqual(doc.returncode, 0, doc.stdout + doc.stderr)
        self.assertTrue(json.loads(doc.stdout)["ok"])

        lst = self.run_deploy("list", "--json", env=env)
        self.assertEqual(lst.returncode, 0)
        self.assertEqual(len(json.loads(lst.stdout)["installs"]), 1)

        # Modify a managed file locally; update preserves it without --force, uninstall blocks without --force.
        scout_md = target / "agents" / "scout.md"
        scout_md.write_text(scout_md.read_text(encoding="utf-8") + "\n# local edit\n", encoding="utf-8")
        sup_cfg = target / "supervisor-config.json"
        sup_cfg.write_text('{"enabled": false}\n', encoding="utf-8")

        upd = self.run_deploy("update", env=env)
        self.assertEqual(upd.returncode, 0, upd.stderr)
        self.assertIn("Preserving 1 locally modified file", upd.stdout)
        self.assertIn("# local edit", scout_md.read_text(encoding="utf-8"))
        self.assertTrue(sup_cfg.is_file())

        un_block = self.run_deploy("uninstall", "--yes", env=env)
        self.assertEqual(un_block.returncode, 1)
        self.assertIn("locally modified", un_block.stderr)

        un_force = self.run_deploy("uninstall", "--yes", "--force", env=env)
        self.assertEqual(un_force.returncode, 0, un_force.stderr)
        self.assertFalse(target.exists())
        self.assertFalse(launcher.exists())
        cfg_after = json.loads((self.cfg_dir / "config.json").read_text(encoding="utf-8"))
        self.assertNotIn("agy-supervisor", cfg_after.get("plugins", {}))
        settings_after = json.loads((self.cli_dir / "settings.json").read_text(encoding="utf-8"))
        self.assertNotIn("permissions", settings_after)

    def test_tagged_workspace_and_sibling_suppression(self) -> None:
        inst1 = self.run_deploy("install", "--skip-agy-validate")
        self.assertEqual(inst1.returncode, 0, inst1.stderr)

        inst_dev = self.run_deploy(
            "install", "--tag", "dev", "--disable-siblings", "--skip-agy-validate"
        )
        self.assertEqual(inst_dev.returncode, 0, inst_dev.stderr)
        dev_target = self.cfg_dir / "plugins" / "agy-dev"
        dev_meta = json.loads((dev_target / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(dev_meta["name"], "agy-dev")

        cfg = json.loads((self.cfg_dir / "config.json").read_text(encoding="utf-8"))
        self.assertFalse(cfg["plugins"]["agy-supervisor"]["enabled"])
        self.assertTrue(cfg["plugins"]["agy-dev"]["enabled"])

        ws = self.run_deploy(
            "install", "--workspace", str(self.workspace), "--skip-agy-validate"
        )
        self.assertEqual(ws.returncode, 0, ws.stderr)
        ws_target = self.workspace / ".agents" / "plugins" / "agy-supervisor"
        self.assertTrue((ws_target / ".agy-supervisor-manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
