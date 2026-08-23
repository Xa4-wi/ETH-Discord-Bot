# Announcements feature

## Status

- Lifecycle: **Planned**
- Extension loaded: **No**
- Project label: `area: discord`
- Existing code: package, cog, service, and view placeholders only

## Purpose

Publish clear, consistently styled competition announcements from approved
organizer input or trusted competition events. The feature should prevent
accidental duplicate or unauthorized broadcasts.

## Current implementation

The module files describe their intended layers but contain no commands, event
listeners, scheduling logic, message layouts, tests, configuration, or extension
setup. No announcements are currently sent by Cody.

## Intended scope

- Organizer-created announcement previews and confirmed publication.
- Consistent Components V2 or embed presentation using Cody's shared palette.
- Configured destination channels resolved by ID rather than name.
- Optional scheduling only after persistence and restart behavior are defined.
- Deduplication when announcements originate from backend competition events.

## Dependencies and boundaries

- Organizer authorization should reuse `cody.shared.permissions`.
- Competition-triggered announcements may consume a future Battlecode API event,
  but provider translation does not belong in the cog.
- Scheduling that must survive restarts requires the database integration; an
  in-memory timer alone is not sufficient.
- Match, ladder, and team state remain owned by their respective features.

## Development checklist

- [ ] Decide the first announcement sources: manual, scheduled, backend, or a
  documented subset.
- [ ] Define destination channel IDs and environment-variable overrides.
- [ ] Define draft, preview, confirmation, publish, and cancellation behavior.
- [ ] Implement authorization and mention-safety rules.
- [ ] Implement service-level deduplication and delivery results.
- [ ] Build Cody-styled views for preview and published messages.
- [ ] Add persistence before enabling restart-safe scheduling.
- [ ] Add extension setup and load only after manual Discord validation.
- [ ] Document final commands, event sources, and permissions here.

## Testing

- Test staff authorization and rejection of unauthorized publication.
- Test channel resolution, missing permissions, deleted channels, and API errors.
- Verify user-controlled text cannot create unintended mass mentions.
- Verify retries do not create duplicate announcements.
- Test scheduled-message recovery across restart if scheduling is implemented.

## Operational notes

Cody will need View Channel and Send Messages in each destination, plus Embed
Links or Components V2-related permissions when used. Broad mention permissions
should remain disabled unless a specific approved workflow requires them.
