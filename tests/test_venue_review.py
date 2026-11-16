import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from ingest.venue_validation import validate, unique_keys, REVIEW

ROOT = Path(__file__).resolve().parents[1]
class VenueReview(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "lt/holidays_2026.json").read_bytes())

    def test_production_scope(self):
        self.assertEqual(validate(self.data, 2026), [])
        self.assertIn("2026-02-16", self.data["exchange_holidays"])
        self.assertNotIn("2026-02-16", self.data["exchange_holidays_by_venue"]["XRIS"])
        self.assertIn("2026-11-18", self.data["exchange_holidays_by_venue"]["XRIS"])
        self.assertIn("2026-12-31", self.data["half_days"])
        for m in ("XVIL", "XRIS", "XTAL"):
            self.assertEqual(self.data["half_days_by_venue"][m], {})
            self.assertIn("2026-12-31", self.data["exchange_holidays_by_venue"][m])

    def test_missing_wrong_duplicate_bad_date_and_time(self):
        for key, value in (("exchange_holidays_by_venue", []),
                           ("exchange_holidays_by_venue", ["2026-11-18"] * 2),
                           ("exchange_holidays_by_venue", ["2027-11-18"]),
                           ("exchange_holidays_by_venue", ["2026-02-30"]),
                           ("half_days_by_venue", {"2026-11-18":"12:30"}),
                           ("half_days_by_venue", {"2026-02-16":"25:00"}),
                           ("half_days_by_venue", None)):
            with self.subTest(key=key, value=value):
                d = copy.deepcopy(self.data); d[key]["XRIS"] = value
                self.assertTrue(validate(d, 2026))
        del self.data["half_days_by_venue"]["XVIL"]
        self.assertTrue(validate(self.data, 2026))
        self.assertTrue(validate(self.data, 2027))

    def test_independent_fallback_of_each_map(self):
        d = dict(year=2028, timezone="Europe/Vilnius", exchange_holidays=["2028-01-04"],
                 half_days={"2028-01-05":"12:30"}, exchange_holidays_by_venue={"XRIS":["2028-01-05"]})
        self.assertTrue(validate(d))  # absent half-day override inherits global
        d["half_days_by_venue"] = {"XRIS": {}}
        self.assertEqual(validate(d), [])
        d["half_days_by_venue"]["XTAL"] = {"2028-01-04":"12:30"}
        self.assertTrue(validate(d))  # absent closure override inherits global

    def test_source_and_duplicates(self):
        with self.assertRaises(ValueError):
            json.loads('{"XRIS":[],"XRIS":[]}', object_pairs_hook=unique_keys)
        with TemporaryDirectory() as t:
            p = Path(t) / "review.json"
            data = json.loads(REVIEW.read_bytes()); data["url"] = "https://example.org/"
            p.write_text(json.dumps(data))
            self.assertTrue(validate(self.data, 2026, p))
