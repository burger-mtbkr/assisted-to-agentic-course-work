Prompt used to build the Admin UI (Exercise 5).

---

Build the Admin UI in `@config-service/ui/`
(sibling to `src/`), using the stack and reasoning already recorded in
`@config-service/context/IMPLEMENTATION.md`.

Scope, exactly this and nothing more:
- List all applications
- View the configuration entries for a selected application
- Update a configuration value

No create-application, no add/delete-configuration-entry, no auth, no
routing library, no UI framework. If something feels like it wants more
structure, that's scope creep - stop and flag it instead of adding it.

Before wiring the UI to the API, check whether CORS is actually configured
on the service (`@config-service/src/ConfigApi.Service/Program.cs`)
- `context/ARCHITECTURE.md` should say either way. If it's missing, add it
as a prerequisite step, scoped to the UI's local dev origin only, and
update `ARCHITECTURE.md` once it's real.

Don't call this done on "the build succeeded" or "tests pass" alone - Module
1's own retro is explicit that mocked tests don't prove the real thing
works. Run the actual dev server, hit the actual running API, and verify a
value written through the UI is readable back afterward, not just that the
UI renders without an error.
