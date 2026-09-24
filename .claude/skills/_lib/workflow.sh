#!/usr/bin/env bash
# Shared grounding helpers for the launch-work-item / land-work-item skill
# pair. Sourced by each skill's script.sh; not a skill itself (no SKILL.md).
#
# Everything here is about resolving "which project, which work item, which
# task" in a project that follows the context/ + changes/ workflow framework
# (see config-service/context/WORKFLOW_STATUS.md). Nothing here is
# project-specific - project knobs live at the top of each script.sh.
#
# Functions print their own === SECTION === block and set globals the caller
# reads afterwards: PROJ, POINTER, WORK_ITEM. All of them exit 0 on expected
# failure conditions after printing an === ERROR === block, because the
# consumer is a language model that needs the reason, not a non-zero exit.
#
# The scripts that source this expect to find it at ../_lib/workflow.sh
# relative to their own directory. Installing one skill without the other is
# fine; installing either without _lib/ is not, and the script says so.

wf_section() { printf '\n=== %s ===\n' "$1"; }

# --- Must be inside a git repo. Sets REPO_ROOT. --------------------------
wf_require_git() {
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    wf_section "ERROR"
    echo "Not inside a git working tree. Run this from a checked-out repo."
    exit 0
  fi
  REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
}

# --- Locate the project. Prints PROJECT, cds into it, sets PROJ. ----------
# $1 = explicit --project-dir (may be empty).
wf_locate_project() {
  local explicit="$1" found=""

  if [ -n "$explicit" ]; then
    if [ -f "$explicit/context/WORKFLOW_STATUS.md" ]; then
      found="$explicit"; how="(given by --project-dir)"
    fi
  else
    # Walk up from the working directory.
    local dir; dir=$(pwd)
    while [ -n "$dir" ]; do
      if [ -f "$dir/context/WORKFLOW_STATUS.md" ]; then
        found="$dir"; how="(found by walking up from the working directory)"; break
      fi
      [ "$dir" = "/" ] && break
      local parent; parent=$(dirname "$dir")
      [ "$parent" = "$dir" ] && break
      dir="$parent"
    done

    # Search the repo. modules/ is excluded on purpose: the course's
    # curriculum examples/ folders carry their own context/ trees, and
    # orienting on read-only reference material would be worse than failing.
    if [ -z "$found" ]; then
      local hit
      hit=$(find "$REPO_ROOT" -maxdepth 3 -type f -name WORKFLOW_STATUS.md \
              -not -path "*/modules/*" \
              -not -path "*/node_modules/*" \
              -not -path "*/bin/*" -not -path "*/obj/*" 2>/dev/null | head -1)
      if [ -n "$hit" ]; then
        found=$(dirname "$(dirname "$hit")"); how="(found by searching the repo)"
      fi
    fi
  fi

  wf_section "PROJECT"
  if [ -z "$found" ]; then
    echo "(not found)"
    wf_section "ERROR"
    echo "No context/WORKFLOW_STATUS.md found. Looked in: the working directory"
    echo "and its parents, then under $REPO_ROOT (max depth 3, excluding"
    echo "modules/, node_modules/, bin/, obj/)."
    echo "Pass --project-dir PATH to point at the project explicitly."
    exit 0
  fi
  echo "$found"
  echo "$how"
  PROJ="$found"
  cd "$PROJ" || { wf_section "ERROR"; echo "Could not enter $PROJ"; exit 0; }
}

# --- Print the ## Current Status block. Sets POINTER. ---------------------
wf_print_pointer() {
  wf_section "WORKFLOW POINTER"
  POINTER=$(sed -n '/^## Current Status/,$p' context/WORKFLOW_STATUS.md 2>/dev/null \
            | awk 'NR==1 {print; next} /^## / {exit} {print}')
  if [ -n "$POINTER" ]; then
    printf '%s\n' "$POINTER"
  else
    echo "(no '## Current Status' section in context/WORKFLOW_STATUS.md)"
  fi
}

# --- Resolve and print the work item. Sets WORK_ITEM (may be empty). -------
# $1 = explicit --work-item (path or NNN, may be empty). Uses POINTER.
wf_print_work_item() {
  local arg="$1" path="" how=""

  if [ -n "$arg" ]; then
    if [ -f "$arg" ]; then
      path="$arg"; how="given by --work-item"
    else
      path=$(ls changes/"$arg"-*.md 2>/dev/null | head -1)
      if [ -n "$path" ]; then how="given by --work-item"
      else how="NOT FOUND - --work-item '$arg' matched no file"; fi
    fi
  else
    path=$(printf '%s' "$POINTER" | grep -oE 'changes/[0-9]{3}-[A-Za-z0-9._-]+\.md' | head -1)
    if [ -n "$path" ] && [ -f "$path" ]; then
      how="resolved from the pointer"
    else
      path=$(ls changes/[0-9][0-9][0-9]-*.md 2>/dev/null | sort | tail -1)
      if [ -n "$path" ]; then how="fallback - pointer had no usable reference"
      else how="none - no work items yet"; fi
    fi
  fi

  wf_section "WORK ITEM"
  if [ -z "$path" ]; then
    WORK_ITEM=""
    echo "path: (unresolved - $how)"
    if ls changes/[0-9][0-9][0-9]-*.md >/dev/null 2>&1; then
      echo "work items that do exist:"
      ls changes/[0-9][0-9][0-9]-*.md | sed 's/^/  /'
    else
      echo "(no work items yet - copy changes/template.md to start one)"
    fi
  else
    WORK_ITEM="$path"
    echo "path: $WORK_ITEM ($how)"
    echo "--- contents ---"
    cat "$WORK_ITEM"
  fi
}

# --- Roll up task statuses from WORK_ITEM. --------------------------------
wf_print_task_status() {
  wf_section "TASK STATUS"
  if [ -z "$WORK_ITEM" ]; then
    echo "(no work item to roll up)"
    return
  fi
  local n_done n_prog n_todo
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
}

# --- Working tree, scoped to the project, project-relative paths. ----------
# Sets PORCELAIN. git status ignores --relative even with a pathspec, so the
# project prefix is stripped by hand.
wf_print_working_tree() {
  local prefix; prefix=$(git rev-parse --show-prefix 2>/dev/null)
  PORCELAIN=$(git status --porcelain --untracked-files=normal -- . 2>/dev/null |
              sed "s|^\(...\)${prefix}|\1|")
  wf_section "WORKING TREE"
  if [ -n "$PORCELAIN" ]; then
    printf '%s\n' "$PORCELAIN"
    echo "(uncommitted changes inside this project only)"
  else
    echo "(clean - nothing uncommitted in this project)"
  fi
}
