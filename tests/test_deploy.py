"""Integration tests for ./deploy install, update, tag, launcher, doctor, and uninstall."""

import json
import os
import shutil
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
        self.assertIn('["--agent", "supervisor", "--model", "gemini-4-carbon-medium", "-p", "hello"]', l_run.stdout)

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

    def test_backup_created_on_force_overwrite(self) -> None:
        target = self.cfg_dir / "plugins" / "agy-supervisor"
        target.mkdir(parents=True)
        conflicting = target / "agents" / "supervisor.md"
        conflicting.parent.mkdir(parents=True)
        conflicting.write_text("# UNMANAGED CONFLICT CONTENT\n", encoding="utf-8")

        # Install with --overwrite-local
        res = self.run_deploy("install", "--overwrite-local", "--skip-agy-validate")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Backed up", res.stdout)

        # Check that a .bak.<timestamp> file was created
        baks = list(conflicting.parent.glob("supervisor.md.bak.*"))
        self.assertEqual(len(baks), 1)
        self.assertEqual(baks[0].read_text(encoding="utf-8"), "# UNMANAGED CONFLICT CONTENT\n")
        self.assertNotEqual(conflicting.read_text(encoding="utf-8"), "# UNMANAGED CONFLICT CONTENT\n")

        # Locally modified managed file backup on update with --force
        scout_md = target / "agents" / "scout.md"
        scout_md.write_text("# LOCALLY MODIFIED SCOUT\n", encoding="utf-8")
        upd = self.run_deploy("update", "--force", "--skip-agy-validate")
        self.assertEqual(upd.returncode, 0, upd.stderr)
        self.assertIn("Backed up", upd.stdout)

        scout_baks = list(scout_md.parent.glob("scout.md.bak.*"))
        self.assertEqual(len(scout_baks), 1)
        self.assertEqual(scout_baks[0].read_text(encoding="utf-8"), "# LOCALLY MODIFIED SCOUT\n")
        self.assertNotEqual(scout_md.read_text(encoding="utf-8"), "# LOCALLY MODIFIED SCOUT\n")

    def test_default_model_in_launcher_and_env_override(self) -> None:
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
        inst = self.run_deploy("install", "--default-model", "test-model-xyz", "--skip-agy-validate", env=env)
        self.assertEqual(inst.returncode, 0, inst.stderr)

        launcher = self.prefix / "bin" / "agy-supervisor"
        launcher_text = launcher.read_text(encoding="utf-8")
        self.assertIn('MODEL="${AGY_SUPERVISOR_MODEL:-test-model-xyz}"', launcher_text)

        # 1. Default invocation passes --model test-model-xyz
        r1 = subprocess.run([str(launcher), "-p", "run1"], capture_output=True, text=True, env=env, check=False)
        self.assertEqual(r1.returncode, 0)
        self.assertIn('["--agent", "supervisor", "--model", "test-model-xyz", "-p", "run1"]', r1.stdout)

        # 2. AGY_SUPERVISOR_MODEL environment override
        env_override = dict(env, AGY_SUPERVISOR_MODEL="env-model-abc")
        r2 = subprocess.run([str(launcher), "-p", "run2"], capture_output=True, text=True, env=env_override, check=False)
        self.assertEqual(r2.returncode, 0)
        self.assertIn('["--agent", "supervisor", "--model", "env-model-abc", "-p", "run2"]', r2.stdout)

        # 3. Explicit -m flag omits launcher default model
        r3 = subprocess.run([str(launcher), "-m", "flag-model", "-p", "run3"], capture_output=True, text=True, env=env, check=False)
        self.assertEqual(r3.returncode, 0)
        self.assertIn('["--agent", "supervisor", "-m", "flag-model", "-p", "run3"]', r3.stdout)

        # 4. Explicit --model flag omits launcher default model
        r4 = subprocess.run([str(launcher), "--model", "flag-model-2", "-p", "run4"], capture_output=True, text=True, env=env, check=False)
        self.assertEqual(r4.returncode, 0)
        self.assertIn('["--agent", "supervisor", "--model", "flag-model-2", "-p", "run4"]', r4.stdout)

        # 5. Explicit --model=flag-model-3 flag omits launcher default model
        r5 = subprocess.run([str(launcher), "--model=flag-model-3", "-p", "run5"], capture_output=True, text=True, env=env, check=False)
        self.assertEqual(r5.returncode, 0)
        self.assertIn('["--agent", "supervisor", "--model=flag-model-3", "-p", "run5"]', r5.stdout)

    def test_update_preserves_default_model(self) -> None:
        inst = self.run_deploy("install", "--default-model", "initial-model", "--skip-agy-validate")
        self.assertEqual(inst.returncode, 0, inst.stderr)

        target = self.cfg_dir / "plugins" / "agy-supervisor"
        manifest = json.loads((target / ".agy-supervisor-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["default_model"], "initial-model")

        # Update without specifying --default-model preserves initial-model
        upd = self.run_deploy("update", "--skip-agy-validate")
        self.assertEqual(upd.returncode, 0, upd.stderr)
        manifest2 = json.loads((target / ".agy-supervisor-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest2["default_model"], "initial-model")

        launcher = self.prefix / "bin" / "agy-supervisor"
        self.assertIn('MODEL="${AGY_SUPERVISOR_MODEL:-initial-model}"', launcher.read_text(encoding="utf-8"))

        # Explicitly updating --default-model updates it
        upd2 = self.run_deploy("update", "--default-model", "updated-model", "--skip-agy-validate")
        self.assertEqual(upd2.returncode, 0, upd2.stderr)
        manifest3 = json.loads((target / ".agy-supervisor-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest3["default_model"], "updated-model")
        self.assertIn('MODEL="${AGY_SUPERVISOR_MODEL:-updated-model}"', launcher.read_text(encoding="utf-8"))

    def test_update_all(self) -> None:
        # Install global install and workspace install
        inst1 = self.run_deploy("install", "--tag", "prod", "--skip-agy-validate")
        self.assertEqual(inst1.returncode, 0, inst1.stderr)

        inst2 = self.run_deploy("install", "--tag", "ws", "--workspace", str(self.workspace), "--skip-agy-validate")
        self.assertEqual(inst2.returncode, 0, inst2.stderr)

        # Combining --all with --tag or --workspace fails
        res_fail1 = self.run_deploy("update", "--all", "--tag", "prod", "--skip-agy-validate")
        self.assertEqual(res_fail1.returncode, 1)
        self.assertIn("cannot combine --all", res_fail1.stderr)

        res_fail2 = self.run_deploy("update", "--all", "--workspace", str(self.workspace), "--skip-agy-validate")
        self.assertEqual(res_fail2.returncode, 1)
        self.assertIn("cannot combine --all", res_fail2.stderr)

        # Run update --all
        res_all = self.run_deploy("update", "--all", "--skip-agy-validate")
        self.assertEqual(res_all.returncode, 0, res_all.stderr)
        self.assertIn("Updated agy-prod", res_all.stdout)
        self.assertIn("Updated agy-ws", res_all.stdout)

    def test_update_from_dir(self) -> None:
        inst = self.run_deploy("install", "--skip-agy-validate")
        self.assertEqual(inst.returncode, 0, inst.stderr)

        # Create a mock source directory with VERSION 9.9 and an updated file
        source_dir = self.root / "mock-source"
        source_pack = source_dir / "pack"
        shutil.copytree(str(REPO_ROOT / "pack"), str(source_pack))
        (source_dir / "VERSION").write_text("9.9\n", encoding="utf-8")
        custom_file = source_pack / "custom_marker.txt"
        custom_file.write_text("CUSTOM_SOURCE_PAYLOAD\n", encoding="utf-8")

        upd = self.run_deploy("update", "--from", str(source_dir), "--skip-agy-validate")
        self.assertEqual(upd.returncode, 0, upd.stderr)

        target = self.cfg_dir / "plugins" / "agy-supervisor"
        manifest = json.loads((target / ".agy-supervisor-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "9.9")
        self.assertTrue((target / "custom_marker.txt").is_file())
        self.assertEqual((target / "custom_marker.txt").read_text(encoding="utf-8"), "CUSTOM_SOURCE_PAYLOAD\n")

    def test_conflict_refusal_without_force(self) -> None:
        target = self.cfg_dir / "plugins" / "agy-supervisor"
        target.mkdir(parents=True)
        conflicting = target / "agents" / "supervisor.md"
        conflicting.parent.mkdir(parents=True)
        conflicting.write_text("# UNMANAGED CONFLICT\n", encoding="utf-8")

        # Install without force should fail
        res_inst = self.run_deploy("install", "--skip-agy-validate")
        self.assertEqual(res_inst.returncode, 1)
        self.assertIn("unmanaged file conflict", res_inst.stderr)
        self.assertIn("--force", res_inst.stderr)

        # Install with force succeeds
        res_inst_force = self.run_deploy("install", "--force", "--skip-agy-validate")
        self.assertEqual(res_inst_force.returncode, 0, res_inst_force.stderr)

        # Modify managed file locally
        conflicting.write_text("# MODIFIED MANAGED\n", encoding="utf-8")

        # Re-running install without force fails
        res_inst_mod = self.run_deploy("install", "--skip-agy-validate")
        self.assertEqual(res_inst_mod.returncode, 1)
        self.assertIn("locally modified managed file", res_inst_mod.stderr)

        # Running update without force preserves it
        res_upd = self.run_deploy("update", "--skip-agy-validate")
        self.assertEqual(res_upd.returncode, 0, res_upd.stderr)
        self.assertIn("Preserving 1 locally modified file", res_upd.stdout)
        self.assertEqual(conflicting.read_text(encoding="utf-8"), "# MODIFIED MANAGED\n")


if __name__ == "__main__":
    unittest.main()
