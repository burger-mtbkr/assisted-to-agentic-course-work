# Work Item 001: Feature Flags

## Story Details

> As an **application developer**, I want **feature flags per application**,
> so that **I can enable or disable functionality without deploying code
> changes**

### Notes

`infra/README.md` already reserves migration `0003` for a `flags` table,
shape already decided: `applicationId` partition key + `flagKey` sort key -
the same composite-key shape as `configurations` (see
`context/ARCHITECTURE.md`). A `Flags` vertical slice (`Controllers/Flags`,
`Services/Flags`, `Repositories/Flags`, `Models/Flags`, `Exceptions/Flags`)
mirrors the existing `Configurations` slice file-for-file. Flags are boolean
to start - no percentage rollout or audience targeting unless a real need
shows up.

### Acceptance Criteria (Given-When-Then)

#### Task 1: Feature Flag Domain Model and API Contract

- **Given**: The Configuration Service already stores per-application
  configuration entries with an established composite-key pattern
- **When**: We define the feature flag shape and API contract
- **Then**: A documented schema exists for boolean flags (`applicationId`,
  `flagKey`, `enabled`, optional `description`), plus the migration
  (`0003_CreateFlagsTable.cs`) and validation rules needed to support it
- **Status**: Complete

#### Task 2: Backend Feature Flag Management

- **Given**: The feature flag schema and migration are agreed
- **When**: The `Flags` vertical slice is implemented (repository, service,
  controller)
- **Then**: `/api/v1/applications/{applicationId}/flags` supports create,
  read, update, and delete, following the same patterns and error handling
  as `configurations`
- **Status**: Complete

#### Task 3: UI Feature Flag Administration

- **Given**: Backend feature flag support exists
- **When**: An administrator opens the Admin UI for an application
- **Then**: They can view and toggle feature flags for that application
  alongside its existing configuration entries
- **Status**: Complete

#### Task 4: Client Consumption Pattern

- **Given**: Feature flags can be stored and retrieved via the API
- **When**: A consuming application needs to read a flag
- **Then**: `README.md` documents a safe pattern for reading a flag,
  handling a missing flag (not the same as "explicitly disabled"), and
  applying a default
- **Status**: Complete

#### Task 5: Rollout and Quality Validation

- **Given**: Feature flag functionality is implemented end to end
- **When**: We validate the whole feature
- **Then**: `npm run check` is clean, `context/ARCHITECTURE.md` and
  `context/IMPLEMENTATION.md` reflect the new slice, and the work item is
  purged down to its acceptance criteria
- **Status**: Not Started

## Current Task Focus

- **Active task**: Task 5 - Rollout and Quality Validation
- **Stage**: PLAN - Not Started
- **Last updated**: 2026-09-17

*Tasks 1-4 committed and purged - see commit history for detail. Task 4's
documentation pass surfaced a real gap while writing the "delete an
application" note: `ApplicationService.DeleteAsync`'s existing
delete-with-children guard only checked configuration entries, not flags -
an application with only flags (no config) could be deleted, orphaning its
flags in DynamoDB. Fixed as part of this task (extended the guard to check
both), not deferred, since it's the same "same patterns as configurations"
behavior Task 2's AC already called for. Verified live: created an app with
only a flag, confirmed `DELETE` returned 409, removed the flag, confirmed
`DELETE` then returned 204.*
