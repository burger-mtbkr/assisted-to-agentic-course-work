---
name: triage-codebase-health
description: "Use when asked whether the codebase is healthy, broken, or needs a diagnosis. Covers which checks to run first, when to inspect files, what evidence makes a result healthy, unhealthy or inconclusive, and the health report format."
allowed-tools: run_tests run_lint ls read_file glob grep
---

# Triage codebase health

A grounded diagnosis: deterministic checks first, files only where the checks
point, and a report that never claims more than the evidence shows. Diagnose;
do not fix.

## Procedure

1. **Run the checks.** Call `run_tests`, then `run_lint`. Run both even if the
   first fails - a lint failure next to a test failure changes the picture.
2. **Read the results before reading files.** For each check note the exit
   code, `passed`, and the specific failure lines: test names, file paths with
   line numbers, compiler or lint rule IDs. A result with an `error` field
   (timeout, missing directory, could not start) means the check did not run
   to completion - that is not a pass.
3. **Inspect files only where the evidence points.** For each failure, open
   the file the output names (`read_file /codebase/<path>`), around the line
   it gives. Use `grep` or `glob` only to locate a file the output names
   ambiguously (a test class, a type). Record why each file was opened. If
   every check passed, there is no failure to trace - do not browse.
4. **Classify.**
   - **Healthy** - every check ran to completion and passed.
   - **Unhealthy** - at least one check ran and failed (non-zero exit code
     with failure output).
   - **Inconclusive** - a check timed out, could not start, or its output is
     too truncated to tell what failed. Say which.
5. **Report**, in the format below. Recommend the single smallest next
   verification step - a command to run or a question for a human.

## Health report format

```markdown
## Health Report

**Status:** Healthy | Unhealthy | Inconclusive - one-sentence reason.

**Evidence collected:**
- Tests: `<command>` - exit <code>, <passed/failed counts or key line>, <duration>.
- Lint: `<command>` - exit <code>, <key line>, <duration>.
- Files inspected: `<path>` - <which check output pointed here>. (Or "none - no failure to trace.")

**Findings:**
- <finding, citing the line of output or file it rests on>

**Uncertainties:**
- <what the evidence does not show: truncated output, checks not covered, environment-only behaviour>

**Recommended next verification step:**
- <one command or human action>
```

## Guardrails

- Never edit files, and never say something is fixed.
- Never invent a test count, rule ID or file path - quote what the tools returned.
- "Healthy" means these checks passed, not that the system is production-ready.
- If output was truncated (it says so), base the diagnosis on the visible part and say that.
