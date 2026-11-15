import unittest
from ingest.notices import append
class Notices(unittest.TestCase):
    def test_idempotent_revision_with_missing_source_clock(self):
        r=dict(source='Nasdaq Baltic',source_url='https://www.nasdaqbaltic.com/statistics/en/calendar?holidays=1',document_id='fixture',source_published_at=None,effective_date='2026-12-31',market='XVIL',kind='trading_holiday',source_sha256='a'*64,revision=1,prior_revision_sha256=None,terms='test fixture, never publish')
        history={};key,added=append(history,r)
        self.assertTrue(added);self.assertFalse(append(history,r)[1])
        with self.assertRaises(ValueError):append(history,{**r,'terms':'conflict'})
        child={**r,'revision':2,'prior_revision_sha256':key,'terms':'revised test'}
        self.assertTrue(append(history,child)[1]);self.assertIsNone(history[key]['source_published_at'])
        self.assertEqual(len(history),2)
