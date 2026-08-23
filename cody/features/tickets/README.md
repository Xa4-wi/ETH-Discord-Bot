# Tickets feature

## Status

- Lifecycle: **Active**
- Extension loaded: **Yes** (`cody.features.tickets.cog`)
- Project labels: `area: discord`, `area: backend`, `type: feature`
- Admin commands: `/tickets setup`, `/tickets status`
- Support channel: `1541132121551274154`
- Private-ticket category: `1541137977613488149`

## Purpose

Give participants one clear place to request help and give trusted staff a
private, structured way to claim and resolve those requests. The first version
deliberately retains no transcript or local ticket database.

## Current implementation

Channel `1541132121551274154` contains a persistent **Open Ticket** panel. A
participant chooses Technical, Competition, Team, Account, or Other and answers
a native Discord form. Cody then creates a private text channel under category
`1541137977613488149`, visible only to the requester, Cody, the configured Admin
role, and the configured Organiser role.

The first ticket message records the category, subject, description, attempted
solution, open status, and assignment. Admins and Organisers can claim or
release it. Resolution requires confirmation, sets the ticket state to
`RESOLVED`, writes metadata-only operational output, and deletes the private
channel. The temporary repository immediately drops the closed form fields from
memory. Cody never reads the conversation to create a transcript.

Ticket records currently live only in process memory. Minimal active routing
metadata is also placed in the private channel topic so persistent controls can
recover after a bot restart. It contains numeric IDs, category, status,
assignment, and creation time—not the form answers or conversation. The topic
is deleted with the channel.

## Intended scope

- A persistent support entry panel and structured intake form.
- One active ticket per Discord member.
- Private ticket-channel creation with explicit role overwrites.
- Claim, release, confirmation, and resolved-state transitions.
- Safe operational metadata for diagnosing failures.
- A provider-neutral repository contract for the official website backend.

The feature does not own website authentication, backend hosting, transcript
retention, moderation archives, or the future backend database schema.

## Dependencies and boundaries

- Discord resource IDs come from `cody.config` and can be overridden through
  environment variables.
- Participants can open tickets. The configured Admin and Organiser roles can
  also open, claim, release, and resolve them.
- Admin setup and diagnostics remain Admin-only and use Discord's Administrator
  command visibility default.
- `TicketRepository` is the integration boundary. The current
  `InMemoryTicketRepository` must later be replaced by a backend client, not by
  adding SQLite to the Discord bot.
- When persistence is approved, the official website backend should own its
  SQLite database, validation, migrations, and durability. Cody should call a
  versioned authenticated API implementing the same operations.
- Monitoring receives only event metadata: ticket number, Discord IDs,
  category, status, and channel ID. Form answers and channel messages must not
  enter logs.

## Development checklist

- [x] Configure the supplied support channel, Tickets category, and Organiser
  role IDs.
- [x] Add the persistent Open Ticket button, category selector, and native form.
- [x] Enforce one active ticket per member.
- [x] Create private channels with requester, Admin, Organiser, and Cody access.
- [x] Add persistent claim, release, and confirmed resolution controls.
- [x] Mark closed tickets `RESOLVED`, delete their channels, and retain no
  transcript.
- [x] Recover active controls from non-content channel-topic metadata after a
  restart.
- [x] Add Admin-only panel setup and configuration diagnostics.
- [x] Define an asynchronous repository contract for a future backend provider.
- [ ] Agree the official backend API, authentication, idempotency, and failure
  behavior before replacing the in-memory repository.
- [ ] Implement SQLite and migrations in the official website backend—not this
  repository—when durable ticket status is requested.

## Testing

Automated tests cover temporary repository transitions, one-ticket enforcement,
topic serialization without form content, category values, role authorization,
persistent component IDs, supplied configuration defaults, and command access
metadata.

After deployment, an Admin should run `/tickets status` and `/tickets setup`,
then test opening as a Participant, claiming as an Organiser, releasing,
resolving, and confirming the private channel disappears. Restart Cody with one
ticket open and confirm its controls still work. Verify no transcript or local
database file is created.

## Operational notes

| Resource | Default ID | Environment variable |
| --- | ---: | --- |
| Support channel | `1541132121551274154` | `CODY_SUPPORT_CHANNEL_ID` |
| Tickets category | `1541137977613488149` | `CODY_TICKET_CATEGORY_ID` |
| Admin role | `1540821890510229571` | `CODY_ADMIN_ROLE_ID` |
| Organiser role | `1540821070213292125` | `CODY_ORGANIZER_ROLE_ID` |
| Participant role | `1541112817476702238` | `CODY_PARTICIPANT_ROLE_ID` |

Cody needs View Channel, Send Messages, Embed Links, Read Message History, and
Manage Channels in the configured server. It also needs permission to apply the
private overwrites when creating ticket channels. `/tickets status` reports the
relevant setup.

Temporary numbering is recovered from active ticket channel topics but is not a
durable global sequence. When all channels are gone and Cody restarts, numbering
can begin again. Permanent numbers and resolved history require the future
backend. Closing a ticket provides no recovery path for its conversation by
design, so staff must not resolve it until the support exchange is complete.
