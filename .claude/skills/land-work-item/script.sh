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

# --- Project knobs ----------------------------------------------------------
# The only part of this script that knows which project it is landing in.
# Everything below the knobs works for any project on the context/ + changes/
# workflow framework; these values are what to change when pointing the skill
# at a different one. Each can also be overridden from the environment.
#
# BLOCKING_PROCESS: a process that holds the build output locked while it
#   runs. config-service/context/ENV_SCRIPTS.md documents that a running API
#   makes dotnet build/test fail with MSB3027 - a failure that looks like a
#   code defect in the gate output. Empty string disables the check.
BLOCKING_PROCESS="${LAND_BLOCKING_PROCESS-ConfigApi.Service}"
BLOCKING_PROCESS_STOP_HINT="${LAND_BLOCKING_PROCESS_STOP_HINT-powershell -NoProfile -Command \"Get-Process ConfigApi.Service -ErrorAction SilentlyContinue | Stop-Process -Force\"}"
# SOURCE_DIRS_RE: which changed paths count as "source" for doc-drift purposes.
SOURCE_DIRS_RE="${LAND_SOURCE_DIRS_RE-^(src|infra|ui)/}"
# API_SURFACE_RE / API_SPEC_FILE: paths whose change should move the committed
# API spec. ENV_SCRIPTS.md: openapi.json "goes stale silently - nothing checks it".
API_SURFACE_RE="${LAND_API_SURFACE_RE-(Controllers|Models)/}"
API_SPEC_FILE="${LAND_API_SPEC_FILE-openapi.json}"
API_SPEC_REGEN_HINT="${LAND_API_SPEC_REGEN_HINT-curl http://localhost:5038/openapi/v1.json -o openapi.json}"
# DIFF_MAX_LINES: cap on the unified diff included as acceptance evidence.
DIFF_MAX_LINES="${LAND_DIFF_MAX_LINES-400}"

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

wf_require_git
wf_locate_project "$PROJECT_DIR"

# --- Blocking processes -----------------------------------------------------
# Checked before the gate so the cause is printed above the symptom.
wf_section "BLOCKING PROCESSES"
if [ -z "$BLOCKING_PROCESS" ]; then
  echo "(check disabled - no BLOCKING_PROCESS configured)"
else
  proc_found=""
  if command -v tasklist >/dev/null 2>&1; then
    proc_found=$(tasklist 2>/dev/null | grep -i "$BLOCKING_PROCESS" || true)
  elif command -v pgrep >/dev/null 2>&1; then
    proc_found=$(pgrep -af "$BLOCKING_PROCESS" 2>/dev/null || true)
  elif command -v ps >/dev/null 2>&1; then
    proc_found=$(ps aux 2>/dev/null | grep -i "$BLOCKING_PROCESS" | grep -v grep || true)
  else
    proc_found="__unchecked__"
  fi
  if [ "$proc_found" = "__unchecked__" ]; then
    echo "(could not check - no tasklist, pgrep or ps available)"
  elif [ -n "$proc_found" ]; then
    printf '%s\n' "$proc_found"
    echo "WARNING: $BLOCKING_PROCESS is running. The build can fail with a locked"
    echo "output file (MSB3027 on .NET) for reasons unrelated to the code. Stop it:"
    echo "  $BLOCKING_PROCESS_STOP_HINT"
  else
    echo "(none)"
  fi
fi

# --- Quality gate -----------------------------------------------------------
wf_section "QUALITY GATE"
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
    grep -E 'Passed!|Failed!|Test Files|^ +Tests |Build succeeded|error' "$log" | tail -12
  else
    echo "result: FAIL ($((SECONDS - start))s) - last 40 lines:"
    # 40, not 20: dotnet build with warnings-as-errors puts its summary well
    # after the first diagnostic, and 20 lines regularly cut off the error.
    tail -n 40 "$log"
  fi
  rm -f "$log"
fi

wf_print_pointer
wf_print_work_item "$WORK_ITEM_ARG"
wf_print_task_status
wf_print_working_tree

# --- The change being landed ------------------------------------------------
# Scoped to the project with `-- .` and --relative, so paths are
# project-relative and unrelated repo changes do not pollute the report.
wf_section "DIFF STAT"
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

# --- The diff itself: the evidence the acceptance verdicts rest on ---------
# A stat line is a filename and a count; a Given-When-Then clause cannot be
# judged from that. Bounded so a large change does not swamp the report - the
# skill body says to read the full file when a truncation marker appears.
wf_section "DIFF"
if [ -z "$CHANGED" ]; then
  echo "(no uncommitted changes)"
else
  diff_all=$( { git diff --cached --relative -- . 2>/dev/null
                git diff --relative -- . 2>/dev/null
              } )
  untracked=$(git ls-files --others --exclude-standard -- . 2>/dev/null)
  if [ -n "$untracked" ]; then
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      case "$f" in */bin/*|*/obj/*|*/node_modules/*|*.dll|*.exe|*.pdb|*.png|*.jpg|*.lock) continue ;; esac
      diff_all="$diff_all"$'\n'"--- new file: $f ---"$'\n'"$(head -80 "$f" 2>/dev/null)"
      lines=$(wc -l < "$f" 2>/dev/null | tr -d ' ')
      [ "${lines:-0}" -gt 80 ] && diff_all="$diff_all"$'\n'"(new file truncated - $lines lines, showing the first 80)"
    done <<< "$untracked"
  fi
  total=$(printf '%s\n' "$diff_all" | wc -l | tr -d ' ')
  printf '%s\n' "$diff_all" | head -n "$DIFF_MAX_LINES"
  if [ "$total" -gt "$DIFF_MAX_LINES" ]; then
    echo "(diff truncated - $total lines, showing the first $DIFF_MAX_LINES;"
    echo " read the remaining files directly before giving a verdict)"
  fi
fi

# --- README review ----------------------------------------------------------
wf_section "README REVIEW"
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
wf_section "DOC DRIFT"
if [ -z "$CHANGED" ]; then
  echo "(no changed files)"
else
  ctx_changed=$(printf '%s\n' "$CHANGED" | grep '^context/' || true)
  src_changed=$(printf '%s\n' "$CHANGED" | grep -E "$SOURCE_DIRS_RE" || true)

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
  api_changed=$(printf '%s\n' "$CHANGED" | grep -E "$API_SURFACE_RE" || true)
  if [ -n "$api_changed" ]; then
    if printf '%s\n' "$CHANGED" | grep -qx "$API_SPEC_FILE"; then
      echo "api surface changed and $API_SPEC_FILE changed with it - ok"
    else
      echo "FLAG: api surface changed ($API_SURFACE_RE) but $API_SPEC_FILE did not."
      echo "It goes stale silently - nothing checks it. Regenerate with:"
      echo "  $API_SPEC_REGEN_HINT"
    fi
  else
    echo "(no api surface changes)"
  fi
fi

# --- Stage sections still present -------------------------------------------
wf_section "STAGE SECTIONS"
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
wf_section "COMMIT STYLE"
styles=$(git log -8 --format=%s 2>/dev/null)
if [ -n "$styles" ]; then
  printf '%s\n' "$styles"
  echo "(match these - plain descriptive subjects, not conventional-commit prefixes)"
else
  echo "(no commit history to sample)"
fi
