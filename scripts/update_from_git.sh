#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/licia/marrabbio"
REPO_URL="https://github.com/leandromacrini/Marrabbio.git"
REMOTE="remote"
BRANCH="master"

cd "$REPO_DIR"

# Ensure this is a git repository.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init
fi

# Ensure fixed remote exists and points to expected URL.
if git remote get-url "$REMOTE" >/dev/null 2>&1; then
  git remote set-url "$REMOTE" "$REPO_URL"
else
  git remote add "$REMOTE" "$REPO_URL"
fi

git fetch --prune "$REMOTE"
git checkout -B "$BRANCH" "$REMOTE/$BRANCH"
git pull --ff-only "$REMOTE" "$BRANCH"
