# aion-market-calendar-data

Holiday and exchange-closure data for the AION market calendar packages. This is
what the libraries fetch at runtime, served from GitHub raw.

| package | path | what it holds |
| --- | --- | --- |
| [`aion-indian-market-calendar`](https://github.com/AION-Analytics-India/aion-indian-market-calendar) | [`in/`](in/) | NSE, BSE and MCX market events |
| [`aion-lithuanian-market-calendar`](https://github.com/AION-Analytics-India/aion-lithuanian-market-calendar) | [`lt/`](lt/) | Nasdaq Baltic closures and half-days |

## Why the data is not in the packages

Some of it is. Each wheel bundles a copy, and that copy is always the fallback.

But an exchange closes when it announces it will, and a government can declare a
day of mourning at a week's notice. A library that could only learn about those
through a PyPI release would be quietly wrong for however long it took someone to
notice and publish — and "quietly wrong" is the failure mode a calendar exists to
prevent.

So the data lives here, and the libraries refresh from it at most once a day.
**A new holiday never needs a release.**

## Why one repository for both

A shared manifest describes country-specific files and checksums. A common maintenance tool verifies both countries without treating their market rules as interchangeable.

## Why the payloads are *not* identical

Deliberate, and worth stating because it looks like an oversight.

Lithuanian data is date lists: a closure is a date. Indian data is events, each
carrying an id, a policy, an impact level and a time range, because callers act
on them — a partial trading day is not the same object as a full closure.

Flattening the Indian payload into date lists would have destroyed information
its users already depend on. Inflating the Lithuanian one into events would have
added ceremony to a file that has nothing to put in it.

**The manifest is the contract. The payload beneath it is the package's own
business.** [`schemas/`](schemas/) holds all three.

## Integrity

Each country manifest lists SHA-256 digests. These detect changed or incomplete payloads; **the data manifests are not digitally signed**. Authenticity depends on the authenticated distribution source, repository access and review. A healthy hash does not establish exchange correctness. The separate experimental software updater uses signed offers and a separate trust policy.

Consumers stage and verify compatible files before adoption. Replacement semantics depend on the installed version: Lithuanian 1.2.1 uses per-file replacement; its review candidate switches one generation pointer. Offline clients use their previously available data within documented coverage. Neither a network failure nor an unreviewed notice extends that coverage.

## Maintaining it

```bash
python -m ingest verify                       # both packages
python -m ingest show --package lt --year 2026

python -m ingest add-holiday --help           # country/market scoped review tooling
python -m ingest add-half-day --help
python -m ingest publish --help               # maintainer release authority required
```

`publish` refuses to push anything that does not verify. Every change records
*why*: a date with no source cannot be checked by the next person and cannot be
defended when a user asks where it came from.

`verify` also checks three contradictions a hash cannot see — a date in the
global list but missing from a venue's own list (the per-venue list wins, so it
would silently do nothing), a day that is both a full closure and a half-day, and
a date in the wrong year's file. Each of those has actually happened here.

## Corrections

A wrong date makes someone's settlement job run on a day the market was shut. It
is the most useful bug report this project can get. Open an issue with the date,
the venue, and **the announcement it comes from**.

## Privacy

Fetching this data sends no identifier. The libraries send a `User-Agent` naming
the package and version, which every HTTP client sends, and nothing else. No
telemetry, no analytics, no install id, no timestamp.

Earlier versions of the Indian package did send a persistent install identifier;
it was removed in 1.4.0 and is documented in that repository's
`docs/TELEMETRY_AUDIT.md`.

Set `AION_IN_CALENDAR_OFFLINE=1` or `AION_LT_CALENDAR_OFFLINE=1` to disable
network access entirely.

---

MIT licensed. [AION Analytics (India)](https://github.com/AION-Analytics-India).

## Review branch: daily discovery and release gates

The deployed baseline has monthly and data-push self-checks. The proposed daily 02:17 UTC workflow and calendar-notice-received dispatch collect source evidence only. A successful page fetch is not approval. The Baltic adapter compares dated market rows; other source-page fingerprints require a human to locate and classify the notice. Missing publication times stay null. Dated changes are reviewed by venue, market and source before publishing. Use python -m ingest.discover PATH/receipts.json for a local checkpoint and python -m ingest verify for data verification. Install jsonschema>=4.18,<5 in the maintainer environment for publish --no-push schema validation. Do not run publish without separate release approval.

