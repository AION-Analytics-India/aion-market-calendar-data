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

The manifest schema is identical across packages, which is what lets a single
ingestion tool maintain all of them. Two repositories would have meant two tools
that drift apart, which is how the Lithuanian and Indian packages ended up with
different update mechanisms in the first place — one of them broken.

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

`manifest.json` lists a SHA-256 for every file beside it. A client downloads to a
staging directory, verifies **every** hash, and only then swaps the files into
place atomically. A single mismatch means nothing is adopted.

This is not ceremony. On 2026-06-26 a refresh without hash verification wrote a
105-byte delta over a 117 KB taxonomy file and wiped a production sector engine.
The guard added at the time checked a size floor and some required keys, which
stops that exact payload and nothing else. A hash stops all of them.

**`manifest.json` is never edited by hand.** Its purpose is to prove the payload
files are the ones the maintainer intended, and a hash typed by a person proves
nothing.

## Maintaining it

```bash
python -m ingest verify                       # both packages
python -m ingest show --package lt --year 2026

python -m ingest add-holiday --package lt --date 2026-11-17 --type exchange \
    --reason "Day of national mourning (Seimas resolution XIV-1234)"

python -m ingest publish                      # rebuild manifests, verify, push
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

## Website, maintainer and security contact

- Website page: https://aionanalytics.in/open-source/indian-market-calendar
- Organisation: https://aionanalytics.in/ (AION Analytics, India)
- Maintainer and security contact: contact@aionanalytics.in. Report a defect through GitHub issues; report a security concern by email, not in a public issue.
- Company page: https://www.linkedin.com/company/aion-analytics-india/
