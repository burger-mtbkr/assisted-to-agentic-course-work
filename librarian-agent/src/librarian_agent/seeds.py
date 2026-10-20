"""Starter decisions for config-service, each taken from its own docs and cited.

`librarian seed` writes these once, so the memory is useful before anyone has told
the Librarian anything. Re-running skips a seed whose title already has a note.
"""

from __future__ import annotations

from librarian_agent.notes import MemoryNote, NoteStore

SEEDS = [
    {
        "title": "Scan-and-cache reads instead of indexed queries",
        "statement": (
            "Both DynamoDB collection types read with a full table scan, cached for ScanCacheSeconds "
            "(appsettings.json, 300 by default) and invalidated on every write, instead of querying an index."
        ),
        "rationale": (
            "Fine at current scale and keeps the data-access layer small. Revisit with a GSI or query-based "
            "access if configurations grow large per application."
        ),
        "sources": [
            "context/ARCHITECTURE.md",
            "src/ConfigApi.Service/Infrastructure/DynamoDb/DynamoDbTableCache.cs",
            "src/ConfigApi.Service/appsettings.json",
        ],
        "entities": ["scan_cache"],
        "confidence": 0.95,
    },
    {
        "title": "Duplicate names and keys map to 409 Conflict",
        "statement": (
            "ErrorMiddleware maps DuplicateApplicationNameException, DuplicateConfigurationKeyException and "
            "DuplicateFlagKeyException to 409 Conflict, ApplicationNotFoundException to 404, and "
            "ValidationException and ArgumentException to 400."
        ),
        "rationale": (
            "A uniqueness violation conflicts with existing state; it is not malformed input, so clients can "
            "tell 'already exists' apart from 'bad request'. The 409s are part of the published contract "
            "(openapi.json). A missing child entity is a null/false service result, not an exception."
        ),
        "sources": [
            "context/ARCHITECTURE.md",
            "src/ConfigApi.Service/Middleware/ErrorMiddleware.cs",
            "src/ConfigApi.Service.UnitTests/Middleware/ErrorMiddlewareTests.cs",
            "openapi.json",
        ],
        "entities": ["error_response", "application"],
        "confidence": 0.9,
    },
    {
        "title": "Secrets in .env, settings in appsettings.json",
        "statement": (
            "AWS credentials come only from a git-ignored .env loaded by DotNetEnv as the first line of "
            "Program.cs; non-secret settings (DynamoDB table names, scan cache TTL) live in appsettings.json "
            "under DynamoDB."
        ),
        "rationale": "Secrets stay out of git; settings that should be reviewed stay in version control.",
        "sources": [
            "context/IMPLEMENTATION.md",
            "context/ENV_SCRIPTS.md",
            "src/ConfigApi.Service/Program.cs",
        ],
        "entities": [],
        "confidence": 0.95,
    },
    {
        "title": "Unit tests do not prove the DynamoDB layer",
        "statement": (
            "Unit tests mock the DynamoDB collection interfaces, so Infrastructure/DynamoDb and its DI "
            "wiring are verified by a live run against AWS, not by npm run test."
        ),
        "rationale": (
            "A missing AddHashKey call once passed every unit test and failed the first live request. "
            "Coverage deliberately excludes that layer: 'tests pass' is necessary but not sufficient there."
        ),
        "sources": [
            "context/IMPLEMENTATION.md",
            "context/ARCHITECTURE.md",
            "src/ConfigApi.Service.UnitTests/coverlet.runsettings",
        ],
        "entities": [],
        "confidence": 0.95,
    },
]


def seed(notes: NoteStore) -> list[MemoryNote]:
    existing = {n.title for n in notes.list()}
    return [notes.remember(**s) for s in SEEDS if s["title"] not in existing]
