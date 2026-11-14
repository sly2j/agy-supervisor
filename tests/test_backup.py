"""Tests for project backup script with GFS retention."""

import datetime
import os
import re
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKUP_SCRIPT = (
    REPO_ROOT / "pack" / "skills" / "project-backup" / "scripts" / "backup.sh"
)


class BackupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            BACKUP_SCRIPT.is_file(), f"backup.sh not found at {BACKUP_SCRIPT}"
        )
        self.assertTrue(
            os.access(BACKUP_SCRIPT, os.X_OK),
            f"backup.sh is not executable: {BACKUP_SCRIPT}",
        )

    def _create_minimal_zip(self, path: Path, content: str = "ok") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("test.txt", content)

    def test_backup_creates_valid_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "sample_project"
            project_dir.mkdir()
            (project_dir / "README.md").write_text("# Sample\n", encoding="utf-8")
            (project_dir / "main.py").write_text("print('hello')\n", encoding="utf-8")
            backup_dir = Path(tmpdir) / "custom_backups"

            env = os.environ.copy()
            env["PROJECT_BACKUP_DIR"] = str(backup_dir)

            proc = subprocess.run(
                [str(BACKUP_SCRIPT), str(project_dir)],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(
                proc.returncode,
                0,
                f"backup.sh failed with stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
            )
            self.assertIn("=== BACKUP REPORT ===", proc.stdout)
            self.assertIn("Integrity: PASSED", proc.stdout)
            self.assertRegex(proc.stdout, r"Disk space:\s+\d+\s+MB available")
            self.assertIn("Retained: 1", proc.stdout)
            self.assertIn("Deleted: 0", proc.stdout)
            self.assertIn("Skipped: 0", proc.stdout)
            self.assertIn("Warnings: none", proc.stdout)
            self.assertIn("========================", proc.stdout)

            archives: List[Path] = list(backup_dir.glob("sample_project-*.zip"))
            self.assertEqual(len(archives), 1)
            archive = archives[0]

            with zipfile.ZipFile(archive, "r") as zf:
                self.assertIsNone(zf.testzip())
                namelist = zf.namelist()
                self.assertTrue(any("README.md" in name for name in namelist))
                self.assertTrue(any("main.py" in name for name in namelist))

    def test_backup_exclusions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "exclusion_project"
            project_dir.mkdir()

            # Files that should be preserved
            (project_dir / "README.md").write_text("# Project\n", encoding="utf-8")
            sub_src = project_dir / "src"
            sub_src.mkdir()
            (sub_src / "app.py").write_text("code\n", encoding="utf-8")
            sup_dir = project_dir / ".supervisor"
            sup_dir.mkdir()
            (sup_dir / "keep.txt").write_text("keep\n", encoding="utf-8")

            # Files and directories that should be excluded
            git_obj = project_dir / ".git" / "objects"
            git_obj.mkdir(parents=True)
            (git_obj / "git_obj").write_text("git\n", encoding="utf-8")

            wt1 = project_dir / ".agents" / "worktrees" / "wt1"
            wt1.mkdir(parents=True)
            (wt1 / "wt.txt").write_text("wt\n", encoding="utf-8")

            wt2 = project_dir / ".claude" / "worktrees" / "wt2"
            wt2.mkdir(parents=True)
            (wt2 / "wt.txt").write_text("wt\n", encoding="utf-8")

            residue = project_dir / ".supervisor" / "working" / "residue"
            residue.mkdir(parents=True)
            (residue / "scratch.tmp").write_text("residue\n", encoding="utf-8")

            venv = project_dir / ".venv" / "bin"
            venv.mkdir(parents=True)
            (venv / "activate").write_text("bin\n", encoding="utf-8")

            pyc1 = project_dir / "__pycache__"
            pyc1.mkdir(parents=True)
            (pyc1 / "mod.pyc").write_text("pyc\n", encoding="utf-8")

            pyc2 = sub_src / "__pycache__"
            pyc2.mkdir(parents=True)
            (pyc2 / "sub.pyc").write_text("pyc\n", encoding="utf-8")

            (project_dir / ".DS_Store").write_bytes(b"\x00")
            (sub_src / ".DS_Store").write_bytes(b"\x00")

            backup_dir = Path(tmpdir) / "backups"
            env = os.environ.copy()
            env["PROJECT_BACKUP_DIR"] = str(backup_dir)

            proc = subprocess.run(
                [str(BACKUP_SCRIPT), str(project_dir)],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

            archives = list(backup_dir.glob("exclusion_project-*.zip"))
            self.assertEqual(len(archives), 1)

            with zipfile.ZipFile(archives[0], "r") as zf:
                self.assertIsNone(zf.testzip())
                namelist = zf.namelist()

                # Retained files must be in zip
                self.assertTrue(any("README.md" in n for n in namelist))
                self.assertTrue(any("app.py" in n for n in namelist))
                self.assertTrue(any("keep.txt" in n for n in namelist))

                # Excluded files must NOT be in zip
                for name in namelist:
                    self.assertNotIn(".git/", name)
                    self.assertNotIn(".agents/worktrees/", name)
                    self.assertNotIn(".claude/worktrees/", name)
                    self.assertNotIn(".supervisor/working/residue/", name)
                    self.assertNotIn(".venv/", name)
                    self.assertNotIn("__pycache__/", name)
                    self.assertFalse(name.endswith(".DS_Store"))

    def test_backup_disk_space_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "disk_project"
            project_dir.mkdir()
            (project_dir / "file.txt").write_text("content\n", encoding="utf-8")
            backup_dir = Path(tmpdir) / "backups"

            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir()
            fake_df = bin_dir / "df"
            # 500000 KB is ~488 MB (< 1048576 KB / 1 GB)
            fake_df.write_text(
                "#!/bin/sh\n"
                "printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\\n"
                "/dev/mock 10000000 9500000 500000 95%% /\\n'",
                encoding="utf-8",
            )
            fake_df.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            env["PROJECT_BACKUP_DIR"] = str(backup_dir)

            proc = subprocess.run(
                [str(BACKUP_SCRIPT), str(project_dir)],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("=== BACKUP REPORT ===", proc.stdout)
            self.assertIn("Warnings: Low disk space: 488 MB available", proc.stdout)
            self.assertIn("Disk space: 488 MB available", proc.stdout)

    def test_backup_gfs_retention_pruning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_name = "gfsproj"
            project_dir = Path(tmpdir) / project_name
            project_dir.mkdir()
            (project_dir / "data.txt").write_text("data\n", encoding="utf-8")

            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            now = datetime.datetime.now()

            # 1. Recent tier: Create 8 archives for today (earlier hours)
            # The 7 newest will be in Recent (including the new one created by backup.sh)
            for h in range(8):
                stamp = (now - datetime.timedelta(hours=12 - h)).strftime(
                    "%y%m%d-%H%M%S"
                )
                self._create_minimal_zip(
                    backup_dir / f"{project_name}-{stamp}.zip", f"recent-{h}"
                )

            # 2. Weekly tier: 4 completed ISO calendar weeks
            mon = now.date() - datetime.timedelta(days=now.date().weekday())

            # Week -1: 2 archives (older will be deleted, newer retained)
            w1_d1 = (mon - datetime.timedelta(days=5)).strftime("%y%m%d")
            w1_d2 = (mon - datetime.timedelta(days=3)).strftime("%y%m%d")
            del_weekly = backup_dir / f"{project_name}-{w1_d1}-100000.zip"
            keep_weekly = backup_dir / f"{project_name}-{w1_d2}-120000.zip"
            self._create_minimal_zip(del_weekly, "weekly-del")
            self._create_minimal_zip(keep_weekly, "weekly-keep")

            # Weeks -2, -3, -4: 1 archive each (retained)
            w2 = (mon - datetime.timedelta(days=10)).strftime("%y%m%d")
            w3 = (mon - datetime.timedelta(days=17)).strftime("%y%m%d")
            w4 = (mon - datetime.timedelta(days=24)).strftime("%y%m%d")
            self._create_minimal_zip(backup_dir / f"{project_name}-{w2}-100000.zip")
            self._create_minimal_zip(backup_dir / f"{project_name}-{w3}-100000.zip")
            self._create_minimal_zip(backup_dir / f"{project_name}-{w4}-100000.zip")

            # 3. Monthly tier: 2 archives in an earlier month of the current year (April)
            cur_year_short = now.strftime("%y")
            del_monthly = backup_dir / f"{project_name}-{cur_year_short}0401-100000.zip"
            keep_monthly = (
                backup_dir / f"{project_name}-{cur_year_short}0415-120000.zip"
            )
            self._create_minimal_zip(del_monthly, "monthly-del")
            self._create_minimal_zip(keep_monthly, "monthly-keep")

            # 4. Bi-yearly tier: prior calendar year (2 years ago)
            prior_year_short = f"{now.year - 2}"[-2:]
            # H1 (months 1-6): 2 archives (Feb deleted, March kept)
            del_biyearly = (
                backup_dir / f"{project_name}-{prior_year_short}0210-100000.zip"
            )
            keep_biyearly = (
                backup_dir / f"{project_name}-{prior_year_short}0315-120000.zip"
            )
            self._create_minimal_zip(del_biyearly, "biyearly-del")
            self._create_minimal_zip(keep_biyearly, "biyearly-keep")

            # H2 (months 7-12): 1 archive (kept)
            h2_biyearly = (
                backup_dir / f"{project_name}-{prior_year_short}0820-100000.zip"
            )
            self._create_minimal_zip(h2_biyearly, "biyearly-h2")

            # 5. Unmanaged files: should NOT be deleted
            unmanaged1 = backup_dir / f"{project_name}-unparseable.zip"
            self._create_minimal_zip(unmanaged1, "unmanaged1")
            unmanaged2 = backup_dir / "unmanaged.zip"
            unmanaged2.write_text("not-a-managed-backup\n", encoding="utf-8")

            env = os.environ.copy()
            env["PROJECT_BACKUP_DIR"] = str(backup_dir)

            proc = subprocess.run(
                [str(BACKUP_SCRIPT), str(project_dir)],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

            # Check report output
            self.assertIn("=== BACKUP REPORT ===", proc.stdout)
            self.assertIn("Integrity: PASSED", proc.stdout)

            # Unmanaged files must survive
            self.assertTrue(unmanaged1.exists(), "unparseable zip was deleted")
            self.assertTrue(unmanaged2.exists(), "unmanaged.zip was deleted")

            # Expected deletions in tiers
            self.assertFalse(del_weekly.exists(), "older weekly archive was not deleted")
            self.assertTrue(keep_weekly.exists(), "newer weekly archive was deleted")

            self.assertFalse(del_biyearly.exists(), "older H1 archive was not deleted")
            self.assertTrue(keep_biyearly.exists(), "newer H1 archive was deleted")
            self.assertTrue(h2_biyearly.exists(), "H2 archive was deleted")

            # If current month is after April, monthly pruning check applies
            if now.month > 4:
                self.assertFalse(
                    del_monthly.exists(), "older monthly archive was not deleted"
                )
                self.assertTrue(
                    keep_monthly.exists(), "newer monthly archive was deleted"
                )

            # Verify safety floor (>= 3 retained)
            m = re.search(r"Retained:\s+(\d+)", proc.stdout)
            self.assertIsNotNone(m)
            retained_count = int(m.group(1))
            self.assertGreaterEqual(retained_count, 3)

            # Verify deletions happened
            m_del = re.search(r"Deleted:\s+(\d+)", proc.stdout)
            self.assertIsNotNone(m_del)
            deleted_count = int(m_del.group(1))
            self.assertGreaterEqual(deleted_count, 2)

            # Verify skipped count reported unparseable zip
            m_skip = re.search(r"Skipped:\s+(\d+)", proc.stdout)
            self.assertIsNotNone(m_skip)
            skipped_count = int(m_skip.group(1))
            self.assertGreaterEqual(skipped_count, 1)

    def test_backup_refuses_nested_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "nested_project"
            project_dir.mkdir()
            (project_dir / "data.txt").write_text("data\n", encoding="utf-8")

            # 1. Directly in project root
            env = os.environ.copy()
            env["PROJECT_BACKUP_DIR"] = str(project_dir)

            proc = subprocess.run(
                [str(BACKUP_SCRIPT), str(project_dir)],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)
            output = proc.stdout + proc.stderr
            self.assertIn("FATAL", output)
            self.assertIn("is inside project", output)

            # 2. In a subdirectory inside the project
            nested_backup = project_dir / "nested" / "backups"
            env["PROJECT_BACKUP_DIR"] = str(nested_backup)

            proc = subprocess.run(
                [str(BACKUP_SCRIPT), str(project_dir)],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)
            output = proc.stdout + proc.stderr
            self.assertIn("FATAL", output)
            self.assertIn("is inside project", output)


if __name__ == "__main__":
    unittest.main()
