---
name: plan-writing
description: Structure durable implementation plans, phase breakdowns, acceptance checks, and handoff specs.
---

# Plan Writing

Produce concrete, verifiable implementation plans before code changes begin. Avoid vague
milestones, hand-waved verification, or hidden scope expansion.

## Plan Anatomy

Write plans to either the user-requested destination or `.supervisor/roadmap.md` / scratch
path agreed with `supervisor`. Every plan must include:

1. **Goal & Non-Goals**: one-paragraph statement of intended behavior plus explicit
   boundaries so `scope-critic` can catch drift later.
2. **Codebase Grounding**: exact existing files, symbols, APIs, and constraints verified
   by reading the repository (never cite unread symbols).
3. **Architecture Decisions**: choices made, alternatives rejected, and why.
4. **Phased Task Breakdown**: ordered steps where each step names:
   - Exact files to create or modify
   - Concrete behavior / interface contract
   - Dependencies on earlier steps
5. **Verification Plan**: exact test suites, linters, smoke commands, and success criteria
   to run after implementation, covering edge cases and failure modes.
6. **Re-Plan Triggers**: conditions under which `executor` should halt and return to
   `planner` instead of guessing (e.g., missing API, failing invariant, scope growth).

## Worktree Planning Rule

For multi-file code changes on an existing branch where dirty edits could clash with main,
specify isolated git worktree execution (`<toplevel>/.agents/worktrees/<slug>`) per
`repo-workflow` (`landing-from-worktree.md`), plus the landing check command.

## Quality Checklist

- Every referenced file path and symbol was directly observed or explicitly marked `NEW`.
- No step asks an executor to "clean up later" or leaves test coverage implicit.
- No silent schema, API, or CLI breaking changes without explicit user consent.
- Each task is small enough to verify cleanly in one `executor` pass.
