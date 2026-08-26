# Participants feature

## Status

- Lifecycle: **Planned**
- Extension loaded: **No**
- Project labels: `area: participants`, `area: backend`, `area: integrations`
- Existing code: package and documentation only

## Purpose

Let a Discord user view the canonical ETH Battlecode participant profile linked
to their account without making Discord itself an identity database.

## Current implementation

There is no participant-profile command or loaded participant extension.
Website Discord OAuth and the Main Backend remain the only source of participant
linkage. The active Welcome feature now has a narrow typed
`BackendParticipantLinkProvider`: it calls `participant.get` only when a member
presses the Participant onboarding button and uses a valid result to assign the
local Discord Participant role. It does not display or persist the profile.

## Intended scope

- Read-only `participant.get` for the invoking actor.
- Safe display of backend-approved participant fields.
- Clear unlinked/not-found/unavailable responses with request references.
- No registration, login, linking, or profile modification in Discord.

## Dependencies and boundaries

- Follow [`CODY_INTEGRATION_SPEC.md`](../../../CODY_INTEGRATION_SPEC.md).
- Forward `interaction.user.id` plus guild/interaction context losslessly.
- The Main Backend resolves linkage and authorizes/filters the profile.
- The Welcome feature's role-verification use is documented in
  [`../welcome/README.md`](../welcome/README.md); shared participant profile UI
  remains owned by this planned feature.
- Discord names and roles are presentation/UX inputs, never identity authority.
- The feature service uses `cody.integrations.backend`; no raw HTTP in cogs/views.

## Development checklist

- [x] Lock authentication/linking to website Discord OAuth.
- [ ] Finalize the `participant.get` response schema and field visibility.
- [ ] Add provider-neutral profile models and strict response translation.
- [ ] Implement a read-only service, command, and Cody-styled view.
- [ ] Handle every standardized identity/backend failure safely.
- [ ] Load only after backend and Discord acceptance checks pass.

## Testing

Verify snowflake/context forwarding, linked/unlinked behavior, authorization,
unknown/missing fields, backend failures, request references, mention safety,
Discord limits, and the absence of local identity persistence or linking flows.

## Operational notes

The command should normally be ephemeral because participant profiles may
contain non-public fields. It needs no elevated Discord permission. Final fields,
cache TTL, and public/private presentation remain open in the integration spec.
