#!/usr/bin/env python3
"""Direct raw arithmetic/geometry/SHA, independent of the primary consumer."""
import argparse,gzip,hashlib,itertools,json,statistics as st
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('raw',type=Path);p.add_argument('--evidence',type=Path,default=Path(__file__).resolve().parent);q=p.parse_args();e=q.evidence;a=json.loads((e/'analysis.json').read_text());s=gzip.decompress((e/'summary.json.gz').read_bytes());run=json.loads(s);assert hashlib.sha256(s).hexdigest()==a['input_sha256'];assert {f.name for f in q.raw.iterdir()}==set(a['all_raw_sha256'])
 for name,digest in a['all_raw_sha256'].items():assert hashlib.sha256((q.raw/name).read_bytes()).hexdigest()==digest
 cells={};count=0
 for epoch in range(5):
  rr=[json.loads(l) for l in (q.raw/f'epoch-{epoch}.stdout.jsonl').read_text().splitlines()];g=rr[1];start=(g['pool_base']+(1<<30)-1)//(1<<30)*(1<<30);assert g['aligned_start']==start
  for f,(t,group) in zip(g['families'],itertools.product((7,100),range(3))):
   hi0=(start>>28)&255;want=[]
   for i in range(12):
    region=i%4 if group else 0;j=i//4 if group else i;vpn=(start>>12)+65536*region+4096*j;hi=(vpn>>16)&255;lo=t^hi^hi0 if group==2 else t;want.append((vpn+lo)<<12)
   assert f['pages']==want
  rows=[x for x in run['rows'] if x['epoch']==f'epoch-{epoch}'];cursor=2
  for row in rows:
   assert rr[cursor]['stage']=='before' and rr[cursor+1]['stage']=='after';cursor+=2;assert rr[cursor:cursor+144]==[dict(type='round',**{k:row[k] for k in ('cell','position','target','group','w','victim','history_direction','direction','passes')},**s) for s in row['samples']];cursor+=144;count+=144;cells[epoch,row['target'],row['group'],row['direction'],row['w']]=row
  assert cursor==len(rr)
 lookup=[];victim=[]
 for epoch,t,g,d,w in itertools.product(range(5),(7,100),range(3),(0,1),(8,9,12)):
  z=cells[epoch,t,g,d,w]['samples'];floor=cells[epoch,t,g,d,1]['samples'];okay=[]
  for pass_index in range(8):
   rr=[s for s in z if s['pass_index']==pass_index];zz=[s for s in floor if s['pass_index']==pass_index];delta=[sum(s['counts'][j] for s in rr)/16-sum(s['counts'][j] for s in zz)/16 for j in range(6)];gates=[dict(event=hex(ev),value=delta[j],lower=.75*(w-1),upper=1.25*(w-1),passed=.75*(w-1)<=delta[j]<=1.25*(w-1)) for j,ev in ((1,5),(3,47))];good=all(x['passed'] for x in gates);okay.append(good);lookup.append(dict(epoch=epoch,target=t,group=g,direction=d,w=w,pass_index=pass_index,count_mean_differences=delta,gates=gates,observable=good))
  rr=[s for s in z if s['role']=='victim'];zz=[s for s in floor if s['role']=='victim'];walk=[s['counts'][4] for s in rr];issues=[]
  if not all(okay):issues.append('lookup-not-observable')
  if any(s['counts'][4] for s in floor):issues.append('control-background')
  if any(x>1 for x in walk):issues.append('single-load-residual')
  rate=sum(x>0 for x in walk)/16;victim.append(dict(epoch=epoch,target=t,group=g,direction=d,w=w,walk=walk,counts=[r['counts'] for r in rr],control_counts=[r['counts'] for r in zz],response_rate=rate,issues=issues,status='INCOMPUTABLE' if issues else 'response' if rate>=.5 else 'no-response'))
 assert lookup==a['lookup_points'] and victim==a['victim_points'] and count==34560
 for d in a['decisions']:
  pp=[x for x in victim if x['target']==d['target'] and x['w']==12];by={g:[x for x in pp if x['group']==g] for g in range(3)};sig=[{x['status'] for x in by[g]} for g in (1,2)];status='INCOMPUTABLE' if any(x['issues'] for x in pp) or any(x['status']!='response' for x in by[0]) else 'low-only-candidate-favored' if sig==[{'response'},{'no-response'}] else 'high-fold-candidate-favored' if sig==[{'no-response'},{'response'}] else 'non-discriminating' if sig[0]==sig[1] and len(sig[0])==1 else 'heterogeneous';assert (status,pp)==(d['status'],d['points'])
 result=dict(checked_windows=count,checked_sha=len(a['all_raw_sha256']),lookup_points=len(lookup),victim_points=len(victim),complete_raw_arithmetic_equal=True,summary_sha256=a['input_sha256'],verdict=a['verdict'],reviewer='second arithmetic path by same root, not another reviewer');(e/'independent-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
