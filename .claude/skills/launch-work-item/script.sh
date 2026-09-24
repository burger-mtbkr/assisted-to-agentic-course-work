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

section() { printf '\n=== %s ===\n' "$1"; }

# --- Sanity: must be inside a git repo -------------------------------------
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  section "ERROR"
  echo "Not inside a git working tree. Run this from a checked-out repo."
  exit 0
fi
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

# --- BEGIN shared resolution block ------------------------------------------
# Deliberately duplicated in land-work-item/script.sh so each skill directory
# stays self-contained and independently installable. Keep the two in sync.

find_project_dir() {
  if [ -n "$PROJECT_DIR" ]; then
    if [ -f "$PROJECT_DIR/context/WORKFLOW_STATUS.md" ]; then
      echo "$PROJECT_DIR"; echo "(given by --project-dir)"
      return 0
    fi
    return 1
  fi

  # Walk up from the working directory.
  local dir; dir=$(pwd)
  while [ -n "$dir" ]; do
    if [ -f "$dir/context/WORKFLOW_STATUS.md" ]; then
      echo "$dir"; echo "(found by walking up from the working directory)"
      return 0
    fi
    [ "$dir" = "/" ] && break
    local parent; parent=$(dirname "$dir")
    [ "$parent" = "$dir" ] && break
    dir="$parent"
  done

  # Search the repo. modules/ is excluded on purpose: the course's curriculum
  # examples/ folders carry their own context/ trees, and orienting on
  # read-only reference material would be worse than failing.
  local hit
  hit=$(find "$REPO_ROOT" -maxdepth 3 -type f -name WORKFLOW_STATUS.md \
          -not -path "*/modules/*" \
          -not -path "*/node_modules/*" \
          -not -path "*/bin/*" -not -path "*/obj/*" 2>/dev/null | head -1)
  if [ -n "$hit" ]; then
    dirname "$(dirname "$hit")"
    echo "(found by searching the repo)"
    return 0
  fi
  return 1
}

resolve_work_item() {
  # $1 = project dir, $2 = pointer text. Echoes "path<TAB>how-resolved".
  local proj="$1" pointer="$2" path=""

  if [ -n "$WORK_ITEM_ARG" ]; then
    if [ -f "$proj/$WORK_ITEM_ARG" ]; then
      printf '%s\t%s\n' "$WORK_ITEM_ARG" "given by --work-item"; return 0
    fi
    if [ -f "$WORK_ITEM_ARG" ]; then
      printf '%s\t%s\n' "$WORK_ITEM_ARG" "given by --work-item"; return 0
    fi
    path=$(ls "$proj"/changes/"$WORK_ITEM_ARG"-*.md 2>/dev/null | head -1)
    if [ -n "$path" ]; then
      printf '%s\t%s\n' "changes/$(basename "$path")" "given by --work-item"; return 0
    fi
    printf '\t%s\n' "NOT FOUND - --work-item '$WORK_ITEM_ARG' matched no file"; return 0
  fi

  path=$(printf '%s' "$pointer" | grep -oE 'changes/[0-9]{3}-[A-Za-z0-9._-]+\.md' | head -1)
  if [ -n "$path" ] && [ -f "$proj/$path" ]; then
    printf '%s\t%s\n' "$path" "resolved from the pointer"; return 0
  fi

  path=$(ls "$proj"/changes/[0-9][0-9][0-9]-*.md 2>/dev/null | sort | tail -1)
  if [ -n "$path" ]; then
    printf '%s\t%s\n' "changes/$(basename "$path")" "fallback - pointer had no usable reference"; return 0
  fi

  printf '\t%s\n' "none - no work items yet"
}
# --- END shared resolution block --------------------------------------------

section "PROJECT"
PROJ_OUT=$(find_project_dir)
if [ -z "$PROJ_OUT" ]; then
  echo "(not found)"
  section "ERROR"
  echo "No context/WORKFLOW_STATUS.md found. Looked in: the working directory"
  echo "and its parents, then under $REPO_ROOT (max depth 3, excluding"
  echo "modules/, node_modules/, bin/, obj/)."
  echo "Pass --project-dir PATH to point at the project explicitly."
  exit 0
fi
PROJ=$(printf '%s' "$PROJ_OUT" | head -1)
echo "$PROJ_OUT"

cd "$PROJ" || { section "ERROR"; echo "Could not enter $PROJ"; exit 0; }

# --- Workflow pointer -------------------------------------------------------
section "WORKFLOW POINTER"
POINTER=$(sed -n '/^## Current Status/,$p' context/WORKFLOW_STATUS.md 2>/dev/null \
          | awk 'NR==1 {print; next} /^## / {exit} {print}')
if [ -n "$POINTER" ]; then
  printf '%s\n' "$POINTER"
else
  echo "(no '## Current Status' section in context/WORKFLOW_STATUS.md)"
fi

# --- Work item --------------------------------------------------------------
section "WORK ITEM"
RESOLVED=$(resolve_work_item "$PROJ" "$POINTER")
WORK_ITEM=$(printf '%s' "$RESOLVED" | cut -f1)
HOW=$(printf '%s' "$RESOLVED" | cut -f2)
if [ -z "$WORK_ITEM" ]; then
  echo "path: (unresolved - $HOW)"
  if ls changes/[0-9][0-9][0-9]-*.md >/dev/null 2>&1; then
    echo "work items that do exist:"
    ls changes/[0-9][0-9][0-9]-*.md | sed 's/^/  /'
  else
    echo "(no work items yet - copy changes/template.md to start one)"
  fi
else
  echo "path: $WORK_ITEM ($HOW)"
  echo "--- contents ---"
  cat "$WORK_ITEM"
fi

# --- Task status roll-up ----------------------------------------------------
section "TASK STATUS"
if [ -z "$WORK_ITEM" ]; then
  echo "(no work item to roll up)"
else
  n_done=$(grep -cE '^\s*-?\s*\*\*Status\*\*:\s*Complete' "$WORK_ITEM" 2>/dev/null || true)
  n_prog=$(grep -cE '^\s*-?\s*\*\*Status\*\*:\s*In Progress' "$WORK_ITEM" 2>/dev/null || true)
  n_todo=$(grep -cE '^\s*-?\s*\*\*Status\*\*:\s*Not Started' "$WORK_ITEM" 2>/dev/null || true)
  echo "Complete: ${n_done:-0}, In Progress: ${n_prog:-0}, Not Started: ${n_todo:-0}"
  echo "--- tasks in file order ---"
  awk '
    /^#### / { task = $0; sub(/^#### /, "", task); next }
    /\*\*Status\*\*:/ {
      status = $0
      sub(/^.*\*\*Status\*\*:[ \t]*/, "", status)
      if (task != "") { printf "  %s -> %s\n", task, status; task = "" }
    }
  ' "$WORK_ITEM"
  grep -qE '^#### ' "$WORK_ITEM" || echo "  (no '#### Task N' headings found)"
fi

# --- Git trajectory ---------------------------------------------------------
section "WORK ITEM HISTORY"
if [ -z "$WORK_ITEM" ]; then
  echo "(no work item to trace)"
else
  hist=$(git log --oneline --follow -- "$WORK_ITEM" 2>/dev/null)
  if [ -n "$hist" ]; then printf '%s\n' "$hist"; else echo "(not committed yet)"; fi
fi

# All git queries below are scoped to the project directory (`-- .`) and use
# --relative, so paths come back relative to the project rather than the repo
# root. Without that, per-file history silently returns nothing for every file
# whenever the project is a subdirectory of the repo.
section "RECENT COMMITS"
commits=$(git log --oneline -10 -- . 2>/dev/null)
if [ -n "$commits" ]; then
  printf '%s\n' "$commits"
  echo "(the last 10 commits touching this project, not the whole repo)"
else
  echo "(no commit history for this project)"
fi

section "FILES TOUCHED"
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

section "PER-FILE HISTORY"
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

# --- Working tree -----------------------------------------------------------
section "WORKING TREE"
# git status ignores --relative even with a pathspec, so strip the project
# prefix by hand to keep every section's paths project-relative.
PROJ_REL=$(git rev-parse --show-prefix 2>/dev/null)
tree_state=$(git status --porcelain --untracked-files=normal -- . 2>/dev/null |
             sed "s|^\(...\)${PROJ_REL}|\1|")
if [ -n "$tree_state" ]; then
  printf '%s\n' "$tree_state"
  echo "(uncommitted changes inside this project only)"
else
  echo "(clean)"
fi

# --- Open TODOs -------------------------------------------------------------
section "OPEN TODOS"
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
section "CONTEXT DOCS"
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
section "DOCUMENTED SCRIPTS"
if [ -f package.json ] && command -v npm >/dev/null 2>&1; then
  npm pkg get scripts 2>/dev/null | sed 's/^/  /' || echo "  (could not read package.json scripts)"
elif [ -f context/ENV_SCRIPTS.md ]; then
  grep -oE 'npm run [a-z:]+' context/ENV_SCRIPTS.md 2>/dev/null | sort -u | sed 's/^/  /' \
    || echo "  (no npm run commands documented)"
else
  echo "  (no package.json and no context/ENV_SCRIPTS.md)"
fi

# --- Optional quality gate --------------------------------------------------
section "QUALITY GATE"
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
    echo "result: FAIL ($((SECONDS - start))s) - last 20 lines:"
    tail -n 20 "$log"
  fi
  rm -f "$log"
fi
