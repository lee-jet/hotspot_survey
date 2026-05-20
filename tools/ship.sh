#!/usr/bin/env bash
# Stage, commit, push the research hub.
#
# Usage:
#   bash tools/ship.sh                       # auto-generated commit message
#   bash tools/ship.sh "feat: add ralph"     # custom commit message
#   bash tools/ship.sh --dry-run             # show what would be done, no push
#
# Only stages index.html, reports/, assets/, README.md to avoid accidentally
# committing the trash/ folder or untracked experiments.

set -euo pipefail

cd "$(dirname "$0")/.."

DRY_RUN=0
MSG=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -*) echo "Unknown flag: $arg" >&2; exit 2 ;;
    *) MSG="$arg" ;;
  esac
done

# Pre-flight: confirm we're on a git repo with a remote
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "ERROR: not inside a git repo" >&2
  exit 1
fi
if ! git remote get-url origin >/dev/null 2>&1; then
  echo "ERROR: no 'origin' remote configured" >&2
  exit 1
fi

# Stage only the allow-listed paths
git add -A index.html reports/ assets/ README.md _redirects _headers robots.txt .nojekyll .github/ 2>/dev/null || true

# Anything to commit?
if git diff --cached --quiet; then
  echo "= Nothing to ship — index.html, reports/, assets/ are unchanged."
  exit 0
fi

# Derive a sensible commit message if not given
if [[ -z "$MSG" ]]; then
  changed_reports=$(git diff --cached --name-only -- reports/ \
                    | /usr/bin/sed 's|reports/||; s|\.html$||' \
                    | /usr/bin/paste -sd ',' -)
  index_changed=$(git diff --cached --name-only -- index.html)
  parts=()
  [[ -n "$changed_reports" ]] && parts+=("reports: $changed_reports")
  [[ -n "$index_changed" ]] && parts+=("merge index")
  if [[ ${#parts[@]} -eq 0 ]]; then
    MSG="chore: misc updates"
  else
    MSG="update: $(IFS='; '; echo "${parts[*]}")"
  fi
fi

echo "── Staged changes ──"
git diff --cached --stat
echo
echo "── Commit message ──"
echo "$MSG"
echo

if [[ $DRY_RUN -eq 1 ]]; then
  echo "(--dry-run) would commit and push to: $(git remote get-url origin)"
  echo "(--dry-run) restoring index (unstaging)"
  git reset HEAD -- . >/dev/null
  exit 0
fi

git commit -m "$MSG"

branch=$(git branch --show-current)
echo "→ Pushing $branch to origin"
git push origin "$branch"
echo "✓ Shipped."
