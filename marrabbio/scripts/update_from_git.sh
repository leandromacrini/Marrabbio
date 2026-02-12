#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/licia/marrabbio"
REMOTE="${1:-origin}"
BRANCH="${2:-master}"

cd "$REPO_DIR"

# Ensure this is a git repository and remote exists.
git rev-parse --is-inside-work-tree >/dev/null
git remote get-url "$REMOTE" >/dev/null

git fetch --prune "$REMOTE"
git pull --ff-only "$REMOTE" "$BRANCH"

