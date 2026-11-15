"""Candidate records from the official NSE circular RSS. Effective dates require review."""
import hashlib,json
from xml.etree import ElementTree as ET
from urllib.parse import urlsplit
from email.utils import parsedate_to_datetime
from datetime import timezone

def candidates(raw):
    if b'<!DOCTYPE' in raw.upper():raise ValueError('Unexpected RSS declaration')
    root=ET.fromstring(raw)
    if root.find('channel') is None:raise ValueError('Not RSS')
    tokens={'emergency_closure':('emergency closure','unscheduled closure'),
            'settlement_holiday':('settlement holiday',),'partial_session':('early close','partial session'),
            'special_session':('muhurat','special trading','special session'),
            'expiry_rule':('expiry','expiration'),'trading_holiday':('holiday','market closed'),
            'session_rule':('session','market timing','trading hour')}
    out={}
    for item in root.findall('channel/item'):
        title=(item.findtext('title') or '').strip();link=(item.findtext('link') or '').strip()
        kinds=[k for k,terms in tokens.items() if any(t in title.lower() for t in terms)]
        if not kinds:continue
        u=urlsplit(link)
        if u.scheme!='https' or u.username or u.password or u.hostname not in {'nsearchives.nseindia.com','archives.nseindia.com','www.nseindia.com'}: raise ValueError('Non-official circular reference')
        published=item.findtext('pubDate')
        ident=item.findtext('guid') or link
        row=dict(document_id=ident,source_url=link,title=title,source_published_at=published,
                 effective_date=None,possible_categories=kinds,disposition='manual_source_review')
        digest=hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
        out[(ident,digest)]={**row,'revision_sha256':digest}
    return [out[k] for k in sorted(out)]
