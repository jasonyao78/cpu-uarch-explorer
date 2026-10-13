"""Own-line cache calibration and original architectural marker qualification, N0 only.

Contract docs/design/2026-10-13-rob-cache-marker.md. Independent calibration cells
alone fix each timer threshold; measured wrong-path labels cannot tune it.
"""
import json,hashlib,statistics as st,subprocess,tempfile
from pathlib import Path
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
ROOT=Path(__file__).resolve().parents[2];MODE='rob-cache-marker';BITS=0x3ff0000000000000;MARKER=0x12345678;PFN_MASK=(1<<55)-1
PROTOCOL='docs/design/2026-10-13-rob-cache-marker.md';BUILD='docs/reviews/evidence/2026-10-13-rob-cache-marker/build.json';PLAN='docs/reviews/evidence/2026-10-13-rob-cache-marker/plan.json';DRIVER='tools/diagnostic/run_sm8650_rob_cache_marker.py';CONSUMER='tools/diagnostic/rob_cache_marker_analysis.py'
def conditions(phase):
 _require(phase=='qualification','cache marker N0 only; capacity scan forbidden');return [dict(name=f'e{e}-k{k}',args=['--run','--chain',str(k)]) for e in range(3) for k in ((16,32) if e%2==0 else (32,16))]
def expected(k):
 cfg=dict(type='config',version=1,probe=MODE,chain=k,groups=0,trials=32,windows=256,training_calls=64,clock='cntvct_el0',marker_word=MARKER,schedule_reverse_block_trials=8);programs=[]
 for marker in ('nop','load'):
  w=[0xaa1f03e9,0x9e670000]+[0x1e61c000]*k+[0x9e66000c,0xb400004c,0x14000002,0xf9400029 if marker=='load' else 0xd503201f,0xd50330ff,0x9e660000,0xd53b442c,0xf900004c,0xf9000449,0xd65f03c0];programs.append(dict(type='program',marker=marker,code_bytes=len(w)*4,words=w))
 cells=[('cal-hot','none'),('cal-cold','none'),('architect','nop'),('architect','load'),('bypass','nop'),('bypass','load'),('speculate','nop'),('speculate','load')];schedule=[]
 for t in range(32):
  for p in range(8):
   i=(t+p)%8;i=7-i if t//8%2 else i;c,m=cells[i];schedule.append(dict(type='schedule',trial=t,position=p,control=c,marker=m,train_bits=BITS if i in (4,5) else 0,test_bits=BITS if i>=4 else 0))
 return [cfg,*programs,*schedule]
def plans():return {str(k):expected(k) for k in (16,32)}
def validate_plan(p):_require(_same(p,plans()),'cache marker actual registered plan mismatch')
def audit_process(rr,c,registered):validate_plan(registered);return _audit_records(rr,c)
def _audit_records(rr,c):
 _require(type(rr)is list and rr and all(type(x)is dict for x in rr),'cache marker record objects');k=int(c['args'][2]);want=expected(k)
 if rr[-1].get('type')=='failure':
  _require(_same(rr[:3],want[:3]) and rr[-1].get('metrics')=={} and type(rr[-1].get('failure'))is dict and type(rr[-1]['failure'].get('reason'))is str,'cache marker failure shape');f=rr[-1]['failure'];cap=f['reason'] in ('DC-timer-unavailable','SB-unavailable');_require(not cap or len(rr)==4,'cache marker capability must precede samples');return dict(condition=c['name'],args=c['args'],status='CAPABILITY_UNAVAILABLE' if cap else 'TECHNICAL_FAILURE',failure=f)
 _require(len(rr)==261 and _same(rr[:3],want[:3]),'cache marker program/window coverage');runtime=rr[3];_fields(runtime,dict(type='runtime',cpu=7,fpcr=0,hwcap_sb=True,dc_timer_available=True),'cache marker runtime');addresses=runtime.get('addresses');_require(type(addresses)is list and len(addresses)==3 and len(set(addresses))==3 and all(type(v)is int and 0<v<1<<39 and v%4096==0 for v in addresses),'cache marker three addresses');_require(type(runtime.get('cntfrq'))is int and 0<runtime['cntfrq']<1<<64 and type(runtime.get('ctr_el0'))is int and 0<runtime['ctr_el0']<1<<64,'cache marker timer')
 def pfns(v):
  _require(type(v)is list and len(v)==3 and all(type(x)is int and 0<=x<1<<64 and x>>63 and not(x&(1<<62)) and x&PFN_MASK for x in v),'cache marker visible PFNs');z=[x&PFN_MASK for x in v];_require(len(set(z))==3,'cache marker independent pages');return z
 final=rr[-1];_fields(final,dict(type='final',fds_closed=True),'cache marker final');_require(pfns(runtime.get('pagemap_before'))==pfns(final.get('pagemap_after')),'cache marker PFN migration')
 for z,s in zip(rr[4:-1],want[3:]):
  a=MARKER if s['control']=='architect' and s['marker']=='load' else 0;_fields(z,dict(s,type='round',result_bits=s['test_bits'],status_raw=0,architectural_marker=a,probe_word=MARKER,code_base=addresses[0],code_matches_plan=True),'cache marker schedule/original result');_require(type(z.get('ticks'))is int and 0<=z['ticks']<1<<64,'cache marker typed ticks')
 return dict(condition=c['name'],args=c['args'],config=rr[0],programs=rr[1:3],runtime=runtime,samples=rr[4:-1],final=final,status='complete')
def quantile(v,q):
 v=sorted(v);x=q*(len(v)-1);i=int(x);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(x-i)
def analyze(run):
 _fields(run,dict(mode=MODE,phase='qualification',processes=6),'cache marker matrix');cc=conditions('qualification');rows=run.get('rows');_require(type(rows)is list and len(rows)==6,'cache marker process coverage');out=[]
 for row,c in zip(rows,cc):
  _fields(row,dict(condition=c['name'],args=c['args'],status='complete'),'cache marker identity');_audit_records([row['config'],*row['programs'],row['runtime'],*row['samples'],row['final']],c);cells={}
  for z in row['samples']:cells.setdefault((z['control'],z['marker']),[]).append(z['ticks'])
  hot=quantile(cells['cal-hot','none'],.9);cold=quantile(cells['cal-cold','none'],.1);threshold=(hot+cold)/2;rates={a+'/'+b:sum(t<=threshold for t in ticks)/32 for (a,b),ticks in cells.items()};g=dict(calibration_separation=cold-hot>=2,hot_positive=rates['cal-hot/none']>=.9,cold_negative=rates['cal-cold/none']<=.1,architectural_positive=rates['architect/load']>=.9,architectural_nop_negative=rates['architect/nop']<=.1,bypass_nop_negative=rates['bypass/nop']<=.1,bypass_load_negative=rates['bypass/load']<=.1,speculative_positive=rates['speculate/load']>=.9,speculative_nop_negative=rates['speculate/nop']<=.1);out.append(dict(process=c['name'],chain=row['config']['chain'],clock='cntvct_el0',cntfrq=row['runtime']['cntfrq'],hot_q90=hot,cold_q10=cold,threshold_ticks=threshold,ticks={a+'/'+b:v for (a,b),v in cells.items()},hit_rates=rates,gates=g,qualified=all(g.values()),calibration_status='resolved' if cold-hot>=2 else 'TIMER_OR_CACHE_UNRESOLVED'))
 return dict(mode=MODE,windows=1536,status='CACHE_SPECULATIVE_MARKER_QUALIFIED' if all(v['qualified'] for v in out) else 'CACHE_MARKER_NOT_QUALIFIED',processes=out,physical_capacity_certified=False,allocation_units_certified=False,naming_limit='own wrong-path footprint with original architectural marker; not physical ROB size/unit')

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
 _require(build['binaries']['rob_cache_marker']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'marker binary/source/plan binding')
 for file,digest in build['source_sha256'].items():_require(sha(blob(head,file))==digest and sha(blob(m['binary_source_head'],file))==digest,'marker source dependency '+file)
 _require(m.get('qualification_input') is None,'marker cannot borrow earlier qualification')
 with tempfile.TemporaryDirectory() as td0:
  td=Path(td0)
  for file in ('probes/diagnostic/rob_cache_marker.c',):
   target=td/file;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob(m['binary_source_head'],file))
  host=td/'producer';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(td/'probes/common'),str(td/'probes/diagnostic/rob_cache_marker.c'),'-o',str(host)],check=True,capture_output=True)
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
