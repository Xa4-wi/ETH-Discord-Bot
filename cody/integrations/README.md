# Integration boundary

The authoritative contract is
[`CODY_INTEGRATION_SPEC.md`](../../CODY_INTEGRATION_SPEC.md).

Official competition traffic has one route:

```text
feature cog → feature service/provider → integrations/backend → Main Backend
```

`backend/` owns the action allow-list, common envelopes, typed errors, transport,
service authentication, retries, response limits, and metadata-only logging.
Feature providers translate action-specific `data` objects into feature-local
models. Cogs and views never make raw HTTP calls.

`battlecode_api.py` is a compatibility import for older planning references.
`database.py` is an intentional boundary marker and exposes no API: Cody must
never connect directly to PostgreSQL or another database, object storage, match
infrastructure, or result databases.

The backend client is lazy. Cody can run Discord-only features without backend
credentials; a provider configured with `CODY_STATS_PROVIDER=backend` requires
the endpoint and service token documented in the root specification.
