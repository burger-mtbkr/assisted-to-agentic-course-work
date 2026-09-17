Prompt used to fill in `context/ARCHITECTURE.md` (Exercise 2 - "what's on
top").

---

Fill in `@assisted-to-agentic-module-1/config-service/context/ARCHITECTURE.md`.
The skeleton has section headers (Layers, Data access, Error handling, API
surface, Key technical decisions) with TODO placeholders.

Derive every section from the real source - don't summarize from memory,
open the files:
- `@assisted-to-agentic-module-1/config-service/src/ConfigApi.Service/Infrastructure/DynamoDb/` -
  both collection abstractions (single hash key vs. composite hash+range
  key) and why both exist
- `@assisted-to-agentic-module-1/config-service/src/ConfigApi.Service/Controllers/`
  and `Services/` - what each layer owns
- `@assisted-to-agentic-module-1/config-service/src/ConfigApi.Service/Middleware/ErrorMiddleware.cs` -
  how exceptions map to HTTP status codes
- `@assisted-to-agentic-module-1/config-service/src/ConfigApi.Service/Program.cs` -
  the actual startup/DI order

Pick this doc over `IMPLEMENTATION.md` for this pass because the
composite-key DynamoDB design is the most non-obvious, currently
undocumented thing in the codebase (previously explained only in a
superseded planning artifact, not anywhere a new contributor would find
it). Point at `openapi.json`/the README for the endpoint list rather than
duplicating it here.
