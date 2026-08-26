# Event status feature

## Status

- Lifecycle: **Planned**
- Extension loaded: **No**
- Project labels: `area: events`, `area: backend`, `area: integrations`
- Existing code: package and documentation only

## Purpose

Present canonical competition phase, availability flags, deadlines, and public
system state in Discord without hardcoded competition decisions.

## Current implementation

There is no event-status command, service, provider, model, or loaded extension.
No active feature currently treats local event flags as canonical.

## Intended scope

- Read-only `event.status` presentation.
- Backend-defined phase, submission/competition flags, deadlines, and `as_of`.
- Short-lived caching with visible staleness when approved.
- Public or actor-scoped behavior according to the final backend contract.

## Dependencies and boundaries

- Follow [`CODY_INTEGRATION_SPEC.md`](../../../CODY_INTEGRATION_SPEC.md).
- The Main Backend owns all event state and deadline semantics.
- Announcements may consume approved backend event information but own delivery.
- Cody does not infer phases from dates, channels, roles, or local constants.
- Services use `cody.integrations.backend`; views never parse backend JSON.

## Development checklist

- [x] Lock event-state authority to the Main Backend.
- [ ] Finalize phase enum, flags, deadline semantics, and visibility.
- [ ] Define strict provider-neutral models and response translation.
- [ ] Implement service, read-only command, and Cody-styled status view.
- [ ] Define short cache TTL, stale labeling, and outage behavior.
- [ ] Load only after backend and Discord acceptance checks pass.

## Testing

Cover every approved phase, timezone-aware RFC3339 timestamps, deadline
boundaries, public/actor authorization, cache isolation/staleness, malformed
responses, outages, Discord limits, and the absence of hardcoded authority.

## Operational notes

Public status needs only ordinary Discord response permissions. Final phase
values, deadlines, public-versus-actor access, cache TTL, and system-health
visibility remain open in the integration specification.
