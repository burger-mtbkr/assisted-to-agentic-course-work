# Module 1 - Integrate & Reflect

Answers to `project/INTEGRATE.md`'s six prompts, from the Configuration API
Service exercise (spec, prompt, plan, implement, then live testing against
real AWS DynamoDB).

## 1. Walk through the spec -> prompt -> plan -> implement cycle. Where did you feel in control? Where did things go sideways?

In control at spec, prompt, and plan - each was a document I read and edited
before it fed the next stage, so decisions like region, credentials, data
model, and name-uniqueness were mine. Reviewing the plan caught real
overreach: an early draft added request DTOs and an `UpdatedDate` field
nobody asked for, cut before Step 5.

Sideways at implementation. The build was clean, 44/44 unit tests passing,
and I nearly called that done. Running the service against real DynamoDB
tables broke on the first request, an error the test suite gave no
indication of - it mocked the AWS SDK boundary, so a broken `TableBuilder`
call inside the mocked class was invisible to it. "All tests pass" was a
weaker claim than I'd been treating it as.

## 2. What did you learn about how much detail your assistant needs? Did more detail produce better results, or add noise?

Concrete detail helped: exact table names, region, billing mode, key
schema, approved dependencies. The assistant followed all of it without
deviating. Where I was vague - not specifying DTO shapes, leaving it to
"the plan should propose them" - it filled the gap with its own invented
structure instead of asking: extra DTO classes, an extra timestamp field.
Nothing was wrong, just unrequested. Ambiguity produced embellishment, not
the clarifying questions the prompt asked for. Lesson: decide it myself
rather than leave room for a plausible-sounding guess.

## 3. Did the journal feel useful or like overhead? What would make it more valuable to you?

The template fields (Prompt/Tool/Mode/Context/Model/Input/Output/Cost) are
quick to fill and mostly bookkeeping. The value was in the "Reflections"
narrative - what broke, what I had to fix myself. The Step 5 entry on the
`TableBuilder` bug is the one worth rereading; the thinner early entries
aren't. The journal is only as useful as the specificity of that field.

## 4. What surprised you about not writing the code directly - either how that felt, or what the output actually looked like?

The layering, naming, and DI patterns stayed consistent across 44 files.
What surprised me was that verification responsibility didn't go away: I
still had to read the code closely enough to catch its own flagged
deviations, run it against a real dependency to catch the bug it couldn't
self-detect, and read a coverage report closely enough to notice
`ErrorMiddleware` had zero tests despite the rest of the suite looking
thorough. Not writing the code shifted the work from typing to auditing.

## 5. What rules did you end up capturing? What behaviour made you want to write them down?

Two went into this module's `AGENTS.md`. The `TableBuilder` needs explicit
`AddHashKey`/`AddRangeKey` before `Build()` rule came from every synthetic
request failing with an error 44 green tests never hinted at. "Only build
what the plan asks for" came from the plan's first draft adding scope (DTOs,
a timestamp field) nobody requested - a reminder that a plan grounded in
real research still needs a separate scope-trim pass.

## 6. What would you do differently on the next run?

Build a "run it for real before calling it done" step into the plan itself,
not as an afterthought once all-green tests look suspicious. Specify
test-coverage expectations up front - e.g. every caught exception type
needs its own test - instead of finding the gaps in a coverage report
after the fact. Push back earlier on vague spec areas (like DTO shapes)
instead of deferring them to the plan.
