# Teams feature

## Status

- Lifecycle: **Planned**
- Extension loaded: **No**
- Project label: `area: teams`
- Existing code: package, cog, service, view, and shared team-model placeholders

## Purpose

Let participants register, inspect, and manage ETH Battlecode teams through
Discord while enforcing competition membership and organizer rules.

## Current implementation

No team commands, registration service, storage, or model fields exist.
`cody/models/team.py`, `cody/integrations/database.py`, and the feature modules
are placeholders. Nothing in the team feature is currently loaded.

## Intended scope

- Create and inspect a team using a stable team identifier.
- Join, leave, invite, or remove members according to approved roster rules.
- Assign team ownership/captain responsibilities and handle transfers safely.
- Enforce unique membership, team-size limits, deadlines, and locked competition
  phases when those rules are finalized.
- Present organizer-safe recovery actions without exposing private user data.

## Dependencies and boundaries

- Discord member identity should map to a persistent player/team model by ID.
- Durable registration requires the database integration; in-memory state is not
  sufficient.
- Official website/backend ownership must be decided before Cody writes team data.
- Match and ladder features consume team identity but must not mutate rosters.
- Administrative recovery may be exposed through the admin feature while team
  invariants remain enforced by this service.

## Development checklist

- [ ] Approve roster size, ownership, invite, deadline, and duplicate-member rules.
- [ ] Decide whether Cody or the official backend is the source of truth.
- [ ] Define player/team models, stable IDs, and database constraints.
- [ ] Implement persistence and migrations before accepting registrations.
- [ ] Define the first participant and organizer commands.
- [ ] Implement atomic service operations and clear domain errors.
- [ ] Build private/public views with appropriate data disclosure.
- [ ] Add extension setup only after restart and concurrency tests pass.
- [ ] Document final commands, schema, configuration, and recovery process here.

## Testing

- Test create, invite, join, leave, ownership transfer, and disband rules.
- Test duplicate requests, concurrent joins, full teams, and locked deadlines.
- Test persistence across bot restart and migration rollback/recovery behavior.
- Verify users cannot modify teams they do not control.
- Verify public responses reveal no unnecessary Discord or backend identifiers.

## Operational notes

Registration actions should generally respond ephemerally until a change is
confirmed. Cody needs only the Discord permissions required for its command
responses and any explicitly approved role assignment; it should not require
Administrator.
