# Architecture

<!--
Instructions to the assistant: derive every section below from the real
source under src/ConfigApi.Service/ - reference files with @path so claims
are grounded, not guessed. Keep it to what a new contributor actually needs
to orient themselves; don't restate the whole codebase.
-->

## Layers

<!-- TODO: Controller -> Service -> Repository, what each layer owns -->

## Data access

<!-- TODO: the two DynamoDB collection abstractions (single hash key vs.
composite hash+range key), why both exist, which entity uses which -->

## Error handling

<!-- TODO: how domain exceptions map to HTTP status codes -->

## API surface

<!-- TODO: brief endpoint overview, pointing at openapi.json/README for
the full contract rather than duplicating it -->

## Key technical decisions

<!-- TODO: decisions worth knowing the "why" of, not just the "what" -->
