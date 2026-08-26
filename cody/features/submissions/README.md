# Submissions feature

## Status

- Lifecycle: **Planned**
- Extension loaded: **No**
- Project labels: `area: submissions`, `area: backend`, `area: integrations`
- Existing code: package and documentation only

## Purpose

Present backend-authorized submission metadata for the invoking participant's
team without transferring source code or exposing storage infrastructure.

## Current implementation

There are no commands, services, models, providers, or loaded extension. Cody
does not access submission storage or metadata today.

## Intended scope

- Read-only `team.submissions` and `submission.get` presentation.
- Approved ID, label/version, language, status, creation time, and active/current
  metadata only.
- Cursor pagination and private, Discord-safe views.
- No uploads, file downloads, source inspection, validation, or modification.

## Dependencies and boundaries

- Follow [`CODY_INTEGRATION_SPEC.md`](../../../CODY_INTEGRATION_SPEC.md).
- The Main Backend resolves team ownership and resource visibility.
- Cody never connects to S3/object storage, hashes files, or sees credentials.
- Services use the shared backend client; cogs/views never parse raw responses.
- Team information remains owned by the teams feature/backend.

## Development checklist

- [x] Lock Cody to read-only submission metadata.
- [ ] Finalize metadata fields, statuses, visibility, ordering, and pagination.
- [ ] Add provider-neutral models and strict response translation.
- [ ] Implement read-only list/detail services, commands, and views.
- [ ] Define cache/staleness and unavailable behavior.
- [ ] Load only after privacy, backend, and Discord acceptance checks pass.

## Testing

Cover actor/team authorization, private/not-found behavior, pagination,
timestamps, status enums, malformed responses, outages, mention safety, Discord
limits, and architecture checks proving no source/storage integration exists.

## Operational notes

Responses should normally be ephemeral. Cody needs no elevated Discord
permission and must never display storage URLs, hashes used as infrastructure
keys, source code, or raw backend diagnostics. Final schemas/TTLs remain open.
