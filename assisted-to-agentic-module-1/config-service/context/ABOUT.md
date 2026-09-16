# About Config API

## Name

Config API (`config-service`)

## Description

A REST API for centrally storing and retrieving per-application configuration.
Callers register an `application`, then create key/value `configuration`
entries scoped to that application. Backed by AWS DynamoDB, deployable for
real (not a demo/in-memory service) - C#, .NET 10, ASP.NET Core MVC,
Controller -> Service -> Repository.

## Justification

Application config (feature toggles aside - see Scope) tends to end up
scattered across `.env` files, hardcoded constants, and per-team ad hoc
stores, with no consistent way to read or update it without a redeploy.
Config API gives every application one place to register itself and manage
its configuration through a uniform REST interface, with each entry
independently readable/writable at runtime.

## Personas

- **Backend engineering teams** - the primary consumer. Register their
  application once, then read/write its configuration entries
  programmatically against `/api/v1/applications/{id}/configurations`.
- **Administrators** - manage applications and configuration values directly,
  without hand-crafting API calls, via the Admin UI (`ui/`, this module).

## Domain context

- **Application** - a registered service/system that owns configuration.
  Identified by a generated `id`; `name` must be unique across all
  applications (`POST` with a duplicate name returns `409 Conflict`).
- **Configuration entry** - a `configKey`/`value` pair belonging to exactly
  one application (`applicationId` is a required reference, the DynamoDB
  equivalent of a foreign key). `configKey` is unique within its application.
- An application cannot be deleted while it still has configuration entries
  (`DELETE` returns `409 Conflict` until they're removed first).

## Scope

In scope today: CRUD for applications and their configuration entries, plus
a dependency-free `GET /health` check. Explicitly not in scope yet:

- **Feature flags** - planned for Module 3 (a separate `flags` table keyed
  by `applicationId` + `flagKey`, already reserved as migration slot `0003`).
- **Authentication/authorization** - the API currently has no auth layer;
  anyone who can reach it can read and write any application's config.
- **Config versioning/rollback and multi-environment separation** - a single
  flat value per key, no history.
