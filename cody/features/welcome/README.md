# Welcome and access-onboarding feature

## Status

- Lifecycle: **Active**
- Extension loaded: **Yes** (`cody.features.welcome.cog`)
- Project labels: `area: welcome`, `area: backend`, `area: discord`
- Events: Discord member join and persistent component interactions
- Admin commands: `/test_welcome`, `/onboarding setup`, `/onboarding status`,
  `/onboarding enforce_rules`
- Required command role: Admin (`1540821890510229571` by default)

## Purpose

Welcome each new Discord member, require an explicit acknowledgement of the
server behavior rules, and then establish one of three mutually exclusive access
states: Participant, Sponsor, or Visitor. Participant identity remains owned by
the website backend; Discord only receives the role after both rule acceptance
and a successful backend linkage check.

## Current implementation

When `on_member_join` fires, Cody renders a personalized 1200×675 arrival card
in memory and posts it in the Welcome channel. The message links to **Read &
Accept Rules** and to the access-selection panel in the Role channel.

Cody creates or refreshes a versioned rules panel in the Rules channel. Its
complete, repository-owned wording is loaded from
`content/community/server_rules.json`; its presentation uses the original
1672×941 `assets/branding/rules-image.png` artwork. The rules cover respectful
conduct, safe content, privacy, spam/scams, correct channel use, competitive
integrity, credentials, truthful roles, sponsor conduct, moderation, Discord
policy, and enforcement. Selecting **Accept Rules** assigns a zero-permission
`Rules Accepted` marker role. That marker persists through restarts but grants
no channel access by itself.

Cody creates or refreshes the persistent role panel at startup and through
`/onboarding setup`. That command also creates/refreshes the rules panel and
validates the configured marker role. The role panel uses
`assets/branding/role-welcome.png` at its original
1672×941 16:9 dimensions; the three signs are already centered, so the runtime
does not crop or alter the source artwork. The three persistent buttons behave
as follows:

- **Participant** calls the authenticated Main Backend action
  `participant.get`, forwarding only Discord's immutable actor, guild, and
  interaction IDs. A valid participant response replaces any other
  Cody-managed access role with Participant. `USER_NOT_LINKED` and
  `USER_NOT_FOUND` show a private website sign-in prompt and a safe HTTPS link
  when `CODY_WEBSITE_SIGNUP_URL` is configured. Backend/configuration failures
  never assign the role. The button is blocked until Rules Accepted is present.
- **Sponsor** replaces any current access role with Under Review and posts one
  pending review card in the Sponsor Review channel. Admins and Organisers can
  approve or reject through persistent buttons. Approval replaces Under Review
  with Sponsor; rejection replaces it with Visitor. Repeated clicks are
  idempotent, and concurrent in-process decisions are serialized per applicant.
- **Visitor** immediately replaces any current access role with Visitor. If the
  member had a pending Sponsor request, Cody marks its review card Withdrawn and
  removes its controls.

All three access buttons fail closed and direct the member back to Rules when
the Rules Accepted marker is absent. Existing access-role members are not
silently marked accepted; `/onboarding status` counts them so an Admin can
perform a deliberate migration. `/onboarding enforce_rules` previews the count
by default; `confirm:true` reversibly removes only Cody access roles from those
members, preserves unrelated roles, and lets them re-enter after acceptance.

Rules acceptance is represented only by its Discord marker role. Pending
sponsor state is represented only by the Discord role and review message. Cody
adds no database, local acceptance file, or transcript. Fixed custom IDs and
message markers allow button handling after a bot restart. This is transitional
Discord-local state, not canonical website data.

The Admin-only `/onboarding status` performs a real `participant.get` contract
probe for the invoking Admin and reports reachability without displaying profile
data. A valid participant result or `USER_NOT_LINKED`/`USER_NOT_FOUND` proves the
connection. It also reports missing channels/roles/artwork, website-link
configuration, rule content/artwork, Cody channel permissions, Manage Roles
permission and hierarchy, members who have access without recorded acceptance,
whether the marker itself accidentally unlocks any channel, plus the public
entry-channel visibility audit.

## Intended scope

- Member-join delivery and in-memory welcome-card rendering.
- Versioned server-rule presentation and durable Discord-local acceptance.
- First-step navigation to rule acceptance and then Role selection.
- Backend-authorized Participant role assignment.
- Discord-local Visitor selection and Sponsor review.
- Safe, persistent rule/role/review controls and an administrator setup/status path.
- Exclusive management of the four access roles listed below while preserving
  all unrelated Discord roles.

Participant profiles, Discord OAuth, registration, account linking, team data,
and durable sponsor/application records remain website/backend responsibilities.
Cody must never treat a username, display name, nickname, or existing Discord
role as proof of participant identity.

## Dependencies and boundaries

- Follow [`CODY_INTEGRATION_SPEC.md`](../../../CODY_INTEGRATION_SPEC.md).
- The feature consumes the typed `ParticipantLinkProvider`; only
  `BackendParticipantLinkProvider` talks to the shared
  `cody.integrations.backend` client.
- The Main Backend must implement the version-1 `participant.get` response
  contract and independently resolve the Discord OAuth association.
- Runtime artwork and quotes live under `assets/`; versioned rule copy lives in
  `content/community/server_rules.json`. Generated welcome cards and backend
  responses are never written to disk.
- `cog.py` owns Discord triggers/interactions, `service.py` delivery and role
  replacement, `providers.py` the typed linkage boundary, `renderer.py` pixels,
  `quotes.py` content selection, and `views.py` presentation.
- This feature deliberately audits but does not automatically rewrite server
  channel overwrites. Permission changes can expose or hide the entire server
  and must be reviewed by an Admin in Discord.

## Development checklist

- [x] Send a personalized, bounded welcome card on member join.
- [x] Load randomized JSON quotes with safe fallback behavior.
- [x] Link the welcome message to rule acceptance and Role selection.
- [x] Publish complete versioned behavior rules with the supplied rules artwork.
- [x] Require a persistent Rules Accepted marker before access selection.
- [x] Ensure the acceptance marker grants no server permissions by itself.
- [x] Create a persistent three-button access-selection panel with supplied art.
- [x] Verify Participant linkage through authenticated `participant.get`.
- [x] Refuse Participant assignment on unlinked, unavailable, or invalid data.
- [x] Assign Visitor immediately and keep access roles mutually exclusive.
- [x] Assign Under Review and create one Sponsor review request.
- [x] Allow only configured Admin and Organiser roles to approve/reject.
- [x] Preserve role/review controls across restarts without local persistence.
- [x] Add Admin-only setup and operational status commands.
- [x] Add an explicit preview/confirmation migration for pre-existing access.
- [ ] Configure and acceptance-test the real endpoint/service token with the
  live `/onboarding status` probe.
- [ ] Configure the official HTTPS signup URL.
- [ ] Apply and manually verify the server permission matrix below.

## Testing

Coverage under `tests/welcome/` checks quote normalization/fallback, render size
and quote bounds, Components V2 attachment/navigation, validated rule content,
both supplied onboarding artworks, persistent rule/role/review custom IDs, rules
acceptance without access grants, sponsor markers/resolution, safe signup URLs,
strict participant response translation, Discord actor/context forwarding,
unlinked behavior, and exclusive access-role replacement.

Before production, run the complete suite and then verify that an unaccepted
member cannot select any role, acceptance survives a restart, and acceptance
alone exposes no additional channel. Continue with four accounts or test roles:
unlinked Participant, linked Participant, Sponsor, and Visitor. Restart Cody
while the rules/selection panels and a Sponsor request are pending, then
exercise their buttons. Also test approve/reject with an ordinary member,
Organiser, and Admin. Preview `/onboarding enforce_rules`; use `confirm:true`
only after reviewing the affected count.

## Operational notes

Default channels:

| Purpose | ID | Environment override |
| --- | ---: | --- |
| Welcome | `1540841975320813649` | `CODY_WELCOME_CHANNEL_ID` |
| Rules | `1540846388328275990` | `CODY_RULES_CHANNEL_ID` |
| Role selection | `1542168230896996352` | `CODY_ROLE_CHANNEL_ID` |
| Sponsor review | `1542176692791939232` | `CODY_SPONSOR_REVIEW_CHANNEL_ID` |
| Member-count VC | `1541109424796602418` | `CODY_STATS_MEMBERS_CHANNEL_ID` |

Default roles:

| Purpose | ID | Environment override |
| --- | ---: | --- |
| Rules Accepted marker | `1542198825756794971` | `CODY_RULES_ACCEPTED_ROLE_ID` |
| Participant | `1541112817476702238` | `CODY_PARTICIPANT_ROLE_ID` |
| Sponsor | `1542162836791361576` | `CODY_SPONSOR_ROLE_ID` |
| Under Review | `1542164526022004877` | `CODY_SPONSOR_UNDER_REVIEW_ROLE_ID` |
| Visitor | `1542164969796272229` | `CODY_VISITOR_ROLE_ID` |
| Admin reviewer | `1540821890510229571` | `CODY_ADMIN_ROLE_ID` |
| Organiser reviewer | `1540821070213292125` | `CODY_ORGANIZER_ROLE_ID` |

Backend/link configuration:

```text
CODY_BACKEND_ENDPOINT=https://backend.example/internal/cody/v1
CODY_BACKEND_SERVICE_TOKEN=<32-4096-character service credential>
CODY_WEBSITE_SIGNUP_URL=https://official.example/register
CODY_RULES_ACCEPTED_ROLE_ID=1542198825756794971
```

The first-time entry corridor contains four visible resources—not three: the
member-count voice channel plus the Welcome, Rules, and Role-selection text
channels. Configure `@everyone` to View Channel on those four and deny View
Channel on every other category/channel. `/onboarding status` detects missing
entry visibility and counts unexpected channels still visible to `@everyone`.

Configure role-specific category access separately:

| Role | Expected access behavior |
| --- | --- |
| No access role / `@everyone` | Entry corridor only |
| Rules Accepted | Marker only; no additional channel permissions |
| Participant | Competition participant areas |
| Under Review | Sponsor review-period areas requested by organisers |
| Sponsor | Approved sponsor areas |
| Visitor | Public visitor/community areas |
| Admin / Organiser | Sponsor Review channel and their staff areas |

Cody needs View Channel, Send Messages, Embed Links, Attach Files, and Read
Message History in both Rules and Role selection; View Channel, Send Messages,
Embed Links, and Read Message History in Sponsor Review; and server-level Manage
Roles. Cody's highest role must sit above Rules Accepted, Participant, Sponsor,
Under Review, and Visitor. Keep the Sponsor Review channel hidden from
`@everyone` and non-staff roles.

Cody resolves Rules Accepted only by its immutable configured ID. Startup,
setup, acceptance, and role selection fail closed if that role is missing,
managed, has any server permission, or has any channel permission overwrite.
Do not give this marker permissions: the subsequent access role performs the
unlock.

Edit `content/community/server_rules.json` to change policy wording, increment
its `version`, update its date, and run `/onboarding setup`. Existing marker
roles record acceptance generally, not per-version. For a material change that
requires everyone to re-accept, an Admin must deliberately remove the marker
from existing members or configure a new marker role; Cody does not mass-remove
roles automatically.

Role assignments, Sponsor requests/decisions, backend verification failures,
and setup failures emit metadata-only operational logs. They may contain Discord
member/reviewer/message IDs, but never backend response fields, tokens, or
display names.

`/test_welcome`, `/onboarding setup`, `/onboarding status`, and `/onboarding
enforce_rules` have Discord's Administrator command-visibility default and a
runtime Admin-role check. Sponsor buttons use a separate runtime check and
accept either Admin or Organiser.
