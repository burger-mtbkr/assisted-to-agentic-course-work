# Module 1 — Integrate & Reflect

Answers to `project/INTEGRATE.md`'s six prompts, written after finishing the
Configuration API Service exercise end-to-end (spec → prompt → plan → implement,
plus live synthetic testing against real AWS DynamoDB).

## 1. Walk through the spec → prompt → plan → implement cycle. Where did you feel in control? Where did things go sideways?

In control at the spec, prompt, and plan stages — each one was a document I read
and edited before it became the input to the next stage, so scope decisions (region,
credentials approach, data model, name-uniqueness behavior) were mine, made
deliberately, and visible in the diff. Reviewing the plan caught real overreach
before it became code: an early draft added request DTOs and an `UpdatedDate`
field nothing had asked for, and I cut both before Step 5 ran.

Things went sideways at implementation, and not in the way I expected. The build
finished clean — 44/44 unit tests passing, zero build warnings — and I almost
treated that as "done." Running the actual service against the real DynamoDB
tables immediately broke on the very first request with a runtime error the test
suite gave zero indication of. The tests mocked the AWS SDK boundary, so a broken
`TableBuilder` call inside the class *being* mocked around was invisible to them.
"All tests pass" turned out to be a much weaker claim than I'd been treating it as.

## 2. What did you learn about how much detail your assistant needs? Did more detail produce better results, or add noise?

Concrete, decisive detail helped every time — exact table names, region, billing
mode, key schema, the approved dependency list. The assistant followed those
faithfully and didn't deviate from them once they were pinned down. Where I was
vague (not specifying exact request/response DTO shapes in the spec, on the theory
that "the plan should propose them"), the assistant filled the gap with its own
invented structure rather than asking — extra DTO classes, an extra timestamp
field — none of it wrong exactly, just unrequested. Ambiguity produced embellishment,
not clarifying questions, even though the prompt explicitly asked for the latter.
Lesson: if a decision matters, make it myself rather than leaving room for the
assistant to make a plausible-sounding one on its own.

## 3. Did the journal feel useful or like overhead? What would make it more valuable to you?

The template fields (Prompt/Tool/Mode/Context/Model/Input/Output/Cost) are cheap
to fill and mostly bookkeeping — useful for reconstructing "what ran when" but not
where the value is. The value was entirely in writing "Reflections" as an actual
narrative — what surprised me, what broke, what I had to go fix myself — rather
than a one-line summary. The Step 5 entry documenting the `TableBuilder` bug and
how I found it is the one I'd actually want to reread before starting a similar
project; the earlier, thinner entries are closer to noise by comparison. Takeaway:
the journal is only as valuable as the honesty and specificity of the reflections
field, and that's worth protecting time for even when it's tempting to write one
line and move on.

## 4. What surprised you about not writing the code directly — either how that felt, or what the output actually looked like?

The output itself was structurally solid — the layering, naming, and DI patterns
matched the reference project closely and consistently across 44 files, which
would have taken real effort to keep consistent by hand across that many files.
What surprised me was how much verification responsibility *didn't* go away just
because I wasn't typing the code: I still had to read the generated code closely
enough to catch the deviations it flagged itself, run it against a real dependency
to catch the bug it couldn't self-detect, and read a coverage report closely enough
to notice `ErrorMiddleware` — the component that turns exceptions into the correct
HTTP status codes — had zero tests despite the rest of the suite looking thorough.
Not writing the code shifted the work from typing to auditing; it didn't reduce it.

## 5. What rules did you end up capturing? What behaviour made you want to write them down?

Two went into this module's `AGENTS.md`. The `TableBuilder` needs explicit
`AddHashKey`/`AddRangeKey` before `Build()` rule came directly from watching every
single synthetic request fail with an error 44 green tests never once hinted at —
worth writing down so the next AWS SDK DocumentModel usage doesn't repeat it blind.
"Only build what the plan asks for" came from catching the plan's own first draft
adding scope (DTOs, a timestamp field) nobody had requested — a reminder that even
a plan grounded in real research (it read the actual reference project's source
via GitHub) isn't automatically scope-disciplined, and needs a separate trim pass.

## 6. What would you do differently on the next run?

Build a "run it for real before calling it done" step into the plan itself, not
as something I bolt on afterward once I get suspicious of all-green test output.
I'd also specify test-coverage expectations explicitly up front — e.g. "every
caught exception type needs its own test" — rather than discovering the gaps by
reading a coverage report after the fact. And I'd push back earlier on vague spec
areas (like DTO shapes) instead of deferring them to "let the plan propose it,"
since that's exactly where unrequested scope crept in this time.
