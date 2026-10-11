#!/usr/bin/env python3
"""Second direct raw arithmetic and all file SHA; no main consumer import.

Same author as primary implementation, not an independent reviewer or new samples.
"""
import argparse,gzip,hashlib,json,statistics as st
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('raw',type=Path);p.add_argument('--evidence',type=Path);args=p.parse_args();phase=json.loads((args.raw/'manifest.json').read_text())['phase'];e=args.evidence or Path(__file__).resolve().parent/phase;a=json.loads((e/'analysis.json').read_text());payload=gzip.decompress((e/'summary.json.gz').read_bytes());s=json.loads(payload)
 assert hashlib.sha256(payload).hexdigest()==a['input_sha256'] and s['phase']==phase
 assert {x.name for x in args.raw.iterdir()}==set(a['all_raw_sha256'])
 for name,digest in a['all_raw_sha256'].items():assert hashlib.sha256((args.raw/name).read_bytes()).hexdigest()==digest
 points=[];ratios=[];values={};stable={};windows=0
 for row in s['rows']:
  rr=[json.loads(l) for l in (args.raw/(row['condition']+'.stdout.jsonl')).read_text().splitlines()];assert rr==[row['config'],row['program'],row['runtime'],*row['samples']];cfg=rr[0];anchor=cfg['anchor'];n=cfg['n'];v=[]
  for pos,z in enumerate(rr[3:]):
   assert z['position']==pos and z['round']==(7-pos if cfg['reverse'] else pos) and z['enabled']==z['running']>0
   assert z['result_bits']==(None if anchor=='none' else [0x3ff0000000000000]*2)
   assert all(type(x) is int and 0<=x<2**64 for x in z['counts']);counts=z['counts'];cycle=counts[0]/131072;v.append(cycle);windows+=1
   ratios.append(dict(condition=row['condition'],position=pos,round=z['round'],counts=counts,cycles_per_iter=cycle,ns=z['ns'],cycles_per_ns=counts[0]/z['ns'],**{hex(event):counts[j]/counts[0] for j,event in enumerate((17,8,58,59,33133,35)) if j>=2}))
  spread=(max(v)-min(v))/st.median(v);points.append(dict(epoch=int(row['condition'][1]),anchor=anchor,n=n,cycles=v,median=st.median(v),range_fraction=spread,stable=spread<=.10));values.setdefault((anchor,n),[]).extend(v);stable.setdefault((anchor,n),[]).append(spread<=.10)
 assert points==a['points'] and ratios==a['window_ratios'] and windows==a['windows']==(144 if phase=='qualification' else 720)
 i0=values['independent',0];s0=values['serial',0];gates=dict(anchors_stable=all(stable['independent',0]+stable['serial',0]),overlap_ratio=max(i0)/min(s0),none_stable=all(stable['none',0]+stable['none',128]),none_max_ratio=max(values['none',0]+values['none',128])/min(i0));qualified=gates['anchors_stable'] and gates['overlap_ratio']<=.70 and gates['none_stable'] and gates['none_max_ratio']<=.80
 assert gates==a['qualification'] and qualified==a['qualified'];status='dual-anchor-overlap-qualified' if qualified else 'not-qualified';interval=None
 if phase=='scan' and qualified:
  curve=[]
  for n in (0,128,256,384,512,640,672,704,768,896):
   ok=all(stable[anchor,n][epoch] for anchor in ('none','serial','independent') for epoch in range(3)) and max(values['none',n])<=.90*min(i0) and max(values['serial',n])<=1.10*min(s0)
   state='supply-or-control-unqualified' if not ok else 'overlap-loss-response' if min(values['independent',n])>=1.25*max(i0) else 'no-overlap-loss' if max(values['independent',n])<=1.10*min(i0) else 'ambiguous'
   curve.append(dict(n=n,state=state,none_max_ratio=max(values['none',n])/min(i0),serial_max_ratio=max(values['serial',n])/min(s0),independent_range=[min(values['independent',n]),max(values['independent',n])]))
  assert curve==a['curve'];states=[x['state'] for x in curve];high=[j for j,state in enumerate(states) if state=='overlap-loss-response'];status='inconclusive'
  if high:
   h=high[0];low=[j for j in range(h) if states[j]=='no-overlap-loss']
   if any(state=='no-overlap-loss' for state in states[h+1:]):status='nonmonotonic'
   elif not low:status='left-censored'
   elif h==len(curve)-1 or states[h+1]!='overlap-loss-response':status='right-censored' if h==len(curve)-1 else 'inconclusive'
   elif all(states[j]=='no-overlap-loss' for j in range(max(low)+1,h)):status='effective-overlap-loss-interval';interval=[curve[max(low)]['n'],curve[h]['n']]
  assert interval==a['interval']
 assert status==a['status']
 if phase=='scan':
  m=json.loads((args.raw/'manifest.json').read_text());qi=m['qualification_input'];qraw=args.raw.parent/qi['raw_directory'];qm=(qraw/'manifest.json').read_bytes();assert hashlib.sha256(qm).hexdigest()==qi['manifest_sha256'] and json.loads(qm)['phase']=='qualification' and qi['qualified'] is True
 result=dict(checked_windows=windows,checked_sha=len(a['all_raw_sha256']),complete_raw_arithmetic_equal=True,summary_sha256=a['input_sha256'],status=status,interval=interval,reviewer='second arithmetic path by same root, not another reviewer');(e/'independent-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
