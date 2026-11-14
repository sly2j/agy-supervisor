"""Tests verifying Wave 3 Project Memory & Lifecycle Skills invariants."""

import re
import unittest
from pathlib import Path
from typing import Any, Dict, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = REPO_ROOT / "pack"
MEM_DIR = PACK_DIR / "skills" / "project-memory"
PICKUP_DIR = PACK_DIR / "skills" / "pick-up"
CLOSEOUT_DIR = PACK_DIR / "skills" / "close-out"


def parse_frontmatter(path: Path) -> Tuple[Dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise AssertionError(f"{path} missing YAML frontmatter start")
    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        raise AssertionError(f"{path} missing YAML frontmatter end")
    header = text[4:end_idx]
    body = text[end_idx + 5 :]

    meta: Dict[str, Any] = {}
    cur_list_key = None
    for raw_line in header.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("  - ") or raw_line.startswith("- "):
            if cur_list_key is None:
                raise AssertionError(f"{path}: unexpected list item {raw_line!r}")
            item = raw_line.split("-", 1)[1].strip()
            meta[cur_list_key].append(item)
            continue
        cur_list_key = None
        if ":" not in raw_line:
            raise AssertionError(f"{path}: invalid frontmatter line {raw_line!r}")
        key, val = raw_line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if not val or val == "[]":
            meta[key] = []
            if not val:
                cur_list_key = key
        elif val == "true":
            meta[key] = True
        elif val == "false":
            meta[key] = False
        else:
            meta[key] = val.strip("'\"")
    return meta, body


def count_words(text: str) -> int:
    return len(re.findall(r"\S+", text))


class ProjectMemoryTest(unittest.TestCase):
    def test_task_template(self) -> None:
        path = MEM_DIR / "templates" / "task.md"
        self.assertTrue(path.is_file())
        meta, body = parse_frontmatter(path)
        expected_keys = {"summary", "status", "owner", "since", "plan", "depends", "decisions"}
        self.assertEqual(set(meta.keys()), expected_keys)
        self.assertEqual(meta["status"], "open")
        self.assertEqual(meta["depends"], [])
        self.assertEqual(meta["decisions"], [])
        for section in ("Goal:", "Scope:", "Done when:", "Notes:"):
            self.assertIn(section, body)

    def test_tasks_reference(self) -> None:
        path = MEM_DIR / "references" / "tasks.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("templates/task.md", text)
        self.assertNotIn("${CLAUDE_SKILL_DIR}", text)
        self.assertIn("status: open", text)
        self.assertIn("status: active", text)
        self.assertIn("depends:", text)
        self.assertIn("Transition", text)
        for action in ("create", "claim", "other status edits", "finish", "drop"):
            self.assertIn(action, text)

    def test_entry_template(self) -> None:
        path = MEM_DIR / "templates" / "entry.md"
        self.assertTrue(path.is_file())
        meta, body = parse_frontmatter(path)
        expected_keys = {"domain", "summary", "affects", "verified", "source", "supersedes"}
        self.assertEqual(set(meta.keys()), expected_keys)
        self.assertLessEqual(count_words(body), 150)
        self.assertIn("The choice", body)
        self.assertIn("Why:", body)
        self.assertIn("Rejected:", body)
        self.assertIn("Behaviour stays in the `affects:` files; do not restate it.", body)

    def test_draft_state_template(self) -> None:
        path = MEM_DIR / "templates" / "draft-state.md"
        self.assertTrue(path.is_file())
        meta, body = parse_frontmatter(path)
        self.assertEqual(set(meta.keys()), {"file"})
        self.assertIn("## Session Decisions", body)
        self.assertIn("## Pending Verification", body)

    def test_store_readme_template(self) -> None:
        path = MEM_DIR / "templates" / "store-readme.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertFalse(text.startswith("---"))
        self.assertIn("Supervisor for Antigravity pack", text)
        self.assertNotIn("Claude", text)
        self.assertNotIn("claude-supervisor", text)
        self.assertTrue(
            "deploy memory externalize" in text or "agy-supervisor memory externalize" in text
        )

    def test_project_memory_skill(self) -> None:
        path = MEM_DIR / "SKILL.md"
        self.assertTrue(path.is_file())
        raw = path.read_bytes()
        self.assertLess(len(raw), 24000)
        lines = raw.decode("utf-8").splitlines()
        self.assertLessEqual(len(lines), 300)

        meta, body = parse_frontmatter(path)
        self.assertEqual(meta.get("name"), "project-memory")
        self.assertLessEqual(count_words(body), 1380)

        # 5 memory kinds
        for kind in ("decisions", "facts", "lessons", "goals", "conventions"):
            self.assertIn(kind, body)

        # Horizons and retrieval validation
        self.assertIn("## Horizons", body)
        self.assertIn("## Retrieval and validation", body)

        # Antigravity project walk roots, never Claude
        self.assertIn("GEMINI.md", body)
        self.assertIn("AGENTS.md", body)
        self.assertIn(".agents/", body)
        self.assertIn(".supervisor/", body)
        self.assertNotIn("CLAUDE.md", body)
        self.assertNotIn(".claude/", body)

        # Store externalization mentions
        self.assertTrue(
            "deploy memory externalize" in body or "agy-supervisor memory externalize" in body
        )

        # Relative links to templates and references
        for rel in (
            "./templates/store-readme.md",
            "./templates/entry.md",
            "./references/curator-procedures.md",
            "./references/writing.md",
            "./references/tasks.md",
        ):
            self.assertIn(f"`{rel}`", body)
            resolved = (MEM_DIR / rel).resolve()
            self.assertTrue(resolved.is_file(), f"broken link {rel} -> {resolved}")

    def test_curator_procedures(self) -> None:
        path = MEM_DIR / "references" / "curator-procedures.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")

        for proc in (
            "Close-out",
            "Idle-plan sweep",
            "Audit",
            "Record",
            "Remember",
            "Forget",
            "Task",
            "Drop task",
            "Make this a project",
            "Migrate",
            "Archive",
        ):
            self.assertIn(f"## {proc}", text)

        self.assertIn("`./tasks.md`", text)
        self.assertIn("`../templates/task.md`", text)
        self.assertTrue((path.parent / "./tasks.md").resolve().is_file())
        self.assertTrue((path.parent / "../templates/task.md").resolve().is_file())
        self.assertTrue(
            "deploy memory externalize" in text or "agy-supervisor memory externalize" in text
        )

    def test_writing_reference(self) -> None:
        path = MEM_DIR / "references" / "writing.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("<key>", text)
        self.assertIn("proposal--body.tex", text)
        self.assertIn("## Precedence", text)
        self.assertIn("promotion checkpoint", text)

    def test_pickup_skill(self) -> None:
        path = PICKUP_DIR / "SKILL.md"
        self.assertTrue(path.is_file())
        raw = path.read_bytes()
        self.assertLess(len(raw), 24000)
        lines = raw.decode("utf-8").splitlines()
        self.assertLessEqual(len(lines), 300)

        meta, body = parse_frontmatter(path)
        self.assertEqual(meta.get("name"), "pick-up")
        self.assertNotIn("argument-hint", meta)
        self.assertNotIn("user-invocable", meta)
        self.assertNotIn("context", meta)
        self.assertLessEqual(count_words(body), 1380)

        self.assertNotIn("$ARGUMENTS", body)
        self.assertIn("scout", body)
        self.assertIn("fixer", body)
        self.assertIn("git-ops", body)
        self.assertIn("status: open", body)
        self.assertIn("status: active", body)

    def test_closeout_skill(self) -> None:
        path = CLOSEOUT_DIR / "SKILL.md"
        self.assertTrue(path.is_file())
        raw = path.read_bytes()
        self.assertLess(len(raw), 24000)
        lines = raw.decode("utf-8").splitlines()
        self.assertLessEqual(len(lines), 300)

        meta, body = parse_frontmatter(path)
        self.assertEqual(meta.get("name"), "close-out")
        self.assertNotIn("argument-hint", meta)
        self.assertNotIn("user-invocable", meta)
        self.assertNotIn("context", meta)
        self.assertLessEqual(count_words(body), 1380)

        self.assertNotIn("$ARGUMENTS", body)
        self.assertIn("fixer", body)
        self.assertIn("curator", body)
        self.assertIn("git-ops", body)
        self.assertIn("Session state:", body)


if __name__ == "__main__":
    unittest.main()
