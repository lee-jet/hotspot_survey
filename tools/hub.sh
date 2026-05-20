#!/usr/bin/env bash
# hub.sh — orchestrate generate / merge / ship in one command.
#
# Usage:
#   bash tools/hub.sh <URL> [<URL2> …] [flags]   # generate + merge + ship
#   bash tools/hub.sh                            # just merge + ship (after manual edits)
#
# Flags:
#   -y, --yes              Skip the confirmation prompt before push
#       --no-push          Stop after merge; do not commit or push
#       --no-merge         Stop after generate; useful with multiple URLs you want to review one-by-one
#       --no-llm           Scaffold mode (skip claude -p, write TODOs)
#       --draft            Mark new reports as hub:status=draft (excluded from index)
#       --overwrite        Replace existing reports with the same slug
#       --order N          Pass --order N to generate.py (sort position)
#       --message MSG      Pass MSG to ship.sh as commit message
#   -h, --help             Show this help
#
# Examples:
#   # Add one tool end-to-end
#   bash tools/hub.sh https://github.com/owner/tool
#
#   # Batch: 3 tools, one commit, one push
#   bash tools/hub.sh \
#       https://github.com/o1/a \
#       https://github.com/o2/b \
#       https://github.com/o3/c \
#       --yes
#
#   # Generate as drafts, review manually, no push
#   bash tools/hub.sh https://github.com/owner/tool --draft --no-push
#
#   # Resync after manual report edit
#   bash tools/hub.sh

set -euo pipefail

cd "$(dirname "$0")/.."

# ── ANSI ──
if [[ -t 1 ]]; then
  BOLD=$'\033[1m'; DIM=$'\033[2m'
  GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'; CYAN=$'\033[36m'
  RESET=$'\033[0m'
else
  BOLD=""; DIM=""; GREEN=""; RED=""; YELLOW=""; CYAN=""; RESET=""
fi

usage() { sed -n '3,30p' "$0" | sed 's/^# \{0,1\}//'; }

# ── parse args ──
URLS=()
YES=0
NO_PUSH=0
NO_MERGE=0
GEN_ARGS=()
SHIP_MSG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes) YES=1; shift;;
    --no-push) NO_PUSH=1; shift;;
    --no-merge) NO_MERGE=1; shift;;
    --no-llm) GEN_ARGS+=("--no-llm"); shift;;
    --draft) GEN_ARGS+=("--draft"); shift;;
    --overwrite) GEN_ARGS+=("--overwrite"); shift;;
    --order) GEN_ARGS+=("--order" "$2"); shift 2;;
    --message|-m) SHIP_MSG="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    --*) echo "${RED}Unknown flag: $1${RESET}" >&2; usage; exit 2;;
    *)
      if [[ "$1" =~ ^https?://github.com/ ]]; then
        URLS+=("$1")
      else
        echo "${RED}Not a github.com URL: $1${RESET}" >&2; exit 2
      fi
      shift;;
  esac
done

step() { echo; echo "${BOLD}${CYAN}══ $* ══${RESET}"; }
ok()   { echo "${GREEN}✓${RESET} $*"; }
warn() { echo "${YELLOW}⚠${RESET}  $*"; }
fail() { echo "${RED}✗${RESET} $*" >&2; }

START_TS=$(date +%s)

# ── Phase 1: generate (per URL) ──
if [[ ${#URLS[@]} -gt 0 ]]; then
  for url in "${URLS[@]}"; do
    step "Step 1 · generate  ${DIM}${url}${RESET}"
    if ! python3 tools/generate.py "$url" "${GEN_ARGS[@]}"; then
      fail "generate.py failed for $url"
      exit 1
    fi
  done
else
  warn "No URL given — skipping generate, going straight to merge."
fi

if [[ $NO_MERGE -eq 1 ]]; then
  step "Stopping after generate (--no-merge)"
  echo "Next: review reports/*.html then run 'bash tools/hub.sh' to merge + ship."
  exit 0
fi

# ── Phase 2: lint ──
step "Step 2a · lint quality gate"
if ! python3 tools/merge.py --lint; then
  fail "Lint failed. Fix the report(s) above, then re-run."
  exit 1
fi

# ── Phase 3: merge ──
step "Step 2b · merge into index.html"
python3 tools/merge.py

# ── Review window ──
PENDING=$(git status -s)
if [[ -z "$PENDING" ]]; then
  step "Nothing to ship — working tree clean."
  exit 0
fi

step "Pending changes"
echo "$PENDING"
echo
DIFFSTAT=$(git diff --stat 2>/dev/null || true)
[[ -n "$DIFFSTAT" ]] && echo "${DIM}$DIFFSTAT${RESET}"

if [[ $NO_PUSH -eq 1 ]]; then
  step "Stopping before push (--no-push)"
  echo "Next: 'bash tools/ship.sh' when ready, or 'bash tools/hub.sh' to retry."
  exit 0
fi

# ── Phase 4: confirm ──
if [[ $YES -eq 0 ]]; then
  echo
  read -r -p "${BOLD}Proceed to commit + push? [y/N]${RESET} " ans
  case "${ans,,}" in
    y|yes) ;;
    *) warn "Aborted before push. Local changes preserved."; exit 0;;
  esac
fi

# ── Phase 5: ship ──
step "Step 3 · commit + push"
if [[ -n "$SHIP_MSG" ]]; then
  bash tools/ship.sh "$SHIP_MSG"
else
  bash tools/ship.sh
fi

ELAPSED=$(( $(date +%s) - START_TS ))
step "${GREEN}Done in ${ELAPSED}s${RESET}"
remote_url=$(git remote get-url origin 2>/dev/null || echo "origin")
echo "Watch:  https://github.com/${remote_url#git@github.com:}/actions"
echo "        https://github.com/${remote_url#git@github.com:}/actions" | sed 's|\.git/actions|/actions|'
