"""Unit tests for tools/audit/audit.py."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = REPO_ROOT / "tools" / "audit" / "audit.py"


def _create_jsonl(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for item in lines:
            fh.write(json.dumps(item) + "\n")


def _create_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


class AuditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _run_audit(self, extra_args=None):
        cmd = [sys.executable, "-I", str(AUDIT_SCRIPT), "--root", str(self.root)]
        if extra_args:
            cmd.extend(extra_args)
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )

    def test_audit_parses_critic_verdicts(self) -> None:
        # Session 1: planner with PASS in round 1, empty findings
        s1 = self.root / "sess-planner"
        _create_jsonl(
            s1 / ".system_generated" / "logs" / "transcript.jsonl",
            [
                {"created_at": "2026-06-01T10:00:00Z", "input_tokens": 100, "output_tokens": 20},
            ],
        )
        _create_json(
            s1 / ".system_generated" / "subagents" / "planner-sub.json",
            {
                "conversationId": "planner-sub",
                "subagentDescriptor": {"typeName": "planner", "role": "Planning Lead"},
            },
        )

        p1 = self.root / "planner-sub"
        _create_jsonl(
            p1 / ".system_generated" / "logs" / "transcript.jsonl",
            [
                {"created_at": "2026-06-01T10:01:00Z", "input_tokens": 200, "output_tokens": 50},
            ],
        )
        _create_json(
            p1 / ".system_generated" / "subagents" / "critic-p1.json",
            {
                "conversationId": "critic-p1",
                "subagentDescriptor": {"typeName": "critic", "role": "Critic"},
            },
        )

        c1 = self.root / "critic-p1"
        c1_handback = (
            "VERDICT: PASS\n"
            "ROUND: 1\n\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n"
            "| None. | — | — | No defects found. | Verified. | None. |\n"
        )
        _create_jsonl(
            c1 / ".system_generated" / "logs" / "transcript.jsonl",
            [
                {
                    "created_at": "2026-06-01T10:02:00Z",
                    "input_tokens": 50,
                    "output_tokens": 20,
                    "content": c1_handback,
                    "tool_calls": [
                        {"name": "send_message", "args": {"Message": c1_handback, "Recipient": "planner-sub"}}
                    ],
                }
            ],
        )

        # Session 2: executor with REVISE in round 1 (has BLOCKING), PASS in round 2 (NIT-only)
        s2 = self.root / "sess-executor"
        _create_jsonl(
            s2 / ".system_generated" / "logs" / "transcript.jsonl",
            [
                {"created_at": "2026-06-01T11:00:00Z", "input_tokens": 100, "output_tokens": 20},
            ],
        )
        _create_json(
            s2 / ".system_generated" / "subagents" / "exec-sub.json",
            {
                "conversationId": "exec-sub",
                "subagentDescriptor": {"typeName": "executor", "role": "Execution Lead"},
            },
        )

        e1 = self.root / "exec-sub"
        _create_jsonl(
            e1 / ".system_generated" / "logs" / "transcript.jsonl",
            [
                {"created_at": "2026-06-01T11:01:00Z", "input_tokens": 300, "output_tokens": 60},
            ],
        )
        _create_json(
            e1 / ".system_generated" / "subagents" / "critic-e1.json",
            {
                "conversationId": "critic-e1",
                "subagentDescriptor": {"typeName": "critic", "role": "Critic R1"},
            },
        )
        _create_json(
            e1 / ".system_generated" / "subagents" / "critic-e2.json",
            {
                "conversationId": "critic-e2",
                "subagentDescriptor": {"typeName": "critic", "role": "Critic R2"},
            },
        )

        c_e1 = self.root / "critic-e1"
        c_e1_handback = (
            "VERDICT: REVISE\n"
            "ROUND: 1\n\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n"
            "| C1 | BLOCKING | line 10 | Syntax error | Traceback | Fix syntax |\n"
            "| C2 | NIT | line 25 | Typo | 'teh' -> 'the' | Fix typo |\n"
        )
        _create_jsonl(
            c_e1 / ".system_generated" / "logs" / "transcript.jsonl",
            [
                {
                    "created_at": "2026-06-01T11:02:00Z",
                    "input_tokens": 70,
                    "output_tokens": 30,
                    "content": c_e1_handback,
                }
            ],
        )

        c_e2 = self.root / "critic-e2"
        c_e2_handback = (
            "VERDICT: PASS\n"
            "ROUND: 2\n\n"
            "| ID | Severity | Location | Finding | Evidence | Minimal fix |\n"
            "|---|---|---|---|---|---|\n"
            "| C2 | NIT | line 25 | Typo | 'teh' -> 'the' | Fix typo |\n"
        )
        _create_jsonl(
            c_e2 / ".system_generated" / "logs" / "transcript.jsonl",
            [
                {
                    "created_at": "2026-06-01T11:05:00Z",
                    "input_tokens": 80,
                    "output_tokens": 25,
                    "content": c_e2_handback,
                }
            ],
        )

        proc = self._run_audit(["--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)

        planner_pass = data["critic_round1_pass"]["planner"]
        self.assertEqual(planner_pass["runs"], 1)
        self.assertEqual(planner_pass["r1_critics"], 1)
        self.assertEqual(planner_pass["pass_count"], 1)
        self.assertEqual(planner_pass["pass_rate"], 1.0)

        exec_pass = data["critic_round1_pass"]["executor"]
        self.assertEqual(exec_pass["runs"], 1)
        self.assertEqual(exec_pass["r1_critics"], 1)
        self.assertEqual(exec_pass["pass_count"], 0)
        self.assertEqual(exec_pass["pass_rate"], 0.0)

        # Findings checks
        planner_findings = data["round1_findings"]["planner"]
        self.assertEqual(planner_findings["empty_count"], 1)
        self.assertEqual(planner_findings["empty_rate"], 1.0)
        self.assertEqual(planner_findings["nit_only_count"], 1)
        self.assertEqual(planner_findings["nit_only_rate"], 1.0)

        exec_findings = data["round1_findings"]["executor"]
        self.assertEqual(exec_findings["empty_count"], 0)
        self.assertEqual(exec_findings["empty_rate"], 0.0)
        self.assertEqual(exec_findings["nit_only_count"], 0)
        self.assertEqual(exec_findings["nit_only_rate"], 0.0)

    def test_audit_parses_scope_critic_rulings(self) -> None:
        s = self.root / "sess-scope"
        _create_jsonl(
            s / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-06-01T12:00:00Z", "input_tokens": 100, "output_tokens": 10}],
        )
        _create_json(
            s / ".system_generated" / "subagents" / "planner-sub.json",
            {"conversationId": "planner-sub", "subagentDescriptor": {"typeName": "planner", "role": "Lead"}},
        )

        p = self.root / "planner-sub"
        _create_jsonl(
            p / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-06-01T12:01:00Z", "input_tokens": 150, "output_tokens": 20}],
        )
        _create_json(
            p / ".system_generated" / "subagents" / "critic-1.json",
            {"conversationId": "critic-1", "subagentDescriptor": {"typeName": "critic", "role": "Critic"}},
        )
        _create_json(
            p / ".system_generated" / "subagents" / "scope-1.json",
            {"conversationId": "scope-1", "subagentDescriptor": {"typeName": "scope-critic", "role": "Scope Critic"}},
        )

        _create_jsonl(
            self.root / "critic-1" / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-06-01T12:02:00Z", "content": "VERDICT: PASS\nROUND: 1"}],
        )

        scope_handback = (
            "VERDICT: TRIM\n\n"
            "| ID | Item | Ruling |\n"
            "|---|---|---|\n"
            "| 1 | Extra helper | DROP |\n"
            "| 2 | Refactoring | DOWNGRADE |\n"
            "| 3 | Core fix | KEEP |\n"
        )
        _create_jsonl(
            self.root / "scope-1" / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-06-01T12:03:00Z", "content": scope_handback}],
        )

        proc = self._run_audit(["--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)

        planner_scope = data["scope_critic"]["by_lead"]["planner"]
        self.assertEqual(planner_scope["reviews"], 1)
        self.assertEqual(planner_scope["keep"], 1)
        self.assertEqual(planner_scope["downgrade"], 1)
        self.assertEqual(planner_scope["drop"], 1)
        self.assertEqual(planner_scope["trim"], 1)
        self.assertEqual(planner_scope["lean"], 0)
        self.assertEqual(planner_scope["trim_rate"], 1.0)
        self.assertEqual(planner_scope["dispatches"], 1)
        self.assertEqual(planner_scope["critic_rounds"], 1)

    def test_audit_worker_file_collision_detection(self) -> None:
        s = self.root / "sess-workers"
        _create_jsonl(
            s / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-06-01T13:00:00Z", "input_tokens": 50, "output_tokens": 10}],
        )
        _create_json(
            s / ".system_generated" / "subagents" / "exec-sub.json",
            {"conversationId": "exec-sub", "subagentDescriptor": {"typeName": "executor", "role": "Lead"}},
        )

        e = self.root / "exec-sub"
        _create_jsonl(
            e / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-06-01T13:01:00Z", "input_tokens": 100, "output_tokens": 20}],
        )
        _create_json(
            e / ".system_generated" / "subagents" / "w1.json",
            {"conversationId": "w1", "subagentDescriptor": {"typeName": "executor-worker", "role": "Worker 1"}},
        )
        _create_json(
            e / ".system_generated" / "subagents" / "w2.json",
            {"conversationId": "w2", "subagentDescriptor": {"typeName": "executor-worker", "role": "Worker 2"}},
        )
        _create_json(
            e / ".system_generated" / "subagents" / "w3.json",
            {"conversationId": "w3", "subagentDescriptor": {"typeName": "executor-worker", "role": "Worker 3"}},
        )

        # w1 reads: file_shared.py, file_w1.py
        _create_jsonl(
            self.root / "w1" / ".system_generated" / "logs" / "transcript.jsonl",
            [
                {
                    "created_at": "2026-06-01T13:02:00Z",
                    "tool_calls": [
                        {"name": "read_file", "args": {"Path": "file_shared.py"}},
                        {"name": "read_file", "args": {"path": "file_w1.py"}},
                    ],
                }
            ],
        )

        # w2 reads: file_shared.py, file_w2.py
        _create_jsonl(
            self.root / "w2" / ".system_generated" / "logs" / "transcript.jsonl",
            [
                {
                    "created_at": "2026-06-01T13:03:00Z",
                    "tool_calls": [
                        {"name": "read_file", "args": {"Path": "file_shared.py"}},
                        {"name": "read_file", "args": {"Path": "file_w2.py"}},
                    ],
                }
            ],
        )

        # w3 reads: file_shared.py
        _create_jsonl(
            self.root / "w3" / ".system_generated" / "logs" / "transcript.jsonl",
            [
                {
                    "created_at": "2026-06-01T13:04:00Z",
                    "tool_calls": [
                        {"name": "read_file", "args": {"Path": "file_shared.py"}},
                    ],
                }
            ],
        )

        proc = self._run_audit(["--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)

        col = data["worker_file_collisions"]["by_lead"]["executor"]
        self.assertEqual(col["runs_affected"], 1)
        self.assertEqual(col["colliding_files"], 1)
        # 3 workers read file_shared.py -> (3 - 1) = 2 excess reads
        self.assertEqual(col["excess_reads"], 2)

    def test_audit_quick_escalate_rate(self) -> None:
        s = self.root / "sess-quick"
        _create_jsonl(
            s / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-06-01T14:00:00Z", "input_tokens": 50, "output_tokens": 10}],
        )
        _create_json(
            s / ".system_generated" / "subagents" / "scout-1.json",
            {"conversationId": "scout-1", "subagentDescriptor": {"typeName": "scout", "role": "Scout 1"}},
        )
        _create_json(
            s / ".system_generated" / "subagents" / "scout-2.json",
            {"conversationId": "scout-2", "subagentDescriptor": {"typeName": "scout", "role": "Scout 2"}},
        )
        _create_json(
            s / ".system_generated" / "subagents" / "fixer-1.json",
            {"conversationId": "fixer-1", "subagentDescriptor": {"typeName": "fixer", "role": "Fixer 1"}},
        )

        _create_jsonl(
            self.root / "scout-1" / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-06-01T14:01:00Z", "content": "I cannot locate the target. ESCALATE to planner."}],
        )
        _create_jsonl(
            self.root / "scout-2" / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-06-01T14:02:00Z", "content": "Target found cleanly. No escalation needed."}],
        )
        _create_jsonl(
            self.root / "fixer-1" / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-06-01T14:03:00Z", "content": "Applied single-line fix successfully."}],
        )

        proc = self._run_audit(["--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)

        quick = data["quick_tier_escalate"]
        self.assertEqual(quick["by_agent"]["scout"]["runs"], 2)
        self.assertEqual(quick["by_agent"]["scout"]["escalated"], 1)
        self.assertAlmostEqual(quick["by_agent"]["scout"]["rate"], 0.5)

        self.assertEqual(quick["by_agent"]["fixer"]["runs"], 1)
        self.assertEqual(quick["by_agent"]["fixer"]["escalated"], 0)
        self.assertEqual(quick["by_agent"]["fixer"]["rate"], 0.0)

        self.assertEqual(quick["all"]["runs"], 3)
        self.assertEqual(quick["all"]["escalated"], 1)
        self.assertAlmostEqual(quick["all"]["rate"], 1.0 / 3.0)

    def test_audit_json_output(self) -> None:
        s = self.root / "sess-all"
        _create_jsonl(
            s / ".system_generated" / "logs" / "transcript.jsonl",
            [
                {
                    "created_at": "2026-06-01T15:00:00Z",
                    "input_tokens": 1000,
                    "cache_read_tokens": 500,
                    "output_tokens": 200,
                }
            ],
        )
        _create_json(
            s / ".system_generated" / "subagents" / "lead-sub.json",
            {"conversationId": "lead-sub", "subagentDescriptor": {"typeName": "planner", "role": "Lead"}},
        )

        proc = self._run_audit(["--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)

        expected_keys = {
            "corpus",
            "critic_round1_pass",
            "round1_findings",
            "scope_critic",
            "subagent_dispatches",
            "worker_file_collisions",
            "quick_tier_escalate",
            "token_and_step_distributions",
        }
        self.assertTrue(expected_keys.issubset(data.keys()))
        self.assertEqual(data["corpus"]["sessions"], 1)
        self.assertEqual(data["corpus"]["lead_runs"], 1)

    def test_audit_privacy_guardrail(self) -> None:
        # Case 1: /Users/ leak
        s1 = self.root / "sess-privacy-users"
        _create_jsonl(
            s1 / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-06-01T16:00:00Z", "input_tokens": 10, "output_tokens": 10}],
        )
        _create_json(
            s1 / ".system_generated" / "subagents" / "bad-sub-1.json",
            {
                "conversationId": "bad-sub-1",
                "subagentDescriptor": {
                    "typeName": "/Users/victim/repo/secret",
                    "role": "Leaking path",
                },
            },
        )

        proc1 = self._run_audit()
        self.assertEqual(proc1.returncode, 2)
        self.assertEqual(proc1.stdout, "")
        self.assertIn("audit.py: refusing to print: the report contains a path-like line; nothing was printed", proc1.stderr)

        # Case 2: /home/ leak
        s2 = self.root / "sess-privacy-home"
        _create_jsonl(
            s2 / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-06-01T16:05:00Z", "input_tokens": 10, "output_tokens": 10}],
        )
        _create_json(
            s2 / ".system_generated" / "subagents" / "bad-sub-2.json",
            {
                "conversationId": "bad-sub-2",
                "subagentDescriptor": {
                    "typeName": "/home/developer/code",
                    "role": "Leaking home path",
                },
            },
        )

        proc2 = self._run_audit()
        self.assertEqual(proc2.returncode, 2)
        self.assertEqual(proc2.stdout, "")
        self.assertIn("audit.py: refusing to print: the report contains a path-like line; nothing was printed", proc2.stderr)

    def test_audit_markdown_report_rendering(self) -> None:
        s = self.root / "sess-md"
        _create_jsonl(
            s / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-06-01T12:00:00Z", "input_tokens": 500, "output_tokens": 100}],
        )
        _create_json(
            s / ".system_generated" / "subagents" / "plan-1.json",
            {"conversationId": "plan-1", "subagentDescriptor": {"typeName": "planner", "role": "Planner"}},
        )
        _create_jsonl(
            self.root / "plan-1" / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-06-01T12:01:00Z", "input_tokens": 300, "output_tokens": 50}],
        )

        proc = self._run_audit()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout
        self.assertIn("# Pack audit", out)
        self.assertIn("## Corpus", out)
        self.assertIn("## Critic round-1 PASS by lead", out)
        self.assertIn("## Scope-critic rulings and TRIM rate", out)
        self.assertIn("## Subagent dispatches by role and tier", out)
        self.assertIn("## Lead-tree tokens per run", out)
        self.assertIn("## Main-thread final context", out)

    def test_audit_empty_corpus(self) -> None:
        proc = self._run_audit(["--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["corpus"]["sessions"], 0)
        self.assertEqual(data["corpus"]["subagents"], 0)
        self.assertIsNone(data["corpus"]["start_range_utc"])

    def test_audit_invalid_since(self) -> None:
        proc = self._run_audit(["--since", "invalid-date"])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--since must be YYYY-MM-DD", proc.stderr)

    def test_audit_since_filter(self) -> None:
        # Session 1: Old session from 2026-01-10
        s1 = self.root / "sess-old"
        _create_jsonl(
            s1 / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-01-10T10:00:00Z", "input_tokens": 100, "output_tokens": 10}],
        )

        # Session 2: New session from 2026-07-20
        s2 = self.root / "sess-new"
        _create_jsonl(
            s2 / ".system_generated" / "logs" / "transcript.jsonl",
            [{"created_at": "2026-07-20T10:00:00Z", "input_tokens": 100, "output_tokens": 10}],
        )

        proc = self._run_audit(["--since", "2026-06-01", "--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)

        self.assertEqual(data["corpus"]["sessions"], 1)
        self.assertEqual(data["corpus"]["start_range_utc"], ["2026-07-20", "2026-07-20"])


if __name__ == "__main__":
    unittest.main()
