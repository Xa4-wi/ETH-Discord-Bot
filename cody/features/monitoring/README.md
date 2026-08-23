# Monitoring feature

## Status

- Lifecycle: **Active**
- Extension loaded: **Yes** (`cody.features.monitoring.cog`)
- Project labels: `area: infrastructure`, `area: admin`
- Admin commands: `/logs status`, `/logs test`
- Default destination: `1541131430682431518`

## Purpose

Mirror Cody's useful operational events into a dedicated Discord channel so bot
health and failures can be understood without continuous terminal access.

## Current implementation

A root logging handler captures INFO, WARNING, ERROR, and CRITICAL records from
the `cody` application namespace. Records are sanitized, converted into readable
severity-colored embeds, and delivered by a bounded asynchronous queue. Full
tracebacks remain in terminal logs; Discord receives the component, severity,
summary, timestamp, error type, and a suggested action for errors.

The feature starts before other extensions so their startup events are queued
until Discord is ready. Monitoring's own delivery failures are excluded from the
Discord handler, preventing recursive error messages.

## Intended scope

- Operator-friendly Cody lifecycle, warning, and failure messages.
- A safe delivery queue that does not block normal bot operations.
- Token/credential redaction and Discord-safe message limits.
- Admin-only health and test commands.
- Clear separation between concise Discord summaries and terminal diagnostics.

This is not a replacement for durable hosted observability, audit storage, or
full traceback retention.

## Dependencies and boundaries

- The channel ID comes from `CODY_LOG_CHANNEL_ID` in `cody.config`.
- Only `cody.*` application logs are relayed; Discord.py and aiohttp internals
  remain terminal-only to avoid noise and accidental request detail exposure.
- The active `DISCORD_TOKEN`, recognizable token shapes, authorization values,
  passwords, and secrets are redacted before an entry reaches the queue.
- Monitoring delivery errors use this feature's logger, which the handler
  deliberately excludes to prevent recursive delivery attempts.
- Admin command access uses the configured Cody Admin role and Discord's
  Administrator visibility default.

## Development checklist

- [x] Configure channel `1541131430682431518` with an environment override.
- [x] Relay Cody INFO/WARNING/ERROR/CRITICAL records through an async queue.
- [x] Use clear severity titles, colors, components, and timestamps.
- [x] Redact credentials and omit traceback bodies from Discord.
- [x] Bound the queue and report dropped entries through `/logs status`.
- [x] Prevent monitoring delivery errors from recursively logging themselves.
- [x] Add `/logs status` and `/logs test` with Admin-role checks.
- [x] Load monitoring before other Cody features.
- [ ] Integrate durable external observability if operational requirements later
  exceed a Discord channel and terminal output.

## Testing

Automated tests cover namespace filtering, recursion prevention, token and secret
redaction, message truncation, component names, embed severity, channel defaults,
queue overflow, and Admin command metadata. The complete repository suite must
pass before changing log handling because failures can affect every feature.

After deployment, run `/logs status` and `/logs test`, then confirm the test embed
appears once in the configured channel without exposing private information.

## Operational notes

Cody requires View Channel, Send Messages, and Embed Links in the destination.
The channel should be visible only to trusted organizers because even sanitized
operational messages can reveal server configuration and failure timing.

Set `CODY_LOG_CHANNEL_ID` to move the relay. The in-memory queue holds at most
200 entries; on overflow it drops the oldest record so current failures remain
visible. When delivery fails, the pending entry is retried every 30 seconds and
the terminal records the delivery error.
