"""Direct JSONL arithmetic independent of the resource criterion implementation."""
import collections,hashlib,json,statistics as st,sys
from pathlib import Path
raw,summary_file,analysis_file,output=map(Path,sys.argv[1:]);s=json.loads(summary_file.read_text());m=json.loads(analysis_file.read_text());manifest=json.loads((raw/'manifest.json').read_text())
counts={};cells={};rounds=[];retired=[]
for entry in manifest['results']:
 rr=[json.loads(l) for l in (raw/(entry['name']+'.stdout.jsonl')).read_text().splitlines()];cfg=rr[0];e=int(entry['name'][1]);key=cfg['class'],cfg['anchor'],cfg['n'],e
 assert len(rr)==5 and key not in cells
 rows=rr[2:];assert [r['round'] for r in rows]==[0,1,2]
 cycles=[r['metrics']['0x11']/cfg['iterations'] for r in rows];cells[key]=cycles
 expected=cfg['iterations']*cfg['loop_instructions']+cfg['loop_offset']//4+1
 retired.extend(abs(r['metrics']['0x8']-expected)/expected for r in rows);rounds.extend(rows)
 measured=next(r for r in m['rows'] if r['condition']==entry['name']);assert measured['cycles']==cycles
 for ev in cfg['events']:assert measured['counts'][hex(ev)]==[r['metrics'][hex(ev)]/cfg['iterations'] for r in rows]
for cls in m['classes']:
 c=cls['class_name'];stable=True;lo=[];hi=[]
 for p in cls['points']:
  n=p['n'];ed=[]
  for row in p['epochs']:
   e=row['epoch'];a=cells[c,'fsqrt',n,e];none=cells[c,'none',n,e];baseline=st.median(cells[c,'fsqrt',0,e]);median=st.median(a);spread=(max(a)-min(a))/median
   assert row==dict(epoch=e,anchor_cycles=a,none_cycles=none,anchor_median=median,none_median=st.median(none),baseline=baseline,difference=median-baseline,range_fraction=spread,supply_reference=max(baseline,st.median(none)),supply_residual=median-max(baseline,st.median(none)))
   stable=stable and spread<=.10;ed.append(median-baseline)
  lo.append(all(abs(x)<=1 for x in ed));hi.append(all(x>1 for x in ed))
 status='ambiguous';interval=None
 if stable:
  if all(lo):status='no-onset-through768'
  else:
   for i in range(1,7):
    if all(lo[:i]) and all(hi[i:]):
     if i==6:status='right-censored'
     elif i==1:status='left-censored'
     else:status='interval';interval=[cls['points'][i-1]['n'],cls['points'][i]['n']]
     break
 assert cls['anchor_stable']==stable and cls['status']==status and cls['interval']==interval
assert len(cells)==140 and len(rounds)==420
assert m['input_sha256']==hashlib.sha256(summary_file.read_bytes()).hexdigest()
assert m['all_raw_sha256']=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(raw.iterdir())}
env=[]
for p in sorted(raw.glob('*-environment.json')):
 x=json.loads(p.read_text());assert not x['violations'] and not x['warnings'];t=x['snapshot'];env.append(dict(endpoint=p.name,max_cpu_c=t['thermal']['max_cpu_c'],policy7=t['cpufreq']['policy7']))
assert len(env)==282
receipt=dict(direct_raw_arithmetic_passed=True,reviewer='root second arithmetic path; no independent reviewer claim',processes=140,windows=420,raw_files=705,environment_endpoints=282,temperature_range=[min(x['max_cpu_c'] for x in env),max(x['max_cpu_c'] for x in env)],retired_relative_error_range=[min(retired),max(retired)],event_statistics=[dict(event=k,minimum=min(r['metrics'][k] for r in rounds),maximum=max(r['metrics'][k] for r in rounds),sum=sum(r['metrics'][k] for r in rounds),nonzero=sum(r['metrics'][k]>0 for r in rounds)) for k in ('0x11','0x8','0x3','0x17','0x34','0x2')],environment=env,source_branch=manifest['source_branch'],source_head=manifest['source_head'],binary_source_head=manifest['binary_source_head'],binary_sha256=manifest['binary_sha256'],wall_seconds=sum(r['wall_seconds'] for r in manifest['results']),class_status={c['class_name']:c['status'] for c in m['classes']})
output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ('environment',)}))
