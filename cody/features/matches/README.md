# Matches feature

## Status

- Lifecycle: **Planned**
- Extension loaded: **No**
- Project label: `area: matches`
- Existing code: package, cog, service, view, and shared match-model placeholders

## Purpose

Give teams and organizers reliable Discord access to match schedules, current
state, results, and approved match operations while keeping the official game
backend authoritative.

## Current implementation

No match commands, services, domain fields, provider, or views exist.
`cody/models/match.py` and `cody/integrations/battlecode_api.py` are placeholders.
Server statistics displays a provider-supplied `matches_today` total but does not
own match records.

## Intended scope

- Read match details and schedules using stable match identifiers.
- Show today's, upcoming, live, and completed matches once supported by the
  official backend.
- Present participants, timing, state, result, and relevant failure information.
- Add organizer actions only after backend contracts, authorization, and
  idempotency behavior are defined.

## Dependencies and boundaries

- Team identity and membership belong to the teams feature/shared team model.
- Ratings and standings updates belong to the ladder or official backend.
- External API request/response translation belongs in
  `cody/integrations/battlecode_api.py` or a match provider.
- The match service should consume provider-neutral models and must not make
  views depend directly on backend JSON.
- Announcements may consume match events but must own their delivery behavior.

## Development checklist

- [ ] Obtain the official match API contract and source-of-truth rules.
- [ ] Define match identifiers, states, timestamps, participants, and result model.
- [ ] Implement a reusable backend adapter with timeouts and explicit errors.
- [ ] Decide the first read-only commands and any autocomplete behavior.
- [ ] Build match list/detail views with timezone and pagination rules.
- [ ] Define caching, staleness display, retries, and outage behavior.
- [ ] Add authorized write operations only when the backend supports them safely.
- [ ] Add extension setup and connect `matches_today` through an aggregate provider.
- [ ] Document final commands, API assumptions, and permissions here.

## Testing

- Test every match state and legal state transition represented by Cody.
- Test missing teams, postponed/cancelled matches, ties, and unavailable results.
- Test backend timeout, invalid JSON, partial data, and stale-cache behavior.
- Verify all displayed times have a documented timezone.
- Verify repeated organizer actions cannot duplicate backend operations.

## Operational notes

Read-only match commands should not require elevated Discord permissions. Any
operation that changes match state must use granular staff authorization and
must never report success until the authoritative backend confirms it.
