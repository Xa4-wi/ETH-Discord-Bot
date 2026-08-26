# Server statistics mock endpoint

`server-stats.json` is an unauthenticated development fixture for Cody's mock
HTTP statistics provider. It must never be configured as a canonical production
source. When GitHub Pages publishes the repository's `/docs`
folder, the endpoint is:

```text
https://xa4-wi.github.io/ETH-Discord-Bot/api/server-stats.json
```

The file contains placeholder competition data only. Discord member and layer
counts never come from this endpoint, and credentials or private Discord data
must never be added here because GitHub Pages is public.

Keep all four fields present and use non-negative JSON numbers for numeric
values. `ladder_leader` must be a non-empty team name. Production statistics use
the authenticated `statistics.summary` action described in
[`CODY_INTEGRATION_SPEC.md`](../../CODY_INTEGRATION_SPEC.md); action-data
translation belongs in `cody/features/server_stats/providers.py`.
