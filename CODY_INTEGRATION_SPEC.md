# Cody ↔ Main Backend integration specification

| Document property | Value |
| --- | --- |
| Contract major version | `1` |
| Repository document revision | `2.4` |
| Architecture boundary | **Locked** |
| Wire/action schemas | **Draft until backend review** |
| Ticket backend database | **PostgreSQL; backend access only** |
| Current backend connection | Client foundation implemented; no production endpoint configured |
| Authoritative copy | This file at the repository root |

This document replaces the external `cody_integration_specs.md` draft as the
repository's integration authority. It preserves that draft's central boundary,
corrects its folder layout to match this repository, reconciles its ticket model
with Cody's approved no-transcript workflow, and identifies provisional details
that must not be mistaken for deployed behavior.

The terms **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative. A table
entry marked **Locked** is an approved boundary. **Proposed** is implemented or
recommended but still needs backend agreement. **Open** blocks the affected
production integration.

## 1. Purpose and locked rules

Cody is the Discord-facing interface for ETH Battlecode. The main website and
Main Backend own participant authentication, identity linkage, authorization,
and canonical competition state.

Cody MAY:

- attest which immutable Discord user ID invoked an interaction;
- request participant, team, submission, match, ranking, leaderboard, event,
  aggregate-statistics, and structured ticket information;
- apply local Discord UX gates and manage Discord-only channels or messages;
- present validated Main Backend responses in Discord;
- temporarily cache approved read-only responses as non-canonical data.

Cody MUST NOT:

- connect directly to PostgreSQL, another database, S3, match infrastructure,
  or a result database;
- schedule, cancel, retry, delete, or modify matches;
- upload, download, inspect, or modify submission source code;
- create or modify teams, membership, invitations, or competition permissions;
- calculate Elo, ranks, layers, match outcomes, or leaderboard order;
- treat Discord names, nicknames, roles, or channel membership as competition
  identity or authorization;
- retain a second canonical copy of backend-owned state;
- invent competition data when the Main Backend is unavailable.

> **Locked architecture rule:** Participants authenticate with Discord OAuth on
> the main website. The Main Backend owns identity, authorization, and canonical
> competition state. Cody forwards Discord identity, performs only allow-listed
> integration actions, and presents validated responses. Except for approved
> ticket lifecycle mutations, Cody is strictly read-only.

## 2. Current state versus target state

This distinction is mandatory. Target guarantees do not imply that an unfinished
feature is available today.

| Capability | Current repository state | V1 target |
| --- | --- | --- |
| Shared backend client | Implemented but inactive without configuration | One long-lived authenticated integration boundary |
| Access onboarding | Versioned rule acceptance, Discord role panel, Visitor/Sponsor flow, and `participant.get` gateway implemented; Participant path inactive without production backend configuration | Accepted rules plus backend-verified Participant role or Discord-local Sponsor/Visitor access |
| Participant profile | No Discord feature | Read-only `participant.get` |
| Teams | Planned skeleton | Read-only team and member information |
| Submissions | No Discord feature | Read-only metadata; never source code |
| Matches | Planned skeleton | Read-only list, detail, status, and result |
| Ladder | Planned skeleton | Backend-owned rank and leaderboard presentation |
| Event status | No Discord feature | Backend-owned public/participant-visible status |
| Server statistics | Discord community counts active; canonical aggregates disabled by default | `statistics.summary` through the Main Backend |
| Tickets | Active temporary Discord workflow; memory/topic routing only | Backend-canonical structured intake and status, with no transcript |
| Direct databases/storage | No runtime dependency | Remains forbidden |

Transitional behavior MUST be documented in its feature README and MUST NOT be
silently promoted into a canonical source.

## 3. System boundary

```text
Discord participant or staff member
                 │
                 │ Discord interaction (untrusted input)
                 ▼
┌──────────────────────────────────────────────┐
│ Cody                                         │
│ feature cog → service → provider/gateway     │
└──────────────────────┬───────────────────────┘
                       │
                       │ one authenticated HTTPS API
                       ▼
              ┌──────────────────┐
              │   Main Backend   │
              └────────┬─────────┘
                       │
                       ├── identity and authorization
                       ├── participants and teams
                       ├── submission metadata/storage integration
                       ├── match/result infrastructure integration
                       ├── rankings and event state
                       └── durable ticket state when enabled
```

Cody has exactly one trusted dependency for competition data: the Main Backend.
The backend hides physical storage and infrastructure topology from Cody.

## 4. Repository-aligned architecture

The original draft's `commands/`, `backend/`, `presentation/`, `events/`, and
`config/` tree does not match this repository and MUST NOT be introduced.

```text
cody/
├── bot.py                         active extension loading
├── config.py                      environment-backed configuration
├── features/
│   └── <feature>/
│       ├── cog.py                 Discord events/commands only
│       ├── service.py             feature orchestration
│       ├── providers.py           optional domain translation
│       ├── models.py              feature-local models
│       ├── views.py               Discord presentation only
│       └── README.md              feature contract and status
├── integrations/
│   └── backend/
│       ├── actions.py             allow-listed action names
│       ├── client.py              the only official HTTP client
│       ├── models.py              common wire envelopes
│       └── errors.py              typed, user-safe failures
├── models/                        only models shared by multiple features
└── shared/                        Discord UI, roles, logging, redaction
```

Required dependency direction:

```text
Discord cog → feature service → feature provider/gateway
                                      │
                                      ▼
                         MainBackendClient → Main Backend
```

- Cogs and views MUST NOT import `aiohttp` or parse backend JSON.
- Feature services MUST consume typed/provider-neutral results.
- Official backend calls MUST use `cody.integrations.backend`.
- Development fixtures MAY use a clearly named local/static provider, but MUST
  never be the production default or be described as canonical.
- `cody/integrations/database.py` intentionally exposes no API. Direct database
  adapters inside Cody are forbidden.

## 5. Identity and authorization

### 5.1 Participant authentication — Locked

Participants authenticate on the main website with Discord OAuth. The backend
stores a lossless association from `discord_user_id` to at most one participant
and resolves that participant's team and permissions.

Cody does not implement login, registration, verification codes, account
linking, or team authentication. Cody's onboarding panel may direct an unlinked
actor to the official HTTPS website, but the OAuth/linking flow remains entirely
outside Discord.

### 5.2 Actor attestation — Locked

For a participant/staff request, Cody forwards only the immutable user ID from
`discord.Interaction.user.id`. Every Discord snowflake is serialized as a JSON
decimal string matching `^[1-9][0-9]{0,19}$` and limited to `2^64 - 1`.

User-triggered requests include:

```json
{
  "actor": {
    "discord_user_id": "123456789012345678"
  },
  "context": {
    "discord_guild_id": "1530000000000000000",
    "discord_interaction_id": "1540000000000000000"
  }
}
```

The authenticated service credential lets the backend trust Cody's attestation
that Discord supplied this actor ID. It does not make the actor authorized. The
backend MUST independently resolve linkage, resource visibility, team
membership, ticket ownership, and staff entitlement.

Cody MUST NOT send or use usernames, display names, nicknames, team names, or
Discord roles as proof of competition identity.

### 5.3 Discord roles — Locked carve-out

Discord roles MAY gate local diagnostics, command visibility, community-role
statistics, Discord channel visibility, access onboarding, and temporary ticket
controls. Cody's local access onboarding MUST require a `Rules Accepted` marker
before assigning Participant, Sponsor Under Review, or Visitor. The marker MUST
have no permissions by itself and MUST NOT be treated as competition identity.
A Participant role MAY be assigned only after rule acceptance and a valid
`participant.get` result for the invoking Discord actor. The resulting role is
still presentation/channel-routing state and MUST NOT grant access to
participant, team, submission, match, ranking, event, or future backend ticket
data by itself. Every later backend request independently forwards the actor ID,
and the backend authorizes it. A backend-facing ticket mutation similarly
forwards the staff actor ID and the backend authorizes it independently.

### 5.4 Service authentication — Proposed

Cody initially authenticates with:

```http
Authorization: Bearer <CODY_BACKEND_SERVICE_TOKEN>
```

Requirements:

- an opaque high-entropy credential stored only in environment/secrets
  management;
- no credentials in URLs, query strings, bodies, Discord, source, or logs;
- action-scoped backend authorization and competition-guild allow-listing;
- credential hashing/secure verification in the backend;
- revocation, rotation, and a two-key overlap window;
- HTTPS certificate and hostname verification.

OAuth2 client credentials or mTLS MAY replace bearer authentication later
without changing feature-service APIs. The production authentication mechanism
and rotation owner remain **Open**.

## 6. Transport and runtime configuration

The single proposed endpoint is:

```text
POST /internal/cody/v1
```

The configured value is the complete endpoint URL. Cody rejects URL credentials,
queries, fragments, redirects, and non-HTTPS production endpoints. Plain HTTP is
available only for explicit localhost development.

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `CODY_BACKEND_ENDPOINT` | none | Complete Main Backend action endpoint |
| `CODY_BACKEND_SERVICE_TOKEN` | none | Service bearer credential |
| `CODY_BACKEND_TIMEOUT_SECONDS` | `10` | Total timeout per HTTP attempt |
| `CODY_BACKEND_READ_RETRIES` | `2` | Additional transient attempts for safe reads |
| `CODY_BACKEND_MAX_REQUEST_BYTES` | `65536` | Maximum encoded request body |
| `CODY_BACKEND_MAX_RESPONSE_BYTES` | `1048576` | Maximum decoded response body |
| `CODY_BACKEND_ALLOW_INSECURE_LOCALHOST` | `false` | Permit local HTTP development only |

These values are bounded implementation defaults, not yet production SLOs.
The current client hard-caps total attempt timeout at 60 seconds, additional read
retries at 5, requests at 1 MiB, and responses at 10 MiB even if environment
configuration asks for more.
Final deadlines, concurrency, retry budget, rate limits, and response limits are
**Open** and require joint load testing.

Every call uses UTF-8 JSON with:

```http
Accept: application/json
Content-Type: application/json
Authorization: Bearer ...
X-Request-ID: <request_id>
```

The backend MUST return `application/json`; Cody fails closed on wrong content
type, malformed UTF-8/JSON, oversized bodies, schema errors, request-ID mismatch,
or API-version mismatch.

## 7. Action allow-list

No action may be constructed from arbitrary user text. Adding an action requires
a spec revision, enum addition, action-specific validation, tests, and backend
approval.

| Action | Actor required | State change | Idempotency | Cacheable |
| --- | :---: | :---: | :---: | :---: |
| `participant.get` | Yes | No | No | Short TTL |
| `team.get` | Yes | No | No | Short TTL |
| `team.members` | Yes | No | No | Short TTL |
| `team.submissions` | Yes | No | No | Short TTL |
| `submission.get` | Yes | No | No | Short TTL |
| `match.get` | Yes | No | No | Very short TTL |
| `match.list` | Yes | No | No | Very short TTL |
| `match.status` | Yes | No | No | None/very short |
| `match.result` | Yes | No | No | Short TTL after completion |
| `ranking.get` | Yes | No | No | Short TTL |
| `ranking.leaderboard` | No | No | No | Short TTL |
| `event.status` | No | No | No | Very short TTL |
| `statistics.summary` | No | No | No | Short TTL |
| `ticket.create` | Yes | Yes | Required | Never |
| `ticket.get` | Yes | No | No | Never |
| `ticket.list` | Yes | No | No | Never |
| `ticket.claim` | Yes | Yes | Required | Never |
| `ticket.release` | Yes | Yes | Required | Never |
| `ticket.resolve` | Yes | Yes | Required | Never |

Public/actor rules for leaderboard, event, and statistics are **Proposed**. The
backend still validates service scope and guild installation.

Explicitly forbidden examples include `team.create`, `team.join`,
`submission.upload`, `match.schedule`, `match.cancel`, `match.retry`,
`match.delete`, and ranking-calculation actions.

## 8. Common wire envelope

### 8.1 Request

```json
{
  "api_version": "1",
  "request_id": "695d72c3-8da4-4fc5-81bf-94b368605275",
  "action": "match.list",
  "actor": {
    "discord_user_id": "123456789012345678"
  },
  "context": {
    "discord_guild_id": "1530000000000000000",
    "discord_interaction_id": "1540000000000000000"
  },
  "payload": {
    "limit": 20
  }
}
```

| Field | Required | Rule |
| --- | :---: | --- |
| `api_version` | Yes | Exact string `"1"` |
| `request_id` | Yes | Lowercase canonical UUIDv4, one per logical operation |
| `action` | Yes | Exact allow-listed action |
| `actor` | Per action | Contains only `discord_user_id` |
| `context` | User-triggered | Guild and interaction snowflakes as strings |
| `payload` | Yes | Action-specific object, even when empty |
| `idempotency_key` | Every write | Lowercase canonical UUIDv4 |

A transport retry reuses the same request object and therefore the same
`request_id` and `idempotency_key`. A new user action gets new identifiers.

### 8.2 Successful response

```json
{
  "api_version": "1",
  "success": true,
  "request_id": "695d72c3-8da4-4fc5-81bf-94b368605275",
  "server_time": "2026-08-26T12:20:00.000Z",
  "data": {}
}
```

### 8.3 Failed response

```json
{
  "api_version": "1",
  "success": false,
  "request_id": "695d72c3-8da4-4fc5-81bf-94b368605275",
  "server_time": "2026-08-26T12:20:00.000Z",
  "error": {
    "code": "USER_NOT_LINKED",
    "message": "Diagnostic text for trusted operators.",
    "retryable": false
  }
}
```

Cody uses only the stable error code for user behavior. The client validates
that a diagnostic message exists and then discards it; backend operators use the
request ID in backend-side logs. Diagnostic text MUST NOT be shown verbatim,
stored on Cody exceptions, or included in terminal/Discord logs.

Success envelopes MUST use a 2xx status; failure envelopes MUST use a non-2xx
status. Unknown additive response fields are ignored. Missing required fields or
unknown values in a closed enum fail closed.

## 9. HTTP and error semantics

| HTTP status | Expected meaning |
| ---: | --- |
| `200` | Successful action |
| `400` | Invalid envelope/request |
| `401` | Cody service authentication failed |
| `403` | Actor/service lacks permission |
| `404` | Resource absent or intentionally not visible |
| `409` | State or idempotency conflict |
| `422` | Action payload validation failed |
| `429` | Rate limit; include bounded `Retry-After` |
| `500` | Internal backend error envelope |
| `502`, `503`, `504` | Transient dependency/backend failure |

Stable V1 error codes:

```text
API_VERSION_UNSUPPORTED  SERVICE_AUTH_FAILED       USER_NOT_LINKED
USER_NOT_FOUND           NO_TEAM                   PERMISSION_DENIED
TEAM_NOT_FOUND           SUBMISSION_NOT_FOUND      MATCH_NOT_FOUND
TICKET_NOT_FOUND         TICKET_RESOLVED           OPEN_TICKET_EXISTS
TICKET_ALREADY_CLAIMED   TICKET_INVALID_STATE      IDEMPOTENCY_CONFLICT
CURSOR_INVALID           REQUEST_TOO_LARGE         RATE_LIMITED
INVALID_REQUEST          BACKEND_UNAVAILABLE       INFRASTRUCTURE_UNAVAILABLE
INTERNAL_ERROR
```

The backend SHOULD use the same outward behavior for an absent resource and a
private resource when revealing existence would leak information.

## 10. Domain contracts

Action examples below are **Proposed wire shapes** until accepted by the backend.
Client-side use does not mean the production endpoint is deployed. Backend
domain IDs are opaque strings no longer than 128 bytes; Cody MUST NOT infer
meaning from prefixes.

### 10.1 Participant

`participant.get` resolves the actor and accepts an empty payload.

```json
{
  "participant_id": "usr_42",
  "display_name": "Alice",
  "team_id": "team_17"
}
```

The backend guarantees at most one participant per Discord ID and filters all
returned fields. Cody does not resolve participants locally. The active welcome
onboarding gateway uses this empty-payload action only to decide whether the
invoking member may receive the local Participant role. It strictly requires a
non-empty `participant_id` of at most 128 UTF-8 bytes, a non-empty
`display_name`, and an optional valid `team_id`; it does not display or persist
the response. `USER_NOT_LINKED` and `USER_NOT_FOUND` fail closed and direct the
member to website Discord OAuth. Transport, protocol, authentication, and all
other backend errors fail closed without assigning Participant.

### 10.2 Teams

Allowed actions are `team.get`, `team.members`, and `team.submissions`. For the
actor's own team, Cody does not send a `team_id`; the backend derives it.

```json
{
  "team_id": "team_17",
  "name": "Solaris",
  "member_count": 4,
  "rating": 1548,
  "rank": "Mirrorwright",
  "layer": "Lumen Belt"
}
```

All team creation, invitations, membership changes, and permissions happen on
the website/backend.

### 10.3 Submissions

`team.submissions` and `submission.get` may return ID, version/label, language,
status, creation time, and active/current metadata. They MUST NOT return source
code, direct object-storage URLs, credentials, or internal storage hashes unless
a separately approved public identifier is required.

Cody never uploads, validates, hashes, stores, or forwards submission files.

### 10.4 Matches

Allowed actions are `match.get`, `match.list`, `match.status`, and
`match.result`. Cody displays backend states only and never infers transitions.

The draft state enum is:

```text
QUEUED  SCHEDULED  RUNNING  COMPLETED  FAILED  CANCELLED
```

Final states, visibility, replay/log fields, result fields, and time semantics
are **Open**. No open decision may introduce a Cody match mutation.

### 10.5 Rankings and leaderboard

`ranking.get` and `ranking.leaderboard` return backend-computed rating, rank,
layer, wins/losses, and ordering. Local rank content may provide descriptions or
visuals only; it MUST NOT contain executable thresholds Cody treats as
authority.

### 10.6 Event status

`event.status` returns backend-owned phase and public flags. Final phase enum,
deadlines, and visibility are **Open**. All timestamps use canonical RFC3339 UTC
with milliseconds and `Z`.

### 10.7 Statistics summary

`statistics.summary` exists to support the active server-statistics feature
without adding independent production endpoints.

```json
{
  "active_teams": 12,
  "matches_today": 37,
  "grid_output": 42.8,
  "ladder_leader": {
    "team_id": "team_17",
    "name": "Solaris"
  },
  "as_of": "2026-08-26T12:20:00.000Z"
}
```

The production adapter requires every field shown above. `ladder_leader` is an
object with both opaque `team_id` and display `name`, and `as_of` is canonical
RFC3339 UTC with milliseconds and `Z`. The looser string-based JSON fixture in
`docs/api` is development-only and is deliberately parsed by a separate
translator.

Discord Members and the three configured Discord role counts are community
telemetry collected from Discord. They are not canonical participant counts,
competition-layer assignments, or authorization inputs.

### 10.8 Pagination

Every list action uses deterministic ordering and opaque cursor pagination:

```json
{
  "limit": 20,
  "cursor": null
}
```

The proposed default is 20 and maximum is 50. A response includes
`next_cursor` as a string or `null`. Exact ordering and cursor lifetime are
**Open** per action. Unbounded arrays are forbidden.

## 11. Ticket contract

### 11.1 Current transitional workflow

The ticket feature is active today without backend persistence:

- categories: `TECHNICAL`, `COMPETITION`, `TEAM`, `ACCOUNT`, `OTHER`;
- states: `OPEN`, `CLAIMED`, `RESOLVED`;
- one active ticket per member while active Discord channel metadata exists;
- Admin and Organiser roles gate local claim/release/resolve buttons;
- process memory holds active structured intake;
- a private channel topic stores only routing/status IDs for restart recovery;
- resolution emits metadata-only operations output and deletes the channel;
- no local database, transcript, or message archive is created.

This is an explicit Phase-0 exception. It is non-canonical and its sequential
display number is not a durable ticket ID.

### 11.2 Target backend-integrated workflow

The approved target retains structured intake and lifecycle status only. Discord
conversation messages and attachments are not synchronized and no transcript is
created.

Allowed actions:

```text
ticket.create  ticket.get  ticket.list
ticket.claim   ticket.release  ticket.resolve
```

State transitions:

```text
create                  → OPEN
claim OPEN              → CLAIMED
release CLAIMED         → OPEN
resolve OPEN|CLAIMED    → RESOLVED (terminal in V1)
```

Rules:

- every mutation uses an idempotency key;
- one active ticket per actor is enforced atomically by the backend;
- ticket IDs are opaque backend IDs with a separate human display reference;
- the backend authorizes ownership and support-staff entitlement on every call;
- a repeated claim by the same staff actor is idempotent;
- a competing claim returns `TICKET_ALREADY_CLAIMED` without leaking private
  staff data to participants;
- release is allowed only for the assignee or a backend-defined privileged
  support entitlement;
- resolution is recorded in the backend before Cody deletes the channel;
- if Discord cleanup fails, the backend remains authoritative and Cody marks or
  locks the channel for reconciliation rather than rolling status back;
- failed backend creation/channel creation requires a documented orphan
  reconciliation strategy before rollout.

Proposed structured create fields and limits:

| Field | Required | Limit |
| --- | :---: | ---: |
| `category` | Yes | Closed enum above |
| `subject` | Yes | 3–100 characters |
| `description` | Yes | 10–1000 characters |
| `attempted_solution` | No | 0–750 characters |
| `related_match_id` | No | Opaque ID, if approved |

The backend revalidates Unicode, lengths, control characters, ownership, and
state. Structured intake is ticket data, not a transcript. Its retention and
deletion policy, attachment warning, staff-entitlement source, backend rollout,
and orphan reconciliation remain **Open**.

The official website backend uses PostgreSQL for durable ticket state. That
storage choice is now **Locked** for the intended backend implementation but is
not part of Cody's wire protocol; Cody remains database-agnostic.

### 11.3 Intended Main Backend database

This section is the **Proposed** logical persistence design for the official
website backend. It is included so backend work starts from one reviewable
model; table names may be adapted to the website repository, but the lifecycle,
uniqueness, idempotency, and no-transcript rules must survive that adaptation.
Nothing in this section permits Cody to open a database connection.

The intended deployment uses PostgreSQL and the website's existing `users` and
`teams` entities rather than creating parallel ticket identities. The example
assumes their keys are UUIDs; the migration must use the actual existing key
type consistently. Opaque ticket/event UUIDs are generated by the application.
The existing `users.discord_user_id` must be unique and lossless; use
`NUMERIC(20,0)` with a `1..18446744073709551615` check (or an equivalently
constrained decimal string), not signed `BIGINT`.

| Table | Purpose | Content boundary |
| --- | --- | --- |
| `support_tickets` | Canonical intake and current lifecycle state | Structured form fields and backend user references only |
| `support_ticket_events` | Immutable lifecycle audit | Created/claimed/released/resolved metadata only |
| `service_idempotency` | Atomic mutation replay protection | Request fingerprint and original safe response; never credentials or request content |

Proposed PostgreSQL-native schema:

```sql
CREATE TYPE support_ticket_category AS ENUM (
    'TECHNICAL', 'COMPETITION', 'TEAM', 'ACCOUNT', 'OTHER'
);

CREATE TYPE support_ticket_status AS ENUM (
    'OPEN', 'CLAIMED', 'RESOLVED'
);

CREATE TYPE support_ticket_event_type AS ENUM (
    'CREATED', 'CLAIMED', 'RELEASED', 'RESOLVED'
);

CREATE TABLE support_tickets (
    display_number           BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    ticket_id                UUID NOT NULL UNIQUE,
    requester_user_id        UUID NOT NULL,
    team_id                  UUID,
    category                 support_ticket_category NOT NULL,
    subject                  TEXT NOT NULL CHECK (char_length(subject) BETWEEN 3 AND 100),
    description              TEXT NOT NULL CHECK (char_length(description) BETWEEN 10 AND 1000),
    attempted_solution       TEXT CHECK (
        attempted_solution IS NULL OR char_length(attempted_solution) <= 750
    ),
    related_match_id         TEXT CHECK (
        related_match_id IS NULL OR char_length(related_match_id) BETWEEN 1 AND 128
    ),
    status                   support_ticket_status NOT NULL DEFAULT 'OPEN',
    assigned_staff_user_id   UUID,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    claimed_at               TIMESTAMPTZ,
    resolved_at              TIMESTAMPTZ,
    purge_after              TIMESTAMPTZ,
    FOREIGN KEY (requester_user_id) REFERENCES users(id),
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (assigned_staff_user_id) REFERENCES users(id),
    CHECK (
        (status = 'OPEN' AND assigned_staff_user_id IS NULL) OR
        (status = 'CLAIMED' AND assigned_staff_user_id IS NOT NULL) OR
        status = 'RESOLVED'
    ),
    CHECK (status <> 'CLAIMED' OR claimed_at IS NOT NULL),
    CHECK ((status = 'RESOLVED') = (resolved_at IS NOT NULL))
);

CREATE UNIQUE INDEX support_tickets_one_active_requester
    ON support_tickets(requester_user_id)
    WHERE status IN ('OPEN', 'CLAIMED');

CREATE INDEX support_tickets_status_created
    ON support_tickets(status, created_at);

CREATE INDEX support_tickets_assignee_status
    ON support_tickets(assigned_staff_user_id, status);

CREATE TABLE support_ticket_events (
    event_id                 UUID PRIMARY KEY,
    ticket_id                UUID NOT NULL,
    event_type               support_ticket_event_type NOT NULL,
    actor_user_id            UUID NOT NULL,
    request_id               UUID NOT NULL UNIQUE,
    occurred_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (ticket_id) REFERENCES support_tickets(ticket_id) ON DELETE CASCADE,
    FOREIGN KEY (actor_user_id) REFERENCES users(id)
);

CREATE INDEX support_ticket_events_ticket_time
    ON support_ticket_events(ticket_id, occurred_at);

CREATE TABLE service_idempotency (
    service_principal        TEXT NOT NULL,
    action                   TEXT NOT NULL CHECK (
        action IN ('ticket.create', 'ticket.claim', 'ticket.release', 'ticket.resolve')
    ),
    idempotency_key          UUID NOT NULL,
    request_fingerprint      BYTEA NOT NULL CHECK (
        octet_length(request_fingerprint) = 32
    ),
    response_http_status     SMALLINT CHECK (
        response_http_status IS NULL OR response_http_status BETWEEN 100 AND 599
    ),
    response_body_json       JSONB,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at               TIMESTAMPTZ NOT NULL,
    completed_at             TIMESTAMPTZ,
    PRIMARY KEY (service_principal, action, idempotency_key),
    CHECK (
        (completed_at IS NULL AND response_http_status IS NULL AND response_body_json IS NULL)
        OR
        (completed_at IS NOT NULL AND response_http_status IS NOT NULL AND response_body_json IS NOT NULL)
    ),
    CHECK (expires_at > created_at)
);

CREATE INDEX service_idempotency_expiry
    ON service_idempotency(expires_at);
```

Implementation requirements:

1. Generate opaque `ticket_id` and `event_id` values in the backend. Use
   `display_number` only for humans; Cody never parses either identifier.
2. Execute each mutation, lifecycle-event insert, and idempotency-result write
   in one PostgreSQL transaction. Let the partial unique index arbitrate
   concurrent creates; never implement “one active ticket” as a separate read
   followed by an unprotected insert.
3. Resolve the incoming Discord actor through the existing website identity
   table and recheck requester/staff authorization before entering the
   transaction. Derive `team_id` from backend state when a creation-time team
   snapshot is useful; never accept it as participant authority. Discord role
   IDs are not stored as backend entitlements.
4. For claim/release/resolve, use a conditional update on the expected current
   state, update `updated_at` and relevant lifecycle timestamps, and verify
   exactly one affected row. The event table is append-only during its approved
   retention period.
5. Store timestamps as `TIMESTAMPTZ`, keep the database/session timezone at UTC,
   and serialize them at the API boundary as canonical RFC3339 UTC with
   milliseconds and `Z`.
6. Store only a cryptographic fingerprint of the normalized mutation request in
   `service_idempotency`. The saved response is the already-filtered integration
   response needed for exact replay; it must not contain credentials or private
   diagnostics.
7. Purge expired idempotency rows after at least 24 hours. Set and enforce
   `purge_after` only after the structured-ticket privacy/retention decision
   is approved.
8. Do not add ticket messages, transcripts, attachments, internal notes,
   Discord message content, service tokens, or raw authorization headers to any
   table. Discord channel routing remains Cody/Discord operational state in V1.
9. Reserve an idempotency row with `INSERT ... ON CONFLICT DO NOTHING`; lock the
   resulting key row while comparing its fingerprint and completing the
   mutation. A concurrent equal request must return the first committed result,
   while a different fingerprint returns `IDEMPOTENCY_CONFLICT`.
10. Keep PostgreSQL migrations ordered and transactional, back up the backend
    database before destructive migrations, test roll-forward/rollback, and use
    bounded application connection pools. Schema or scaling changes stay behind
    the same Main Backend contract rather than creating a new Cody integration.

## 12. Idempotency

Idempotency keys are required for every state-changing ticket action.

Backend requirements:

1. Scope the key by service principal and action.
2. Atomically persist a fingerprint of actor/action/payload and the original
   HTTP status/body with the mutation.
3. Retain it for at least the maximum documented retry/reconciliation window
   (proposed minimum: 24 hours).
4. Same key and same fingerprint returns the original result.
5. Same key and a different fingerprint returns `409 IDEMPOTENCY_CONFLICT`.

Cody does not automatically retry writes. If a write outcome is uncertain, the
feature replays the same logical request with the same key after an approved
reconciliation decision.

## 13. Retry, availability, and caching

Cody automatically retries only safe read actions on connection errors,
timeouts, and `502`/`503`/`504`, using the same request ID. Current configurable
default: two additional attempts with bounded exponential backoff.

Cody does not blindly retry authentication, permission, validation, not-found,
conflict, schema, TLS, redirect, or malformed-response failures. `429` behavior
and bounded `Retry-After` handling remain **Open**.

Cache rules:

1. cache is never canonical;
2. backend responses override cache;
3. keys include API version, action, actor, guild, and normalized payload;
4. participant data uses short TTLs;
5. live match state uses no cache or a very short TTL;
6. ticket reads/writes, permissions, and private notes are never cached;
7. stale public data is labeled with its `as_of`/last-success time.

No general backend-response cache is implemented yet. Server statistics retain
the last valid aggregate for at most 30 minutes, measured from canonical
`as_of` (or local receipt time for a development fixture). A provider failure
marks retained channel values `stale HH:MMZ`; expired/missing values are renamed
`Unavailable`. Discord-only mode also actively marks all four backend-owned
displays unavailable so old fixture values cannot survive a configuration
change.

## 14. Input, output, and Discord safety

Every interaction and backend response is untrusted until validated.

- The backend rechecks identity, authorization, visibility, state, ranges, and
  action-specific schemas.
- Cody validates for safe presentation and fails closed on missing required
  fields or unknown closed-enum values.
- User text MUST use `AllowedMentions.none()` or an explicit narrow allow-list.
- No backend diagnostic text is rendered directly.
- Domain timestamps are backend-generated RFC3339 UTC values with milliseconds.
- Cody MUST NOT parse opaque backend IDs or rely on physical database keys.

## 15. Logging, observability, and privacy

Every backend call is traceable using only allow-listed metadata:

```text
request_id  action  attempt  HTTP status  safe error code  latency
```

Logs MUST NOT contain:

- authorization headers or service/OAuth tokens;
- endpoint queries, request/response bodies, or raw backend diagnostics;
- ticket subject, description, attempted solution, messages, or attachments;
- submission source, database credentials, or storage URLs.

Cody applies shared secret redaction to both terminal and Discord operations
logs as defense in depth. Redaction does not make logging arbitrary payloads
acceptable. A user-facing failure MAY include the request reference.

Discord IDs are pseudonymous operational data. Access and retention for the
operations-log channel and hosted terminal logs remain an organizational
**Open** decision. Current local ticket and access-onboarding lifecycle events
include member, reviewer, message, and channel IDs in the restricted operations
channel; this is documented transitional behavior, not permission to add ticket
content or backend participant fields.

## 16. User-safe failure behavior

Representative messages:

| Condition | User-facing behavior |
| --- | --- |
| Backend unavailable | “Battlecode data is currently unavailable. Please try again shortly.” |
| User not linked | “Your Discord account is not connected to an ETH Battlecode participant. Sign in on the website with Discord first.” |
| Permission denied | Do not reveal whether a private resource exists |
| Invalid backend schema | Generic unavailable response plus request reference |
| Uncertain ticket write | Do not claim success; preserve request/idempotency references for reconciliation |

Features use typed error codes and local safe-message mappings. They never show
the backend's diagnostic `error.message` verbatim.

## 17. Data ownership

| Data | Canonical owner |
| --- | --- |
| Discord OAuth association | Main Backend |
| Participants and teams | Main Backend |
| Submission metadata | Main Backend/submission subsystem |
| Submission bytes | Backend-controlled object storage |
| Match scheduling/execution/results | Backend/infrastructure, hidden behind Main Backend |
| Ratings, ranks, layers, leaderboard | Main Backend/ranking subsystem |
| Event state | Main Backend |
| Durable ticket intake/status | Main Backend when integration is enabled |
| Versioned Discord server-rule wording | Cody repository / ETH Battlecode organisers |
| Rules Accepted/Participant/Sponsor/Under Review/Visitor Discord roles and pending Sponsor review card | Cody/Discord, local and non-canonical |
| Temporary Discord ticket channel | Cody/Discord, non-canonical |
| Read cache | Cody, non-canonical and disposable |

Competition-domain physical schemas, joins, migrations, hashes, and storage
engines remain backend implementation details. Section 11.3 records only the
proposed ticket persistence model requested for backend implementation; Cody
still depends solely on the wire contract.

## 18. Guarantees

### Cody guarantees

1. Actor and context snowflakes come from Discord and are serialized losslessly.
2. Each logical request has one UUIDv4 request ID reused across its retries.
3. Official competition traffic uses only the shared Main Backend client.
4. Cody never directly queries storage or infrastructure.
5. Competition actions remain read-only.
6. Backend data is canonical; cached/local data is not.
7. Discord roles do not grant backend competition authority.
8. Every ticket mutation has an explicit idempotency key.
9. Ticket conversations are never copied into a transcript.
10. Secrets and backend diagnostics are not exposed to users or logs.

### Main Backend guarantees

1. One Discord ID resolves to at most one participant.
2. Every actor/resource/action is independently authorized.
3. Responses are filtered to the caller's visibility.
4. Competition and durable ticket state is canonical.
5. Error codes and V1 schemas are stable; breaking changes use `/v2`.
6. Request IDs are echoed exactly and mutations are idempotent.
7. Cody never needs physical storage/infrastructure knowledge.
8. Private/internal backend data is never returned through participant actions.

## 19. Target V1 scope

Included target capabilities:

- participant profile, team, team members, and submission metadata reads;
- match history, status, and result reads;
- ranking, leaderboard, event status, and statistics summary reads;
- structured ticket creation, viewing, claiming, releasing, and resolution;
- no ticket conversation/transcript synchronization.

Explicit exclusions:

- account linking outside website Discord OAuth;
- all team, submission, match, ranking, and event mutations;
- direct databases, object storage, and infrastructure;
- ticket messages, internal notes, transcripts, and attachments in V1;
- local competition calculations.

## 20. Open integration decisions

These block production activation of the affected provider/action:

- production endpoint host and deployment environments;
- official public HTTPS signup/sign-in URL for unlinked onboarding members;
- bearer versus OAuth2 client credentials or mTLS, rotation owner, and scopes;
- final timeout, concurrency, retry, rate-limit, and size budgets;
- exact action payload/response schemas and optional/null fields;
- list ordering, pagination cursors, and non-statistics cache/staleness limits;
- match state enum, visibility, result, replay, and log fields;
- leaderboard/event/statistics public versus actor-scoped access;
- event phase/deadline semantics;
- backend support-staff entitlement independent of Discord roles;
- ticket structured-data retention/deletion and user privacy notice;
- ticket backend rollout, attachment behavior, and orphan reconciliation.

Open decisions may refine schemas but MUST NOT weaken the locked boundary.

## 21. Change and review process

Any integration change must:

1. update this document and mark the decision Locked, Proposed, or Open;
2. update `BackendAction` for an action change;
3. add strict request/response translation outside cogs/views;
4. add contract, authorization, failure, redaction, and idempotency tests;
5. update the owning feature README and root README if operational behavior
   changes;
6. use the GitHub backend/integration issue form and security label when
   credentials or private data are involved;
7. pass the complete repository suite before deployment.

No feature may bypass this contract because a backend implementation detail is
convenient to access directly.
