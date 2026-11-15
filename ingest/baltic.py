"""Extract candidate closure rows from the Nasdaq Baltic HTML table, never its ICS market labels."""
import re
from html.parser import HTMLParser
from datetime import datetime,timedelta

SOURCE='https://www.nasdaqbaltic.com/statistics/en/calendar?holidays=1'
MICS={'VLN':'XVIL','RIG':'XRIS','TLN':'XTAL'}

class Rows(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.col=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr': self.row=[]
        if tag=='td' and self.row is not None: self.col=[]
    def handle_data(self,data):
        if self.col is not None: self.col.append(data.strip())
    def handle_endtag(self,tag):
        if tag=='td' and self.col is not None:
            self.row.append(' '.join(self.col).strip()); self.col=None
        if tag=='tr' and self.row is not None:
            self.rows.append(self.row); self.row=None; self.col=None

def parse(raw,year):
    parser=Rows(); parser.feed(raw.decode('utf-8-sig'))
    events=set()
    for cells in parser.rows:
        if len(cells)<3 or cells[1].strip()!='Trading holiday': continue
        ds=cells[0].split(); markets=cells[2].split()
        if len(ds) not in (1,2) or not markets or not set(markets)<=MICS.keys():
            raise ValueError('Unknown exchange row format; review required')
        start,end=[datetime.strptime(s,'%d.%m.%Y').date() for s in (ds[0],ds[-1])]
        if start.year!=year: continue
        if end.year!=year or not 0<=(end-start).days<=14: raise ValueError('Invalid date interval')
        for i in range(1+(end-start).days):
            for market in markets: events.add(((start+timedelta(days=i)).isoformat(),MICS[market]))
    if not events or {m for _,m in events}!=set(MICS.values()):
        raise ValueError('Incomplete exchange table')
    return sorted(events)
