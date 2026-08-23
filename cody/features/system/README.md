# System feature

## Status

- Lifecycle: **Active**
- Extension loaded: **Yes** (`cody.features.system.cog`)
- Project label: `area: discord`
- User commands: `/ping`, `/about`
- Required role: Participant or Admin

## Purpose

Provide small, dependable commands that identify Cody and confirm the command
interface is operational. These commands are useful before more complex feature
diagnostics are available.

## Current implementation

`SystemCog` registers two global slash commands:

- `/ping` returns a green `NETWORK STATUS` embed.
- `/about` returns an ETH Battlecode identification embed.

Both layouts use the shared `cody_embed` helper and therefore inherit Cody's
standard uppercase title and `CODY // NETWORK INTERFACE` footer. The feature has
no service, configuration, persistence, external requests, or scheduled tasks.

## Intended scope

- Lightweight bot identity and command-interface health information.
- General, non-sensitive information that does not belong to another feature.
- Fast responses that remain useful when optional providers are unavailable.

Deep health checks belong with the feature or integration they diagnose. `/ping`
currently confirms the Discord command path, not backend, database, or latency
health.

## Dependencies and boundaries

- Presentation uses `cody.shared.components` and `cody.shared.colors`.
- Do not add backend calls to the current `/ping` response without renaming or
  clearly redefining what its health result means.
- Feature-specific diagnostics belong in that feature, such as
  `/stats permissions`.
- No user or guild data should be persisted by this feature.

## Development checklist

- [x] Implement `/ping` and `/about`.
- [x] Use shared Cody styling.
- [x] Load the extension during startup.
- [x] Cover both response builders with focused tests.
- [ ] If richer health reporting is requested, define every dependency, timeout,
  degraded state, and disclosure rule in a feature issue first.
- [ ] Keep this README synchronized with any added command.

## Testing

Automated coverage lives in `tests/system/test_views.py`. It verifies the success
color and shared footer. New commands should test their response content and any
error states without requiring a live Discord connection. Run the complete
repository suite before changing the extension.

## Operational notes

Both commands require either the configured Participant role
(`1541112817476702238`) or Admin role (`1540821890510229571`). They otherwise
need only the ordinary permissions required for Cody to receive an interaction
and send an embed. They expose no credentials, private member data, or
organizer-only diagnostics.
