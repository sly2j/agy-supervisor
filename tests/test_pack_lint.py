"""Lint tests enforcing Supervisor for Antigravity pack invariants."""

import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = REPO_ROOT / "pack"
AGENTS_DIR = PACK_DIR / "agents"
SKILLS_DIR = PACK_DIR / "skills"

EXPECTED_AGENTS = {
    "supervisor",
    "researcher",
    "planner",
    "executor",
    "writer",
    "researcher-worker",
    "planner-worker",
    "executor-worker",
    "writer-worker",
    "critic",
    "scope-critic",
    "curator",
    "fixer",
    "git-ops",
    "scout",
}

EXPECTED_SKILLS = {
    "agent-authoring",
    "lead-loop",
    "plan-writing",
    "residue",
    "project-memory",
    "git-safety",
    "repo-workflow",
    "python-env",
    "science-writing-style",
    "presentation-style",
    "document-extraction",
    "email-extraction",
    "meeting-summary",
    "close-out",
    "pick-up",
    "project-backup",
    "supervisor-config",
}

VALID_MODELS = {"inherit", "pro", "flash", "flash_lite"}
BANNED_AGENT_KEYS = {"disallowedTools", "effort", "color", "enableSubagentTools"}
BANNED_SKILL_KEYS = {"user-invocable", "context", "argument-hint"}
VALID_TOOLS = {
    "read_file",
    "write_file",
    "edit_file",
    "run_command",
    "manage_task",
    "search_web",
    "invoke_subagent",
    "define_subagent",
    "manage_subagents",
    "send_message",
    "ask_question",
}

WORD_CAPS = {
    "supervisor": 1000,
    "researcher": 700,
    "planner": 700,
    "executor": 700,
    "writer": 700,
    "critic": 600,
    "scope-critic": 600,
    "researcher-worker": 400,
    "planner-worker": 400,
    "executor-worker": 400,
    "writer-worker": 400,
    "curator": 400,
    "fixer": 350,
    "git-ops": 350,
    "scout": 350,
}

ROUTING_SCOPE = {
    "researcher": ("literature", "evidence", "analysis", "investigation", "benchmark"),
    "planner": ("architecture", "implementation plan", "design", "spec", "phase breakdown"),
    "executor": ("implement", "code", "refactor", "debug", "tests", "worktree"),
    "writer": ("documentation", "manuscript", "report", "prose", "slides"),
    "fixer": ("single-file", "typo", "small fix", "surgical edit"),
    "git-ops": ("git", "commit", "branch", "worktree", "merge", "status"),
    "scout": ("fast lookup", "locate", "grep", "read-only", "inspect"),
}

LEAKS = (
    "opencode",
    "argo/",
    "~/.config/opencode",
    "${CLAUDE_SKILL_DIR}",
    "$ARGUMENTS",
    "claude-supervisor",
)


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
        if not val:
            meta[key] = []
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


class PackLintTest(unittest.TestCase):
    def test_expected_components_present(self) -> None:
        found_agents = {p.stem for p in AGENTS_DIR.glob("*.md")}
        self.assertEqual(found_agents, EXPECTED_AGENTS)
        found_skills = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
        self.assertEqual(found_skills, EXPECTED_SKILLS)
        for skill in EXPECTED_SKILLS:
            self.assertTrue((SKILLS_DIR / skill / "SKILL.md").is_file())

    def test_plugin_json_and_logo(self) -> None:
        pj = json.loads((PACK_DIR / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(pj["name"], "agy-supervisor")
        self.assertTrue((PACK_DIR / pj["logo"]).is_file())
        self.assertLessEqual(len(pj.get("suggestedPrompts", [])), 3)

    def test_agents_frontmatter_boundaries_and_routing(self) -> None:
        sup_body = ""
        for name in sorted(EXPECTED_AGENTS):
            path = AGENTS_DIR / f"{name}.md"
            meta, body = parse_frontmatter(path)
            self.assertEqual(meta.get("name"), name)
            self.assertIn(meta.get("model"), VALID_MODELS, f"{name}: bad model")
            for bad_key in BANNED_AGENT_KEYS:
                self.assertNotIn(bad_key, meta, f"{name} contains banned key {bad_key}")

            tools = meta.get("tools") or []
            self.assertTrue(isinstance(tools, list) and tools, f"{name} must declare tools")
            for tool in tools:
                self.assertIn(tool, VALID_TOOLS, f"{name} unknown tool {tool}")

            if name == "supervisor":
                self.assertIs(meta.get("mainAgent"), True)
                self.assertIs(meta.get("subagent"), False)
                self.assertNotIn("run_command", tools)
                self.assertNotIn("manage_task", tools)
                self.assertEqual(
                    set(meta.get("agents") or []),
                    EXPECTED_AGENTS
                    - {"supervisor", "researcher-worker", "planner-worker", "executor-worker", "writer-worker"},
                )
                sup_body = body
            else:
                self.assertIs(meta.get("mainAgent"), False)
                self.assertIs(meta.get("subagent"), True)

            if name in ("researcher", "planner", "executor", "writer"):
                self.assertEqual(
                    set(meta.get("agents") or []), {f"{name}-worker", "critic", "scope-critic"}
                )
            elif name != "supervisor":
                self.assertNotIn("agents", meta, f"leaf agent {name} must omit agents")
                for sub_tool in ("invoke_subagent", "define_subagent", "manage_subagents"):
                    self.assertNotIn(sub_tool, tools, f"leaf {name} must omit {sub_tool}")

            if name in ("curator", "fixer"):
                self.assertIn("git commit", body)
                self.assertIn("Never run", body)

            if name in ROUTING_SCOPE:
                desc_lower = str(meta.get("description", "")).lower()
                for kw in ROUTING_SCOPE[name]:
                    self.assertIn(kw, desc_lower, f"{name} description missing keyword {kw!r}")

            self.assertLessEqual(count_words(body), WORD_CAPS[name], f"{name} over word cap")

        # Supervisor body must name all 10 routed agents and ban built-in generic subagents.
        for target in (
            "researcher",
            "planner",
            "executor",
            "writer",
            "critic",
            "scope-critic",
            "fixer",
            "curator",
            "git-ops",
            "scout",
        ):
            self.assertIn(target, sup_body)
        for banned in ("`self`", "`research`", "`deepagent`", "`review-agent`"):
            self.assertIn(banned, sup_body)

    def test_skills_frontmatter_budgets_and_relative_links(self) -> None:
        rel_link_re = re.compile(r"`(\.{1,2}/[^`\s]+)`")
        for skill in sorted(EXPECTED_SKILLS):
            path = SKILLS_DIR / skill / "SKILL.md"
            raw = path.read_bytes()
            self.assertLess(len(raw), 24000, f"{skill} exceeds 24 KB limit")
            lines = raw.decode("utf-8").splitlines()
            self.assertLessEqual(len(lines), 300, f"{skill} exceeds 300 lines")

            meta, body = parse_frontmatter(path)
            self.assertEqual(meta.get("name"), skill)
            for bad_key in BANNED_SKILL_KEYS:
                self.assertNotIn(bad_key, meta, f"{skill} has unsupported key {bad_key}")

            cap = 350 if skill == "residue" else 1380
            self.assertLessEqual(count_words(body), cap, f"{skill} over word cap")

            for match in rel_link_re.finditer(body):
                rel = match.group(1)
                if "<" in rel or "*" in rel or "..." in rel:
                    continue
                resolved = (path.parent / rel).resolve()
                self.assertTrue(
                    resolved.exists(), f"{skill} broken relative reference {rel!r} -> {resolved}"
                )

    def test_line_lengths_and_zero_leaks_in_pack(self) -> None:
        for md_path in sorted(PACK_DIR.rglob("*.md")):
            text = md_path.read_text(encoding="utf-8")
            for leak in LEAKS:
                self.assertNotIn(leak, text, f"{md_path} contains leak {leak!r}")
            in_fence = False
            for idx, line in enumerate(text.splitlines(), 1):
                if line.lstrip().startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                if line.lstrip().startswith("|"):
                    continue
                if idx <= 20 and (
                    line.startswith("description:") or line.startswith("name:") or line.strip() == "---"
                ):
                    continue
                self.assertLessEqual(
                    len(line),
                    100,
                    f"{md_path.relative_to(PACK_DIR)}:{idx} exceeds 100 chars ({len(line)})",
                )

    def test_agy_plugin_validate_strict(self) -> None:
        agy_bin = os.environ.get("AGY_BIN") or shutil.which("agy") or str(
            Path.home() / ".local" / "bin" / "agy"
        )
        if not Path(agy_bin).is_file():
            self.skipTest("agy binary not available")
        proc = subprocess.run(
            [agy_bin, "plugin", "validate", "--strict", "--json", str(PACK_DIR)],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["findings"], [])
        self.assertEqual(data["components"]["agents"], 15)
        self.assertEqual(data["components"]["skills"], 17)


if __name__ == "__main__":
    unittest.main()
