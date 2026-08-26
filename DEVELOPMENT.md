# Cody development workflow

All work that reads or changes official competition data must follow
[`CODY_INTEGRATION_SPEC.md`](CODY_INTEGRATION_SPEC.md). The Main Backend is the
only approved integration point; Cody-side competition mutations and direct
database/storage/infrastructure connections are out of scope.

GitHub calls tags **labels**. This repository uses labels for work type, product
area, priority, size, and exceptional state. GitHub Projects provides the
status board and overview.

## Classifying work

Every open issue should normally have:

1. Exactly one `type:` label.
2. At least one `area:` label.
3. Exactly one `priority:` label after triage.
4. One `size:` label when the work is understood well enough to estimate.
5. `blocked`, `needs decision`, or `security` only when applicable.

| Label family | Values |
| --- | --- |
| Type | Feature, bug, task, maintenance, documentation |
| Area | Discord, welcome, backend, backend-owned PostgreSQL, integrations, participants, teams, submissions, matches, ladder, events, lore, admin, website, infrastructure |
| Priority | Critical, high, medium, low |
| Size | Small, medium, large |
| Special | Blocked, needs decision, security, good first issue, help wanted |

The canonical names, colors, and descriptions are stored in
`.github/labels.json`.

## Issue workflow

Use the issue form that best matches the work:

- **Bug report** for incorrect existing behavior.
- **Feature request** for a new participant or organizer capability.
- **Backend or integration work** for APIs, databases, authentication, or
  external system connections.
- **Development task** for implementation, refactoring, maintenance, or
  investigation.

During triage, confirm the acceptance criteria, add area/priority/size labels,
and split `size: large` work into smaller linked issues where practical.

## Project board

The project should be named **Cody Development** and linked to this repository.
Use these Status options:

1. `Backlog` — valid work that is not scheduled.
2. `Todo` — ready and selected for implementation.
3. `In Progress` — actively being worked on.
4. `Review` — implementation is complete and awaiting validation or review.
5. `Done` — merged, deployed where required, and documented.

Recommended saved views:

- **Board** — board layout grouped by Status.
- **Bugs** — table filtered by `label:"type: bug"`.
- **Backend** — table filtered by `label:"area: backend","area: integrations"`.
- **Features** — table filtered by `label:"type: feature"`.
- **Blocked** — table filtered by `label:blocked`.
- **Untriaged** — table filtered by `no:label`.

In the project's **Workflows** settings, enable **Auto-add to project**, select
this repository, use the filter `is:issue,pr`, and turn the workflow on. Keep
the built-in workflows that set closed issues and merged pull requests to
`Done` enabled.

## Initial GitHub setup

Install and authenticate GitHub CLI, then grant it project access:

```text
gh auth login
gh auth refresh -s project
python3 scripts/setup_github_project.py
```

The setup utility creates or updates the labels, reuses or creates the
**Cody Development** project, links it to this repository, and adds Priority
and Effort fields. It does not delete existing labels or projects.

After the utility finishes, open the project and perform the small UI-only
steps described above: add the `Backlog` and `Review` Status options, create the
saved views, and enable Auto-add.
