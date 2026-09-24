#!/usr/bin/env bash
# launch-work-item skill - grounding script.
#
# Gathers the deterministic facts a launch brief needs: the workflow pointer,
# the resolved work item, the git trajectory behind it, and the state of the
# tree. Output is sectioned plain text on stdout.
#
# Read-only, except for the optional --with-check gate run. Exits 0 on every
# expected condition, including errors - the LLM needs to see the reason, and
# a non-zero exit would surface as a tool failure instead of a finding.
#
# Usage: script.sh [--project-dir PATH] [--work-item PATH|NNN] [--with-check]

set -uo pipefail

# Shared resolution helpers (project, pointer, work item, task status, tree).
LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_lib/workflow.sh"
if [ ! -f "$LIB" ]; then
  printf '\n=== ERROR ===\n'
  echo "Missing $LIB"
  echo "This skill needs the sibling .claude/skills/_lib/ directory. Copy it"
  echo "alongside the skill when installing into another harness."
  exit 0
fi
# shellcheck source=../_lib/workflow.sh
. "$LIB"

PROJECT_DIR=""
WORK_ITEM_ARG=""
WITH_CHECK=0

while [ $# -gt 0 ]; do
  case "$1" in
    --project-dir) PROJECT_DIR="${2:-}"; shift 2 ;;
    --work-item)   WORK_ITEM_ARG="${2:-}"; shift 2 ;;
    --with-check)  WITH_CHECK=1; shift ;;
    -h|--help)
      sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *)
      printf '\n=== ERROR ===\n'
      echo "Unknown argument: $1"
      echo "Usage: script.sh [--project-dir PATH] [--work-item PATH|NNN] [--with-check]"
      exit 0 ;;
  esac
done

wf_require_git
wf_locate_project "$PROJECT_DIR"
wf_print_pointer
wf_print_work_item "$WORK_ITEM_ARG"
wf_print_task_status

# --- Git trajectory ---------------------------------------------------------
# All git queries are scoped to the project directory (`-- .`) and use
# --relative, so paths come back relative to the project rather than the repo
# root. Without that, per-file history silently returns nothing for every
# file whenever the project is a subdirectory of the repo.
wf_section "WORK ITEM HISTORY"
if [ -z "$WORK_ITEM" ]; then
  echo "(no work item to trace)"
else
  hist=$(git log --oneline --follow -- "$WORK_ITEM" 2>/dev/null)
  if [ -n "$hist" ]; then printf '%s\n' "$hist"; else echo "(not committed yet)"; fi
fi

wf_section "RECENT COMMITS"
commits=$(git log --oneline -10 -- . 2>/dev/null)
if [ -n "$commits" ]; then
  printf '%s\n' "$commits"
  echo "(the last 10 commits touching this project, not the whole repo)"
else
  echo "(no commit history for this project)"
fi

wf_section "FILES TOUCHED"
TOUCHED=""
if [ -n "$commits" ]; then
  TOUCHED=$(git log -10 --name-only --relative --format= -- . 2>/dev/null | sed '/^$/d' | sort -u)
fi
TOUCHED_TOTAL=0
if [ -n "$TOUCHED" ]; then
  TOUCHED_TOTAL=$(printf '%s\n' "$TOUCHED" | wc -l | tr -d ' ')
  printf '%s\n' "$TOUCHED" | head -60
  [ "$TOUCHED_TOTAL" -gt 60 ] && echo "(truncated - $TOUCHED_TOTAL files, showing the first 60)"
else
  echo "(no files changed in the last 10 commits)"
fi

wf_section "PER-FILE HISTORY"
if [ -z "$TOUCHED" ]; then
  echo "(no files to report on)"
else
  shown=0
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    if [ "$shown" -ge 25 ]; then
      echo "(truncated - $TOUCHED_TOTAL files touched, showing the first 25)"
      break
    fi
    echo "--- $f ---"
    fh=$(git log --oneline -5 -- "$f" 2>/dev/null)
    if [ -n "$fh" ]; then printf '%s\n' "$fh"; else echo "  (no history)"; fi
    shown=$((shown + 1))
  done <<< "$TOUCHED"
fi

wf_print_working_tree

# --- Open TODOs -------------------------------------------------------------
wf_section "OPEN TODOS"
if [ -z "$TOUCHED" ]; then
  echo "(nothing to grep)"
else
  found=0
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    case "$f" in */bin/*|*/obj/*|*/node_modules/*|*.dll|*.exe|*.pdb) continue ;; esac
    m=$(grep -nE 'TODO|FIXME|HACK' "$f" 2>/dev/null | head -10)
    if [ -n "$m" ]; then echo "--- $f ---"; printf '%s\n' "$m"; found=1; fi
  done <<< "$TOUCHED"
  [ "$found" -eq 0 ] && echo "(none found)"
fi

# --- Context doc freshness --------------------------------------------------
wf_section "CONTEXT DOCS"
if [ -d context ]; then
  for f in context/*.md; do
    [ -f "$f" ] || continue
    d=$(git log -1 --format=%ad --date=short -- "$f" 2>/dev/null)
    echo "$f - ${d:-uncommitted}"
  done
else
  echo "(no context/ directory)"
fi

# --- Documented scripts -----------------------------------------------------
wf_section "DOCUMENTED SCRIPTS"
if [ -f package.json ] && command -v npm >/dev/null 2>&1; then
  npm pkg get scripts 2>/dev/null | sed 's/^/  /' || echo "  (could not read package.json scripts)"
elif [ -f context/ENV_SCRIPTS.md ]; then
  grep -oE 'npm run [a-z:]+' context/ENV_SCRIPTS.md 2>/dev/null | sort -u | sed 's/^/  /' \
    || echo "  (no npm run commands documented)"
else
  echo "  (no package.json and no context/ENV_SCRIPTS.md)"
fi

# --- Optional quality gate --------------------------------------------------
wf_section "QUALITY GATE"
if [ "$WITH_CHECK" -eq 0 ]; then
  echo "(not run - pass --with-check to include it)"
elif ! command -v npm >/dev/null 2>&1; then
  echo "(npm not found - cannot run the gate)"
elif [ ! -f package.json ] || ! grep -q '"check"' package.json; then
  echo "(no 'check' script in package.json - see context/ENV_SCRIPTS.md)"
else
  log=$(mktemp)
  echo "command: npm run check"
  start=$SECONDS
  if npm run check >"$log" 2>&1; then
    echo "result: PASS ($((SECONDS - start))s)"
  else
    echo "result: FAIL ($((SECONDS - start))s) - last 40 lines:"
    tail -n 40 "$log"
  fi
  rm -f "$log"
fi
