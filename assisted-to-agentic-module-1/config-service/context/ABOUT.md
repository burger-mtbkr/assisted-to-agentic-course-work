# About Config API

## Name

Config API (`config-service`)

## Description

A REST API for centrally storing and retrieving per-application configuration
and feature flags. Callers register an `application`, then create key/value
`configuration` entries and boolean `flag`s scoped to that application.
Backed by AWS DynamoDB, deployable for real (not a demo/in-memory service) -
C#, .NET 10, ASP.NET Core MVC, Controller -> Service -> Repository.

## Justification

Application config and feature toggles tend to end up scattered across
`.env` files, hardcoded constants, and per-team ad hoc stores, with no
consistent way to read or update either without a redeploy. Config API
gives every application one place to register itself and manage both
through a uniform REST interface, with each entry independently
readable/writable at runtime.

## Personas

- **Backend engineering teams** - the primary consumer. Register their
  application once, then read/write its configuration entries and feature
  flags programmatically against `/api/v1/applications/{id}/configurations`
  and `/api/v1/applications/{id}/flags` - see `README.md`'s "Consuming
  feature flags safely" for the read pattern.
- **Administrators** - manage applications, configuration values, and
  feature flags directly, without hand-crafting API calls, via the Admin UI
  (`ui/`, this module).

## Domain context

- **Application** - a registered service/system that owns configuration.
  Identified by a generated `id`; `name` must be unique across all
  applications (`POST` with a duplicate name returns `409 Conflict`).
- **Configuration entry** - a `configKey`/`value` pair belonging to exactly
  one application (`applicationId` is a required reference, the DynamoDB
  equivalent of a foreign key). `configKey` is unique within its application.
- **Feature flag** - a `flagKey`/`enabled` (boolean) pair belonging to
  exactly one application, same shape and uniqueness rule as a configuration
  entry. Boolean only for now - no percentage rollout or audience targeting.
- An application cannot be deleted while it still has configuration entries
  or feature flags (`DELETE` returns `409 Conflict` until both are removed
  first).

## Scope

In scope today: CRUD for applications and their configuration entries,
per-application boolean feature flags (Module 3 - a separate `flags` table,
`applicationId` + `flagKey`, same shape as configuration entries), plus a
dependency-free `GET /health` check. Explicitly not in scope yet:

- **Authentication/authorization** - the API currently has no auth layer;
  anyone who can reach it can read and write any application's config.
- **Config versioning/rollback and multi-environment separation** - a single
  flat value per key, no history.
