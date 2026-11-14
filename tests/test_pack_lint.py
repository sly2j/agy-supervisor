"""Lint tests enforcing Supervisor for Antigravity pack invariants."""

import ast
import json
import os
import py_compile
import re
import shutil
import subprocess
import tempfile
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

    def test_agent_exact_models(self) -> None:
        """1. Exact per-agent model map."""
        expected_models = {
            "supervisor": "inherit",
            "writer": "inherit",
            "planner": "pro",
            "researcher": "pro",
            "executor": "pro",
            "critic": "pro",
            "scope-critic": "pro",
            "writer-worker": "pro",
            "curator": "flash",
            "planner-worker": "flash",
            "researcher-worker": "flash",
            "executor-worker": "flash",
            "scout": "flash_lite",
            "git-ops": "flash_lite",
            "fixer": "flash_lite",
        }
        for name, expected_model in expected_models.items():
            path = AGENTS_DIR / f"{name}.md"
            meta, _ = parse_frontmatter(path)
            self.assertEqual(
                meta.get("model"),
                expected_model,
                f"{name}: expected model {expected_model!r}, got {meta.get('model')!r}",
            )

    def test_agent_models_match_tiers_table(self) -> None:
        """2. Alignment between pack/agents/*.md models and Tiers table in agent-authoring/SKILL.md."""
        authoring_text = (SKILLS_DIR / "agent-authoring" / "SKILL.md").read_text(encoding="utf-8")
        section = authoring_text.split("## Tiers", 1)[1].split("\n## ", 1)[0]
        table_rows = [l for l in section.splitlines() if l.startswith("|")][2:]
        tiers_table_models: Dict[str, str] = {}
        for row in table_rows:
            parts = [c.strip() for c in row.strip("|").split("|")]
            agents_cell = parts[1]
            model_effort_cell = parts[2]
            model = model_effort_cell.split("/")[0].strip().split()[0]
            for agent_name in agents_cell.split(","):
                tiers_table_models[agent_name.strip()] = model

        for name in EXPECTED_AGENTS:
            self.assertIn(name, tiers_table_models, f"{name} missing from Tiers table in agent-authoring")
            meta, _ = parse_frontmatter(AGENTS_DIR / f"{name}.md")
            self.assertEqual(
                meta.get("model"),
                tiers_table_models[name],
                f"{name} frontmatter model {meta.get('model')} != Tiers table {tiers_table_models[name]}",
            )

    def test_project_memory_template_invariants(self) -> None:
        """3. v10 project-memory template invariants."""
        templates_dir = SKILLS_DIR / "project-memory" / "templates"
        entry_meta, _ = parse_frontmatter(templates_dir / "entry.md")
        self.assertEqual(
            set(entry_meta.keys()),
            {"domain", "summary", "affects", "verified", "source", "supersedes"},
        )

        draft_meta, _ = parse_frontmatter(templates_dir / "draft-state.md")
        self.assertEqual(set(draft_meta.keys()), {"file"})

        task_meta, _ = parse_frontmatter(templates_dir / "task.md")
        self.assertEqual(
            set(task_meta.keys()),
            {"summary", "status", "owner", "since", "plan", "depends", "decisions"},
        )

        store_readme = templates_dir / "store-readme.md"
        self.assertTrue(store_readme.is_file())
        self.assertFalse(
            store_readme.read_text(encoding="utf-8").startswith("---"),
            "store-readme.md must not contain YAML frontmatter",
        )

        tasks_ref = SKILLS_DIR / "project-memory" / "references" / "tasks.md"
        self.assertTrue(tasks_ref.is_file(), "references/tasks.md must exist")

    def test_curator_task_operations_in_scope(self) -> None:
        """4. curator.md explicitly covers task and drop task operations."""
        curator_text = (AGENTS_DIR / "curator.md").read_text(encoding="utf-8")
        scope = curator_text.split("## Scope", 1)[1].split("\n## ", 1)[0]
        self.assertIn("task <text>", scope)
        self.assertIn("drop task <card>", scope)

    def test_memory_agents_prohibit_committing(self) -> None:
        """5. curator.md and fixer.md both prohibit committing (Never run + git commit)."""
        for name in ("curator", "fixer"):
            text = (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")
            self.assertIn("Never run", text, f"{name} must contain 'Never run'")
            self.assertIn("git commit", text, f"{name} must contain 'git commit'")

    def test_git_ops_loads_safety_and_workflow_skills(self) -> None:
        """6. git-ops.md references git-safety and repo-workflow."""
        meta, _ = parse_frontmatter(AGENTS_DIR / "git-ops.md")
        skills = set(meta.get("skills", []))
        self.assertTrue(
            {"git-safety", "repo-workflow"} <= skills,
            f"git-ops must load git-safety and repo-workflow, got {skills}",
        )

    def test_origin_rebase_and_landing_rules(self) -> None:
        """7. Origin rebase / upstream landing rule present in repo-workflow and git-ops.md."""
        repo_wf = (SKILLS_DIR / "repo-workflow" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("git fetch origin", repo_wf)
        self.assertIn("pull --rebase", repo_wf)
        self.assertIn("`origin` first", repo_wf)

        git_ops = (AGENTS_DIR / "git-ops.md").read_text(encoding="utf-8")
        self.assertIn("git fetch origin", git_ops)
        self.assertIn("pull --rebase", git_ops)
        self.assertIn("`origin` first", git_ops)

    def test_attribution_conventions(self) -> None:
        """8. Attribution invariant: supervisor.md and git-ops.md require Co-Authored-By and reject harness reminders."""
        for name in ("supervisor", "git-ops"):
            text = " ".join((AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8").split())
            self.assertIn("Co-Authored-By: Supervisor for Antigravity", text, f"{name} attribution trailer missing")
            self.assertIn("harness attribution reminders", text, f"{name} generic harness reminder rejection missing")
            self.assertNotIn("claude-session", text, f"{name} must not leak claude-session")

    def test_residue_skill_preloaded(self) -> None:
        """9. residue skill referenced in executor, executor-worker, researcher, researcher-worker, and fixer."""
        for name in ("executor", "executor-worker", "researcher", "researcher-worker", "fixer"):
            meta, _ = parse_frontmatter(AGENTS_DIR / f"{name}.md")
            skills = meta.get("skills", [])
            self.assertIn("residue", skills, f"{name} must list residue in skills")

    def test_residue_teardown_wiring(self) -> None:
        """10. Residue teardown wiring present in supervisor.md, close-out/SKILL.md, and fixer.md."""
        for target in (
            AGENTS_DIR / "supervisor.md",
            AGENTS_DIR / "fixer.md",
            SKILLS_DIR / "close-out" / "SKILL.md",
        ):
            text = target.read_text(encoding="utf-8")
            self.assertIn("teardown", text, f"{target.name} must wire teardown")

    def test_scripts_executable_and_syntax(self) -> None:
        """11. All scripts exist, have executable bits where appropriate, and pass syntax compilation & AST checks."""
        scripts = [
            REPO_ROOT / "deploy",
            SKILLS_DIR / "supervisor-config" / "scripts" / "external-critic",
            SKILLS_DIR / "project-backup" / "scripts" / "backup.sh",
            REPO_ROOT / "tools" / "audit" / "audit.py",
        ]
        for s in scripts:
            self.assertTrue(s.is_file(), f"{s} does not exist")

        for s in (
            REPO_ROOT / "deploy",
            SKILLS_DIR / "supervisor-config" / "scripts" / "external-critic",
            SKILLS_DIR / "project-backup" / "scripts" / "backup.sh",
        ):
            self.assertTrue(bool(s.stat().st_mode & 0o111), f"{s} is not executable")

        with tempfile.TemporaryDirectory() as td:
            for py_s in (
                REPO_ROOT / "deploy",
                SKILLS_DIR / "supervisor-config" / "scripts" / "external-critic",
                REPO_ROOT / "tools" / "audit" / "audit.py",
            ):
                cfile = Path(td) / f"{py_s.name}.pyc"
                py_compile.compile(str(py_s), cfile=str(cfile), doraise=True)
                tree = ast.parse(py_s.read_text(encoding="utf-8"), filename=str(py_s))
                for node in ast.walk(tree):
                    if hasattr(ast, "Match") and isinstance(node, ast.Match):
                        self.fail(f"{py_s} contains ast.Match which requires Python 3.10+")

        proc = subprocess.run(
            ["bash", "-n", str(SKILLS_DIR / "project-backup" / "scripts" / "backup.sh")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, f"backup.sh syntax error: {proc.stderr}")


if __name__ == "__main__":
    unittest.main()
