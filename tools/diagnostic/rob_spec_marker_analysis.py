"""One-shot wrong-path own marker; N0 observed execution/retirement qualification only.

Contract docs/design/2026-10-13-rob-speculative-marker.md; neither speculative
operation count nor this reference is a physical allocation-unit certificate.
"""
import json,hashlib,statistics as st,subprocess,tempfile
from pathlib import Path
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
ROOT=Path(__file__).resolve().parents[2];MODE='rob-speculative-marker'
PROTOCOL='docs/design/2026-10-13-rob-speculative-marker.md';BUILD='docs/reviews/evidence/2026-10-13-rob-speculative-marker/build.json';PLAN='docs/reviews/evidence/2026-10-13-rob-speculative-marker/plan.json';DRIVER='tools/diagnostic/run_sm8650_rob_spec_marker.py';CONSUMER='tools/diagnostic/rob_spec_marker_analysis.py'
EVENTS=(17,8,112,6,34,59,1);BITS=0x3ff0000000000000;PFN_MASK=(1<<55)-1

def conditions(phase):
 _require(phase=='qualification','marker N0 only; capacity scan forbidden');return [dict(name=f'e{e}-k{k}',args=['--run','--chain',str(k)]) for e in range(3) for k in ((16,32) if e%2==0 else (32,16))]
def expected(k):
 cfg=dict(type='config',version=1,probe=MODE,chain=k,groups=0,trials=18,windows=108,training_calls=64,full_window_warmup_calls=4,events=list(EVENTS),pmu_type=8,schedule_reverse_block_trials=6);pp=[]
 for marker in ('nop','load'):
  w=[0x9e670000]+[0x1e61c000]*k+[0x9e66000c,0xb400004c,0x14000002,0xf9400029 if marker=='load' else 0xd503201f,0xd50330ff,0x9e660000,0xd53b442c,0xf900004c,0xd65f03c0];pp.append(dict(type='program',marker=marker,code_bytes=len(w)*4,words=w))
 schedule=[]
 for t in range(18):
  for pos in range(6):
   i=(t+pos)%6;i=5-i if (t//6)%2 else i;control=('architect','bypass','speculate')[i//2];schedule.append(dict(type='schedule',trial=t,position=pos,control=control,marker='load' if i%2 else 'nop',train_bits=BITS if control=='bypass' else 0,test_bits=0 if control=='architect' else BITS))
 return [cfg,*pp,*schedule]
def plans():return {str(k):expected(k) for k in (16,32)}
def validate_plan(p):_require(_same(p,plans()),'marker actual registered plan mismatch')
def audit_process(rr,c,registered):validate_plan(registered);return _audit_records(rr,c)
def _audit_records(rr,c):
 _require(type(rr)is list and rr and all(type(x)is dict for x in rr),'marker record objects');k=int(c['args'][2]);want=expected(k)
 if rr[-1].get('type')=='failure':
  _require(_same(rr[:3],want[:3]) and rr[-1].get('metrics')=={} and type(rr[-1].get('failure'))is dict and type(rr[-1]['failure'].get('reason'))is str,'marker failure shape');f=rr[-1]['failure'];_require(f['reason'] not in ('seven-PMU-unavailable','SB-unavailable') or len(rr)==4,'marker capability must precede samples');return dict(condition=c['name'],args=c['args'],status='CAPABILITY_UNAVAILABLE' if f['reason'] in ('seven-PMU-unavailable','SB-unavailable') else 'TECHNICAL_FAILURE',failure=f)
 _require(len(rr)==113 and _same(rr[:3],want[:3]),'marker program/window coverage');runtime=rr[3];_fields(runtime,dict(type='runtime',cpu=7,fpcr=0,hwcap_sb=True),'marker runtime');base=runtime.get('code_base');data=runtime.get('marker_base');_require(type(base)is int and base>0 and base%4096==0 and type(data)is int and data>0 and data%4096==0 and data!=base,'marker addresses');ids=runtime.get('event_ids');_require(type(ids)is list and len(ids)==7 and all(type(v)is int and 0<v<1<<64 for v in ids) and len(set(ids))==7,'marker seven IDs')
 def pfn(v):_require(type(v)is int and 0<=v<1<<64 and v>>63 and not(v&(1<<62)) and v&PFN_MASK,'marker visible PFN');return v&PFN_MASK
 final=rr[-1];_fields(final,dict(type='final',fds_closed=True),'marker final');_require(pfn(runtime.get('code_pagemap_before'))==pfn(final.get('code_pagemap_after')) and pfn(runtime.get('marker_pagemap_before'))==pfn(final.get('marker_pagemap_after')),'marker PFN migration')
 for z,s in zip(rr[4:-1],want[3:]):
  _fields(z,dict(s,type='round',result_bits=s['test_bits'],status_raw=0,code_base=base,code_matches_plan=True),'marker schedule/original result');_require(all(type(z.get(n))is int and 0<z[n]<1<<64 for n in ('enabled','running')) and z['enabled']==z['running'],'marker time/mux');counts=z.get('counts');_require(type(counts)is list and len(counts)==7 and all(type(x)is int and 0<=x<1<<64 for x in counts) and counts[0]>0 and k+9<=counts[1]<=k+1024,'marker counts/IR')
 return dict(condition=c['name'],args=c['args'],config=rr[0],programs=rr[1:3],runtime=runtime,samples=rr[4:-1],final=final,status='complete')
def q90(values):
 v=sorted(values);x=.9*(len(v)-1);i=int(x);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(x-i)
def analyze(run):
 _fields(run,dict(mode=MODE,phase='qualification',processes=6),'marker matrix');cc=conditions('qualification');rows=run.get('rows');_require(type(rows)is list and len(rows)==6,'marker process coverage');out=[]
 for row,c in zip(rows,cc):
  _fields(row,dict(condition=c['name'],args=c['args'],status='complete'),'marker identity');_audit_records([row['config'],*row['programs'],row['runtime'],*row['samples'],row['final']],c);cells={(z['trial'],z['control'],z['marker']):z for z in row['samples']};controls={}
  for ctl in ('architect','bypass','speculate'):
   deltas={hex(event):[cells[t,ctl,'load']['counts'][index]-cells[t,ctl,'nop']['counts'][index] for t in range(18)] for index,event in enumerate(EVENTS)};spec=1 if ctl!='bypass' else 0;ret=1 if ctl=='architect' else 0;g=dict(ld_spec_mean=.9<=st.mean(deltas['0x70'])<=1.1 if spec else abs(st.mean(deltas['0x70']))<=.1,ld_retired_mean=.9<=st.mean(deltas['0x6'])<=1.1 if ret else abs(st.mean(deltas['0x6']))<=.1,ld_spec_q90=q90([abs(x-spec) for x in deltas['0x70']])<=1,ld_retired_q90=q90([abs(x-ret) for x in deltas['0x6']])<=1,retired_ir_delta=abs(st.mean(deltas['0x8']))<=1);controls[ctl]=dict(deltas=deltas,means={k:st.mean(v) for k,v in deltas.items()},gates=g,qualified=all(g.values()))
  branch={m:{ctl:st.median(cells[t,ctl,m]['counts'][4] for t in range(18)) for ctl in ('architect','bypass','speculate')} for m in ('nop','load')};g=dict(control_signals=all(v['qualified'] for v in controls.values()),trained_direction=all(v['speculate']-v['bypass']>=.75 and v['architect']<=.25 and v['bypass']<=.25 for v in branch.values()),icache_background=all(z['counts'][6]<=1 for z in row['samples']));out.append(dict(process=c['name'],chain=row['config']['chain'],controls=controls,branch_medians=branch,gates=g,qualified=all(g.values())))
 good=all(x['qualified'] for x in out);return dict(mode=MODE,windows=648,status='SPECULATIVE_MARKER_QUALIFIED' if good else 'MARKER_NOT_QUALIFIED',processes=out,physical_capacity_certified=False,allocation_units_certified=False,naming_limit='N0 own wrong-path execution without retirement, not physical ROB size or unit')

def audit_raw(path):
 """Launch/source/build/environment and complete raw inventory, never patched input."""
 m=json.loads((path/'manifest.json').read_text());phase=m.get('phase');planned=conditions(phase);cap=m.get('status')=='capability-unavailable';cc=planned[:1] if cap else planned
 inventory={'manifest.json','driver.py','consumer.py','environment-policy.json','initial-environment.json','final-environment.json'}|{c['name']+suffix for c in cc for suffix in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')}
 _require({p.name for p in path.iterdir()}==inventory and all(p.is_file() for p in path.iterdir()),'marker raw inventory')
 _fields(m,dict(mode=MODE,status='capability-unavailable' if cap else 'complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,protocol_path=PROTOCOL,plan_path=PLAN,consumer_path=CONSUMER),'marker manifest identity')
 _require(_same(m.get('conditions'),planned) and type(m.get('results')) is list and len(m['results'])==len(cc),'marker requested/result coverage')
 blob=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for file,key in ((DRIVER,'driver_sha256'),(CONSUMER,'consumer_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,file))==m[key],'marker launch SHA '+file)
 for saved,key in (('driver.py','driver_sha256'),('consumer.py','consumer_sha256')):_require(sha((path/saved).read_bytes())==m[key],'marker saved '+saved)
 build=json.loads(blob(head,BUILD));registered=json.loads(blob(head,PLAN));validate_plan(registered)
 _require(build['binaries']['rob_speculative_marker']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'marker binary/source/plan binding')
 for file,digest in build['source_sha256'].items():_require(sha(blob(head,file))==digest and sha(blob(m['binary_source_head'],file))==digest,'marker source dependency '+file)
 _require(m.get('qualification_input') is None,'marker cannot borrow earlier qualification')
 with tempfile.TemporaryDirectory() as td0:
  td=Path(td0)
  for file in ('probes/diagnostic/rob_speculative_marker.c','probes/common/rob_codegen.h','probes/common/perf_group_read.h'):
   target=td/file;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob(m['binary_source_head'],file))
  host=td/'producer';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(td/'probes/common'),str(td/'probes/diagnostic/rob_speculative_marker.c'),'-o',str(host)],check=True,capture_output=True)
  for k in (16,32):
   args=['--plan','--chain',str(k)];actual=[json.loads(l) for l in subprocess.check_output([str(host),*args],text=True).splitlines()];_require(_same(actual,registered[str(k)]),'marker immutable producer plan mismatch')
 from tools.diagnostic.analyze_long_load import audit_environment
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt'
 env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy)
 rows=[]
 for r,c in zip(m['results'],cc):
  _fields(r,dict(name=c['name'],timed_out=False),'marker result identity');f=path/(c['name']+'.stdout.jsonl');_require(sha(f.read_bytes())==r['stdout_sha256'],'marker stdout SHA');row=_audit_records([json.loads(l) for l in f.read_text().splitlines()],c)
  if cap:_require(type(r.get('exit_code'))is int and r['exit_code']!=0 and row['status']=='CAPABILITY_UNAVAILABLE','marker capability first-stop')
  else:_require(type(r.get('exit_code'))is int and r['exit_code']==0 and (path/(c['name']+'.stderr.log')).read_bytes()==b'' and row['status']=='complete','marker success status/stderr')
  rows.append(row)
 return dict(mode=MODE,phase=phase,status=m['status'],processes=len(cc),source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],raw_directory=path.name,manifest_sha256=sha((path/'manifest.json').read_bytes()),max_cpu_c_range=[min(v['snapshot']['thermal']['max_cpu_c'] for v in env.values()),max(v['snapshot']['thermal']['max_cpu_c'] for v in env.values())],rows=rows),{p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())}
