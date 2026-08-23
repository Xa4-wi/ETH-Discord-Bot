# Lore feature

## Status

- Lifecycle: **Planned**
- Extension loaded: **No**
- Project label: `area: lore`
- Existing code: package, cog, service, and view placeholders; empty lore content

## Purpose

Make ETH Battlecode's world, layers, glossary, and transmissions discoverable
inside Discord without mixing narrative content into command code.

## Current implementation

There are no lore commands or lookup services. `content/lore/glossary.json` and
`content/lore/layers.json` are empty objects, while
`content/lore/transmissions.json` is an empty list. The feature modules are
placeholders and are not loaded.

## Intended scope

- Browse approved layer descriptions using **The Lumen Belt** terminology.
- Look up glossary terms with normalized, user-friendly matching.
- Read approved transmissions with pagination or selection where required.
- Present lore through Cody-styled Discord layouts.
- Fail safely when optional content is missing or malformed.

## Dependencies and boundaries

- Canonical narrative content belongs in `content/lore`, not Python literals.
- Content changes should be reviewable independently from Discord presentation.
- General welcome navigation may link users toward lore, but onboarding behavior
  remains owned by the welcome feature.
- This feature is read-only unless a separate authenticated content-management
  workflow is designed later.

## Development checklist

- [ ] Agree on JSON schemas for glossary, layers, and transmissions.
- [ ] Populate the content files with approved canonical text.
- [ ] Add startup or test-time schema validation with useful error messages.
- [ ] Implement exact and friendly lookup behavior in `service.py`.
- [ ] Define initial browse/search commands and autocomplete behavior.
- [ ] Build Components V2 layouts that handle Discord text limits.
- [ ] Add missing-content fallbacks without inventing lore at runtime.
- [ ] Add extension setup and load after content and commands are approved.
- [ ] Document final commands and content schemas here.

## Testing

- Validate every content asset and reject duplicate identifiers or terms.
- Test case-insensitive lookup, aliases, missing terms, and empty collections.
- Test long descriptions and pagination against Discord limits.
- Verify only **The Lumen Belt** appears in current user-facing content.
- Snapshot or inspect representative Discord layouts after content changes.

## Operational notes

The feature should require only ordinary View Channel and Send Messages access.
Content files ship with the bot, so changes require deployment unless a future
trusted remote content provider is explicitly introduced.
