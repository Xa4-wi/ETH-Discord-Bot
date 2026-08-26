# Teams feature

## Status

- Lifecycle: **Planned**
- Extension loaded: **No**
- Project labels: `area: teams`, `area: backend`, `area: integrations`
- Existing code: package, cog, service, view, and shared-model placeholders

## Purpose

Present the invoking participant's canonical ETH Battlecode team and approved
member/submission metadata inside Discord. Team registration and management
remain website/backend workflows.

## Current implementation

No team commands, service, response model, or backend gateway exists. The files
are unloaded placeholders and must not be described as an available feature.

## Intended scope

- Read-only `team.get`, `team.members`, and `team.submissions` actions.
- Backend-authorized display of the actor's own team information.
- Pagination and Discord-safe presentation of approved member metadata.
- User-safe handling for unlinked participants and participants without teams.

Cody will not create, rename, disband, invite to, join, leave, or otherwise
modify teams. Those operations are explicitly outside this feature.

## Dependencies and boundaries

- Follow [`CODY_INTEGRATION_SPEC.md`](../../../CODY_INTEGRATION_SPEC.md).
- Identity is the immutable interaction user ID; the Main Backend resolves the
  participant/team and authorizes every response.
- The Participant Discord role may improve command visibility but never grants
  backend team access.
- The service consumes a provider/gateway backed by
  `cody.integrations.backend`; cogs and views make no HTTP calls.
- Cody has no team database, migrations, membership constraints, or write API.
- Match and ladder features may consume approved team display models but never
  mutate rosters.

## Development checklist

- [x] Lock team ownership and all mutations to the website/Main Backend.
- [ ] Finalize `team.get`, `team.members`, and `team.submissions` schemas.
- [ ] Finalize member-field visibility, ordering, and cursor pagination.
- [ ] Add provider-neutral read models and strict response translation.
- [ ] Implement the feature service using the shared backend client.
- [ ] Define read-only commands and Cody-styled private/public views.
- [ ] Handle `USER_NOT_LINKED`, `NO_TEAM`, permission, timeout, and schema errors.
- [ ] Load the extension only after contract and Discord acceptance checks pass.

## Testing

Tests must verify unchanged Discord snowflakes, actor/guild/interaction context,
backend authorization failures, no-team behavior, pagination, Discord limits,
mention safety, and unavailable/malformed responses. An architecture test should
continue to reject team write actions and direct database access.

## Operational notes

Read-only team commands need ordinary Discord response permissions. They do not
need Manage Roles or Administrator. Names and Discord roles are presentation
data only; no response should expose unnecessary backend or Discord identifiers.
Backend configuration and open schemas are documented in the integration spec.
