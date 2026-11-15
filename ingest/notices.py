"""Validate an explicit reviewed notice for handoff to a country-specific builder.

There is deliberately no network, Git push or inference from a missing date.
Approval belongs to repository review, not a boolean in a submitted document.
"""
from datetime import date,datetime
from urllib.parse import urlsplit
import hashlib,json,re
from .discover import SOURCES

CATEGORIES=('trading_holiday','settlement_holiday','partial_session','special_session','expiry_rule','emergency_closure','statutory_holiday')
def validate(row):
    required={'source','source_url','document_id','source_published_at','effective_date','market','kind','source_sha256','revision','prior_revision_sha256','terms'}
    if set(row)!=required: raise ValueError('Incorrect notice schema')
    url=urlsplit(row['source_url'])
    if row['source'] not in SOURCES or url.scheme!='https' or url.netloc!=urlsplit(SOURCES[row['source']]).netloc or url.username or url.password: raise ValueError('Unrecognized authority')
    if not row['document_id'] or not row['market'] or row['kind'] not in CATEGORIES or not row['terms']:raise ValueError('Missing market, terms or scope')
    date.fromisoformat(row['effective_date'])
    if row['source_published_at'] is not None:
        t=row['source_published_at']
        if len(t)==10: date.fromisoformat(t)
        elif datetime.fromisoformat(t.replace('Z','+00:00')).utcoffset() is None: raise ValueError('Ambiguous publication time')
    h=r'[a-f0-9]{64}'
    if not re.fullmatch(h,row['source_sha256']) or type(row['revision'])!=int or row['revision']<1: raise ValueError('Invalid evidence or revision')
    prev=row['prior_revision_sha256']
    if (row['revision']==1 and prev is not None) or (row['revision']>1 and not re.fullmatch(h,prev or '')):raise ValueError('Missing or unexpected revision parent')
    raw=json.dumps(row,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()
def append(history,row):
    h=validate(row)
    if h in history:return h,False
    identity=lambda r:(r['source'],r['document_id'],r['market'],r['kind'])
    prior=[(r['revision'],k) for k,r in history.items() if identity(r)==identity(row)]
    version,parent=max(prior,default=(0,None))
    if (row['revision'],row['prior_revision_sha256'])!=(version+1,parent):raise ValueError('Revision does not continue the evidence chain')
    history[h]=dict(row)
    return h,True
