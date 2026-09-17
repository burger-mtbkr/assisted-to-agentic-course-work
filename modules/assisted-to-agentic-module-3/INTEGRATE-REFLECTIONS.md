# Module 3 - Integrate & Reflect

Answers to `project/INTEGRATE.md`'s four prompts, from building the
procedural (`context/ENV_SCRIPTS.md`) and episodic (`context/WORKFLOW_STATUS.md`)
memory layers on top of Module 2's context framework, then delivering
`changes/001-feature-flags.md` end to end through all five tasks.

## 1. Were you able to successfully get your assistant to pick up where you left off (with an empty context window) with just "what's the next step?" or "what is our status?"

Not tested as a genuine empty-context restart within this session - the
work happened continuously in one conversation, same caveat Module 2's
reflections already named for that module's exercise. What can be said
concretely: `context/WORKFLOW_STATUS.md`'s "Current Status" pointer and
each work item's purged "Current Task Focus" section were kept accurate
after every task (Task 1 -> Task 2 -> ... -> "story complete, no active
task"), so the mechanism a fresh session would need is in place and
correct as of the last commit. The real test - opening a new conversation
cold and asking "what's our status?" - is still outstanding.

## 2. Were you able to get your assistant to behave properly during the transitions?

Partially, and the gap is worth naming honestly rather than glossing over.
`context/WORKFLOW_STATUS.md` states plainly: "ONLY the user decides when a
stage is complete... the assistant MUST NOT declare stage completion." This
session didn't follow that - after the first task's PLAN was drafted and
reviewed, the user directed the assistant to "do everything needed for
module 3," and from that point the assistant self-drove PLAN -> BUILD &
ASSESS -> REFLECT & ADAPT -> COMMIT & PICK NEXT for four more tasks without
stopping for a stage-gate confirmation each time. That was an explicit,
informed choice by the user (confirmed again before it started producing
multiple commits), not drift - but it means this session tested "does the
assistant execute the four stages correctly and thoroughly" rather than
"does the assistant respect the human-in-the-loop gate the workflow
document itself insists on." Those are different questions, and only the
first one got a real answer here.

## 3. Did your assistant apply the workflow rules consistently - or only when you were working inside the workflow documents themselves?

Consistently, in the parts that didn't require stopping for confirmation:
every task ran through PLAN (documented in the work item before touching
code), BUILD & ASSESS (implemented, then validated - and validated against
the real API and real DynamoDB each time a change touched that layer, not
just the mocked unit suite, per `context/IMPLEMENTATION.md`'s own "tests
pass isn't sufficient" rule), REFLECT & ADAPT (a genuine process note each
time, including naming a scope deviation in Task 2 and a real bug found in
Task 4), and COMMIT & PICK NEXT (purge stage notes, review touched
READMEs, pick the next task). The README-review step caught real drift
more than once - `context/IMPLEMENTATION.md`'s Validation section was
found to be flatly wrong (it claimed no key-format validation existed;
`ConfigurationService` already had one) while writing Task 2, and Task 4's
own documentation writing surfaced a real correctness gap (the
delete-with-children guard didn't check flags) that got fixed rather than
just written down as a known issue. Both of those happened because the
workflow's own discipline - read the real code before describing it,
don't let a stale doc stand - was applied consistently, not just inside
`changes/001-feature-flags.md` itself.

## 4. What took the most iteration to get right?

Two things, both infrastructure rather than application code. First, the
`0003_CreateFlagsTable.cs` migration initially failed against the real AWS
account with an IAM `AccessDeniedException` - `config-service-local-dev`'s
policy listed table ARNs explicitly rather than a wildcard, so a brand-new
table needed its own grant before provisioning could succeed. That
required a real decision from the user (fix the IAM policy now vs. proceed
without live verification) and then an out-of-band `aws iam put-user-policy`
step with no corresponding `npm run` script - now documented in
`context/ENV_SCRIPTS.md`'s "when to go off-script" section so the next
person (or session) doesn't rediscover it the same way. Second, verifying
the UI change properly: this environment has no `chromium-cli`, so
confirming the new Feature Flags checkbox actually rendered and the toggle
round-tripped through the real API took standing up a throwaway Playwright
script against the system-installed Chrome rather than a one-line skill
invocation - more setup than the rest of the module's verification steps
combined, for what the workflow's own quality bar (no UI change ships
without being seen working) treats as non-negotiable.
