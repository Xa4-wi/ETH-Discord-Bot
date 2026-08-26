# Admin feature

## Status

- Lifecycle: **Planned**
- Extension loaded: **No**
- Project label: `area: admin`
- Existing code: package, cog, and view placeholders only

## Purpose

Provide restricted organizer operations that coordinate Cody safely without
granting the bot unnecessary server-wide Administrator permission. This feature
is for cross-feature administration; domain actions should remain in their
own feature services.

## Current implementation

`cog.py` and `views.py` contain documentation placeholders. There are no admin
commands, services, tests, configuration values, or extension setup function.
Nothing in this folder is loaded at runtime.

## Intended scope

- Staff-only diagnostics and controlled maintenance operations.
- Manual recovery actions that legitimately coordinate multiple features.
- Confirmation and result interfaces for high-impact organizer actions.
- Audit-friendly responses that identify what changed without exposing secrets.

The exact initial command set remains a product decision. It must be specified
in a feature issue before implementation rather than inferred while coding.

## Dependencies and boundaries

- Reuse `cody.shared.permissions` for application-command checks.
- Call public services owned by teams, matches, ladder, announcements, or other
  features; do not duplicate their business rules here.
- Follow [`CODY_INTEGRATION_SPEC.md`](../../../CODY_INTEGRATION_SPEC.md) for any
  official data. Cody has no direct database or persistence adapter.
- Discord Admin/Organiser roles may authorize local operational controls but
  never grant competition-data authority. Backend actions are independently
  authorized by the Main Backend.
- Discord-specific layouts belong in `views.py`; secret values must never appear
  in responses or logs.

## Development checklist

- [ ] Agree on the first organizer workflows and permission model.
- [ ] Define each command's impact, confirmation step, and failure behavior.
- [ ] Implement a cog with default Discord permissions and runtime checks.
- [ ] Add a service only for genuinely cross-feature orchestration.
- [ ] Add confirmation/result views using Cody's shared message style.
- [ ] Record high-impact actions in an appropriate audit log.
- [ ] Add an async `setup()` function and load the extension only when complete.
- [ ] Update this README with the final commands and configuration.

## Testing

- Verify non-staff users cannot execute any admin command.
- Verify allowed staff can use each command only in the configured guild.
- Test confirmation, cancellation, partial failure, retry, and idempotency paths.
- Confirm logs and ephemeral responses never contain credentials or private data.
- Run the full repository suite before loading the extension.

## Operational notes

Prefer granular Discord permissions over requiring the Cody bot role to have
Administrator. High-impact command responses should be ephemeral unless an
explicit public audit message is part of the approved design. Admin workflows
must not become a route to team, match, submission, or ranking mutations.
