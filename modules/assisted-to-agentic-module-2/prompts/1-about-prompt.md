Prompt used to fill in `context/ABOUT.md` (Exercise 1).

---

Fill in `@config-service/context/ABOUT.md`.
The file already has a skeleton with section headers (Name, Description,
Justification, Personas, Domain context, Scope) and TODO placeholders -
replace the placeholders, don't change the structure.

Ground every claim in something real, not invented:
- `@modules/assisted-to-agentic-module-1/project/prompts/1-web-api-specs.md` for
  what the service was originally specified to do
- `@config-service/README.md` for what it
  actually does today
- the live OpenAPI schema (`GET /openapi/v1.json` against the running
  service) for the real `Application`/`Configuration` shapes

Keep it short - this doc exists to remove high-level ambiguity for a new
reader, not to be comprehensive. If something is genuinely not decided yet
(auth, versioning, multi-environment), say so under Scope rather than
guessing or leaving it out.
