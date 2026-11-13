---
name: project-backup
description: Create a clean timestamped tar.gz archive of the project excluding caches, venvs, and worktrees.
disable-model-invocation: true
---

# Project Backup Archive

Create a clean, portable `.tar.gz` backup of a project directory while excluding heavy build
caches, virtualenvs, and temporary worktree directories.

## Usage

Run `./scripts/backup.sh <project_dir> [output_dir]` from this skill directory (or resolve
its installed path under the plugin root):

- `project_dir`: target project directory to archive (defaults to `.`)
- `output_dir`: destination folder for the `.tar.gz` archive (defaults to `<parent>/backups`)

## Exclusions

The backup script automatically excludes `.git`, `.venv`, `node_modules`, `__pycache__`,
`.pytest_cache`, `.agents/worktrees`, `.claude/worktrees`, and OS metadata (`.DS_Store`).

## Safety

- Always verify the destination has sufficient disk space before archiving large datasets.
- Print the final archive path and compressed size clearly to the user.
