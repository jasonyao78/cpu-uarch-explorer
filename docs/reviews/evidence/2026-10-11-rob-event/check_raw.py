"""Independent direct raw arithmetic; root second path, not another reviewer."""
import hashlib,json,statistics as st,sys
from pathlib import Path
raw,summary,analysis,output=map(Path,sys.argv[1:]);m=json.loads((raw/'manifest.json').read_text());a=json.loads(analysis.read_text());s=json.loads(summary.read_text());assert m['status']=='complete'
cells={};rrall=[];retired=[]
for entry in m['results']:
 rr=[json.loads(x) for x in (raw/(entry['name']+'.stdout.jsonl')).read_text().splitlines()];cfg=rr[0];rounds=rr[2:];assert len(rr)==5 and [r['round'] for r in rounds]==[0,1,2]
 key=(cfg['class'],cfg['anchor'],cfg['n'],int(entry['name'][1]));assert key not in cells
 counts={k:[r['metrics'][k]/cfg['iterations'] for r in rounds] for k in rounds[0]['metrics']};cells[key]=counts;rrall.extend(rounds)
 expected=cfg['iterations']*cfg['loop_instructions']+17;retired.extend(abs(r['metrics']['0x8']-expected)/expected for r in rounds)
 row=next(r for r in a['rows'] if r['condition']==entry['name']);assert row['counts']==counts and row['cycles']==counts['0x11']
for p in a['points']:
 key=tuple(p[k] for k in ('class_name','anchor','n','epoch'));counts=cells[key];base=cells[key[0],key[1],0,key[3]]
 for event,v in counts.items():
  mid=st.median(v);delta=mid-st.median(base[event]);expected=dict(raw=v,median=mid,range_fraction=(max(v)-min(v))/mid if mid else (None if max(v)>0 else 0),delta_from_n0=delta,per_filler_delta=delta/(2*key[2]) if key[2] else None)
  if event in ('0x816d','0x23'):expected['cycle_fraction']=[x/y for x,y in zip(v,counts['0x11'])]
  assert expected==p['events'][event]
gates=[]
for c in ('add','movi'):
 for event in ('0x3a','0x3b'):
  ds=[]
  for e in (0,1):
   v=cells[c,'none',128,e][event];base=cells[c,'none',0,e][event];mid=st.median(v);d=mid-st.median(base);ds.append(d);spread=(max(v)-min(v))/mid if mid else float('inf')
   gates.extend((d>128,spread<=.1))
  mean=st.mean(ds);gates.append(mean>0 and abs(ds[0]-ds[1])/mean<=.1)
assert gates==[g['passed'] for g in a['operation_control_gates']]
assert a['operation_control_status']==('qualified-for-controls' if all(gates) else 'not-qualified')
for event,field in [('0x816d','rename_status'),('0x23','frontend_status')]:
 ratios=[x/y for v in cells.values() for x,y in zip(v[event],v['0x11'])]
 status='cycle-semantics-incompatible' if max(ratios)>1 else 'positive-response-observed-semantics-not-certified' if max(ratios)>0 else 'positive-response-not-observed';assert a[field]==status
assert len(cells)==64 and len(rrall)==192 and len(list(raw.iterdir()))==325
assert a['input_sha256']==hashlib.sha256(summary.read_bytes()).hexdigest()
assert a['all_raw_sha256']=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(raw.iterdir())}
env=[]
for p in sorted(raw.glob('*-environment.json')):
 v=json.loads(p.read_text());assert not v['warnings'] and not v['violations'];env.append(dict(endpoint=p.name,max_cpu_c=v['snapshot']['thermal']['max_cpu_c'],policy7=v['snapshot']['cpufreq']['policy7']))
assert len(env)==130
receipt=dict(direct_raw_arithmetic_passed=True,reviewer='root second arithmetic path; no independent reviewer claim',processes=64,windows=192,raw_files=325,environment_endpoints=130,temperature_range=[min(x['max_cpu_c'] for x in env),max(x['max_cpu_c'] for x in env)],retired_relative_error_range=[min(retired),max(retired)],event_statistics=[dict(event=k,minimum=min(r['metrics'][k] for r in rrall),maximum=max(r['metrics'][k] for r in rrall),nonzero=sum(r['metrics'][k]>0 for r in rrall)) for k in ('0x11','0x8','0x3a','0x3b','0x816d','0x23')],gates_passed=sum(gates),gates_total=len(gates),maximum_cycle_fractions={k:max(r['metrics'][k]/r['metrics']['0x11'] for r in rrall) for k in ('0x816d','0x23')},environment=env,source_branch=m['source_branch'],source_head=m['source_head'],binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],wall_seconds=sum(r['wall_seconds'] for r in m['results']))
output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='environment'}))
