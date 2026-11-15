import argparse, unittest
from unittest.mock import patch
from ingest.__main__ import cmd_add_holiday,cmd_add_half_day

class VenueScope(unittest.TestCase):
    def test_one_venue_edit_does_not_change_other_venues(self):
        r={'year':2026,'exchange_holidays':[],'half_days':{},'exchange_holidays_by_venue':{'XTAL':[],'XVIL':[]},
           'half_days_by_venue':{'XTAL':{'2026-12-31':'12:00'},'XVIL':{}}}
        args=argparse.Namespace(package='lt',year=2026,date='2026-12-31',venue='XVIL',type='exchange',reason='local fixture',close='12:15')
        with patch('ingest.__main__._load',return_value=r),patch('ingest.__main__._save'):
            cmd_add_half_day(args)
            self.assertEqual(r['half_days'],{})
            cmd_add_holiday(args)
            self.assertEqual(r['half_days_by_venue']['XTAL'],{'2026-12-31':'12:00'})
            self.assertEqual(r['exchange_holidays'],[])
            self.assertEqual(r['exchange_holidays_by_venue']['XVIL'],['2026-12-31'])
            with self.assertRaises(SystemExit):cmd_add_half_day(args)
