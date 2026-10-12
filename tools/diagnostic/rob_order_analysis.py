"""Paired anchor register order; frozen median contrasts, never a physical ROB estimate.

Contract docs/design/2026-10-13-rob-anchor-order.md; actual source and typed
complete windows/PFN identity must qualify before statistics.
"""
import copy,hashlib,json,statistics as st,subprocess,tempfile
from pathlib import Path
from tools.diagnostic.rob_drain_analysis import expected as drain_expected
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
ROOT=Path(__file__).resolve().parents[2]
MODE='rob-anchor-order';ITERATIONS=262144
PROTOCOL='docs/design/2026-10-13-rob-anchor-order.md'
BUILD='docs/reviews/evidence/2026-10-13-rob-anchor-order/build.json'
PLAN='docs/reviews/evidence/2026-10-13-rob-anchor-order/plan.json'
DRIVER='tools/diagnostic/run_sm8650_rob_order.py';CONSUMER='tools/diagnostic/rob_order_analysis.py'
EVENTS=(17,8,58,33133,35,1);PFN_MASK=(1<<55)-1

def conditions(phase):
 _require(phase=='qualification','order only frozen finite contrast; scan forbidden');spec=[(k,s) for k in (16,32) for s in (False,True)]
 return [dict(name=f'e{e}-k{k}-{("swapped" if s else "normal")}',args=['--run','--chain',str(k),'--slots','swapped' if s else 'normal',*(['--reverse'] if e%2 else [])]) for e in range(3) for k,s in (spec if e%2==0 else list(reversed(spec)))]
def identity(c):a=c['args'];return int(a[2]),a[4]=='swapped','--reverse' in a
def plan_key(k,s,v):return f'k{k}-s{int(s)}-r{int(v)}'
def expected(k,s,v):
 cfg=dict(type='config',version=1,probe=MODE,chain=k,slots='swapped' if s else 'normal',reverse=v,iterations=ITERATIONS,warmup_iterations=ITERATIONS,trials=8,windows=64,trial_sleep_s=3,drain='fpsr',events=list(EVENTS),pmu_type=8)
 pp=[]
 for i in range(8):
  anchor='serial' if i//2==1 else 'independent' if i//2==2 else 'none';g=64 if i//2==3 else 0;p=copy.deepcopy(drain_expected(anchor,'fpsr',g,k,False)[1]);p.update(condition=i,page=i//2,slot=2048*((i%2)^s))
  if i==5:p['words'][16:16+2*k]=[0x1e61c000,0x1e61c021]*k
  pp.append(p)
 return [cfg,*pp,*[dict(type='schedule',trial=t,position=pos,condition=7-(t+pos)%8 if v else (t+pos)%8) for t in range(8) for pos in range(8)]]
def plans():return {plan_key(k,s,v):expected(k,s,v) for k in (16,32) for s in (False,True) for v in (False,True)}
def validate_plan(p):_require(_same(p,plans()),'order actual registered plan mismatch')
def audit_process(rr,c,registered):validate_plan(registered);return _audit_records(rr,c)
def _audit_records(rr,c):
 k,s,v=identity(c);want=expected(k,s,v);_require(type(rr)is list and len(rr)==75,'order window coverage');_require(_same(rr[:9],want[:9]),'order config/program mismatch')
 runtime=rr[9];_fields(runtime,dict(type='runtime',cpu=7,fpcr=0),'order runtime');base=runtime.get('code_base');ids=runtime.get('event_ids');_require(type(base)is int and base>0 and base%4096==0,'order code base');_require(type(ids)is list and len(ids)==6 and all(type(x)is int and 0<x<1<<64 for x in ids) and len(set(ids))==6,'order event IDs')
 final=rr[-1];_fields(final,dict(type='code-final',code_base=base),'order final')
 def pfns(values):
  _require(type(values)is list and len(values)==4 and all(type(x)is int and 0<=x<1<<64 and x>>63 and not(x&(1<<62)) and x&PFN_MASK for x in values),'order code pagemap');return [x&PFN_MASK for x in values]
 before=pfns(runtime.get('code_pagemap_before'));after=pfns(final.get('code_pagemap_after'));_require(len(set(before))==4 and before==after,'order code PFN uniqueness/migration')
 for z,schedule in zip(rr[10:-1],want[9:]):
  i=schedule['condition'];program=want[1+i];_fields(z,dict(schedule,type='round',code_address=base+program['page']*4096+program['slot'],code_matches_plan=True,result_bits=[0x3ff0000000000000]*2,status_raw=0,gpr_result=0),'order schedule/code/result')
  _require(all(type(z.get(n))is int and 0<z[n]<1<<64 for n in ('ns','enabled','running')) and z['enabled']==z['running'],'order time/mux');counts=z.get('counts');_require(type(counts)is list and len(counts)==6 and all(type(x)is int and 0<=x<1<<64 for x in counts) and counts[0]>0,'order counts');ir=ITERATIONS*program['loop_instructions']+21;_require(abs(counts[1]-ir)<=max(1000,.01*ir),'order IR')
 return dict(condition=c['name'],args=c['args'],config=rr[0],programs=rr[1:9],runtime=runtime,samples=rr[10:-1],final=final)

def classify_contrast(items):
 med=[x['did_median'] for x in items];values=[v for x in items for v in x['did']]
 if all(v>=10 for v in med) and all(v>0 for v in values):return 'BLOCKED_ANCHOR_ORDER_DELAY'
 if all(v<=-10 for v in med) and all(v<0 for v in values):return 'INTERLEAVED_ANCHOR_ORDER_DELAY'
 if all(abs(v)<=2 for v in med):return 'ORDER_CONTRAST_NOT_CHANGED_AT_REGISTERED_MEDIAN_SCALE'
 return 'INCONCLUSIVE'
def analyze(run):
 _fields(run,dict(mode=MODE,phase='qualification',processes=12),'order matrix');cc=conditions(run.get('phase'));rows=run.get('rows');_require(type(rows)is list and len(rows)==12,'order process coverage');items=[]
 for row,c in zip(rows,cc):
  _fields(row,dict(condition=c['name'],args=c['args']),'order process identity/order');_audit_records([row['config'],*row['programs'],row['runtime'],*row['samples'],row['final']],c);k,slot,rev=identity(c);values={(z['trial'],z['condition']):z['counts'][0]/ITERATIONS for z in row['samples']};points=[]
  for i in range(8):
   vv=[values[t,i] for t in range(8)];ic=[z['counts'][5]/ITERATIONS for z in row['samples'] if z['condition']==i];spread=(max(vv)-min(vv))/st.median(vv);points.append(dict(condition=i,cycles=vv,median=st.median(vv),range_fraction=spread,stable=spread<=.05,icache_per_iter=ic,background_passed=max(ic)<=.001))
  negative={str(i):[values[t,i]-values[t,i+1] for t in range(8)] for i in (0,2,6)};di=[values[t,4]-values[t,5] for t in range(8)];ds=negative['2'];did=[a-b for a,b in zip(di,ds)]
  gates=dict(stability=all(x['stable'] for x in points),icache_background=all(x['background_passed'] for x in points),negative_medians=all(abs(st.median(x))<=1 for x in negative.values()),negative_windows=all(abs(v)<=2 for x in negative.values() for v in x),overlap=all(max(points[i]['cycles'])/min(points[i-2]['cycles'])<=.70 for i in (4,5)),none64_supply=all(max(points[i+2]['cycles'])/min(points[i]['cycles'])<=.80 for i in (4,5)))
  items.append(dict(process=c['name'],chain=k,slots='swapped' if slot else 'normal',reverse=rev,points=points,negative_deltas=negative,independent_delta=di,serial_delta=ds,did=did,did_median=st.median(did),gates=gates,qualified=all(gates.values())))
 qualified=all(x['qualified'] for x in items);main=classify_contrast([x for x in items if x['chain']==32]) if qualified else 'CONTROL_NOT_QUALIFIED';aux=classify_contrast([x for x in items if x['chain']==16]) if qualified else 'CONTROL_NOT_QUALIFIED'
 return dict(mode=MODE,windows=768,status=main,chain16_auxiliary=aux,qualified=qualified,processes=items,physical_entries_certified=False,allocation_units_certified=False,naming_limit='register schedule contribution at registered median scale; not scheduler/PRF/ROB identification')

def audit_raw(path):
 """Launch/source/build/environment and complete raw inventory, never patched input."""
 phase=json.loads((path/'manifest.json').read_text()).get('phase');cc=conditions(phase)
 inventory={'manifest.json','driver.py','consumer.py','environment-policy.json','initial-environment.json','final-environment.json'}|{c['name']+suffix for c in conditions(phase) for suffix in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')}
 _require({p.name for p in path.iterdir()}==inventory and all(p.is_file() for p in path.iterdir()),'order raw inventory')
 m=json.loads((path/'manifest.json').read_text());phase=m.get('phase');cc=conditions(phase);_fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,protocol_path=PROTOCOL,plan_path=PLAN,consumer_path=CONSUMER),'order manifest identity')
 _require(_same(m.get('conditions'),cc) and type(m.get('results')) is list and len(m['results'])==len(cc),'order requested/result coverage')
 blob=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for file,key in ((DRIVER,'driver_sha256'),(CONSUMER,'consumer_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,file))==m[key],'order launch SHA '+file)
 for saved,key in (('driver.py','driver_sha256'),('consumer.py','consumer_sha256')):_require(sha((path/saved).read_bytes())==m[key],'order saved '+saved)
 build=json.loads(blob(head,BUILD));registered=json.loads(blob(head,PLAN));validate_plan(registered)
 _require(build['binaries']['rob_anchor_order']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'order binary/source/plan binding')
 for file,digest in build['source_sha256'].items():_require(sha(blob(head,file))==digest and sha(blob(m['binary_source_head'],file))==digest,'order source dependency '+file)
 _require(m.get('qualification_input') is None,'order cannot borrow earlier qualification')
 with tempfile.TemporaryDirectory() as td0:
  td=Path(td0)
  for file in ('probes/diagnostic/rob_anchor_order.c','probes/common/rob_codegen.h','probes/common/perf_group_read.h'):
   target=td/file;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob(m['binary_source_head'],file))
  host=td/'producer';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(td/'probes/common'),str(td/'probes/diagnostic/rob_anchor_order.c'),'-o',str(host)],check=True,capture_output=True)
  for k in (16,32):
   for swapped in (False,True):
    for reverse in (False,True):
     args=['--plan','--chain',str(k),'--slots','swapped' if swapped else 'normal',*(['--reverse'] if reverse else [])];actual=[json.loads(l) for l in subprocess.check_output([str(host),*args],text=True).splitlines()];_require(_same(actual,registered[plan_key(k,swapped,reverse)]),'order immutable producer plan mismatch')
 from tools.diagnostic.analyze_long_load import audit_environment
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt'
 env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy)
 rows=[]
 for r,c in zip(m['results'],conditions(phase)):
  _fields(r,dict(name=c['name'],exit_code=0,timed_out=False),'order result identity/status');f=path/(c['name']+'.stdout.jsonl')
  _require(sha(f.read_bytes())==r['stdout_sha256'] and (path/(c['name']+'.stderr.log')).read_bytes()==b'','order stdout/stderr')
  rows.append(_audit_records([json.loads(l) for l in f.read_text().splitlines()],c))
 return dict(mode=MODE,phase=phase,processes=len(cc),source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],raw_directory=path.name,manifest_sha256=sha((path/'manifest.json').read_bytes()),max_cpu_c_range=[min(v['snapshot']['thermal']['max_cpu_c'] for v in env.values()),max(v['snapshot']['thermal']['max_cpu_c'] for v in env.values())],rows=rows),{p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())}
