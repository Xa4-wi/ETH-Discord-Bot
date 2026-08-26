# Matches feature

## Status

- Lifecycle: **Planned**
- Extension loaded: **No**
- Project labels: `area: matches`, `area: backend`, `area: integrations`
- Existing code: package, cog, service, view, and shared-model placeholders

## Purpose

Give participants read-only Discord access to backend-authorized match history,
status, details, and results while keeping all orchestration in the official
website/backend/infrastructure flow.

## Current implementation

No match commands, service, response model, or provider exists. Server
statistics may display one aggregate `matches_today` value but does not own
match records. Nothing in this feature is loaded.

## Intended scope

- Read-only `match.list`, `match.get`, `match.status`, and `match.result`.
- Backend-defined states, participants, timing, outcomes, and safe failures.
- Opaque cursor pagination and documented UTC timestamp presentation.
- Clear unavailable/stale behavior without inventing state.

Cody will never schedule, cancel, retry, delete, or modify a match. This is a
locked boundary, not an open future option.

## Dependencies and boundaries

- Follow [`CODY_INTEGRATION_SPEC.md`](../../../CODY_INTEGRATION_SPEC.md).
- The Main Backend owns visibility, state translation, outcomes, and access to
  match/result infrastructure.
- Match services use `cody.integrations.backend`; cogs/views do not parse JSON or
  communicate with infrastructure.
- Teams and ladder consume only backend-approved match/team models.
- Server statistics consumes only `statistics.summary`, never match lists.
- No Discord role grants access to private match data.

## Development checklist

- [x] Lock Cody to read-only match actions.
- [ ] Finalize match states, visibility, result fields, timestamps, and paging.
- [ ] Define strict provider-neutral models and backend translation.
- [ ] Implement a service using the shared backend client and safe error mapping.
- [ ] Define list/detail/status/result commands and autocomplete boundaries.
- [ ] Build pagination and timezone-aware views.
- [ ] Define short TTL/staleness behavior for active states.
- [ ] Load only after contract, outage, privacy, and Discord acceptance checks.

## Testing

Cover every approved state, missing/private resources, ties/cancellations,
pagination, timestamp validation, backend timeout, invalid content type/JSON,
schema errors, stale data, and Discord limits. Tests must assert the action
allow-list contains no match mutation and that repeated reads never trigger
infrastructure operations.

## Operational notes

Read-only commands normally require no elevated Discord permissions. Cody must
display a generic unavailable response rather than guess a state. Final match
enum, visibility, replay/log fields, and cache TTL remain open in the integration
spec and block production activation.
