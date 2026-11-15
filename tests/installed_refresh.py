"""Exercise two *installed* releases against a disposable source-data channel.

Run with aion-indian-market-calendar==1.8.0 and aion-lithuanian-market-calendar==1.2.1
installed in this interpreter. No runtime files or published data are modified.
"""
from pathlib import Path
from datetime import date,datetime,timezone
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from tempfile import TemporaryDirectory
from threading import Thread
from importlib.metadata import version
import importlib,json,sys,os,hashlib
def main():
    root=Path(__file__).resolve().parents[1]
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self,*a):pass
    http=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(root)))
    thread=Thread(target=http.serve_forever,daemon=True);thread.start()
    result={}
    try:
        with TemporaryDirectory() as tmp:
            for market,name,wanted in [('in','indian','1.8.0'),('lt','lithuanian','1.2.1')]:
                pkg=f'aion_{name}_market_calendar'
                assert version(pkg)==wanted
                pref='AION_'+market.upper()+'_CALENDAR_'
                os.environ.update({pref+'CACHE':str(Path(tmp)/market),pref+'OFFLINE':'1',pref+'URL':f'http://127.0.0.1:{http.server_port}/{market}'})
                st=importlib.import_module(pkg+'.store')
                def read():
                    if market=='lt':
                        return str(importlib.import_module(pkg).session_bounds_utc(date(2026,12,31),'XVIL'))
                    events=st.payload_for(2026)['events']
                    return next(e['metadata']['source'] for e in events if e['id']=='MCX_HOLIDAY_20260101')
                before=read();os.environ[pref+'OFFLINE']='0';status=st.refresh(force=True);assert status.startswith('updated to'),status
                after=read(); assert before!=after and st.status()['source']=='cache'
                if market=='lt':assert after=='None'
                else:assert after.endswith('trading-surveillance/trading-holidays')
                result[market]=dict(package_version=version(pkg),before=before,after=after,result=status,dataset=st.status()['dataset_version'],manifest_sha256=hashlib.sha256((root/market/'manifest.json').read_bytes()).hexdigest())
    finally:http.shutdown();http.server_close();thread.join()
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
