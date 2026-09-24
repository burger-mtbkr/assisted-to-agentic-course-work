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
  - The four filled-in design docs, one `DESIGN.md` + `SCRIPT-DESIGN.md`
    per skill. First written to `modules/assisted-to-agentic-module-4/docs/`;
    moved next to their skills in `.claude/skills/<name>/` in Entry 2.
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

## Entry 2: Review the pair, fix everything it found, run the eval loop

- **Prompt**: "review the quality of this skill and where the most
  appropriate place is for the docs it added to live", then "Fix it all",
  then "you are mumbling on. just complete module 4!"
- **Tool**: Claude Code (VS Code extension)
- **Mode**: Direct execution. Review first (every finding verified by
  running something, not by rereading), then the fixes, then the
  `skill-creator` eval loop with subagents: two prompts per skill, each run
  with and without the skill, graded by hand against written assertions.
- **Context**: `.claude/skills/` (both skills, their scripts, design docs),
  `config-service/` (the eval target, with a staged in-flight work item and
  a deliberately half-built code change for the second pair of evals),
  Module 4's own quality heuristics and anti-patterns list.
- **Model**: Claude Fable 5.1 (`claude-fable-5-1`)
- **Input**: The review found five things. (1) `SKILL.md` invoked the
  script by a repo-relative path that fails from inside `config-service/`.
  (2) `land-work-item`'s description claimed framework-generality while the
  script hard-coded six config-service specifics inline. (3) The acceptance
  section pointed the model at `git diff --stat`, which cannot support a
  clause-by-clause verdict. (4) 133 lines duplicated between the two
  scripts, defended in the design doc as self-containment, undermined the
  first time one bug had to be fixed twice. (5) No evals. Plus the docs
  question: they were in `modules/.../docs/`, but the skills span modules
  (M4 builds, M6 assembles), so by the repo's own `config-service/` rule
  the design docs belong with the skill.
- **Output**: All five fixed and the docs moved. `.claude/skills/_lib/workflow.sh`
  now holds the shared resolution helpers (no `SKILL.md`, so the harness
  ignores it; each script prints a clear error naming the path if it is
  missing). The six project specifics are named knobs at the top of
  `land-work-item/script.sh`, each overridable via a `LAND_*` env var. A
  bounded `=== DIFF ===` section (400 lines, truncation marker) feeds the
  acceptance verdicts. Both `SKILL.md` files invoke the script by the
  skill's base directory, which the harness announces on load. Design docs
  live at `.claude/skills/<name>/DESIGN.md` and `SCRIPT-DESIGN.md`, updated
  to say why each of those decisions changed. `evals/evals.json` and
  `evals/results-iteration-1.md` per skill. Eval scores: launch 5/5 and
  6/6 with the skill vs 4.5/5 and 4/6 without; land 6/6 and 6/6 vs 5/6 and
  5/6. Tree restored and verified clean after every staged state.
- **Cost**: Eight subagent runs at roughly 55-97k tokens each, about 600k
  tokens for the eval loop, plus the review and fixes in the main session.
  No dollar figure surfaced (subscription).
- **Reflections**: The eval loop earned its cost by being humbling in a
  specific way. Both baselines - same model, no skill - independently
  found that the staged diff called an undeclared `_cache` field and that
  the work item's "Task 1 Complete" had no code behind it. The model does
  not need a skill to read code well. Where the baselines lost points was
  entirely on process: paraphrasing the acceptance criteria instead of
  quoting them, taking "it was green" as verification, writing the whole
  PLAN section before the user had confirmed anything, ending with `git
  stash` instructions instead of a question. Those are exactly the four
  assertions a Module 6 agent would fail most expensively, and they are
  what the skill body actually constrains. The lesson for what a skill is
  *for*: not to make the model smarter about the codebase, but to make it
  stop at the right places.

  The second lesson was about my own design doc. It argued, with some
  conviction, that duplicating 130 lines was the right call for
  self-containment. It was wrong within the hour - the porcelain bug had to
  be fixed in both files. A design doc that records a decision and its
  reasoning is only useful if it also gets corrected when the reasoning
  fails, which is why the "Notes and decisions" sections now say what
  changed and why rather than pretending the first version was right.
