# Memory Writing Style

Project memory entries are read by future agents across fresh context windows. Optimize
for rapid scanning and exact grounding.

## Rules

- **Ground every claim**: cite file paths, symbol names, command flags, and commit SHAs
  that were directly observed.
- **State status honestly**: distinguish implemented & tested behavior from planned or
  blocked work.
- **Keep entries short**: 10–35 lines for decision records; 3–8 lines per milestone in
  `history.md`. Avoid pasting long command logs or duplicating code.
- **Stay out of `GEMINI.md`**: `GEMINI.md` holds stable repo-wide coding and workflow rules;
  volatile state, open tasks, and historical logs belong in `.supervisor/`.
- **Date format**: always use ISO dates (`YYYY-MM-DD`).
