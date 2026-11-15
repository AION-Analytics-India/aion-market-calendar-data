#!/usr/bin/env python3
"""One tool, both calendars.

    python -m ingest verify
    python -m ingest show       --package lt --year 2026
    python -m ingest add-holiday --help
    python -m ingest add-half-day --help
    python -m ingest publish

Works on both packages because the *manifest* is shared. The payloads are not,
and deliberately so: Lithuanian data is date lists, Indian data is events
carrying a policy and an impact level that callers act on. Flattening the second
into the first would lose information users already depend on.

Consequence, stated rather than hidden: the holiday-editing commands currently
operate on the Lithuanian payload only. Adding an Indian event means writing an
event object with an id, a policy and a time range, which is a different job and
is not guessed at here. `verify` and `publish` cover both.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from ingest.manifest import verify as verify_dir, write as write_manifest  # noqa: E402

PACKAGES = {"lt": "Lithuanian (Nasdaq Baltic)", "in": "Indian (NSE/BSE/MCX)"}


def _dir(package: str) -> Path:
    return REPO / package


def _payload(package: str, year: int) -> Path:
    return _dir(package) / f"holidays_{year}.json"


def _load(package: str, year: int) -> dict:
    path = _payload(package, year)
    if not path.exists():
        sys.exit(f"no data for {package}/{year} at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _save(package: str, year: int, payload: dict) -> None:
    _payload(package, year).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _record(payload: dict, entry: str) -> None:
    """An in-file changelog. Git history serves maintainers; this file is what
    users download, and someone asking why their exchange shut on a Tuesday
    should not have to clone a repository to find out."""
    payload.setdefault("changes", []).append(
        {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "change": entry})


def _consistency(package: str, payload: dict) -> list[str]:
    """Contradictions a hash cannot catch. Each of these has actually happened."""
    problems: list[str] = []
    if package != "lt":
        return problems            # the Indian payload has its own shape
    year = payload.get("year")
    global_ex = set(payload.get("exchange_holidays") or [])
    by_venue = payload.get("exchange_holidays_by_venue") or {}
    for mic, dates in by_venue.items():
        missing = global_ex - set(dates)
        if missing:
            problems.append(f"{mic} is missing {sorted(missing)} which are in the global "
                            f"list; the per-venue list wins, so they do nothing for {mic}")
    for day in (payload.get("half_days") or {}):
        if day in global_ex:
            problems.append(f"{day} is both a full closure and a half-day")
    for mic, table in (payload.get("half_days_by_venue") or {}).items():
        for day in table:
            if day in set(by_venue.get(mic, global_ex)):
                problems.append(f"{day} is both a closure and a half-day for {mic}")
    for field in ("public_holidays", "exchange_holidays"):
        for day in (payload.get(field) or []):
            if not str(day).startswith(str(year)):
                problems.append(f"{day} in {field} is not in year {year}")
    return problems


def cmd_verify(args) -> int:
    failed = False
    for package in (args.package,) if args.package else PACKAGES:
        ok, why = verify_dir(_dir(package))
        print(f"  {package}/: manifest {'ok' if ok else 'FAILED - ' + why}")
        failed |= not ok
        for path in sorted(_dir(package).glob("holidays_*.json")):
            problems = _consistency(package, json.loads(path.read_text(encoding="utf-8")))
            for problem in problems:
                print(f"    {path.name}: {problem}")
            failed |= bool(problems)
            if not problems:
                print(f"    {path.name}: consistent")
    if failed:
        print("\n  to rebuild a manifest: python -m ingest publish --no-push")
    return 1 if failed else 0


def cmd_show(args) -> int:
    payload = _load(args.package, args.year)
    if args.package == "lt":
        pub = payload.get("public_holidays") or []
        exch = payload.get("exchange_holidays") or []
        print(f"  {args.package}/{args.year}  verified_on {payload.get('verified_on')}")
        print(f"    public: {len(pub)}  exchange: {len(exch)}  half-days: {payload.get('half_days') or '{}'}")
        print(f"    closed but not a public holiday: {sorted(set(exch) - set(pub)) or 'none'}")
    else:
        print(f"  {args.package}/{args.year}  version {payload.get('version')}")
        print(f"    events: {len(payload.get('events') or [])}  range: {payload.get('range', {}).get('start')} to {payload.get('range', {}).get('end')}")
    for change in (payload.get("changes") or [])[-5:]:
        print(f"    [{change['at'][:10]}] {change['change']}")
    return 0


def cmd_add_holiday(args) -> int:
    if args.package != "lt":
        sys.exit("add-holiday currently edits the Lithuanian payload only. An Indian "
                 "entry is an event object with an id, a policy and a time range; "
                 "write it by hand rather than have this tool guess at it.")
    day = date.fromisoformat(args.date)
    payload = _load(args.package, day.year)
    key = "exchange_holidays" if args.type == "exchange" else "public_holidays"
    tables=payload.get("exchange_holidays_by_venue") or {}
    if args.type != "exchange":
        if args.venue: raise SystemExit("Statutory dates do not take an exchange venue")
        payload[key]=sorted(set(payload.get(key,[]))|{args.date})
    else:
        venue=args.venue.upper() if args.venue else None
        if venue and venue not in tables: raise SystemExit("Unknown venue; no edits made")
        for mic in ([venue] if venue else tables):
            tables[mic]=sorted(set(tables[mic])|{args.date})
            (payload.get("half_days_by_venue",{}).get(mic) or {}).pop(args.date,None)
        payload[key]=sorted(set.intersection(*(set(v) for v in tables.values()))) if tables else sorted(set(payload.get(key,[]))|{args.date})
        if args.date in payload[key]: payload.get("half_days",{}).pop(args.date,None)
    _record(payload, f"added {args.date} to {key}: {args.reason}")
    _save(args.package, day.year, payload)
    print(f"  {args.package}/{day.year}: {args.date} added to {key}")
    return 0


def cmd_add_half_day(args) -> int:
    if args.package != "lt":
        sys.exit("add-half-day currently edits the Lithuanian payload only.")
    day = date.fromisoformat(args.date)
    datetime.strptime(args.close, "%H:%M")
    payload = _load(args.package, day.year)
    if args.date in set(payload.get("exchange_holidays") or []):
        sys.exit(f"  {args.date} is already a full closure; remove it from "
                 f"exchange_holidays before making it a half-day")
    tables=payload.get("half_days_by_venue") or {}
    venue=args.venue.upper() if args.venue else None
    if venue and venue not in tables: raise SystemExit("Unknown venue; no edits made")
    markets=[venue] if venue else list(tables)
    if any(args.date in payload.get("exchange_holidays_by_venue",{}).get(mic,[]) for mic in markets):
        raise SystemExit("Venue is closed; refusing a simultaneous half-day")
    if not venue: payload.setdefault("half_days",{})[args.date]=args.close
    for mic in markets: tables[mic][args.date]=args.close
    _record(payload, f"half-day {args.date} closing {args.close}: {args.reason}")
    _save(args.package, day.year, payload)
    print(f"  {args.package}/{day.year}: {args.date} closes {args.close}")
    return 0


def cmd_publish(args) -> int:
    """Rebuild manifests, verify, and push. Refuses to push anything that does
    not verify -- the whole point of the hash is that it gates publication."""
    for package in (args.package,) if args.package else PACKAGES:
        manifest = write_manifest(_dir(package), args.dataset_version)
        print(f"  {package}/: manifest {manifest['dataset_version']}, "
              f"{len(manifest['files'])} file(s)")
    rc = cmd_verify(argparse.Namespace(package=args.package))
    if rc != 0:
        sys.exit("  verification failed; nothing pushed")
    from .schema_gate import validate_generation
    for package in (args.package,) if args.package else PACKAGES:
        validate_generation(REPO,package)
    if args.no_push:
        print("\n  --no-push: manifests rebuilt, nothing committed")
        return 0
    try:
        if subprocess.run(["git","diff","--cached","--quiet"],cwd=REPO).returncode:
            raise SystemExit("Pre-existing staged changes; use an isolated publication checkout")
        owned=[args.package] if args.package else sorted(PACKAGES)
        subprocess.run(["git","add","--",*owned],cwd=REPO,check=True)
        subprocess.run(["git", "commit", "-m",
                        f"data: {datetime.now(timezone.utc):%Y-%m-%d} update"],
                       cwd=REPO, check=True)
        subprocess.run(["git", "push"], cwd=REPO, check=True)
        print("\n  pushed. Eligible online clients can adopt a compatible verified generation.")
    except subprocess.CalledProcessError as exc:
        print(f"\n  git step failed ({exc}); the manifests are rebuilt locally.")
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="python -m ingest", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    def add_pkg(parser, required=False):
        parser.add_argument("--package", choices=sorted(PACKAGES), required=required,
                            help="lt or in; omit on verify/publish to do both")

    v = sub.add_parser("verify"); add_pkg(v); v.set_defaults(func=cmd_verify)
    s = sub.add_parser("show"); add_pkg(s, True)
    s.add_argument("--year", type=int, required=True); s.set_defaults(func=cmd_show)

    a = sub.add_parser("add-holiday"); add_pkg(a, True)
    a.add_argument("--date", required=True)
    a.add_argument("--type", required=True, choices=("exchange", "public"))
    a.add_argument("--reason", required=True, help="the circular or announcement")
    a.add_argument("--venue"); a.set_defaults(func=cmd_add_holiday)

    h = sub.add_parser("add-half-day"); add_pkg(h, True)
    h.add_argument("--date", required=True)
    h.add_argument("--close", required=True, help="HH:MM local")
    h.add_argument("--reason", required=True)
    h.add_argument("--venue"); h.set_defaults(func=cmd_add_half_day)

    p = sub.add_parser("publish"); add_pkg(p)
    p.add_argument("--dataset-version")
    p.add_argument("--no-push", action="store_true")
    p.set_defaults(func=cmd_publish)

    args = ap.parse_args()
    rc = args.func(args)
    if args.command in {"add-holiday", "add-half-day"}:
        print("\n  now: python -m ingest publish")
    return rc


if __name__ == "__main__":
    sys.exit(main())
