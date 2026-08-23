# Server statistics feature

## Status

- Lifecycle: **Active**
- Extension loaded: **Yes** (`cody.features.server_stats.cog`)
- Project labels: `area: discord`, `area: backend`, `area: integrations`
- Admin commands: `/stats refresh`, `/stats permissions`
- Required command role: Admin (`1540821890510229571` by default)
- Scheduled refresh: every ten minutes

## Purpose

This feature maintains eight display-only Discord voice channels. Four values
come directly from Discord and four come from a replaceable competition-stats
provider. Discord-facing code never depends on the provider's JSON schema.

## Current implementation

Cody counts human members and configured layer roles from Discord, then combines
them with a provider-neutral `CompetitionStats` snapshot. Static development
values work without a backend; the HTTP provider consumes one aggregate endpoint
through a reusable session. Changed channel names are updated, unchanged names
are skipped, and the last successful competition values are retained after a
provider failure. The extension, admin commands, mock endpoint, and focused tests
are implemented and active.

## Intended scope

- Permanent Discord display channels for the eight documented statistics.
- Direct Discord authority for member and layer-role counts.
- Replaceable aggregate providers for competition-owned values.
- Periodic and staff-triggered refresh through one shared service.
- Effective permission reporting without exposing provider credentials.

Detailed ladder, match, and team records remain in their own features; this
feature consumes only the aggregate values needed for permanent displays.

## Dependencies and boundaries

- Channel and role IDs come from `cody.config` and are never resolved by name.
- HTTP response translation belongs in `providers.py`, not the cog or service.
- Discord collection and channel naming belong in `service.py`.
- The mock JSON under `docs/api` is public placeholder data, never private state.
- The Server Members Intent supplies member/role data; the bot does not need
  Administrator permission.

## Module responsibilities

| Module | Responsibility |
| --- | --- |
| `cog.py` | Ten-minute task loop and admin-only `/stats refresh` and `/stats permissions` commands |
| `service.py` | Discord counts, formatting, caching, and changed-name-only channel updates |
| `providers.py` | Static and aggregate HTTP provider implementations |
| `models.py` | Provider-neutral statistics, configuration, snapshot, and result models |
| `constants.py` | Refresh, formatting, and assembled ID configuration |

The persistent `ServerStatsService` keeps the most recent successful
`CompetitionStats`. If an HTTP request or schema validation fails, Cody leaves
those competition displays at their last good values, logs the failure, and
still refreshes Discord-derived values.

## Discord configuration

The supplied IDs are runtime defaults. Override any of them with its environment
variable when cloning the bot into another server.

### Roles

| Layer | Default role ID | Environment variable |
| --- | ---: | --- |
| Umbral City | `1541114274079051959` | `CODY_STATS_UMBRAL_ROLE_ID` |
| The Lumen Belt | `1541114432954830868` | `CODY_STATS_LUMEN_ROLE_ID` |
| Helio-Citadels | `1541114604002873395` | `CODY_STATS_HELIO_ROLE_ID` |

### Channels

| Display | Data owner | Default channel ID | Environment variable |
| --- | --- | ---: | --- |
| Members | Discord | `1541109424796602418` | `CODY_STATS_MEMBERS_CHANNEL_ID` |
| Umbral City | Discord role | `1541109668263362691` | `CODY_STATS_UMBRAL_CHANNEL_ID` |
| The Lumen Belt | Discord role | `1541109719530344538` | `CODY_STATS_LUMEN_CHANNEL_ID` |
| Helio-Citadels | Discord role | `1541109796063674519` | `CODY_STATS_HELIO_CHANNEL_ID` |
| Active Teams | Provider | `1541111483897749534` | `CODY_STATS_ACTIVE_TEAMS_CHANNEL_ID` |
| Matches Today | Provider | `1541111104661495929` | `CODY_STATS_MATCHES_TODAY_CHANNEL_ID` |
| Grid Output | Provider | `1541111224882823239` | `CODY_STATS_GRID_OUTPUT_CHANNEL_ID` |
| Ladder Leader | Provider | `1541111316310396949` | `CODY_STATS_LADDER_LEADER_CHANNEL_ID` |

Cody locates channels and roles only by ID. Channel names can therefore change
without breaking subsequent refreshes.

## Display format

```text
👥 Members · 123
🌑 Umbral City · 64
🪞 The Lumen Belt · 41
☀️ Helio-Citadels · 18

⚔️ Active Teams · 27
🎮 Matches Today · 143
☀️ Grid Output · 84.7 GW
🏆 Ladder Leader · Team X
```

Names are whitespace-normalized and truncated to Discord's 100-character
channel-name limit. Cody compares the desired name with the current name before
calling Discord's edit API.

## Provider configuration

Static development data is the default:

```text
CODY_STATS_PROVIDER=static
```

To use one aggregate JSON endpoint instead:

```text
CODY_STATS_PROVIDER=http
CODY_STATS_ENDPOINT=https://xa4-wi.github.io/ETH-Discord-Bot/api/server-stats.json
```

The HTTP provider accepts the repository mock shape:

```json
{
  "active_teams": 12,
  "matches_today": 37,
  "grid_output": 42.8,
  "ladder_leader": "Team X"
}
```

It also accepts a future backend response where `ladder_leader` is an object
containing a `name`. Provider translation keeps backend response changes out of
the service and cog.

`CODY_STATS_INCLUDE_BOTS` defaults to `false`. Set it to `true` if the Members
display should use Discord's complete guild member count, including bots.

## Discord permissions

Cody needs **View Channel** and **Manage Channels** for these channels. It does
not need Administrator permission. The Server Members Intent must remain enabled
so layer-role counts use the member cache.

Configure the statistic voice channels as display-only:

```text
@everyone: View Channel = allowed, Connect = denied, Speak = denied
Cody:      View Channel = allowed, Manage Channels = allowed
```

The `/stats` commands require Cody's configured Admin role, respond ephemerally,
and do not expose provider credentials. `/stats permissions`
reports the resolved Cody member ID, assigned role IDs, and effective View
Channel/Manage Channels result for every display channel.

The `/stats` group uses Discord's Administrator visibility default so ordinary
roles do not see its subcommands in the command picker. This default is applied
to the group because Discord ignores visibility defaults placed on subcommands.
The configured Admin-role runtime check remains authoritative.

## Extending the feature

Add backend fields to `CompetitionStats`, translate them inside the provider,
and format selected permanent displays in `service.py`. Do not parse HTTP data
in the cog, search for channels by name, or create separate backend requests for
each channel.

## Development checklist

- [x] Configure all supplied channel and role IDs with environment overrides.
- [x] Count Members, Umbral City, The Lumen Belt, and Helio-Citadels from Discord.
- [x] Implement static and reusable-session HTTP providers.
- [x] Cache the most recent successful competition statistics.
- [x] Rename only channels whose desired name changed.
- [x] Add ten-minute refresh and the admin-only `/stats refresh` command.
- [x] Add `/stats permissions` for Cody's identity, roles, and effective access.
- [x] Publish and document the optional aggregate mock endpoint.
- [x] Load the extension and cover provider/service/configuration behavior.
- [ ] Replace development values with the official aggregate endpoint when its
  contract and production URL are approved.
- [ ] Update this README whenever a permanent statistic is added or removed.

## Testing

Coverage under `tests/server_stats/` verifies supplied ID defaults, static and
future response translation, invalid data rejection, bot exclusion, role counts,
documented channel formats, Discord's name limit, changed-name-only edits, mock
JSON compatibility, and cached fallback after provider failure.

Before deployment, run `/stats permissions`, force `/stats refresh`, confirm every
configured channel is display-only, and verify Cody can manage those channels
without an Administrator role.

## Operational notes

The static provider contains visible development placeholders, not authoritative
competition results. Production should remain on `static` only while that is an
intentional operator choice. When switching to HTTP, configure one trusted HTTPS
aggregate endpoint and verify cached-failure behavior before deployment.

Cody requires View Channel and Manage Channels for all eight display channels,
while ordinary members should have Connect and Speak denied. `/stats refresh`
and `/stats permissions` require the configured Admin role and are ephemeral.
Provider credentials,
private backend responses, and Discord member details must not be added to the
public mock JSON or permission report.

The permission report checks the permissions this feature actually uses: View
Channel to resolve each display and Manage Channels to rename it. Administrator,
Connect, and Speak are explicitly not required. Missing or invisible channels
are reported by ID.
