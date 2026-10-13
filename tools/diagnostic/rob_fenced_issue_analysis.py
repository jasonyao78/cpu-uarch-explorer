"""Own near/far issue qualification; event semantics and architecture stay separate.

Contract docs/design/2026-10-13-rob-fenced-issue-marker.md. N0 cannot identify ROB allocation.
"""
import json,hashlib,statistics as st,subprocess,tempfile
from pathlib import Path
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
ROOT=Path(__file__).resolve().parents[2];MODE='rob-fenced-issue-marker'
PROTOCOL='docs/design/2026-10-13-rob-fenced-issue-marker.md';BUILD='docs/reviews/evidence/2026-10-13-rob-fenced-issue-marker/build.json';PLAN='docs/reviews/evidence/2026-10-13-rob-fenced-issue-marker/plan.json';DRIVER='tools/diagnostic/run_sm8650_rob_fenced_issue.py';CONSUMER='tools/diagnostic/rob_fenced_issue_analysis.py'
EVENTS=(17,8,112,113,34,1);BITS=0x3ff0000000000000;PFN_MASK=(1<<55)-1;MARKER=0x12345678
def conditions(phase):
 _require(phase=='qualification','issue marker N0 only; capacity scan forbidden');return [dict(name=f'e{e}-k{k}',args=['--run','--chain',str(k)]) for e in range(3) for k in ((16,32) if e%2==0 else (32,16))]
def expected(k):
 cfg=dict(type='config',version=1,probe=MODE,chain=k,groups=0,trials=32,windows=256,training_calls=64,full_window_warmup_calls=4,events=list(EVENTS),pmu_type=8,schedule_reverse_block_trials=8);pp=[]
 for fence in ('pre','post'):
  for marker in ('nop','taps'):
   w=[0xaa1f03e9,0x9e670000,0xaa0403e6]+[0x1e61c000]*k+[0x9e66000c,0xb500026c,0xd50330ff if fence=='pre' else 0xd503201f]+[0xf9400029+(j*8<<10) if marker=='taps' else 0xd503201f for j in range(8)]+[0xf9000046+(j*8<<10) if marker=='taps' else 0xd503201f for j in range(8)]+[0xd503201f if fence=='pre' else 0xd50330ff,0xd50330ff,0x9e660000,0xd53b442c,0xf900006c,0xf9000469,0xd65f03c0];pp.append(dict(type='program',marker=marker,fence=fence,code_bytes=len(w)*4,words=w))
 schedule=[]
 for t in range(32):
  for pos in range(8):
   i=(t+pos)%8;i=7-i if (t//8)%2 else i;ctl=('architect','speculate')[i//4];fence=('pre','post')[(i%4)//2];schedule.append(dict(type='schedule',trial=t,position=pos,control=ctl,marker='taps' if i%2 else 'nop',fence=fence,train_bits=0,test_bits=0 if ctl=='architect' else BITS))
 return [cfg,*pp,*schedule]
def plans():return {str(k):expected(k) for k in (16,32)}
def validate_plan(p):_require(_same(p,plans()),'fenced actual registered plan mismatch')
def audit_process(rr,c,registered):validate_plan(registered);return _audit_records(rr,c)
def _audit_records(rr,c):
 _require(type(rr)is list and rr and all(type(x)is dict for x in rr),'issue record objects');k=int(c['args'][2]);want=expected(k)
 if rr[-1].get('type')=='failure':
  _require(_same(rr[:5],want[:5]) and rr[-1].get('metrics')=={} and type(rr[-1].get('failure'))is dict and type(rr[-1]['failure'].get('reason'))is str,'issue failure shape');f=rr[-1]['failure'];_require(f['reason'] not in ('six-PMU-unavailable','SB-unavailable') or len(rr)==6,'issue capability precedes samples');return dict(condition=c['name'],args=c['args'],status='CAPABILITY_UNAVAILABLE' if f['reason'] in ('six-PMU-unavailable','SB-unavailable') else 'TECHNICAL_FAILURE',failure=f)
 _require(len(rr)==263 and _same(rr[:5],want[:5]),'issue program/window coverage');runtime=rr[5];_fields(runtime,dict(type='runtime',cpu=7,fpcr=0,hwcap_sb=True),'issue runtime');base=runtime.get('code_base');addrs=[runtime.get(n+'_base') for n in ('code','near','far','output')];_require(all(type(v)is int and v>0 and v%4096==0 for v in addrs) and len(set(addrs))==4,'issue addresses');ids=runtime.get('event_ids');_require(type(ids)is list and len(ids)==6 and all(type(v)is int and 0<v<1<<64 for v in ids) and len(set(ids))==6,'issue event IDs')
 def pfn(v):_require(type(v)is int and 0<=v<1<<64 and v>>63 and not(v&(1<<62)) and v&PFN_MASK,'issue visible PFN');return v&PFN_MASK
 final=rr[-1];_fields(final,dict(type='final',fds_closed=True),'issue final');a=runtime.get('pagemap_before');b=final.get('pagemap_after');_require(type(a)is list and type(b)is list and len(a)==len(b)==4,'issue pagemap shape');_require([pfn(v) for v in a]==[pfn(v) for v in b] and len({pfn(v) for v in a})==4,'issue PFN migration/alias')
 for z,s in zip(rr[6:-1],want[5:]):
  arch=MARKER if s['control']=='architect' and s['marker']=='taps' else 0;_fields(z,dict(s,type='round',result_bits=s['test_bits'],status_raw=0,near_architectural=arch,far_architectural_words=[arch]*8,code_base=base,code_matches_plan=True),'issue schedule/originals');_require(all(type(z.get(n))is int and 0<z[n]<1<<64 for n in ('enabled','running')) and z['enabled']==z['running'],'issue time/mux');counts=z.get('counts');_require(type(counts)is list and len(counts)==6 and all(type(x)is int and 0<=x<1<<64 for x in counts) and counts[0]>0 and k+9<=counts[1]<=k+1024,'issue counts/IR')
 return dict(condition=c['name'],args=c['args'],config=rr[0],programs=rr[1:5],runtime=runtime,samples=rr[6:-1],final=final,status='complete')
def quantile(v,q):
 v=sorted(v);x=q*(len(v)-1);i=int(x);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(x-i)
def analyze(run):
 _fields(run,dict(mode=MODE,phase='qualification',processes=6),'fenced matrix');rows=run.get('rows');_require(type(rows)is list and len(rows)==6,'fenced process coverage');out=[]
 for row,c in zip(rows,conditions('qualification')):
  _fields(row,dict(condition=c['name'],args=c['args'],status='complete'),'fenced identity');_audit_records([row['config'],*row['programs'],row['runtime'],*row['samples'],row['final']],c);cells={(z['trial'],z['control'],z['fence'],z['marker']):z for z in row['samples']};dd={}
  for ctl in ('architect','speculate'):
   for fence in ('pre','post'):dd[ctl+'-'+fence]={hex(event):[cells[t,ctl,fence,'taps']['counts'][ix]-cells[t,ctl,fence,'nop']['counts'][ix] for t in range(32)] for ix,event in enumerate(EVENTS)}
  gates={};thresholds={};cal={}
  for name,event in (('near','0x70'),('far','0x71')):
   aa=[dd['architect-'+f][event] for f in ('pre','post')];b=dd['speculate-pre'][event];lo=min(quantile(v,.1) for v in aa);hi=quantile(b,.9);gates[name+'_architect']=all(7<=st.mean(v)<=9 and quantile([abs(x-8) for x in v],.9)<=3 for v in aa);gates[name+'_structural_negative']=abs(st.mean(b))<=1 and quantile([abs(v) for v in b],.9)<=3;gates[name+'_separable']=lo-hi>=4;thresholds[name]=(lo+hi)/2 if gates[name+'_separable'] else None;cal[name]=dict(architect_q10_min=lo,structural_negative_q90=hi,architect_pre_mean=st.mean(aa[0]),architect_post_mean=st.mean(aa[1]),structural_negative_mean=st.mean(b))
  gates['ir_matched']=all(abs(st.mean(dd[key]['0x8']))<=2 for key in dd);gates['ir_fence_matched']=all(abs(st.mean(cells[t,'speculate','post',marker]['counts'][1]-cells[t,'speculate','pre',marker]['counts'][1] for t in range(32)))<=2 for marker in ('nop','taps'))
  eligible=[t for t in range(32) if thresholds['near']is not None and dd['speculate-post']['0x70'][t]>=thresholds['near']];responding=[t for t in eligible if thresholds['far']is not None and dd['speculate-post']['0x71'][t]>=thresholds['far']];rate=len(responding)/len(eligible) if eligible else None;gates['eligible_count']=len(eligible)>=8;gates['far_given_near']=rate is not None and rate>=.9
  branch={f+'-'+m:{ctl:st.median(cells[t,ctl,f,m]['counts'][4] for t in range(32)) for ctl in ('architect','speculate')} for f in ('pre','post') for m in ('nop','taps')}
  out.append(dict(process=c['name'],chain=row['config']['chain'],calibration=cal,thresholds=thresholds,deltas=dd,branch_medians=branch,eligible_trials=eligible,responding_trials=responding,eligible_rate=len(eligible)/32,far_given_near_rate=rate,absolute_icache_range=[min(z['counts'][5] for z in row['samples']),max(z['counts'][5] for z in row['samples'])],gates=gates,qualified=all(gates.values())))
 return dict(mode=MODE,windows=1536,status='FENCED_ISSUE_MARKER_QUALIFIED' if all(x['qualified'] for x in out) else 'FENCED_ISSUE_MARKER_NOT_QUALIFIED',processes=out,physical_capacity_certified=False,allocation_units_certified=False,instruction_supply_certified=False,naming_limit='N0 own speculative operations separated from pre-tap SB negative; not frontend capacity, ROB allocation units or size')
def audit_raw(path):
 """Launch/source/build/environment and complete raw inventory, never patched input."""
 m=json.loads((path/'manifest.json').read_text());phase=m.get('phase');planned=conditions(phase);cap=m.get('status')=='capability-unavailable';cc=planned[:1] if cap else planned
 inventory={'manifest.json','driver.py','consumer.py','environment-policy.json','initial-environment.json','final-environment.json'}|{c['name']+suffix for c in cc for suffix in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')}
 _require({p.name for p in path.iterdir()}==inventory and all(p.is_file() for p in path.iterdir()),'issue raw inventory')
 _fields(m,dict(mode=MODE,status='capability-unavailable' if cap else 'complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,protocol_path=PROTOCOL,plan_path=PLAN,consumer_path=CONSUMER),'issue manifest identity')
 _require(_same(m.get('conditions'),planned) and type(m.get('results')) is list and len(m['results'])==len(cc),'issue requested/result coverage')
 blob=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for file,key in ((DRIVER,'driver_sha256'),(CONSUMER,'consumer_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,file))==m[key],'issue launch SHA '+file)
 for saved,key in (('driver.py','driver_sha256'),('consumer.py','consumer_sha256')):_require(sha((path/saved).read_bytes())==m[key],'issue saved '+saved)
 build=json.loads(blob(head,BUILD));registered=json.loads(blob(head,PLAN));validate_plan(registered)
 _require(build['binaries']['rob_fenced_issue_marker']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'issue binary/source/plan binding')
 for file,digest in build['source_sha256'].items():_require(sha(blob(head,file))==digest and sha(blob(m['binary_source_head'],file))==digest,'issue source dependency '+file)
 _require(m.get('qualification_input') is None,'issue cannot borrow earlier qualification')
 with tempfile.TemporaryDirectory() as td0:
  td=Path(td0)
  for file in ('probes/diagnostic/rob_fenced_issue_marker.c','probes/common/perf_group_read.h'):
   target=td/file;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob(m['binary_source_head'],file))
  host=td/'producer';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(td/'probes/common'),str(td/'probes/diagnostic/rob_fenced_issue_marker.c'),'-o',str(host)],check=True,capture_output=True)
  for k in (16,32):
   args=['--plan','--chain',str(k)];actual=[json.loads(l) for l in subprocess.check_output([str(host),*args],text=True).splitlines()];_require(_same(actual,registered[str(k)]),'issue immutable producer plan mismatch')
 from tools.diagnostic.analyze_long_load import audit_environment
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt'
 env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy)
 rows=[]
 for r,c in zip(m['results'],cc):
  _fields(r,dict(name=c['name'],timed_out=False),'issue result identity');f=path/(c['name']+'.stdout.jsonl');_require(sha(f.read_bytes())==r['stdout_sha256'],'issue stdout SHA');row=_audit_records([json.loads(l) for l in f.read_text().splitlines()],c)
  if cap:_require(type(r.get('exit_code'))is int and r['exit_code']!=0 and row['status']=='CAPABILITY_UNAVAILABLE','issue capability first-stop')
  else:_require(type(r.get('exit_code'))is int and r['exit_code']==0 and (path/(c['name']+'.stderr.log')).read_bytes()==b'' and row['status']=='complete','issue success status/stderr')
  rows.append(row)
 return dict(mode=MODE,phase=phase,status=m['status'],processes=len(cc),source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],raw_directory=path.name,manifest_sha256=sha((path/'manifest.json').read_bytes()),max_cpu_c_range=[min(v['snapshot']['thermal']['max_cpu_c'] for v in env.values()),max(v['snapshot']['thermal']['max_cpu_c'] for v in env.values())],rows=rows),{p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())}
