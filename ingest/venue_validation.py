"""Publisher-only validation of an effective venue calendar. No network access."""
from datetime import date, datetime
import json
import re
from pathlib import Path

BALTIC = {"XVIL", "XRIS", "XTAL"}
SOURCE = "https://www.nasdaqbaltic.com/statistics/en/calendar?holidays=1"
REVIEW = Path(__file__).with_name("sources") / "nasdaq_baltic_2026.json"


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def validate(payload, expected_year=None, review_path=REVIEW):
    def require(ok, reason):
        if not ok:
            raise ValueError(reason)

    def day(s):
        require(isinstance(s, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", s), "invalid ISO date")
        require(date.fromisoformat(s).year == year, f"unexpected year: {s}")
        return s

    def dates(items):
        require(isinstance(items, list), "closure dates must be an array")
        result = {day(s) for s in items}
        require(len(result) == len(items), "duplicate closure date")
        return result

    def halves(table):
        require(isinstance(table, dict), "half-days must be a mapping")
        for key, value in table.items():
            day(key)
            require(isinstance(value, str) and re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value),
                    f"invalid local closing time for {key}")
        return set(table)

    try:
        require(isinstance(payload, dict), "payload must be an object")
        year = payload.get("year")
        require(type(year) is int and (expected_year is None or expected_year == year), "filename/year mismatch")
        require(payload.get("timezone") == "Europe/Vilnius", "invalid payload timezone")
        global_ex = dates(payload["exchange_holidays"])
        global_half = halves(payload.get("half_days", {}))
        dates(payload.get("public_holidays", []))
        require(not global_ex & global_half, "global full-day/half-day contradiction")
        overrides = payload.get("exchange_holidays_by_venue", {})
        partials = payload.get("half_days_by_venue", {})
        require(isinstance(overrides, dict) and isinstance(partials, dict), "invalid MIC mapping")
        for mic in set(overrides) | set(partials):
            require(re.fullmatch(r"[A-Z0-9]{4}", mic), f"invalid MIC: {mic}")
            closures = dates(overrides[mic]) if mic in overrides else global_ex
            early = halves(partials[mic]) if mic in partials else global_half
            require(not closures & early, f"full-day/half-day contradiction for {mic}")
        if year == 2026:
            review = json.loads(review_path.read_bytes(), object_pairs_hook=unique_keys)
            require(review["url"] == SOURCE and re.fullmatch(r"[a-f0-9]{64}", review["sha256"]),
                    "invalid reviewed Nasdaq source")
            require(datetime.fromisoformat(review["at"]).utcoffset() is not None, "undated source receipt")
            rows = [(day(d), m) for d, m in review["rows"]]
            require(len(rows) == len(set(rows)) == 39 and {m for _, m in rows} == BALTIC,
                    "incomplete or duplicate reviewed records")
            for mic in sorted(BALTIC):
                require(mic in overrides and mic in partials, f"missing explicit mapping for {mic}")
                require(dates(overrides[mic]) == {d for d, m in rows if m == mic},
                        f"{mic} differs from reviewed Nasdaq closures")
                require(partials[mic] == {}, f"unreviewed half-day for {mic}")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return [str(exc)]
    return []
