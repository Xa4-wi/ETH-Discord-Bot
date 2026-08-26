# Ladder feature

## Status

- Lifecycle: **Planned**
- Extension loaded: **No**
- Project labels: `area: ladder`, `area: backend`, `area: integrations`
- Existing code: package, cog, service, and view placeholders; empty rank content

## Purpose

Present canonical backend-computed standings, team ratings, ranks, layers, and
progression in Discord without implementing competition calculations in Cody.

## Current implementation

No ladder commands, models, calculations, or provider exist. Server statistics
can display a provider-supplied leader summary but is not a leaderboard source.
`content/ranks/ranks.json` is empty and nothing here is loaded.

## Intended scope

- Read-only `ranking.get` and `ranking.leaderboard` actions.
- Backend ordering, ties, provisional/unranked state, and phase-aware results.
- Opaque cursor pagination and Discord-safe presentation.
- Optional local descriptions/artwork for ranks, never calculation thresholds.

Elo, rating changes, rank thresholds, layer assignment, match outcomes, and
leaderboard ordering are exclusively Main Backend responsibilities.

## Dependencies and boundaries

- Follow [`CODY_INTEGRATION_SPEC.md`](../../../CODY_INTEGRATION_SPEC.md).
- Backend JSON translation belongs behind the shared backend client/provider,
  not in cogs or views.
- Team and match identities are opaque backend data.
- `content/ranks` may contain approved presentation copy only. Cody must not use
  it to derive a team's official state.
- Server statistics may display the returned leader but never becomes canonical.

## Development checklist

- [x] Lock ranking and ordering authority to the Main Backend.
- [ ] Finalize ranking fields, public/actor visibility, ties, and pagination.
- [ ] Define strict provider-neutral ranking and standing models.
- [ ] Decide whether approved rank descriptions/artwork are needed.
- [ ] Implement read services using `cody.integrations.backend`.
- [ ] Define read-only commands and paginated Cody-styled views.
- [ ] Handle unavailable, stale, unranked, and malformed responses safely.
- [ ] Load only after backend contract and Discord acceptance checks pass.

## Testing

Test backend-provided order without local recalculation, ties, provisional and
unranked states, empty pages, cursors, malformed/stale responses, outages, and
Discord limits. Verify the displayed summary leader agrees with a fixed backend
fixture and no local file can alter official rating/rank/layer values.

## Operational notes

Read-only commands need no elevated Discord permission. The feature must show an
`as_of`/last-success indicator for cached data once caching exists. Final fields,
visibility, ordering, cursor lifetime, and cache TTL remain open in the
integration specification.
