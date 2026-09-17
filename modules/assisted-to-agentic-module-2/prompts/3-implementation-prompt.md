Prompt used to fill in `context/IMPLEMENTATION.md` and create the root
`AGENTS.md` (Exercises 3 and 4).

---

Two things:

1. Create `@assisted-to-agentic-module-1/config-service/AGENTS.md` using
   the template from `project/INSTRUCTIONS.md` Exercise 3, listing
   whichever `context/*.md` files exist right now. This is a living
   document - every time a new context file is added, add it here too in
   the same change.

2. Fill in `@assisted-to-agentic-module-1/config-service/context/IMPLEMENTATION.md`.
   Ground it in the real project files, don't invent conventions:
   - `@assisted-to-agentic-module-1/config-service/src/ConfigApi.Service/ConfigApi.Service.csproj` -
     exact dependency versions
   - `@assisted-to-agentic-module-1/config-service/src/ConfigApi.Service/appsettings.json`
     and `.env.example` - configuration and credential handling
   - `@assisted-to-agentic-module-1/config-service/src/ConfigApi.Service/Models/` -
     check whether any validation attributes actually exist before
     documenting validation rules
   - `@assisted-to-agentic-module-1/config-service/src/ConfigApi.Service.UnitTests/coverlet.runsettings` -
     what's excluded from coverage and why
   - `git log` for the real commit convention in use - don't assume
     conventional commits just because other reference material uses them

   This is also where the Admin UI's tech stack gets decided (needed
   before Exercise 5) - state the choice and the reasoning, not just the
   name of a framework.
