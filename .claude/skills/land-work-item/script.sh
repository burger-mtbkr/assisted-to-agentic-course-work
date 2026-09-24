#!/usr/bin/env bash
# land-work-item skill - grounding script.
#
# Runs the project's quality gate for real and collects everything the closing
# process needs to judge: the uncommitted diff, the folders and READMEs it
# touches, the docs that did not move with it, the stage notes still sitting in
# the work item, and a sample of the repo's commit style.
#
# Order matters: blocking-process check, then the gate, then everything else.
# A red gate short-circuits the report the skill writes.
#
# Exits 0 on every expected condition, including errors and a failing gate -
# those are findings for the LLM to report, not tool failures.
#
# Usage: script.sh [--project-dir PATH] [--work-item PATH|NNN] [--skip-check]

set -uo pipefail

PROJECT_DIR=""
WORK_ITEM_ARG=""
SKIP_CHECK=0

while [ $# -gt 0 ]; do
  case "$1" in
    --project-dir) PROJECT_DIR="${2:-}"; shift 2 ;;
    --work-item)   WORK_ITEM_ARG="${2:-}"; shift 2 ;;
    --skip-check)  SKIP_CHECK=1; shift ;;
    -h|--help)
      sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *)
      printf '\n=== ERROR ===\n'
      echo "Unknown argument: $1"
      echo "Usage: script.sh [--project-dir PATH] [--work-item PATH|NNN] [--skip-check]"
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
# Deliberately duplicated from launch-work-item/script.sh so each skill
# directory stays self-contained and independently installable. Keep in sync.

find_project_dir() {
  if [ -n "$PROJECT_DIR" ]; then
    if [ -f "$PROJECT_DIR/context/WORKFLOW_STATUS.md" ]; then
      echo "$PROJECT_DIR"; echo "(given by --project-dir)"
      return 0
    fi
    return 1
  fi

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

  # modules/ is excluded on purpose: the course's curriculum examples/ folders
  # carry their own context/ trees, and landing against read-only reference
  # material would be worse than failing.
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

# --- Blocking processes -----------------------------------------------------
# context/ENV_SCRIPTS.md documents this: a running ConfigApi.Service locks the
# build output and dotnet build/test fails with MSB3027. That looks like a code
# failure in the gate output, which is the worst kind of misleading evidence to
# lead a landing report with - so it is checked first.
section "BLOCKING PROCESSES"
proc_found=""
if command -v tasklist >/dev/null 2>&1; then
  proc_found=$(tasklist 2>/dev/null | grep -i "ConfigApi.Service" || true)
elif command -v pgrep >/dev/null 2>&1; then
  proc_found=$(pgrep -af "ConfigApi.Service" 2>/dev/null || true)
elif command -v ps >/dev/null 2>&1; then
  proc_found=$(ps aux 2>/dev/null | grep -i "[C]onfigApi.Service" || true)
else
  proc_found="__unchecked__"
fi
if [ "$proc_found" = "__unchecked__" ]; then
  echo "(could not check - no tasklist, pgrep or ps available)"
elif [ -n "$proc_found" ]; then
  printf '%s\n' "$proc_found"
  echo "WARNING: the API is running. dotnet build/test can fail with MSB3027"
  echo "(locked .exe) for reasons unrelated to the code. Stop it with:"
  echo "  powershell -NoProfile -Command \"Get-Process ConfigApi.Service -ErrorAction SilentlyContinue | Stop-Process -Force\""
else
  echo "(none)"
fi

# --- Quality gate -----------------------------------------------------------
section "QUALITY GATE"
if [ "$SKIP_CHECK" -eq 1 ]; then
  echo "result: SKIPPED (--skip-check was passed - this landing is UNVERIFIED)"
elif ! command -v npm >/dev/null 2>&1; then
  echo "result: (npm not found - cannot run the gate)"
elif [ ! -f package.json ] || ! grep -q '"check"' package.json; then
  echo "result: (no 'check' script in package.json - see context/ENV_SCRIPTS.md)"
else
  gate_cmd=$(node -e "process.stdout.write(require('./package.json').scripts.check||'')" 2>/dev/null)
  echo "command: npm run check"
  [ -n "$gate_cmd" ] && echo "expands to: $gate_cmd"
  log=$(mktemp)
  start=$SECONDS
  if npm run check >"$log" 2>&1; then
    echo "result: PASS ($((SECONDS - start))s)"
    echo "--- summary lines ---"
    grep -iE 'Passed!|passed|Test summary|Build succeeded|✓|Tests:' "$log" | tail -12
  else
    echo "result: FAIL ($((SECONDS - start))s) - last 40 lines:"
    # 40, not 20: dotnet build with warnings-as-errors puts its summary well
    # after the first diagnostic, and 20 lines regularly cut off the error.
    tail -n 40 "$log"
  fi
  rm -f "$log"
fi

# --- Workflow pointer and work item -----------------------------------------
section "WORKFLOW POINTER"
POINTER=$(sed -n '/^## Current Status/,$p' context/WORKFLOW_STATUS.md 2>/dev/null \
          | awk 'NR==1 {print; next} /^## / {exit} {print}')
if [ -n "$POINTER" ]; then
  printf '%s\n' "$POINTER"
else
  echo "(no '## Current Status' section in context/WORKFLOW_STATUS.md)"
fi

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

# --- The change being landed ------------------------------------------------
# Scoped to the project with `-- .` and --relative, so paths are
# project-relative and unrelated repo changes do not pollute the report.
section "WORKING TREE"
# git status ignores --relative even with a pathspec, so strip the project
# prefix by hand to keep every section's paths project-relative.
PROJ_REL=$(git rev-parse --show-prefix 2>/dev/null)
PORCELAIN=$(git status --porcelain --untracked-files=normal -- . 2>/dev/null |
            sed "s|^\(...\)${PROJ_REL}|\1|")
if [ -n "$PORCELAIN" ]; then
  printf '%s\n' "$PORCELAIN"
else
  echo "(clean - nothing uncommitted in this project)"
fi

section "DIFF STAT"
d_work=$(git diff --stat --relative -- . 2>/dev/null)
d_stage=$(git diff --cached --stat --relative -- . 2>/dev/null)
if [ -z "$d_work" ] && [ -z "$d_stage" ]; then
  echo "(no uncommitted changes)"
else
  if [ -n "$d_stage" ]; then echo "--- staged ---"; printf '%s\n' "$d_stage"; fi
  if [ -n "$d_work" ];  then echo "--- unstaged ---"; printf '%s\n' "$d_work"; fi
fi

# Changed paths, project-relative, tracked and untracked alike.
CHANGED=$( { git diff --name-only --relative -- . 2>/dev/null
             git diff --cached --name-only --relative -- . 2>/dev/null
             git ls-files --others --exclude-standard -- . 2>/dev/null
           } | sed '/^$/d' | sort -u )

# --- README review ----------------------------------------------------------
section "README REVIEW"
if [ -z "$CHANGED" ]; then
  echo "(no changed files to review)"
else
  FOLDERS=$(printf '%s\n' "$CHANGED" | xargs -I{} dirname {} 2>/dev/null | sort -u)
  while IFS= read -r folder; do
    [ -z "$folder" ] && continue
    if [ -f "$folder/README.md" ]; then
      if printf '%s\n' "$CHANGED" | grep -qx "$folder/README.md"; then
        echo "$folder - README: yes, changed: yes"
      else
        echo "$folder - README: yes, changed: NO (review it)"
      fi
    else
      echo "$folder - README: no"
    fi
  done <<< "$FOLDERS"
fi

# --- Doc drift --------------------------------------------------------------
section "DOC DRIFT"
if [ -z "$CHANGED" ]; then
  echo "(no changed files)"
else
  ctx_changed=$(printf '%s\n' "$CHANGED" | grep '^context/' || true)
  src_changed=$(printf '%s\n' "$CHANGED" | grep -E '^(src|infra|ui)/' || true)

  echo "--- context docs changed ---"
  if [ -n "$ctx_changed" ]; then printf '%s\n' "$ctx_changed"; else echo "(none)"; fi

  echo "--- source paths changed ---"
  if [ -n "$src_changed" ]; then printf '%s\n' "$src_changed" | head -30; else echo "(none)"; fi

  echo "--- context docs NOT changed ---"
  if [ -d context ]; then
    for f in context/*.md; do
      [ -f "$f" ] || continue
      printf '%s\n' "$CHANGED" | grep -qx "$f" || echo "$f"
    done
  else
    echo "(no context/ directory)"
  fi

  echo "--- api surface ---"
  api_changed=$(printf '%s\n' "$CHANGED" | grep -E '(Controllers|Models)/' || true)
  if [ -n "$api_changed" ]; then
    if printf '%s\n' "$CHANGED" | grep -qx 'openapi.json'; then
      echo "controllers/models changed and openapi.json changed with them - ok"
    else
      echo "FLAG: controllers/models changed but openapi.json did not."
      echo "context/ENV_SCRIPTS.md: it goes stale silently - nothing checks it."
      echo "Regenerate with the API running:"
      echo "  curl http://localhost:5038/openapi/v1.json -o openapi.json"
    fi
  else
    echo "(no controller or model changes)"
  fi
fi

# --- Stage sections still present -------------------------------------------
section "STAGE SECTIONS"
if [ -z "$WORK_ITEM" ]; then
  echo "(no work item to check)"
else
  stages=$(grep -nE '^### STAGE' "$WORK_ITEM" 2>/dev/null || true)
  if [ -n "$stages" ]; then
    printf '%s\n' "$stages"
    echo "(these are the sections the purge step deletes once the task is committed)"
  else
    echo "(none - already purged)"
  fi
fi

# --- Commit style sample ----------------------------------------------------
section "COMMIT STYLE"
styles=$(git log -8 --format=%s 2>/dev/null)
if [ -n "$styles" ]; then
  printf '%s\n' "$styles"
  echo "(match these - plain descriptive subjects, not conventional-commit prefixes)"
else
  echo "(no commit history to sample)"
fi
