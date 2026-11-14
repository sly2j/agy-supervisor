# Antigravity Supervisor Audit Tool

The audit tool scans local Antigravity session brain directories to compute usage, coordination,
and efficiency metrics across multi-agent workflows.

## Execution

Run the script in isolated mode using standard Python 3.9+ without third-party dependencies:

```bash
python3 -I tools/audit/audit.py > tools/audit/out/run.md
```

To emit machine-readable JSON:

```bash
python3 -I tools/audit/audit.py --json > tools/audit/out/run.json
```

## CLI Flags

- `--root DIR`: Brain root directory to scan. Repeatable for multi-root analysis.
  Defaults to `~/.gemini/antigravity-cli/brain`.
- `--since YYYY-MM-DD`: Filters sessions to those starting on or after the specified UTC date.
- `--json`: Emits structured JSON output instead of the default Markdown tables.

## Computed Metrics

The audit tool aggregates session data into several key metric categories:

1. **Critic Round-1 PASS Rate**: Pass rate of round-1 critic reviews by lead role
   (`researcher`, `planner`, `executor`, `writer`).
2. **Round-1 Findings Table Rates**: Proportion of round-1 reviews with empty findings tables
   (0 rows) or NIT-only/empty findings (eligible to bypass secondary scope review).
3. **Scope-Critic Rulings and TRIM Rate**: Breakdown of `KEEP`, `DOWNGRADE`, and `DROP` rulings,
   verdict distribution (`LEAN` vs `TRIM`), and dispatches per critic round.
4. **Subagent Dispatches by Role and Tier**: Total count of dispatched agents across standard
   tiers (`lead`, `worker`, `critic`, `scope-critic`, `quick`).
5. **Worker File Collisions and Excess Reads**: Files read by two or more workers under the same
   lead run, measuring coordination overlap and redundant I/O.
6. **Quick-Tier ESCALATE Rate**: Proportion of quick-tier runs (`scout`, `fixer`, `git-ops`, etc.)
   requesting escalation to higher tiers.
7. **Token and Step Distributions**: Cumulative token consumption (including prompt cache) and
   step counts for leads, workers, reviewers, and entire trees, plus main thread context size.

## Privacy Guarantee

To prevent accidental data leakage:
- Reports contain aggregated counts, ratios, medians, and 8-character session prefixes only.
- The script inspects the full output buffer prior to printing.
- If any output line contains a user home directory path (`/Users/` or `/home/`) or matches any
  recorded session working directory, execution halts immediately with exit status `2`, printing
  a refusal error to `stderr` and writing nothing to `stdout`.
