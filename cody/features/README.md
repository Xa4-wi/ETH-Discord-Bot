# Cody feature index

Each feature owns one user-facing or operational capability and keeps its
Discord triggers, business logic, presentation, tests, and documentation
separate from unrelated features. Every feature folder must contain a
`README.md` and keep it current as implementation decisions are made.

## Feature overview

| Feature | Status | Loaded by Cody | Project label | Documentation |
| --- | --- | --- | --- | --- |
| System | Active | Yes | `area: discord` | [`system/README.md`](system/README.md) |
| Welcome | Active | Yes | `area: welcome` | [`welcome/README.md`](welcome/README.md) |
| Server statistics | Active | Yes | `area: discord`, `area: backend` | [`server_stats/README.md`](server_stats/README.md) |
| Admin | Planned | No | `area: admin` | [`admin/README.md`](admin/README.md) |
| Announcements | Planned | No | `area: discord` | [`announcements/README.md`](announcements/README.md) |
| Ladder | Planned | No | `area: ladder` | [`ladder/README.md`](ladder/README.md) |
| Lore | Planned | No | `area: lore` | [`lore/README.md`](lore/README.md) |
| Matches | Planned | No | `area: matches` | [`matches/README.md`](matches/README.md) |
| Teams | Planned | No | `area: teams` | [`teams/README.md`](teams/README.md) |

The authoritative loaded-extension list is `EXTENSIONS` in `cody/bot.py`.
Documentation must never describe a planned feature as available until that
extension is loaded and its acceptance checks pass.

## Status definitions

- **Planned** — only a skeleton or design exists; users cannot rely on it.
- **In progress** — implementation is underway behind an explicit development
  task or feature issue.
- **Active** — loaded by Cody, tested, documented, and safe to operate.
- **Paused** — intentionally not progressing; the feature README records why.
- **Deprecated** — scheduled for removal with a documented replacement or
  migration path.

## Required feature documentation

Every feature README must include:

1. **Status** — lifecycle state, extension state, and GitHub project labels.
2. **Purpose** — the user or organizer outcome the feature owns.
3. **Current implementation** — an honest inventory of working code and gaps.
4. **Intended scope** — behavior that belongs inside the feature.
5. **Dependencies and boundaries** — integrations, models, content, and work
   that must remain elsewhere.
6. **Development checklist** — implementation tasks and acceptance criteria.
7. **Testing** — automated and Discord-side checks required before activation.
8. **Operational notes** — permissions, configuration, failure behavior, and
   commands or events where applicable.

When a new feature directory is added, add its README and index row in the same
change. The documentation test enforces the per-folder README requirement.

## Standard feature architecture

Use only the modules the feature needs:

```text
feature_name/
├── README.md   Feature contract, status, and development checklist
├── __init__.py Package description
├── cog.py      Discord events, tasks, and application commands
├── service.py  Business logic and orchestration
├── views.py    Discord embeds and Components V2 layouts
├── models.py   Feature-local data structures
├── providers.py Replaceable external or static data sources
└── constants.py Feature-specific presentation and timing constants
```

Discord cogs should stay thin. Reusable logic belongs in services, rendering in
views/renderers, and external response translation in integrations or providers.
Shared domain models belong in `cody/models` only when multiple features use
them.

## Development workflow

1. Create or select a GitHub issue using the relevant `area:` and `type:`
   labels from `DEVELOPMENT.md`.
2. Update the feature README from **Planned** to **In progress** and link the
   concrete acceptance criteria in the issue.
3. Implement the smallest vertical slice without loading an incomplete feature
   in production.
4. Add focused tests under `tests/<feature_name>/`.
5. Verify required Discord intents, bot permissions, channel/role IDs, secrets,
   and failure behavior.
6. Load the extension in `cody/bot.py`, run the complete suite, and perform the
   feature README's manual checks.
7. Mark the README **Active** and update its current-implementation section.

See [`DEVELOPMENT.md`](../../DEVELOPMENT.md) for the project board, triage rules,
and complete label taxonomy.
