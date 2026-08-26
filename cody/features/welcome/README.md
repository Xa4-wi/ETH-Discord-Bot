# Welcome feature

## Status

- Lifecycle: **Active**
- Extension loaded: **Yes** (`cody.features.welcome.cog`)
- Project label: `area: welcome`
- Event: Discord member join
- Admin command: `/test_welcome`
- Required command role: Admin (`1540821890510229571` by default)

## Purpose

Welcome each new Discord member with a personalized ETH Battlecode arrival card,
clear first steps, and direct navigation to the rules and world channels.

## Current implementation

When `on_member_join` fires, the service resolves the configured welcome channel,
renders a 1200×675 PNG in memory, and sends it inside a Components V2 layout. The
card contains the member avatar/display name, arrival count, and a randomized
quote loaded from `assets/welcome/welcome_quotes.json`.

The renderer wraps, resizes, and truncates quotes to keep them inside the inner
panel. Missing or malformed quote data uses a safe fallback. The Components V2
message includes Rules and Explore World buttons using configured channel IDs.
Administrators can run `/test_welcome`; it uses the same production service and
their own member profile.

## Intended scope

- Member-join trigger and safe delivery to one configured welcome channel.
- In-memory visual-card rendering and welcome-specific assets/content.
- First-step navigation relevant to onboarding.
- An administrator-only path for verifying the real production flow.

Role assignment, team information, lore browsing, and general announcements
remain owned by their respective features.

## Dependencies and boundaries

- Channel IDs and asset/font paths come from `cody.config`.
- Runtime artwork and quotes live under `assets/welcome`; code must not embed
  large content lists or images.
- Shared buttons/colors come from `cody.shared`.
- `cog.py` owns Discord triggers, `service.py` delivery, `renderer.py` pixels,
  `quotes.py` content selection, and `views.py` Components V2 layout.
- The feature needs the Server Members Intent but does not persist member data or
  generated cards.

## Development checklist

- [x] Handle member joins through one reusable service.
- [x] Render personalized cards in memory.
- [x] Load randomized JSON quotes with a fallback.
- [x] Keep all quote text within the card border.
- [x] Provide Rules and Explore World navigation.
- [x] Provide the admin-only `/test_welcome` command.
- [x] Load the extension during startup.
- [ ] For future layout/content changes, update focused render and Components V2
  tests in the same change.
- [ ] Keep asset names, dimensions, IDs, and operator instructions documented.

## Testing

Coverage lives in `tests/welcome/` and checks quote normalization/fallback,
project quote availability, pixel dimensions, supplied-quote rendering, quote
fit constraints, member-count fallback, and Components V2 attachment wiring.

After artwork or typography changes, run the full suite and manually inspect a
card generated through `/test_welcome` in Discord at normal and mobile widths.

## Operational notes

Configuration variables:

- `CODY_WELCOME_CHANNEL_ID`
- `CODY_RULES_CHANNEL_ID`
- `CODY_WORLD_CHANNEL_ID`
- `CODY_ADMIN_ROLE_ID`

Cody needs View Channel, Send Messages, Embed Links, Attach Files, and Read
Message History in the welcome channel. `/test_welcome` requires Cody's
configured Admin role and its status response is ephemeral. Discord's generic
Administrator flag alone does not grant command access. Tokens, private profile
data, and rendered cards are never written to disk by this feature.

The command uses Discord's Administrator visibility default so participant roles
do not see it in the command picker. Server owners can override visibility under
the Cody integration, but the configured Admin-role check still runs.
