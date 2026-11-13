---
name: residue
description: Sweep changed files and working tree for debug leftovers, dead code, and untracked scratch files.
---

# Residue Sweep

Inspect every touched file and `git status` before reporting completion so temporary
artifacts never leak into commits or user diffs.

## What to Check

1. **Debug & scratch code**: remove temporary `print` / `console.log` / `dbg!` calls,
   commented-out code blocks, `TODO(temp)` markers, hardcoded test paths, or disabled
   assertions introduced during iteration.
2. **Unused imports & dead helpers**: remove unreferenced imports, variables, scratch
   functions, or obsolete branches left behind after refactoring.
3. **Untracked artifacts**: inspect `git status --short` for stray `.bak`, `.orig`,
   `tmp_*`, scratch scripts, logs, or compiled artifacts inside the repository tree.
4. **Formatting & lint**: run the repository's existing formatter/linter if configured,
   or verify syntax compilation (`py_compile`, `tsc --noEmit`, etc.) on modified files.
5. **Scope check**: verify `git diff --stat` contains only files required by the task;
   revert unrelated formatting noise in untouched blocks.

## Rule

Do not suppress failing checks, delete unrelated files, or run `git reset --hard` on
untracked files without verifying whether the user created them before your turn.
