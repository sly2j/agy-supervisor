"""Changelog alignment tests."""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class ChangelogTest(unittest.TestCase):
    def test_changelog_has_current_version_heading(self) -> None:
        version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        pattern = rf"^##\s+{re.escape(version)}\s+-\s+\d{{4}}-\d{{2}}-\d{{2}}\b"
        self.assertRegex(changelog, re.compile(pattern, re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
