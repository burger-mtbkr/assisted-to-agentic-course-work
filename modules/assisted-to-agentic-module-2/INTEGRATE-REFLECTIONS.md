# Module 2 - Integrate & Reflect

Answers to `project/INTEGRATE.md`'s six prompts, from building a context
framework (`context/ABOUT.md`, `ARCHITECTURE.md`, `IMPLEMENTATION.md`,
root `AGENTS.md`) on top of Module 1's Config API, then building the Admin
UI against it.

## 1. Did the context framework change the quality of your assistant's output? Give a specific example.

Yes, most visibly by surfacing gaps before they caused friction rather than
after. Writing `ARCHITECTURE.md` from the real source (not from memory)
turned up two things nobody had written down anywhere: the
delete-with-children 409 returns a different JSON error shape than every
other error (bypasses `ErrorMiddleware`, hits ASP.NET's default
`ProblemDetails` instead), and there was no CORS middleware at all. Both
went into the doc immediately - and the CORS gap got fixed as a named
prerequisite before Exercise 5 started, instead of being discovered
mid-build when the UI's first `fetch` call failed silently in a browser
with no server-side error to point at.

## 2. What was harder: defining context upfront or keeping it accurate as the project evolved?

Keeping it accurate. Writing the docs the first time was close to
mechanical - read the real code, describe what it does. Staying accurate
was the part that needed a deliberate extra step: `ARCHITECTURE.md`'s "no
CORS middleware yet - needs adding" line became false the moment CORS was
added, and had to be caught and rewritten rather than left as a leftover
TODO. The service's own `README.md` had gone stale even before this
module started (its project-layout tree never mentioned `context/`,
`ui/`, or `AGENTS.md` once they existed) - a small thing, but proof that
"keep it accurate" doesn't happen by default; something has to trigger it.

## 3. Did you find yourself updating context documents during the exercise? What triggered updates?

Yes, twice in ways worth naming. `AGENTS.md` was updated the moment
`IMPLEMENTATION.md` came into existence (Exercise 3 built it with only two
files listed, on purpose, rather than pre-listing a file that didn't exist
yet). `ARCHITECTURE.md`'s CORS line was rewritten once the middleware was
actually added. In both cases the trigger was the same: a fact the
document stated stopped being true the moment the corresponding code
changed, and the two updates happened in the same work session as the
code change, not as a separate later cleanup pass.

## 4. Which context document felt most valuable to the assistant - and which felt hardest to write? Why?

Most valuable for the actual UI work: `IMPLEMENTATION.md`, specifically
the "no field-level validation exists" note - it directly shaped the
UI's `api.ts` error handling and meant not assuming a guard the server
doesn't provide. Hardest to write: `ARCHITECTURE.md`. Unlike `ABOUT.md`
(which could draw heavily on the spec that already existed) or
`IMPLEMENTATION.md` (largely reading `.csproj`/`appsettings.json`
directly), getting `ARCHITECTURE.md` right meant actually opening the
`Infrastructure/DynamoDb`, controller, and middleware source files rather
than summarizing from an earlier research pass - the "derive it, don't
guess" instruction in its own skeleton had teeth.

## 5. What surprised you about how the assistant used (or didn't use) the context you provided?

The bigger payoff was catching gaps (CORS, the error-shape inconsistency,
missing validation) before they cost a debugging cycle, not the tone/style
consistency the framework is usually pitched on. The other surprise:
this exercise ran in one continuous session rather than the fresh
conversations the instructions describe (see the Exercise 1 journal
entry), so the context docs ended up functioning less as cross-session
memory and more as an explicit, auditable log of decisions made along the
way - a real, useful effect, but a different one than "my assistant forgot
everything and these files fixed it."

## 6. How would you approach building a context framework for a project you're actually working on?

Start with whichever single document removes the most immediate ambiguity
- `ARCHITECTURE.md` first if the codebase already exists and its shape
isn't obvious, `ABOUT.md` first if it's greenfield and the "why" isn't
settled yet. Tie every doc update to the same commit as the code change
that invalidates it, not a separate cleanup pass - the CORS line proved
that's exactly where staleness creeps in. And resist writing a document
because the framework "should probably have one" - every file in this
pass existed because something concrete needed explaining (a real bug, a
real missing gap, a real decision), never speculatively.
