# Server statistics mock endpoint

`server-stats.json` is the development response for Cody's aggregate HTTP
statistics provider. When GitHub Pages publishes the repository's `/docs`
folder, the endpoint is:

```text
https://xa4-wi.github.io/ETH-Discord-Bot/api/server-stats.json
```

The file contains placeholder competition data only. Discord member and layer
counts never come from this endpoint, and credentials or private Discord data
must never be added here because GitHub Pages is public.

Keep all four fields present and use non-negative JSON numbers for numeric
values. `ladder_leader` must be a non-empty team name. The official backend may
later return a richer ladder-leader object; translation belongs in
`cody/features/server_stats/providers.py`.
