"""Read-only source discovery. Emits review evidence, never published market rules."""
import hashlib,json,sys,time,os,tempfile
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib import request,parse
from . import baltic,nse
from xml.etree.ElementTree import ParseError
SOURCES=json.loads(Path(__file__).with_name('sources.json').read_text('utf-8'))
BUDGET=3*1024*1024
class OfficialOnly(request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        a,b=map(parse.urlsplit,(req.full_url,newurl))
        if b.scheme!='https' or b.netloc!=a.netloc: raise ValueError('Unapproved redirect')
        return super().redirect_request(req,fp,code,msg,headers,newurl)
def fetch(url):
    req=request.Request(url,headers={'User-Agent':'AION-Calendar-Data/1.0 (source review)'})
    with request.build_opener(OfficialOnly()).open(req,timeout=8) as r:
        content=r.read(BUDGET+1)
        if len(content)>BUDGET or not content: raise ValueError('Empty or oversized response')
        if r.headers.get_content_type() not in ('text/html','application/pdf','text/plain','application/xhtml+xml','application/xml','text/xml','application/rss+xml'):raise ValueError('Unrecognized document type')
        return content
def snapshot(name,url,prior,now,fetcher=fetch):
    last=prior.get('last_success')
    try:
        raw=fetcher(url)
        digest=hashlib.sha256(raw).hexdigest()
        if name=='Nasdaq Baltic':
            rows=baltic.parse(raw,now.year)
            # Hash canonical dates + MIC, not ephemeral export IDs or retrieval time.
            identity=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
            observed=[dict(mic=m,effective_date=d,kind='trading_holiday') for d,m in rows]
        elif name=='NSE circular RSS':
            observed=nse.candidates(raw)
            identity=hashlib.sha256(json.dumps(observed,sort_keys=True).encode()).hexdigest()
        else:
            identity=digest;observed=None
        return dict(source=url,observed_at=now.isoformat(),last_success=now.isoformat(),
                    source_publication_time=None,source_sha256=digest,identity=identity,
                    comparison='unchanged' if prior.get('identity')==identity else ('changed' if prior.get('identity') else 'baseline'),
                    state='review_candidate' if observed is not None else 'source_page_only',
                    events=observed,authorized_for_publication=False)
    except (OSError,ValueError,UnicodeError,ParseError) as exc:
        stale=not last or now-datetime.fromisoformat(last)>timedelta(days=2)
        return {**prior,'source':url,'observed_at':now.isoformat(),'last_success':last,'state':'unavailable',
                'overdue':stale,'error_type':type(exc).__name__,'authorized_for_publication':False}
def main():
    path=Path(sys.argv[1]);old=json.loads(path.read_text('utf-8')) if path.is_file() else {}
    now=datetime.now(timezone.utc)
    current={name:snapshot(name,url,old.get(name,{}),now) for name,url in SOURCES.items()}
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,delete=False,encoding='utf-8') as out:
        json.dump(current,out,sort_keys=True,indent=2);out.write('\n')
    os.replace(out.name,path)
    for name,r in current.items():print(name,r['state'],r.get('comparison'),r.get('overdue'))
    return 1 if any(r['state']=='unavailable' for r in current.values()) else 0
if __name__=='__main__':sys.exit(main())
