# ETH Discord Bot Test

The authoritative architecture and API boundary between Cody and the official
website backend is [`CODY_INTEGRATION_SPEC.md`](CODY_INTEGRATION_SPEC.md).
Backend-facing work must follow it before a feature is loaded in production.

## Running the bot securely

Never paste the Discord bot token into source code, configuration committed to Git, a command-line argument, or a chat message. `main.py` reads it only from the `DISCORD_TOKEN` environment variable.

### macOS

The native macOS launcher requires Python 3.9 or newer. From Terminal, complete this setup once from the repository directory:

```zsh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Start Cody with:

```zsh
./scripts/start-bot.sh
```

At the prompt, paste the token with Command+V and press Return. The hidden prompt deliberately displays no characters while you paste. It confirms the token's character count afterward without revealing the token.

For a long token, you can avoid pasting into Terminal entirely. Copy the token to the macOS clipboard, then run:

```zsh
./scripts/start-bot.sh --clipboard
```

The launcher reads the clipboard without printing the token or adding it to shell history. It uses the virtual environment automatically and removes `DISCORD_TOKEN` from its environment when Cody stops. Press Ctrl+C to stop the bot. Because macOS retains copied text, replace the token in your clipboard with non-sensitive text after Cody starts.

If the launcher is not executable after downloading the repository, run this once:

```zsh
chmod +x scripts/start-bot.sh
```

### Windows

From PowerShell, create a virtual environment and install the dependencies once:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start Cody with:

```powershell
.\scripts\start-bot.ps1
```

The PowerShell launcher also detects the repository virtual environment automatically and securely clears the token when Cody stops.

If script execution is disabled on Windows, run the launcher for the current session without changing the system policy:

```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/start-bot.ps1
```

For member welcome events to work, enable **Server Members Intent** for Cody in the Discord Developer Portal. Do not save the token in either launcher. Local `.env` files are ignored by Git as an additional safeguard, but this project does not require one.

## Command access roles

Cody authorizes application commands by Discord role ID:

| Access level | Default role ID | Environment override |
| --- | ---: | --- |
| Participant | `1541112817476702238` | `CODY_PARTICIPANT_ROLE_ID` |
| Sponsor | `1542162836791361576` | `CODY_SPONSOR_ROLE_ID` |
| Sponsor — Under Review | `1542164526022004877` | `CODY_SPONSOR_UNDER_REVIEW_ROLE_ID` |
| Visitor | `1542164969796272229` | `CODY_VISITOR_ROLE_ID` |
| Admin | `1540821890510229571` | `CODY_ADMIN_ROLE_ID` |
| Organiser | `1540821070213292125` | `CODY_ORGANIZER_ROLE_ID` |

Participant-facing commands accept either the Participant or Admin role. Admin
operations and diagnostics accept only the configured Admin role. Discord's
generic Administrator permission does not bypass these role-ID checks.

Ticket management is the exception to the two command levels: both the Admin
and Organiser roles can claim, release, and resolve private support tickets from
their buttons. `/tickets setup` and `/tickets status` remain Admin-only.

Admin commands are also marked with Discord's Administrator visibility default,
so they are hidden from ordinary roles in the command picker. The configured
Admin role must therefore have Discord's Administrator permission, or a server
owner must explicitly allow the commands under **Server Settings → Integrations
→ Cody**. The role-ID runtime check remains authoritative after any override.

Cody registers commands globally. On startup it removes obsolete guild-specific
copies left by older development synchronization, preventing duplicate entries.

## Discord operations log

Cody mirrors its own operational events to channel `1541131430682431518` using
readable severity-colored embeds. Configure another destination with
`CODY_LOG_CHANNEL_ID`. The Admin-only `/logs status` command checks channel
permissions, queue health, and delivery state; `/logs test` sends a safe test
event. Complete tracebacks remain in the terminal, and credentials are redacted
from Discord summaries. See
[`cody/features/monitoring/README.md`](cody/features/monitoring/README.md).

## Cody message style

Cody speaks as a concise network/interface AI. Traditional user-facing embeds should use `cody_embed` from `cody/shared/components.py` so titles, footer text, and colors remain consistent. Rich interfaces such as the welcome message use Discord Components V2 layouts from `cody/features/welcome/views.py`.

| Message type | Color | Intended use |
| --- | --- | --- |
| System | Gold `#E8A13C` | Welcome and general information |
| Success | Green `#7BD389` | Completed actions and healthy status |
| Warning | Rust `#D8A14A` | Deadlines and recoverable issues |
| Error | Dark rust `#8C3F22` | Invalid actions and failures |
| Umbral | Deep green `#244D3B` | Umbral rank messages |
| The Lumen Belt | Amber-gray `#8F8066` | The Lumen Belt rank messages |
| Citadels | Gold `#F1C75B` | Citadel rank messages |

Prefer short interface-style titles such as `ARRIVAL REGISTERED`, `TEAM REGISTERED`, `RANK UPDATED`, and `SYSTEM NOTICE`. Keep functional text clear and restrained, with occasional in-world flavor.

### Testing Discord messages

Administrators can run `/test_welcome` inside the server to send the real welcome card using their own member profile. The command invokes the same `send_welcome_message` function as the member-join event, so the test and production behavior stay identical. Its status response is visible only to the administrator. Welcome cards are generated in memory and are not stored on disk.

The welcome message now directs members to read and accept Rules before using
the Role-selection channel. Cody publishes the complete versioned behavior
rules with the supplied `rules-image.png` artwork and records acceptance through
a zero-permission `Rules Accepted` marker role. The persistent access panel then
offers Participant, Sponsor, and Visitor choices using `role-welcome.png`. Run
`/onboarding setup` to create or refresh both panels and validate the marker role, and
`/onboarding status` to audit its backend, channels, public
visibility, role hierarchy, and permissions. The status command performs a real
`participant.get` contract probe without displaying participant data. Both
commands are Admin-only.

## Repository structure

- `main.py` is the only executable entry point.
- `cody/bot.py` configures the Discord client and loads active extensions.
- `cody/config.py` owns environment configuration and channel IDs.
- `cody/features/` separates Discord triggers, services, views, and renderers by feature.
- `cody/features/README.md` indexes active and planned features and defines the required documentation format.
- `cody/features/server_stats/` maintains live statistics channels through replaceable data providers; its local README documents IDs and operation.
- `cody/integrations/backend/` is the only approved client boundary for official competition data.
- `cody/shared/` contains the palette, reusable components, permissions, errors, and logging.
- `assets/` contains runtime branding, fonts, and welcome artwork.
- `content/` contains structured lore and rank content.
- `tests/` mirrors the feature packages.
- `reference/` contains internal material that Cody does not load at runtime.
- `scripts/` contains local developer utilities.
- `docs/` contains only the static GitHub Pages website.

Runtime artwork uses descriptive, role-based names:

- `assets/branding/cody-icon.png` — Cody's master icon.
- `assets/branding/cody-banner.png` — current master Battlecode banner.
- `assets/branding/role-welcome.png` — centered three-role onboarding artwork.
- `assets/branding/rules-image.png` — centered server-rules panel artwork.
- `assets/welcome/umbral-background.png` — background consumed by the welcome renderer.
- `assets/welcome/welcome_quotes.json` — randomized welcome-card quotes.
- `content/community/server_rules.json` — validated, versioned server behavior rules.
- `assets/fonts/play-display.ttf` — display/body typeface.
- `assets/fonts/share-tech-system.ttf` — system-interface typeface.
- `docs/assets/cody-icon.png` and `docs/assets/cody-banner.png` — website-only copies.
- `reference/game-design/cody-banner-original.png` — retained original concept banner.

Run the automated checks from the repository root with:

```text
# macOS
.venv/bin/python -m unittest discover

# Windows PowerShell
.\.venv\Scripts\python.exe -m unittest discover
```

## Development planning

Use the repository's structured GitHub issue forms for bugs, features,
backend/integration work, and development tasks. The complete label taxonomy,
triage rules, project-board layout, and one-time setup command are documented
in [`DEVELOPMENT.md`](DEVELOPMENT.md).

## Server statistics

Cody updates the configured Members, layer, team, match, grid-output, and
ladder-leader voice channels every ten minutes. The supplied role/channel IDs,
provider settings, Discord permissions, failure behavior, and `/stats` admin
commands are documented in
[`cody/features/server_stats/README.md`](cody/features/server_stats/README.md).

The safe default is `CODY_STATS_PROVIDER=discord`: Cody refreshes human/community
role counts and marks backend-owned competition displays `Unavailable`. `static`
and `http` are explicit development-fixture modes only. Production aggregates
use `CODY_STATS_PROVIDER=backend`, `CODY_BACKEND_ENDPOINT`, and
`CODY_BACKEND_SERVICE_TOKEN`; this sends `statistics.summary` through the
versioned authenticated client.

## Main Backend integration

Cody has one official competition-data dependency: the Main Backend. The shared
client enforces the action allow-list, HTTPS, service authentication, request
IDs, idempotency on ticket mutations, strict response envelopes and sizes,
safe read retries, and user-safe errors. It remains inactive until backend
configuration is supplied, so local Discord-only operation does not require a
placeholder credential.

Cody never connects directly to a competition database, object storage, or
match infrastructure. Teams, matches, submissions, rankings, and event state
are read-only from Cody's perspective. See the complete current/target matrix,
wire format, ticket transition plan, and open production decisions in
[`CODY_INTEGRATION_SPEC.md`](CODY_INTEGRATION_SPEC.md).

## Welcome access onboarding

New members should initially see the member-count voice channel plus the
Welcome, Rules, and Role-selection text channels. Although the objective is
often described as “three channels,” these IDs define four visible entry
resources. Configure `@everyone` to see those four and deny every other
category/channel until Cody assigns an access role; `/onboarding status` audits
that public visibility but deliberately does not rewrite permission overwrites.

| Channel | Default ID |
| --- | ---: |
| Member-count VC | `1541109424796602418` |
| Welcome | `1540841975320813649` |
| Rules | `1540846388328275990` |
| Role selection | `1542168230896996352` |
| Sponsor review (staff only) | `1542176692791939232` |

Every role selection first requires the `Rules Accepted` marker. Acceptance
itself grants no channel access. Cody uses role `1542198825756794971` by default
and fails closed if it is missing, managed, has server permissions, or has any
channel overwrite. The later access role performs the unlock. The full editable rule text is stored in
`content/community/server_rules.json` and rendered in the Rules channel.

Participant selection uses the authenticated `participant.get` backend action.
Set `CODY_BACKEND_ENDPOINT`, `CODY_BACKEND_SERVICE_TOKEN`, and the official
`CODY_WEBSITE_SIGNUP_URL` (HTTPS). Unlinked members receive the website link;
only a valid backend participant response grants Participant. Sponsor selection
grants Under Review immediately and creates a persistent staff decision in the
Sponsor Review channel. Admins and Organisers can approve to Sponsor or reject
to Visitor. Visitor selection grants Visitor immediately. The four access roles
are mutually exclusive; unrelated roles are preserved.

Cody must have Manage Roles and sit above Participant, Sponsor, Under Review,
Visitor, and Rules Accepted. Existing access-role members are not silently
marked accepted; `/onboarding status` counts them for deliberate migration.
`/onboarding enforce_rules` previews the affected count, and `confirm:true`
reversibly removes only their Cody access roles so they must accept and select
again.
Full permission setup, rule-update behavior, IDs, environment overrides, and
acceptance checks are in
[`cody/features/welcome/README.md`](cody/features/welcome/README.md).

## Support tickets

Cody maintains an **Open Ticket** panel in channel `1541132121551274154` and
creates private ticket channels under category `1541137977613488149`.
Participants submit a category and short form; Admins and Organisers can claim,
release, and resolve the resulting ticket.

This first version has no local database and saves no transcripts. Resolution
marks the temporary ticket `RESOLVED`, sends safe metadata to Cody's operations
log, and deletes the private channel. The future integration separates
backend-canonical ticket actions from local Discord channel routing; PostgreSQL
and durable ticket status belong only to the website backend. Configuration,
permissions, limitations, and the backend hand-off are documented in
[`cody/features/tickets/README.md`](cody/features/tickets/README.md).

## Website

The temporary ETH Battlecode website used for Discord application verification is located in `/docs`.

GitHub Pages can publish it using:

Settings → Pages → Deploy from a branch → main → /docs
