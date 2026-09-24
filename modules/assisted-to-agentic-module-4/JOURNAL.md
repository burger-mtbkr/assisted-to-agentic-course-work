# Module 4 Journal

## Entry 1: Design and author the `launch-work-item` / `land-work-item` skill pair

- **Prompt**: "we have completed module 1 - 3. GO and do module 4 completely
  until its done and you are completely happy with it then give me a summary
  of what you did once its done", then two mid-flight corrections: "you are
  creating prompts not a skill as per the instructions the script needs to
  relate to a skill.md file!" and "there should be no prompts man!!! use a
  docs folder if needed but they are NOT PROMPTS nowhere in the instructions
  does it ask for prompts!"
- **Tool**: Claude Code (VS Code extension)
- **Mode**: Direct execution, bypass permissions. No plan-mode gate - the
  module's own process (design doc -> author -> install -> invoke -> iterate)
  supplied the structure instead.
- **Context**: `modules/assisted-to-agentic-module-4/` (curriculum:
  `README.md`, `project/INSTRUCTIONS.md`, `project/INTEGRATE.md`, the two
  design templates, the worked `start-work-DESIGN.md`, and the bundled
  `start-work` and `skill-creator` reference skills) and `config-service/`
  (the real project the skills are built against - `context/`, `changes/`,
  the npm task runner).
- **Model**: Claude Opus 5 (`claude-opus-5`)
- **Input**: Read the module's actual exercise steps rather than only the
  README, then picked **Option C** (the `launch-work-item` / `land-work-item`
  pair) because this repo already has the thing the pair brackets: the
  four-stage workflow in `context/WORKFLOW_STATUS.md` and the
  `changes/NNN-*.md` work items built in Module 3. Filled in the skill design
  template and the script design template for each of the two skills (four
  design docs), then authored `SKILL.md` + `script.sh` for each from those
  specs, installed them at project scope in `.claude/skills/`, and iterated
  against the real project.
- **Output**:
  - `.claude/skills/launch-work-item/{SKILL.md,script.sh}` - orients on the
    single task about to be planned: resolves the workflow pointer to a work
    item, picks the in-flight task, quotes its Given-When-Then verbatim, and
    produces a five-section launch brief. Quality gate is opt-in
    (`--with-check`).
  - `.claude/skills/land-work-item/{SKILL.md,script.sh}` - runs the closing
    process: checks for the API process that locks the build, runs
    `npm run check` for real, rolls up touched folders against their READMEs,
    flags context-doc and `openapi.json` drift, finds the `### STAGE` sections
    to purge, and samples commit style. Reports and hands over; never commits.
  - `modules/assisted-to-agentic-module-4/docs/` - the four filled-in design
    docs (`*-SKILL-DESIGN.md`, `*-SCRIPT-DESIGN.md`).
  - Verified live, not just by inspection: both skills invoked through the
    harness; the landing gate run for real against `config-service`
    (**PASS, 78s - 87 API tests, 5 UI tests, build clean**); the FAIL path
    verified by deliberately breaking `FlagsController.cs` and confirming the
    real `CS1525` compiler error appeared in the failure tail; the dirty-tree
    path verified with a scratch edit plus untracked file, which correctly
    produced the README roll-up and fired the `openapi.json` drift flag; the
    in-flight-task path verified against a scratch work item with a
    Complete/In Progress/Not Started mix, since the real repo has no active
    task. Working tree restored to clean after every destructive test.
- **Cost**: No per-call dollar figure surfaced (subscription session). The
  expensive step by far was the real `npm run check` runs - roughly 3 minutes
  of wall clock across the PASS and FAIL verifications.
- **Reflections**: Three things worth keeping.

  First, **the two corrections mid-session were both right and both about
  naming, not code.** The design docs first landed in `prompts/` because
  that is this repo's convention from Modules 1-3, but Module 4's
  INSTRUCTIONS.md never says "prompt" - it says design doc. Carrying an
  earlier module's folder convention into a module that asks for something
  different is exactly the kind of drift the course's own "read the
  instructions, not the summary" discipline is meant to catch. Moved to
  `docs/`, named to match the curriculum's own `start-work-DESIGN.md`.

  Second, **running the scripts for real found bugs that reading them would
  not have.** The first version of the launch script returned `(no history)`
  for every single file - it emitted repo-root-relative paths while running
  `git log` from the project directory, so every per-file lookup silently
  matched nothing. That is the worst failure mode for a grounding script:
  it produced a complete, confident, entirely empty report. Fixed with
  `--relative` and a `-- .` pathspec. A second, smaller version of the same
  bug hit `git status --porcelain`, which ignores `--relative` even with a
  pathspec.

  Third, **the "nothing to do" case was the sharper test than the happy
  path.** `config-service` currently has no active task - work item 001 is
  complete and 002 does not exist. A launch skill that only worked with a
  task in flight would have produced a confidently wrong brief on the exact
  state the repo is in. Both skills were designed so the empty case returns
  an explicit "there is nothing to launch / nothing to land, here is what to
  create next" rather than inventing work.
