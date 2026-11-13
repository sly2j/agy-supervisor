---
name: python-env
description: Python environment detection, uv / venv selection, and reproducible dependency practices.
---

# Python Environment Rules

Prefer deterministic, isolated Python environments and never mutate system Python packages.

## Interpreter Resolution Order

1. Check if the project defines `.venv/bin/python` or `uv.lock` / `pyproject.toml`.
2. If using `uv`: prefer `uv run python ...` or `uv run pytest ...` so lockfiles stay synced.
3. For stdlib-only scripts (no third-party imports), verify which system/framework Python works
   cleanly (for example `/usr/bin/python3` on macOS when sandboxed conda environments fail) and
   respect `requires-python` version floors (for example Python 3.9 syntax without `X | Y`
   unions).
4. Record the exact interpreter path used when reporting test verification results.

## Rules

- Never run `pip install` into global or system site-packages.
- Always quote exact commands and interpreter paths in verification reports.
- Do not pin OS-specific absolute paths inside shipped library modules unless required by a
  host-environment fallback.
