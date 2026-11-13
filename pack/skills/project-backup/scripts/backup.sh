#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-.}"
if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "error: project directory not found: $PROJECT_DIR" >&2
  exit 1
fi

ABS_PROJECT="$(cd "$PROJECT_DIR" && pwd)"
PROJECT_NAME="$(basename "$ABS_PROJECT")"
DEFAULT_OUT="$(dirname "$ABS_PROJECT")/backups"
OUT_DIR="${2:-$DEFAULT_OUT}"

mkdir -p "$OUT_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="$OUT_DIR/${PROJECT_NAME}-${STAMP}.tar.gz"

tar -czf "$ARCHIVE" \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='.agents/worktrees' \
  --exclude='.claude/worktrees' \
  --exclude='.DS_Store' \
  -C "$(dirname "$ABS_PROJECT")" \
  "$PROJECT_NAME"

SIZE="$(du -h "$ARCHIVE" | awk '{print $1}')"
echo "Created backup: $ARCHIVE ($SIZE)"
