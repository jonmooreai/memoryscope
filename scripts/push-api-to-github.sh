#!/usr/bin/env bash
# Push only the API (no website) to GitHub, replacing existing repo content.
# Ensures no .env or secrets are included.
set -e

REPO_URL="${1:-https://github.com/jonmooreai/memoryscope.git}"
SRCDIR="$(cd "$(dirname "$0")/.." && pwd)"
DESTDIR="${TMPDIR:-/tmp}/memoryscope-api-$$"

echo "Source: $SRCDIR"
echo "Target repo: $REPO_URL"
echo "Building API-only tree in $DESTDIR"
echo ""

rm -rf "$DESTDIR"
mkdir -p "$DESTDIR"

rsync -a \
  --exclude='.git' \
  --exclude='website' \
  --exclude='demo' \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='*.backup' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='node_modules' \
  --exclude='*.pyc' \
  --exclude='*-firebase-adminsdk-*.json' \
  --exclude='firebase-adminsdk-*.json' \
  --exclude='test_app/test_api_key.json' \
  --exclude='.DS_Store' \
  --exclude='.cursor' \
  "$SRCDIR/" "$DESTDIR/"

cd "$DESTDIR"
git init
git add .
git status

if ! git diff --cached --quiet; then
  git commit -m "MemoryScope API - backend only"
  git branch -M main
  git remote add origin "$REPO_URL"
  echo ""
  echo "Pushing to $REPO_URL (this will replace existing content)..."
  if git push -f origin main; then
    echo ""
    echo "Done. API-only code is now at $REPO_URL"
    rm -rf "$DESTDIR"
  else
    echo ""
    echo "Push failed (often due to auth). To push manually, run:"
    echo "  cd $DESTDIR && git push -f origin main"
    echo "Then remove the temp dir: rm -rf $DESTDIR"
  fi
else
  echo "Nothing to commit (no changes)."
  rm -rf "$DESTDIR"
fi
