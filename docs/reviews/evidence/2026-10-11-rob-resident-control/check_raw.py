#!/usr/bin/env python3
"""Independent direct raw arithmetic and every SHA; no primary consumer imported."""
import argparse,gzip,hashlib,json,statistics as st
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('raw',type=Path);p.add_argument('--evidence',type=Path,default=Path(__file__).resolve().parent);args=p.parse_args();e=args.evidence;a=json.loads((e/'analysis.json').read_text());summary=gzip.decompress((e/'summary.json.gz').read_bytes());s=json.loads(summary)
 assert hashlib.sha256(summary).hexdigest()==a['input_sha256']
 assert {x.name for x in args.raw.iterdir()}==set(a['all_raw_sha256'])
 for name,digest in a['all_raw_sha256'].items():assert hashlib.sha256((args.raw/name).read_bytes()).hexdigest()==digest
 points=[];blocks=[];count=0
 for row in s['rows']:
  rr=[json.loads(l) for l in (args.raw/(row['condition']+'.stdout.jsonl')).read_text().splitlines()];assert rr==[row['config'],row['program'],row['runtime'],*row['samples']];cfg=rr[0];by={}
  epoch=int(row['condition'][1]);generation=1
  for pos,z in enumerate(rr[3:]):
   index=15-pos if cfg['reverse'] else pos;b=index//2;slot=index%2;prep='reinstall' if (b+slot)%2 else 'resident';generation+=prep=='reinstall';assert (z['position'],z['block'],z['slot'],z['preparation'],z['installation_generation'])==(pos,b,slot,prep,generation);by[b,prep]=z['counts'][0]/131072;count+=1
  for prep in ('resident','reinstall'):
   values=[by[b,prep] for b in range(8)];spread=(max(values)-min(values))/st.median(values);points.append(dict(epoch=epoch,anchor=cfg['anchor'],link=cfg['link'],n=cfg['n'],preparation=prep,cycles=values,median=st.median(values),range_fraction=spread,stable=spread<=.10))
  for b in range(8):
   delta=by[b,'reinstall']-by[b,'resident'];blocks.append(dict(epoch=epoch,anchor=cfg['anchor'],link=cfg['link'],n=cfg['n'],block=b,resident=by[b,'resident'],reinstall=by[b,'reinstall'],delta=delta,relative_delta=delta/by[b,'resident']))
 assert points==a['points'] and blocks==a['blocks'] and count==240
 for c in a['conditions']:
  pp=[p for p in points if all(p[k]==c[k] for k in ('anchor','link','n'))];bb=[b for b in blocks if all(b[k]==c[k] for k in ('anchor','link','n'))];stable={p:all(z['stable'] for z in pp if z['preparation']==p) for p in ('resident','reinstall')};effect='maintenance-associated-increase' if all(b['delta']>2 and b['relative_delta']>.05 for b in bb) else 'maintenance-associated-decrease' if all(b['delta']<-2 and b['relative_delta']<-.05 for b in bb) else 'effect-not-replicated';state='resident-supply-still-variable' if not stable['resident'] else 'maintenance-condition-associated-instability' if not stable['reinstall'] else 'both-conditions-stable-in-this-protocol'
  assert (stable,effect,state)==(c['within_process_stable'],c['maintenance_effect'],c['state'])
 result=dict(checked_windows=count,checked_sha=len(a['all_raw_sha256']),complete_raw_arithmetic_equal=True,summary_sha256=a['input_sha256'],primary=a['primary']['state'],reviewer='second arithmetic path by same root, not another reviewer');(e/'independent-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
