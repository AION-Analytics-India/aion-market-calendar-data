# Shared market calendar data

Official Nasdaq Baltic 2026 review -> ingest/sources/nasdaq_baltic_2026.json -> ingest/venue_validation.py -> ingest/__main__.py verify/publish -> lt/holidays_2026.json and lt/manifest.json -> installed client cache. A present MIC overrides only its own mapping. in/ and lt/holidays_2027.json are unchanged. ingest/manifest.py enforces file hashes and completeness. schemas/ documents the public data shapes. tests/test_venue_review.py and .github/workflows/selfcheck.yml verify this boundary.

CI uses ingest/schema_gate.py with the checked-in JSON Schemas. The Indian sources schema accepts the already published name-to-string mapping as well as historical string lists. No Indian payload, consumer, or release change.
