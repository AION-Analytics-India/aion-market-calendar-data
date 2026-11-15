import unittest
from datetime import datetime,timezone,timedelta
from ingest.discover import snapshot
from ingest.baltic import SOURCE
class TestSourceReview(unittest.TestCase):
    def test_venue_scope_idempotence_and_outage(self):
        html=b'<table><tr><td>31.12.2026</td><td>Trading holiday</td><td>TLN RIG VLN</td></tr><tr><td>18.11.2026</td><td>Trading holiday</td><td>RIG</td></tr></table>'
        at=datetime(2026,11,15,tzinfo=timezone.utc)
        first=snapshot('Nasdaq Baltic',SOURCE,{},at,lambda _:html)
        self.assertEqual(len(first['events']),4)
        again=snapshot('Nasdaq Baltic',SOURCE,first,at,lambda _:html+b'<!-- daily counter -->')
        self.assertEqual(again['comparison'],'unchanged')
        last=snapshot('Nasdaq Baltic',SOURCE,again,at+timedelta(days=3),lambda _:b'<html>unavailable</html>')
        self.assertEqual(last['state'],'unavailable')
        self.assertTrue(last['overdue']);self.assertEqual(last['identity'],first['identity'])
        self.assertFalse(last['authorized_for_publication'])
        self.assertIsNone(first['source_publication_time'])
    def test_reachable_page_alone_is_not_classification(self):
        r=snapshot('NSE','https://www.nseindia.com/',{},datetime.now(timezone.utc),lambda _:b'landing')
        self.assertEqual(r['state'],'source_page_only');self.assertIsNone(r['events'])

class NSE(unittest.TestCase):
    def test_no_change_and_separate_revisions(self):
        from ingest.nse import candidates
        base='<rss><channel>{}</channel></rss>'
        item='<item><title>Settlement holiday</title><guid>123</guid><link>https://nsearchives.nseindia.com/content/a.pdf</link></item>'
        self.assertEqual(candidates(base.format('').encode()),[])
        rows=candidates(base.format(item+item).encode());self.assertEqual(len(rows),1)
        self.assertIsNone(rows[0]['effective_date']);self.assertIsNone(rows[0]['source_published_at'])
        self.assertNotEqual(rows[0]['revision_sha256'],candidates(base.format(item.replace('Settlement holiday','Revised settlement holiday')).encode())[0]['revision_sha256'])
