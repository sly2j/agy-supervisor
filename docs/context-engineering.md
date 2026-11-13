# Context Engineering

`agy-supervisor` protects attention and token budgets across long multi-turn projects using
five structural mechanisms:

1. **Shell Isolation at the Coordinator**: `supervisor` carries no shell tools, preventing
   megabytes of test logs, stack traces, or package installs from filling top-level context.
2. **Tiered Subagent Routing**: quick lookups use `scout` (`flash_lite`), single-file edits
   use `fixer` (`flash_lite`), and heavy verification uses `pro` models on leads and critics.
3. **Selective Preloaded Skills**: agents only preload skills needed on every turn (`lead-loop`,
   `residue`, `project-memory`, `git-safety`, `repo-workflow`, `plan-writing`), keeping system
   prompts compact.
4. **Capped Lead & Worker Reports**: workers return observed facts, changed paths, and
   verification output; leads return bounded `Status` / `Summary` / `Files changed` /
   `Verification` / `Open issues` blocks.
5. **Externalized `.supervisor/` Memory**: durable milestones, active roadmap items, and
   decision records live outside `GEMINI.md` under `.supervisor/` and are loaded selectively
   by relevance rather than pasted into every turn.
