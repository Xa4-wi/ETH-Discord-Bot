# Ladder feature

## Status

- Lifecycle: **Planned**
- Extension loaded: **No**
- Project label: `area: ladder`
- Existing code: package, cog, service, and view placeholders; empty rank content

## Purpose

Let participants and organizers inspect ETH Battlecode standings, team ratings,
ranks, and progression through clear Discord interfaces.

## Current implementation

No ladder commands or calculations exist. `content/ranks/ranks.json` is empty,
the feature modules are placeholders, and the shared domain layer has no rating
model. Server statistics currently displays only a provider-supplied ladder
leader and does not implement the ladder itself.

## Intended scope

- Read-only standings and individual team-rank lookup.
- Rank presentation based on approved competition rules and content.
- Pagination or filtering for lists that exceed one Discord response.
- Clear handling of unranked teams, tied ratings, provisional results, and
  competition phases.

Rating calculation and result authority must be decided before implementation.
If the official backend owns ratings, Cody should display translated backend
data instead of independently recomputing it.

## Dependencies and boundaries

- Team identity comes from the teams feature/shared team model.
- Match results come from the matches feature or official backend adapter.
- Rank names and thresholds belong in validated structured content.
- Backend JSON translation belongs in a provider/integration, not `views.py`.
- Server statistics may consume the resolved leader but must not become the
  ladder's source of truth.

## Development checklist

- [ ] Approve rating ownership, tie behavior, and rank/provisional rules.
- [ ] Define provider-neutral ladder and standing models.
- [ ] Populate and validate `content/ranks/ranks.json` if rank content is used.
- [ ] Implement a provider or service for standings and team lookup.
- [ ] Define the first slash commands and pagination behavior.
- [ ] Build Cody-styled standings and team-rank views.
- [ ] Handle unavailable/stale data without presenting false standings.
- [ ] Add extension setup and update the server-stats integration if appropriate.
- [ ] Document final commands, data source, and refresh semantics here.

## Testing

- Test ordering, ties, rank boundaries, unranked teams, and empty standings.
- Test malformed/stale provider data and backend outages.
- Test pagination limits and Discord-safe display lengths.
- Verify the ladder leader agrees with the complete standings snapshot.
- Run integration tests against a fixed representative ladder fixture.

## Operational notes

Read-only commands normally need no elevated user permissions. Any organizer
operation that changes ratings requires explicit authorization, audit behavior,
and an approved source-of-truth design.
