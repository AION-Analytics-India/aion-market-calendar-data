
CAL-DISCOVERY (read-only official sources) -> review proposal -> maintainer approval -> payload -> manifest/verify -> consumers. No automatic publication.

ingest/discover.py and ingest/sources.json -> bounded official-source readback; ingest/baltic.py -> per-market review candidate; ingest/notices.py -> revision and effective dates; ingest/schema_gate.py -> maintainer schema gate before publish. tests/installed_refresh.py exercises released wheels with disposable data. .github/workflows/discover.yml schedules read-only discovery after approval; selfcheck.yml independently verifies payload bytes.

ingest/nse.py -> dated NSE RSS candidate documents and tentative categories, not auto-approved calendar entries; schemas/holidays.in.schema.json represents the published named provenance map as well as the documented legacy list.
