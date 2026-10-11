#!/usr/bin/env python3
"""Same-code-VA signed dependency contrasts, with N0 and NONE control gates.

Contract: docs/design/2026-10-11-rob-same-address-pair.md. Complete real
program/schedule/raw coverage precedes statistics; no physical ROB allocation.
"""
import argparse,hashlib,json,statistics as st,subprocess,sys,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
from tools.diagnostic.rob_dependency_analysis import expected_code
MODE='rob-same-address-pair';PROTOCOL='docs/design/2026-10-11-rob-same-address-pair.md';BUILD='docs/reviews/evidence/2026-10-11-rob-same-address-pair/build.json';PLAN='docs/reviews/evidence/2026-10-11-rob-same-address-pair/plan.json';DRIVER='tools/diagnostic/run_sm8650_rob_pair.py'
EVENTS=(17,8,58,59,33133,35);VARIANTS=('i0','d0','i128','d128');ITERATIONS=131072

def conditions():return [dict(name=f'e{e}-{a}-k{k}',args=['--run','--anchor',a,'--chain',str(k),*(['--reverse'] if e%2 else [])]) for e in range(5) for a,k in [('none',16),('fsqrt',8),('fsqrt',16)]]
def identity(c):
 args=c['args'];return args[2],int(args[4]),'--reverse' in args

def expected(a,k,rev):
 cfg=dict(type='config',version=1,probe=MODE,**{'class':'add'},anchor=a,chain=k,iterations=ITERATIONS,warmup_iterations=ITERATIONS,blocks=8,windows=32,reverse=rev,events=list(EVENTS),pmu_type=8,loop_mod64=0);pp=[]
 for v in VARIANTS:
  n=int(v[1:]);link='dependent' if v[0]=='d' else 'independent';data=expected_code({'args':['--anchor-link',link,'-a',a,'--chain',str(k),'-n',str(n)]});words=list(struct.unpack('<'+'I'*(len(data)//4),data));loop=2*n+(2*k if a=='fsqrt' else 0)+4;pp.append(dict(type='program',variant=v,n=n,link=link,loop_offset=64,branch_offset=4*(16+loop-1),loop_instructions=loop,prologue_instructions=16,code_bytes=len(data),words=words))
 schedule=[dict(type='schedule',block=b,slot=s,variant=v) for b in range(8) for s,v in enumerate(VARIANTS if b%2==0 else reversed(VARIANTS))]
 if rev:schedule.reverse()
 return [cfg,*pp,*[dict(s,position=i) for i,s in enumerate(schedule)]]
def validate_plan(value):_require(_same(value,{f'{a}-{k}-{int(rev)}':expected(a,k,rev) for a,k in [('none',16),('fsqrt',8),('fsqrt',16)] for rev in (False,True)}),'pair actual registered plan mismatch')

def audit_process(records,c,registered):
 """Exact bytes, execution identity, schedule, PMU IDs and retired IR, typed."""
 validate_plan(registered);a,k,rev=identity(c);want=expected(a,k,rev);_require(type(records) is list and len(records)==38,'pair raw window coverage');_require(_same(records[:5],want[:5]),'pair config/program words mismatch');runtime=records[5];_fields(runtime,dict(type='runtime',cpu=7,fpcr=0),'pair runtime CPU/FPCR');base=runtime.get('code_base');ids=runtime.get('event_ids');_require(type(base) is int and base>0 and base%4096==0,'pair code base');_require(type(ids) is list and len(ids)==6 and all(type(x) is int and 0<x<2**64 for x in ids) and len(set(ids))==6,'pair unique kernel IDs');by={p['variant']:p for p in want[1:5]}
 for r,s in zip(records[6:],want[5:]):
  _fields(r,dict(s,type='round',code_base=base,code_matches_plan=True),'pair sample schedule/code VA');_require(all(type(r.get(n)) is int and 0<r[n]<2**64 for n in ('ns','enabled','running')) and r['enabled']==r['running'],'pair timing/mux');counts=r.get('counts');_require(type(counts) is list and len(counts)==6 and all(type(x) is int and 0<=x<2**64 for x in counts) and counts[0]>0,'pair uint64 count coverage');p=by[s['variant']];ir=ITERATIONS*p['loop_instructions']+p['prologue_instructions']+1;_require(abs(counts[1]-ir)<=max(1000,.01*ir),'pair retired instruction mismatch')
 return dict(condition=c['name'],args=c['args'],config=records[0],programs=records[1:5],runtime=runtime,samples=records[6:])

def analyze(run):
 """Re-audit all value flow, then signed block arithmetic and frozen gates."""
 _fields(run,dict(mode=MODE,processes=15),'pair run identity');rows=run.get('rows');_require(type(rows) is list and len(rows)==15,'pair matrix coverage');registered={f'{a}-{k}-{int(rev)}':expected(a,k,rev) for a,k in [('none',16),('fsqrt',8),('fsqrt',16)] for rev in (False,True)};points=[];blocks=[];sentinels=[];index={};fractions=[]
 for r,c in zip(rows,conditions()):
  _fields(r,dict(condition=c['name'],args=c['args']),'pair output identity/order');audit_process([r['config'],*r['programs'],r['runtime'],*r['samples']],c,registered);a,k,rev=identity(c);e=int(c['name'][1]);by={(s['block'],s['variant']):s for s in r['samples']};E=[]
  for v in VARIANTS:
   ss=[by[b,v] for b in range(8)];values=[s['counts'][0]/ITERATIONS for s in ss];points.append(dict(epoch=e,anchor=a,chain=k,variant=v,cycles=values,cycle_median=st.median(values),cycle_range_fraction=(max(values)-min(values))/st.median(values)))
  for b in range(8):
   counts={v:by[b,v]['counts'] for v in VARIANTS};cv={v:vcount[0]/ITERATIONS for v,vcount in counts.items()};t=(cv['d128']-cv['d0'])-(cv['i128']-cv['i0']);ev=cv['d0']-cv['i0'];E.append(ev);index[e,a,k,b]=t;blocks.append(dict(epoch=e,anchor=a,chain=k,block=b,cycles=cv,T=t,E=ev))
   for v in VARIANTS:
    s=by[b,v];fractions.append(dict(epoch=e,anchor=a,chain=k,block=b,variant=v,cycles_per_iter=cv[v],counts=counts[v],ns=s['ns'],cycles_per_ns=counts[v][0]/s['ns'],**{hex(event):counts[v][j]/counts[v][0] for j,event in enumerate(EVENTS) if j>=2}))
  med=st.median(E);spread=max(E)-min(E);sentinels.append(dict(condition=c['name'],E=E,median=med,range=spread,passed=abs(med)<=1 and spread<=2))
 none=[index[e,'none',16,b] for e in range(5) for b in range(8)];negative=dict(T=none,median=st.median(none),range=max(none)-min(none));negative['passed']=abs(negative['median'])<=5 and negative['range']<=5;contrasts=[dict(epoch=e,chain=k,block=b,D=index[e,'fsqrt',k,b]-index[e,'none',16,b],passed=index[e,'fsqrt',k,b]-index[e,'none',16,b]>5) for e in range(5) for k in (8,16) for b in range(8)];good=all(g['passed'] for g in sentinels) and negative['passed'] and all(g['passed'] for g in contrasts);semantics={event:'cycle-semantics-incompatible' if any(f[event]>1 for f in fractions) else 'observed-event-response-not-structure-certification' for event in ('0x816d','0x23')}
 return dict(mode=MODE,windows=480,verdict='paired-dependency-associated-response' if good else 'not-qualified',sentinel_gates=sentinels,negative_control=negative,contrasts=contrasts,blocks=blocks,points=points,window_ratios=fractions,cycle_semantics=semantics,physical_entries_certified=False,naming_limit='same-code-VA equal-value dependency contrast, not physical ROB/PRF/scheduler entries')

def audit_raw(path):
 """Whole inventory and exact committed source/build/launch/env/raw binding."""
 inventory={'manifest.json','driver.py','environment-policy.json','initial-environment.json','final-environment.json'}|{c['name']+s for c in conditions() for s in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')};_require({p.name for p in path.iterdir()}==inventory and all(p.is_file() for p in path.iterdir()),'pair raw inventory');m=json.loads((path/'manifest.json').read_text());_fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,protocol_path=PROTOCOL,plan_path=PLAN),'pair manifest identity');_require(_same(m.get('conditions'),conditions()) and type(m.get('results')) is list and len(m['results'])==15,'pair requested/result coverage');blob=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for file,key in ((DRIVER,'driver_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,file))==m[key],'pair launch SHA '+file)
 _require(sha((path/'driver.py').read_bytes())==m['driver_sha256'],'pair saved driver');build=json.loads(blob(head,BUILD));registered=json.loads(blob(head,PLAN));validate_plan(registered);_require(build['binaries']['rob_dependency_pair']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'pair binary/source/plan binding')
 for p,digest in build['source_sha256'].items():_require(sha(blob(head,p))==digest and sha(blob(m['binary_source_head'],p))==digest,'pair dependency SHA '+p)
 from tools.diagnostic.analyze_long_load import audit_environment
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt';env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy);rows=[]
 for r,c in zip(m['results'],conditions()):
  _fields(r,dict(name=c['name'],exit_code=0,timed_out=False),'pair result order/status');f=path/(c['name']+'.stdout.jsonl');_require(sha(f.read_bytes())==r['stdout_sha256'] and (path/(c['name']+'.stderr.log')).read_bytes()==b'','pair stdout/stderr binding');rows.append(audit_process([json.loads(l) for l in f.read_text().splitlines()],c,registered))
 return dict(mode=MODE,processes=15,source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],raw_directory=path.name,manifest_sha256=sha((path/'manifest.json').read_bytes()),max_cpu_c_range=[min(v['snapshot']['thermal']['max_cpu_c'] for v in env.values()),max(v['snapshot']['thermal']['max_cpu_c'] for v in env.values())],rows=rows),{p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())}
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--summary-output',type=Path,required=True);a=p.parse_args(argv);run,hashes=audit_raw(a.raw);result=analyze(run);s=json.dumps(run,indent=2,allow_nan=False)+'\n';result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes);a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(windows=result['windows'],verdict=result['verdict'],sentinel_passed=sum(g['passed'] for g in result['sentinel_gates']),none_passed=result['negative_control']['passed'],D_passed=sum(g['passed'] for g in result['contrasts']))))
if __name__=='__main__':main()
