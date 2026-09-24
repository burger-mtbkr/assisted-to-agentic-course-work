# Module 4 - Integrate & Reflect

Answers to `project/INTEGRATE.md`'s four prompts, from designing and
authoring the `launch-work-item` / `land-work-item` skill pair (Option C)
against `config-service/`.

## 1. Where in your development cycle did this skill emerge from - what friction was it answering?

From the ends of the four-stage workflow built in Module 3, and from
Module 3's own reflections, which named the friction before this module
asked for it.

The **launch** friction is a fixed sequence of four manual reads, performed
identically every time a task starts: open `context/WORKFLOW_STATUS.md`,
follow its pointer to `changes/NNN-*.md`, scroll past the completed tasks to
find the active one, then check git separately to see what actually happened
since. Nothing about that requires judgement. It is a recipe, and a recipe
executed by hand every time is the clearest signal a skill is missing.

The **landing** friction is different and worse: not repetition, but
omission. `WORKFLOW_STATUS.md` asks for five things at the end of a task - a
clean gate, behaviour checked against the Given-When-Then, a README review
of touched folders, the stage-note purge, and a commit in the repo's own
style. They get skipped because by then the interesting part is over.
Module 3's reflections recorded exactly that, and the purge step is the one
called out in the workflow document itself as the one that slips ("a work
item file that only ever grows is a sign the purge step is being skipped").
The landing skill turns five remembered obligations into one piece of
evidence per obligation.

Worth noting where this did **not** come from: it is not the demo scenario
made mine. `start-work` answers "where were we?" across a repo. Neither of
these does. They answer "which task am I planning, against which acceptance
criteria?" and "is this task actually finished?" - questions this repo's
workflow already poses and previously answered by memory.

## 2. Did the skill activate when you expected it to? If not, what change to the description fixed it?

Both activated on first invocation, and both showed up in the harness skill
list as soon as `SKILL.md` was written - no restart, no registration step.
But "it activated when I invoked it by name" is a weak test, and the
description work went beyond it.

The first drafts of both descriptions led with the mechanism ("reads the
workflow pointer and the work item file..."). That describes what the skill
does to itself, not the situation the user is in - and the situation is the
actual trigger. Rewritten to front-load the moment plus a spread of the
phrasings someone would really use: "picking up a work item task", "starting
or resuming a task", "asking which task is next", "about to plan or scope a
change" for the launcher; "a task looks done", "before committing",
"wrapping up or closing out", "ready to commit" for the lander.

Two specific additions matter. First, `even if the user does not say "work
item"` - most of the time nobody says it; they say "what's next?" or "I think
that's done". A description that only matches the jargon would undertrigger
on every natural phrasing. Second, both descriptions name the activation
*condition* - "in a project that follows the context/ + changes/ workflow
framework" - so the skills stay quiet in a repo where they would have
nothing to read. Narrow scope is a quality heuristic for the body, but it has
to be visible in the description too, or the skill fires where it does not
belong.

The lander's description also ends with "Reports and hands over; never
commits on its own." That is there to set the expectation before the skill
is invoked rather than after, since the most likely reason someone would
hesitate to use it is fear of what it might do unasked.

The eval loop (two prompts per skill, run with and without the skill,
graded against written assertions - see `evals/results-iteration-1.md` in
each skill directory) gave the sharper answer to "did it activate as
expected". All four with-skill runs followed the skill from the first line
without prompting, so the description did its job. What the evals also
showed is that activation is not where the value is: the baselines, same
model and no skill, found the same code facts. Where they lost points was
process - paraphrasing acceptance criteria, accepting "it was green" as
verification, writing the whole PLAN unasked, ending with git commands
instead of a question. The skill's job turned out to be making the model
stop at the right places, not making it see more.

## 3. Did your skill need a script? What did the script give you that the LLM alone couldn't?

Yes, both, and the two cases are qualitatively different - which turned out
to be the most useful thing this module taught.

For **launch**, the script supplies current-state facts: which commits
carried this work item, which files moved in the last ten commits touching
this project, whether the tree is dirty, when each context doc last changed.
None of it is inferable from training data, and all of it is cheap and exact
to compute. Standard grounding.

For **land**, the script does something the model cannot do at all: it
*runs the quality gate*. An LLM can read a test file and form an opinion
about it. Only executing `npm run check` establishes that it passes today,
on this machine, with these changes. That is not grounding, it is
verification, and it is the reason a "tests pass" claim in the landing report
can be trusted. The same script also checks for a running `ConfigApi.Service`
before the gate, because `ENV_SCRIPTS.md` documents that a locked `.exe`
makes the build fail with `MSB3027` - a failure that looks exactly like a
code defect in the gate output, and would otherwise be the most misleading
possible evidence to lead a landing report with.

Running the scripts for real is also what found the bugs. The first launch
script produced a complete, well-formed, entirely empty report: it emitted
repo-root-relative paths while running `git log` from the project directory,
so every per-file lookup silently matched nothing and printed `(no history)`.
Reading the script would not have caught it. The same failure in a Module 6
agent would be invisible and would poison everything downstream, which is
why both scripts now print an explicit marker for every section that found
nothing - `(none found)`, `(clean)`, `(could not determine)` - rather than
omitting it. An omitted section reads as "nothing to worry about". That is a
different claim from "I did not check", and the difference matters more the
further the output travels from a human who could notice.

The line the module draws - script for what needs the current state of *this*
codebase, LLM for the reasoning over it - held up exactly. Every row in both
script design docs passes that test, and nothing that failed it was given to
a script.

## 4. What's a skill you'd build next if you had time?

**`assess-tests`** (Option D), and for a concrete reason rather than
completeness: `config-service` reports 100% line and branch coverage on
every measured class, and a recent commit in this repo was
"Fix silently-broken coverage filters, close the gaps they were hiding" -
the number was green because the filters were wrong, not because the tests
were good. That is precisely the gap Option D names: coverage percentage as
a proxy for test quality, measuring the wrong thing confidently. A skill
that assessed mock coupling, whether integration tests hit real
infrastructure or fake it, and which end-to-end paths are actually covered
would have caught it sooner than a number ever could.

Second choice: **`purge-work-item`**, splitting the purge out of
`land-work-item` and letting it emit the pruned file rather than describe
it. Deliberately left out of this version - "reports, never writes" is what
makes the landing skill safe to trust on its first outing, and the right
time to add writing is after enough landings to know the report is reliable.
That sequencing is itself the module's point about where skills come from:
notice the friction first, then build for it.
