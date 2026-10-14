# Module 5 - Integrate & Reflect

## Summary

**What I did:** Built `domain-lang`, a stdio MCP server that wraps the
course's `knowledge-graph` CLI with five read-only tools, and pointed it at a
knowledge graph written for *this* repo's C# config-service rather than the
curriculum's Python one. Verified it in MCP Inspector, registered it for
Claude Code at project scope, and confirmed Claude Code calls it on its own
for domain questions.

**How it went:** The protocol side was easy; the backend was not. Running
the CLI by hand before designing found three failure modes. One is silent
(a missing db answers `not_found` for everything and validates as "valid"),
and two crash with output no agent can act on (Windows encoding, and
option-like terms parsed as flags). The reference server passes the silent
one straight through.
The curriculum's sample data would also have passed every exercise check
while describing files that do not exist here.

**What I learned:** An MCP server's value is the *trust* the agent places in
it, so its failure modes matter more than its happy path. A server that
says "not found" when it really means "I could not look" is worse than no
server. The agent reached for it first on both test prompts, before reading
any code, so whatever it says gets believed.

---

Answers to `project/INTEGRATE.md`'s prompts.

## 1. What did writing the tool *description* feel like - what did you optimise for, knowing the LLM reads it?

It felt like writing routing rules rather than documentation. The question
for each sentence was "does this change which tool the model picks, or what
it does with the answer?" If it did neither, it was cut.

Three things I optimised for:

- **When to choose this over the alternative, and the alternative was not
  another tool.** For `lookup_term`, the competitor is the model's own
  general knowledge about "config services" and "feature flags", plus
  grepping the code. So the description lists this repo's actual terms
  (Application, ConfigurationItem, FeatureFlag, FlagKey, ScanCache,
  ErrorResponse) and says to call it *before* searching code because "this
  repo's meanings and file names differ from common conventions". It
  worked: in both headless Claude Code runs the first real tool call was
  `lookup_term` / `get_related_terms`, and code reads came only after, to
  confirm a path the graph had given.
- **Negative space.** `ping`'s description says it does *not* touch the
  knowledge graph, so a successful ping proves nothing about the data. A
  model that pings, sees "Pong", and then reports the graph healthy would be
  reasoning correctly from a misleading description.
- **What the output means, not just its shape.** "Returns
  `{"error": "not_found"}` for unknown terms" and "`[]` means it has no
  outgoing edges" tell the model how to read an empty or negative answer.
  Those are the cases it otherwise improvises.

The schema turned out to be part of the description too. Moving "not blank"
from prose into `pattern: \S` means a whitespace term is rejected before the
handler runs, rather than relying on the model to read a sentence.

## 2. Did you hit any friction registering the MCP in your coding agent - once MCP Inspector confirmed it worked, how did the hand-off to your harness go?

Mostly smooth, with three real speed bumps.

- **Project scope has a trust gate.** `claude mcp add --scope project`
  writes `.mcp.json` correctly, but the server then sits at "Pending
  approval" until someone approves it in an interactive session. A headless
  `claude -p` run never prompts, so it simply did not have the tools. The
  fix is the local, git-ignored `enabledMcpjsonServers` setting. The gate
  is right: a cloned repo should not be able to start processes on my
  machine silently. But it means "it's in the repo" does not equal "it's
  available".
- **`.mcp.json` has no working-directory field.** The server starts in
  whatever directory Claude Code launched in. So the command became
  `uv run --project domain-lang-mcp ...` and `KG_PROJECT_DIR` / `KG_DB` are
  repo-root-relative, which ties the registration to running Claude Code
  from the repo root.
- **The harness hides the schema until it needs it.** Claude Code listed
  only the tool names up front and loaded the full schemas through a
  `ToolSearch` call when it decided to use them. So the name and the first
  impression of the description do the selecting, not the input schema.
  That is the same progressive-disclosure pattern Module 6 builds for
  skills, and it raises the stakes on naming.

The hand-off itself was quick *because* Inspector came first. When the
first headless run worked, there was nothing left to debug except
registration.

## 3. What surprised you in the MCP Inspector?

- **Schema rejection is not a protocol error.** With `mcp` 2.x, a call
  missing a required field comes back as an ordinary tool result with
  `isError: true` and a pydantic message, not a JSON-RPC `-32602`. The model
  sees it and can correct itself, which is useful, but "the schema stops
  bad calls" really means "the server returns an error the model can read".
- **The CLI mode is scriptable.** `npx @modelcontextprotocol/inspector
  --cli ... --method tools/call` made all nine exercise checks a repeatable
  shell loop instead of clicking through a UI. It even exits non-zero
  (`tool_is_error`) on an error result.
- **It surfaced a shell bug, not a server bug.** The "bad
  `KG_PROJECT_DIR`" check passed `/nowhere/kg`, and the error came back
  naming `C:\Program Files\Git\nowhere\kg`. Git Bash had rewritten the
  POSIX-looking path before the server ever saw it. The structured error
  message (`detail` names the resolved path) is what made that visible in
  seconds. That is the argument for detailed errors in one example.

The biggest surprise was underneath Inspector, though: everything Inspector
showed was "correct" according to the CLI. The CLI quietly creates an empty
db if pointed at a missing one, so with a typo in `KG_DB` Inspector would
show clean `not_found` answers. Inspector checks the protocol, not whether
the backend is telling the truth.

## 4. (Optional, if you tried HTTP) What felt architecturally different beyond transport?

Did not try it. This graph is local, single-developer, and read-only, which
is the case where stdio wins: no port, no auth, and no server lifetime to
manage. HTTP becomes the right answer when the graph is shared across a team
or hosted. At that point the bigger change is not the transport but owning
a running service.

## 5. What MCP would you want for the codebase you actually work in - and would it be a personal workflow tool that travels with you, or a team shared asset that lives in the repo? What does that answer change about where you'd store it and how you'd maintain it?

This one, extended. `config-service` was ported from `income-service` (its
DynamoDB collection abstractions came from there), so the domain language
and the data-access conventions are shared across a family of services. The
MCP I would want answers "what does this term mean in *this* service, and
where does it live", across that family. On top of the domain graph it would
add the one operational fact that bit us in Module 1: which DynamoDB tables
and key schemas a service expects, compared with what is actually
provisioned.

That makes it a **team shared asset with a split home**:

- **The data lives in each service repo**, next to the code it describes
  (`config-service/knowledge/` here), because the only way it stays true is
  if the commit that renames `FlagService` also updates the node pointing at
  it. Stale knowledge is worse than none, since the agent trusts it first.
- **The server lives once, shared**, not copied into every repo. It is an
  interface over the data, and it should be versioned on its own, with each
  repo registering it in `.mcp.json`.
- **Maintenance becomes a review concern.** The knowledge YAML needs the
  same "did the docs drift?" check the Module 4 `land-work-item` skill
  already runs for READMEs and `context/`. That is the natural next step:
  have it flag a change to a file listed in some node's `source_files`.

A personal-tool version (just in my harness config) would be quicker to
start, but it fails exactly where this one has to succeed: the moment a
teammate's change makes it wrong, nobody but me would notice.
