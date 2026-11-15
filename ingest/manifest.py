"""Build and verify a data manifest.

The manifest is the contract every package shares. Its payload beneath is not:
Lithuanian data is date lists, Indian data is events carrying a policy and an
impact level. Unifying those would have cost the Indian package information its
users already act on, so the manifest is what is shared and the payload is not.

**Never edit manifest.json by hand.** Its entire purpose is to prove the data
files are the ones the maintainer intended, and a hash typed by a person proves
nothing at all.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
REPO = "https://github.com/AION-Analytics-India/aion-market-calendar-data"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _years(directory: Path) -> list[int]:
    """Years covered, read from whatever shape the payload happens to be."""
    years: set[int] = set()
    for path in directory.glob("holidays_*.json"):
        try:
            years.add(int(path.stem.split("_")[-1]))
        except ValueError:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if "year" in payload:
                years.add(int(payload["year"]))
    return sorted(years)


def build(directory: Path, dataset_version: str | None = None) -> dict[str, Any]:
    files = sorted(p for p in directory.glob("*.json") if p.name != "manifest.json")
    if not files:
        raise SystemExit(f"no payload files in {directory}")
    today = date.today()
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_version": dataset_version or datetime.now(timezone.utc).strftime("%Y.%m.%d"),
        "last_updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # Exchanges publish next year's calendar in the autumn; this lands before
        # then so the reminder arrives while the data still has time to be wrong.
        "next_review_date": min(date(today.year + (0 if today.month < 10 else 1), 10, 1), date(max(_years(directory)), 12, 1)).isoformat(),
        "years": _years(directory),
        "files": {p.name: sha256(p) for p in files},
        "source": REPO,
        "note": ("Every file must verify against its hash before any is adopted. "
                 "A partial adoption is how a 105-byte delta overwrote a 117 KB "
                 "taxonomy on 2026-06-26."),
    }


def write(directory: Path, dataset_version: str | None = None) -> dict[str, Any]:
    manifest = build(directory, dataset_version)
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def verify(directory: Path) -> tuple[bool, str]:
    """Does this directory hold a manifest whose hashes match its files?"""
    path = directory / "manifest.json"
    if not path.exists():
        return False, "manifest.json is missing"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"manifest.json is unreadable ({exc})"
    if manifest.get("schema_version") != SCHEMA_VERSION:
        return False, f"schema {manifest.get('schema_version')!r} is not {SCHEMA_VERSION}"
    files = manifest.get("files") or {}
    if not files:
        return False, "manifest lists no files"
    for name, expected in files.items():
        candidate = directory / name
        if not candidate.exists():
            return False, f"{name} is listed but missing"
        if sha256(candidate) != expected:
            return False, f"{name} does not match its manifest hash"
    # A file present but unlisted is as wrong as one listed and missing: the
    # manifest must describe the directory exactly, or "verified" means nothing.
    on_disk = {p.name for p in directory.glob("*.json")} - {"manifest.json"}
    unlisted = on_disk - set(files)
    if unlisted:
        return False, f"{sorted(unlisted)} present but not in the manifest"
    return True, "ok"
